"""
Tests de la API pública (Fase 2 — P15).

La superficie pública queda definida por __all__ en cada módulo:
`lfs_insim` (core), `lfs_insim.packets` (paquetes), `lfs_insim.insim_enums`
(enums) y `lfs_insim.utils` (helpers). La facade `insim_packet_class` queda
deprecada pero funcional (re-exporta packets + enums, como el monolito
original).
"""

import importlib
import sys
import warnings

import pytest


def _all_resuelve(mod):
    return [n for n in mod.__all__ if not hasattr(mod, n)]


class TestAllPorModulo:
    @pytest.mark.parametrize(
        "modulo",
        [
            "lfs_insim",
            "lfs_insim.packets",
            "lfs_insim.packets.base",
            "lfs_insim.packets.structures",
            "lfs_insim.packets.insim",
            "lfs_insim.packets.outsim",
            "lfs_insim.packets.maps",
            "lfs_insim.insim_enums",
            "lfs_insim.utils",
            "lfs_insim.exceptions",
            "lfs_insim.config",
        ],
    )
    def test_todo_nombre_de_all_existe(self, modulo):
        mod = importlib.import_module(modulo)
        assert hasattr(mod, "__all__"), f"{modulo} no define __all__"
        assert _all_resuelve(mod) == []

    def test_all_sin_duplicados(self):
        import lfs_insim.packets as p
        import lfs_insim.insim_enums as e

        assert len(p.__all__) == len(set(p.__all__))
        assert len(e.__all__) == len(set(e.__all__))


class TestSinFugas:
    """El import * queda acotado: cada módulo exporta solo lo suyo."""

    def test_packets_no_reexporta_enums(self):
        import lfs_insim.packets as p

        assert "ISF" not in p.__all__
        assert "TINY" not in p.__all__

    def test_enums_no_reexporta_la_stdlib(self):
        import lfs_insim.insim_enums as e

        assert "IntEnum" not in e.__all__
        assert "IntFlag" not in e.__all__

    def test_import_estrella_de_packets_no_trae_enums(self):
        ns = {}
        exec("from lfs_insim.packets import *", ns)
        assert "ISP_MSO" in ns
        assert "CompCar" in ns
        assert "ISF" not in ns


class TestFacadeDeprecada:
    """insim_packet_class: deprecada pero compatible (P15)."""

    def _importar_facade(self):
        # Forzar la re-ejecución del módulo para capturar su warning
        sys.modules.pop("lfs_insim.insim_packet_class", None)
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            import lfs_insim.insim_packet_class as facade
        return facade, ws

    def test_emite_deprecation_warning(self):
        _, ws = self._importar_facade()
        deprecaciones = [w for w in ws if issubclass(w.category, DeprecationWarning)]
        assert deprecaciones, "la facade no avisó de su deprecación"
        assert "lfs_insim.packets" in str(deprecaciones[0].message)

    def test_conserva_la_superficie_del_monolito(self):
        # El monolito original exponía paquetes Y enums juntos: el código
        # viejo (p. ej. ai_control) importa ambos desde aquí.
        facade, _ = self._importar_facade()
        assert hasattr(facade, "ISP_MSO")  # paquete
        assert hasattr(facade, "AIInputVal")  # estructura
        assert hasattr(facade, "SND")  # enum
        assert hasattr(facade, "ALLOWED_PACKETS")


class TestVersionUnica:
    """Fuente única de versión (Fase 4): `lfs_insim.__version__`.

    pyproject.toml la lee de aquí (`dynamic = ["version"]`), así que el
    número vive en UN solo sitio.
    """

    def test_version_definida_y_exportada(self):
        import re
        import lfs_insim

        assert re.fullmatch(
            r"\d+\.\d+\.\d+([abc.]|rc|dev|post|\d)*", lfs_insim.__version__
        ), f"__version__ no parece PEP 440: {lfs_insim.__version__!r}"
        assert "__version__" in lfs_insim.__all__

    def test_version_coincide_con_metadata_instalada(self):
        # Si falla tras un bump de versión, reinstala: pip install -e ".[dev]"
        from importlib.metadata import version
        import lfs_insim

        assert version("lfs-insim") == lfs_insim.__version__
