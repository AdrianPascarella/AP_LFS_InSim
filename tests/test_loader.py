"""
Tests de caracterización del InSimLoader (Fase 1).

Cubre: carga simple, resolución recursiva de dependencias, el "coup d'état"
actual (el último módulo cargado se convierte en Master, degrada al anterior
a módulo suyo y aplana la lista modules[]), caché de instancias, fallos
(módulo inexistente, entry point ausente, sin clase InSimApp, versión
insuficiente, rollback del master) y el tragado de errores de dependencias
(P20 en DIAGNOSTICO.md).

Los InSims de prueba se generan en tmp_path (insim.json + app.py mínimo),
sin conexión a LFS: instanciar un InSimApp no abre sockets.
"""
import json
import sys

import pytest

import lfs_insim.insim_state as state
from lfs_insim.exceptions import InSimModuleError
from lfs_insim.insim_loader import InSimLoader, _check_version, _parse_version

CODIGO_MINIMO = (
    "from lfs_insim import InSimApp\n"
    "\n"
    "class {clase}(InSimApp):\n"
    "    pass\n"
)


class _FabricaInsims:
    """Crea directorios de InSim sintéticos bajo un insims/ temporal."""

    def __init__(self, insims_dir):
        self.insims_dir = insims_dir
        self.creados = []

    def crear(self, name, *, version="1.0.0", deps=None, entry="app.py", codigo=None):
        d = self.insims_dir / name
        d.mkdir(parents=True)
        manifest = {
            "name": name,
            "version": version,
            "description": "insim sintético de test",
            "author": "test",
            "entry_point": entry,
            "insim_dependencies": deps or {},
            "python_dependencies": [],
        }
        (d / "insim.json").write_text(json.dumps(manifest), encoding="utf-8")
        if codigo is None:
            clase = "".join(p.capitalize() for p in name.split("_"))
            codigo = CODIGO_MINIMO.format(clase=clase)
        (d / entry).write_text(codigo, encoding="utf-8")
        # El loader EXIGE __init__.py cuando el entry point es otro archivo
        # (sin él, spec_from_file_location devuelve None y la carga revienta);
        # ver test_sin_init_py_falla.
        if entry != "__init__.py":
            (d / "__init__.py").write_text("", encoding="utf-8")
        self.creados.append(name)
        return d


@pytest.fixture
def fabrica(tmp_path):
    state.reset_insim_client()
    state.reset_sockets()
    f = _FabricaInsims(tmp_path / "insims")
    yield f
    # Limpiar sys.modules (el loader registra name y name.<entry> globalmente)
    for name in f.creados:
        for key in [k for k in sys.modules if k == name or k.startswith(f"{name}.")]:
            del sys.modules[key]
    state.reset_insim_client()
    state.reset_sockets()


def _loader(fabrica) -> InSimLoader:
    return InSimLoader(insims_path=fabrica.insims_dir)


class TestCargaBasica:

    def test_carga_simple(self, fabrica):
        fabrica.crear("solo_mod", version="2.1.0")
        loader = _loader(fabrica)

        instancia = loader.load("solo_mod")

        assert type(instancia).__name__ == "SoloMod"
        assert instancia.version == "2.1.0"          # leída del manifiesto
        assert loader._instances["solo_mod"] is instancia
        assert state.get_insim_client() is instancia  # es el Master

    def test_carga_con_entry_point_init(self, fabrica):
        fabrica.crear("init_mod", entry="__init__.py")
        loader = _loader(fabrica)

        instancia = loader.load("init_mod")

        assert type(instancia).__name__ == "InitMod"

    def test_cache_devuelve_la_misma_instancia(self, fabrica):
        fabrica.crear("cacheado")
        loader = _loader(fabrica)

        primera = loader.load("cacheado")
        segunda = loader.load("cacheado")

        assert primera is segunda

    def test_discover_lista_los_insims(self, fabrica):
        fabrica.crear("mod_uno")
        fabrica.crear("mod_dos")
        loader = _loader(fabrica)

        assert sorted(loader.discover()) == ["mod_dos", "mod_uno"]

    def test_discover_sin_directorio_devuelve_vacio(self, tmp_path):
        loader = InSimLoader(insims_path=tmp_path / "no_existe")
        assert loader.discover() == []


