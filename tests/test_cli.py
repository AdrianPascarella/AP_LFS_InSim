"""
Tests del CLI `lfs-insim` (Fase 4 — DX).

Los antiguos entry points sueltos `generate-stubs` y `update-all` se
instalaban como comandos GLOBALES en el PATH de quien hiciera `pip install`
(nombres genéricos que invaden el entorno ajeno). Fase 4 los pliega en
subcomandos de `lfs-insim` (`lfs-insim stubs`, `lfs-insim update-all`) y los
quita de `[project.scripts]`, dejando `lfs-insim` como el único console-script.
"""

import json
import types
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


# ---------------------------------------------------------------------------
# W2 (Fase 6) — `lfs-insim init` con perfiles --minimal / --full
# ---------------------------------------------------------------------------


@pytest.fixture
def insims_dir(tmp_path, monkeypatch):
    """Redirige `lfs-insim init` a un directorio de insims temporal, para no
    escribir en el repo real."""
    insims = tmp_path / "insims"
    insims.mkdir()
    monkeypatch.setattr(
        cli, "get_loader", lambda: types.SimpleNamespace(insims_path=insims)
    )
    return insims


def _read_main(insims_dir: Path, name: str) -> str:
    return (insims_dir / name / "main.py").read_text(encoding="utf-8")


class TestInitPerfiles:
    """W2: `init` acepta `--minimal`/`--full`; el perfil por defecto es
    `--full` (decidido con el usuario, S26). El template `--full` trae comando
    de cierre admin-guarded (`client.stop()`), validación de permisos,
    `on_reconnect` (P12) y petición de estado inicial (`TINY.NCN/NPL`)."""

    def test_default_es_full(self, insims_dir):
        assert cli.main(["init", "foo"]) == 0
        src = _read_main(insims_dir, "foo")
        assert "def on_reconnect" in src
        assert "self.client.stop()" in src
        assert "_is_admin" in src
        assert "TINY.NCN" in src

    def test_minimal(self, insims_dir):
        assert cli.main(["init", "bar", "--minimal"]) == 0
        src = _read_main(insims_dir, "bar")
        assert "_cmd_hola" in src
        # el escueto NO trae reconexión ni cierre
        assert "on_reconnect" not in src
        assert "stop()" not in src

    def test_full_explicito(self, insims_dir):
        assert cli.main(["init", "baz", "--full"]) == 0
        src = _read_main(insims_dir, "baz")
        assert "self.client.stop()" in src
        assert "def on_reconnect" in src

    def test_flags_mutuamente_excluyentes(self, insims_dir):
        # argparse rechaza --minimal y --full juntos (SystemExit(2)).
        with pytest.raises(SystemExit):
            cli.main(["init", "x", "--minimal", "--full"])

    def test_clase_camelcase_y_manifiesto(self, insims_dir):
        assert cli.main(["init", "mi_bot"]) == 0
        assert "class MiBot(InSimApp):" in _read_main(insims_dir, "mi_bot")
        manifest = json.loads(
            (insims_dir / "mi_bot" / "insim.json").read_text(encoding="utf-8")
        )
        assert manifest["name"] == "mi_bot"
        assert manifest["entry_point"] == "main.py"

    def test_ya_existe_devuelve_1(self, insims_dir):
        assert cli.main(["init", "dup"]) == 0
        assert cli.main(["init", "dup"]) == 1


class TestInitTemplatesValidos:
    """Ambos templates deben ser Python válido e importable: un scaffold roto
    es un fallo de DX serio (el usuario ejecuta este código tal cual)."""

    @pytest.mark.parametrize(
        "render", [cli._render_minimal_main, cli._render_full_main]
    )
    def test_template_compila(self, render):
        src = render("mi_modulo", "MiModulo")
        compile(src, "<template>", "exec")

    @pytest.mark.parametrize(
        "render", [cli._render_minimal_main, cli._render_full_main]
    )
    def test_template_define_subclase_de_insimapp(self, render):
        from lfs_insim import InSimApp

        src = render("demo", "Demo")
        ns: dict = {}
        exec(compile(src, "<demo>", "exec"), ns)
        assert issubclass(ns["Demo"], InSimApp)
