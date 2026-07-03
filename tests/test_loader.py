"""
Tests del InSimLoader (Fase 2, arquitectura de composición — P11).

Cubre: carga simple, resolución recursiva de dependencias, registro de las
apps en el cliente único del loader (en orden de dependencias: primero las
dependencias, después el dependiente), caché de instancias, fallos (módulo
inexistente, entry point ausente, sin clase InSimApp, versión insuficiente)
y el tragado de errores de dependencias (P20 en DIAGNOSTICO.md, fail-fast
pendiente).

Los InSims de prueba se generan en tmp_path (insim.json + app.py mínimo),
sin conexión a LFS: instanciar un InSimApp no abre sockets ni toca el
estado global (ya no existe el "coup d'état": el único cliente lo crea el
loader de forma perezosa).
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
    f = _FabricaInsims(tmp_path / "insims")
    yield f
    # Limpiar sys.modules (el loader registra name y name.<entry> globalmente)
    for name in f.creados:
        for key in [k for k in sys.modules if k == name or k.startswith(f"{name}.")]:
            del sys.modules[key]
    state.reset_insim_client()


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
        assert loader.client.apps == [instancia]      # registrada en el cliente
        assert instancia.client is loader.client      # y con el cliente asignado

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
        assert loader.client.apps == [primera]        # registrada una sola vez

    def test_discover_lista_los_insims(self, fabrica):
        fabrica.crear("mod_uno")
        fabrica.crear("mod_dos")
        loader = _loader(fabrica)

        assert sorted(loader.discover()) == ["mod_dos", "mod_uno"]

    def test_discover_sin_directorio_devuelve_vacio(self, tmp_path):
        loader = InSimLoader(insims_path=tmp_path / "no_existe")
        assert loader.discover() == []


class TestConfigDelLoader:
    """P14: el loader propaga la config al cliente perezoso y a las apps."""

    def test_config_llega_al_cliente_perezoso(self, fabrica):
        loader = InSimLoader(insims_path=fabrica.insims_dir,
                             config={'prefix': '$', 'tcp_port': 12345})

        assert loader.client.config['prefix'] == '$'
        assert loader.client.config['tcp_port'] == 12345
        assert loader.client.config['insim_ver'] == 10   # defaults intactos

    def test_apps_heredan_la_config_del_cliente(self, fabrica):
        fabrica.crear("con_config")
        loader = InSimLoader(insims_path=fabrica.insims_dir,
                             config={'prefix': '$'})

        app = loader.load("con_config")

        assert app.config['prefix'] == '$'

    def test_cliente_inyectado_manda_sobre_la_config_del_loader(self, fabrica):
        from lfs_insim.insim_client import InSimClient

        fabrica.crear("con_cliente")
        mi_cliente = InSimClient(config={'prefix': '&'})
        loader = InSimLoader(insims_path=fabrica.insims_dir,
                             client=mi_cliente, config={'prefix': '$'})

        app = loader.load("con_cliente")

        # Con cliente inyectado, la config del loader se ignora (documentado):
        # las apps heredan la config efectiva del cliente.
        assert app.config['prefix'] == '&'


class TestRegistroEnCliente:
    """P11: un solo cliente; las apps se registran en orden de dependencias."""

    def test_cliente_unico_y_perezoso(self, fabrica):
        fabrica.crear("cualquiera")
        loader = _loader(fabrica)

        cliente = loader.client            # se crea en el primer acceso
        loader.load("cualquiera")

        assert loader.client is cliente    # y es siempre el mismo
        assert state.get_insim_client() is cliente   # registrado como global

    def test_se_puede_inyectar_un_cliente_propio(self, fabrica):
        from lfs_insim.insim_client import InSimClient

        fabrica.crear("inyectado")
        mi_cliente = InSimClient(config={})
        loader = InSimLoader(insims_path=fabrica.insims_dir, client=mi_cliente)

        app = loader.load("inyectado")

        assert loader.client is mi_cliente
        assert mi_cliente.apps == [app]

    def test_dependencia_se_registra_antes_que_el_dependiente(self, fabrica):
        fabrica.crear("dep_base")
        fabrica.crear("principal", deps={"dep_base": ">=1.0.0"})
        loader = _loader(fabrica)

        principal = loader.load("principal")
        dep = loader._instances["dep_base"]

        # Orden de dispatch = orden de registro: la dependencia procesa
        # los paquetes ANTES que quien consume su estado.
        assert loader.client.apps == [dep, principal]

    def test_cadena_de_tres_en_orden_de_dependencias(self, fabrica):
        # nivel2 depende de nivel1, que depende de nivel0
        fabrica.crear("nivel0")
        fabrica.crear("nivel1", deps={"nivel0": ">=1.0.0"})
        fabrica.crear("nivel2", deps={"nivel1": ">=1.0.0"})
        loader = _loader(fabrica)

        n2 = loader.load("nivel2")
        n1 = loader._instances["nivel1"]
        n0 = loader._instances["nivel0"]

        assert loader.client.apps == [n0, n1, n2]

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
        with pytest.raises(InSimModuleError, match="InSim not found"):
            loader.load("fantasma")

    def test_entry_point_ausente(self, fabrica):
        d = fabrica.crear("sin_entry")
        (d / "app.py").unlink()
        loader = _loader(fabrica)

        with pytest.raises(InSimModuleError, match="Entry point file not found"):
            loader.load("sin_entry")

    def test_sin_init_py_falla(self, fabrica):
        # Comportamiento actual: si el paquete no tiene __init__.py y el entry
        # point es otro archivo, spec_from_file_location(name, None) devuelve
        # None y la carga falla con "Error loading module" (mensaje críptico:
        # 'NoneType' object has no attribute 'loader').
        d = fabrica.crear("sin_init")
        (d / "__init__.py").unlink()
        loader = _loader(fabrica)

        with pytest.raises(InSimModuleError, match="Error loading module sin_init"):
            loader.load("sin_init")

    def test_sin_clase_insimapp(self, fabrica):
        # El error interno se re-envuelve como "Error loading module ..."
        fabrica.crear("sin_clase", codigo="x = 42\n")
        loader = _loader(fabrica)

        with pytest.raises(InSimModuleError, match="Error loading module sin_clase"):
            loader.load("sin_clase")

    def test_un_fallo_no_ensucia_el_cliente(self, fabrica):
        # Si una carga falla, el cliente conserva solo las apps ya registradas
        fabrica.crear("estable")
        fabrica.crear("roto", codigo="x = 42\n")
        loader = _loader(fabrica)

        estable = loader.load("estable")
        with pytest.raises(InSimModuleError):
            loader.load("roto")

        assert loader.client.apps == [estable]
        assert "roto" not in loader._instances

    def test_version_insuficiente(self, fabrica):
        fabrica.crear("dep_vieja", version="1.0.0")
        fabrica.crear("exigente", deps={"dep_vieja": ">=2.0.0"})
        loader = _loader(fabrica)

        with pytest.raises(InSimModuleError, match="requires 'dep_vieja>=2.0.0'"):
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