class TestCoupDEtat:
    """Caracteriza el patrón actual: el último cargado asume el rol de Master."""

    def test_dependencia_degradada_a_modulo(self, fabrica):
        fabrica.crear("dep_base")
        fabrica.crear("principal", deps={"dep_base": ">=1.0.0"})
        loader = _loader(fabrica)

        principal = loader.load("principal")
        dep = loader._instances["dep_base"]

        assert state.get_insim_client() is principal   # el dependiente manda
        assert principal.modules == [dep]              # la dependencia, súbdita
        assert dep.modules == []                       # y limpia de módulos

    def test_cadena_de_tres_se_aplana(self, fabrica):
        # nivel2 depende de nivel1, que depende de nivel0
        fabrica.crear("nivel0")
        fabrica.crear("nivel1", deps={"nivel0": ">=1.0.0"})
        fabrica.crear("nivel2", deps={"nivel1": ">=1.0.0"})
        loader = _loader(fabrica)

        n2 = loader.load("nivel2")
        n1 = loader._instances["nivel1"]
        n0 = loader._instances["nivel0"]

        assert state.get_insim_client() is n2
        # Aplanado: primero el master anterior (n1), luego sus módulos robados (n0)
        assert n2.modules == [n1, n0]
        assert n1.modules == []
        assert n0.modules == []

    def test_get_insim_resuelve_la_dependencia(self, fabrica):
        fabrica.crear("dep_util")
        fabrica.crear("consumidor", deps={"dep_util": ">=1.0.0"})
        loader = _loader(fabrica)

        consumidor = loader.load("consumidor")

        assert consumidor.get_insim("dep_util") is loader._instances["dep_util"]
        assert consumidor.get_insim("inexistente") is None


class TestFallosDeCarga:

    def test_modulo_inexistente(self, fabrica):
        loader = _loader(fabrica)
        with pytest.raises(InSimModuleError, match="No se encontró el InSim"):
            loader.load("fantasma")

    def test_entry_point_ausente(self, fabrica):
        d = fabrica.crear("sin_entry")
        (d / "app.py").unlink()
        loader = _loader(fabrica)

        with pytest.raises(InSimModuleError, match="Archivo de entrada no encontrado"):
            loader.load("sin_entry")

    def test_sin_init_py_falla(self, fabrica):
        # Comportamiento actual: si el paquete no tiene __init__.py y el entry
        # point es otro archivo, spec_from_file_location(name, None) devuelve
        # None y la carga falla con "Error cargando módulo" (mensaje críptico:
        # 'NoneType' object has no attribute 'loader').
        d = fabrica.crear("sin_init")
        (d / "__init__.py").unlink()
        loader = _loader(fabrica)

        with pytest.raises(InSimModuleError, match="Error cargando módulo sin_init"):
            loader.load("sin_init")

    def test_sin_clase_insimapp(self, fabrica):
        # El error interno se re-envuelve como "Error cargando módulo ..."
        fabrica.crear("sin_clase", codigo="x = 42\n")
        loader = _loader(fabrica)

        with pytest.raises(InSimModuleError, match="Error cargando módulo sin_clase"):
            loader.load("sin_clase")

    def test_rollback_del_master_tras_fallo(self, fabrica):
        # Si la carga falla, el master anterior recupera el trono
        fabrica.crear("estable")
        fabrica.crear("roto", codigo="x = 42\n")
        loader = _loader(fabrica)

        estable = loader.load("estable")
        with pytest.raises(InSimModuleError):
            loader.load("roto")

        assert state.get_insim_client() is estable
        assert "roto" not in loader._instances

    def test_version_insuficiente(self, fabrica):
        fabrica.crear("dep_vieja", version="1.0.0")
        fabrica.crear("exigente", deps={"dep_vieja": ">=2.0.0"})
        loader = _loader(fabrica)

        with pytest.raises(InSimModuleError, match="requiere 'dep_vieja>=2.0.0'"):
            loader.load("exigente")

    def test_p20_dependencia_rota_se_traga_y_sigue(self, fabrica):
        # Comportamiento actual (P20): si una dependencia no se puede cargar,
        # el loader lo loguea y CONTINÚA — el dependiente se carga igualmente
        # y el error real aflora después (get_insim devuelve None).
        fabrica.crear("optimista", deps={"dep_fantasma": ">=1.0.0"})
        loader = _loader(fabrica)

        instancia = loader.load("optimista")     # no lanza, pese a la dependencia rota

        assert type(instancia).__name__ == "Optimista"
        assert "dep_fantasma" not in loader._instances
        assert instancia.get_insim("dep_fantasma") is None


class TestVersionHelpers:

    @pytest.mark.parametrize("texto, esperado", [
        ("1.2.3", (1, 2, 3)),
        ("1.2", (1, 2, 0)),
        ("2", (2, 0, 0)),
        ("1.2.3-beta", (1, 2, 3)),   # el sufijo pre-release se descarta
        ("abc", (0, 0, 0)),          # texto no numérico → 0
    ])
    def test_parse_version(self, texto, esperado):
        assert _parse_version(texto) == esperado

    @pytest.mark.parametrize("actual, constraint, esperado", [
        ("1.2.3", ">=1.0.0", True),
        ("1.0.0", ">=2.0.0", False),
        ("1.2.3", "==1.2.3", True),
        ("1.2.3", "1.2.3", True),    # sin operador = igualdad exacta
        ("1.2.3", "!=1.2.3", False),
        ("2.0.0", "<3.0.0", True),
        ("3.0.0", "<=3.0.0", True),
        ("3.0.1", ">3.0.0", True),
        ("1.2.3", "", True),         # constraint vacío = siempre válido
    ])
    def test_check_version(self, actual, constraint, esperado):
        assert _check_version(actual, constraint) is esperado
