"""
Tests del CLI `lfs-insim` (Fase 4 — DX).

Los antiguos entry points sueltos `generate-stubs` y `update-all` se
instalaban como comandos GLOBALES en el PATH de quien hiciera `pip install`
(nombres genéricos que invaden el entorno ajeno). Fase 4 los pliega en
subcomandos de `lfs-insim` (`lfs-insim stubs`, `lfs-insim update-all`) y los
quita de `[project.scripts]`, dejando `lfs-insim` como el único console-script.
"""
from pathlib import Path

import pytest

from lfs_insim import cli


class TestSubcomandosGeneradores:
    """`stubs` y `update-all` existen como subcomandos y despachan al
    `main()` del módulo correspondiente (mismo comportamiento que tenían
    los console-scripts: llamar a `main()` y devolver 0)."""

    def test_stubs_despacha_a_generate_stubs(self, monkeypatch):
        llamado = {"n": 0}

        def fake_main():
            llamado["n"] += 1

        monkeypatch.setattr("lfs_insim.generate_stubs.main", fake_main)
        rc = cli.main(["stubs"])
        assert rc == 0
        assert llamado["n"] == 1

    def test_update_all_despacha_a_update_all(self, monkeypatch):
        llamado = {"n": 0}

        def fake_main():
            llamado["n"] += 1

        monkeypatch.setattr("lfs_insim.update_all.main", fake_main)
        rc = cli.main(["update-all"])
        assert rc == 0
        assert llamado["n"] == 1


class TestScriptsNoContaminanElPath:
    """El único console-script declarado es `lfs-insim`; los generadores ya
    NO se exponen como comandos globales (motivo del ítem, Fase 4)."""

    def _scripts(self):
        tomllib = pytest.importorskip("tomllib")
        root = Path(__file__).resolve().parents[1]
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        return data.get("project", {}).get("scripts", {})

    def test_solo_lfs_insim_es_console_script(self):
        assert set(self._scripts()) == {"lfs-insim"}

    def test_generadores_no_son_console_scripts(self):
        scripts = self._scripts()
        assert "generate-stubs" not in scripts
        assert "update-all" not in scripts
