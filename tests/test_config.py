"""
Tests de la config interna del paquete (Fase 2 — P14).

El core lleva sus defaults en lfs_insim/config.py y NO importa
config.settings del CWD: un paquete instalado funciona sin archivos de
proyecto alrededor. Se verifica bloqueando el paquete `config` en
sys.modules e instanciando cliente y app igualmente.
"""
import sys

import pytest

import lfs_insim.insim_state as state
from lfs_insim.config import DEFAULT_CONFIG, build_config
from lfs_insim.insim_app import InSimApp
from lfs_insim.insim_client import InSimClient


@pytest.fixture(autouse=True)
def _cliente_por_defecto_limpio():
    """Instanciar InSimClient fija el cliente por defecto; no ensuciar otros tests."""
    state.reset_insim_client()
    yield
    state.reset_insim_client()


@pytest.fixture
def sin_config_del_proyecto(monkeypatch):
    """Bloquea el import del paquete `config` del proyecto (simula paquete instalado)."""
    monkeypatch.setitem(sys.modules, 'config', None)
    monkeypatch.setitem(sys.modules, 'config.settings', None)


class TestBuildConfig:

    def test_sin_overrides_devuelve_los_defaults(self):
        assert build_config() == DEFAULT_CONFIG

    def test_devuelve_una_copia_no_el_original(self):
        config = build_config()
        config['tcp_port'] = 11111
        config['clave_nueva'] = True

        assert DEFAULT_CONFIG['tcp_port'] == 29999
        assert 'clave_nueva' not in DEFAULT_CONFIG

    def test_overrides_pisan_y_extienden(self):
        config = build_config({'tcp_port': 12345, 'extra': 'x'})

        assert config['tcp_port'] == 12345          # clave pisada
        assert config['extra'] == 'x'               # clave nueva
        assert config['prefix'] == '!'              # el resto, defaults

    def test_defaults_esperados_por_el_core(self):
        # Las claves que el cliente lee en set_isi_packet/start/_activate_outsim
        # deben existir en los defaults (si falta una, el .get() escondería el hueco).
        for clave in ('tcp_host', 'tcp_port', 'insim_name', 'admin_pass',
                      'insim_ver', 'prefix', 'interval', 'insim_udp_port',
                      'udp_host', 'udp_port', 'udp_buffer',
                      'use_thread_pool', 'max_workers'):
            assert clave in DEFAULT_CONFIG, f"falta '{clave}' en DEFAULT_CONFIG"


class TestCoreSinConfigDelProyecto:
    """P14: el core funciona con `config.settings` inimportable."""

    def test_cliente_se_instancia_con_defaults(self, sin_config_del_proyecto):
        cliente = InSimClient()

        assert cliente.config['tcp_port'] == 29999
        assert cliente.config['prefix'] == '!'

    def test_app_se_instancia_con_defaults(self, sin_config_del_proyecto):
        app = InSimApp(name="app_sin_proyecto")

        assert app.config['interval'] == 10
        assert app.client is None                    # sin registrar aún

    def test_overrides_del_constructor_llegan(self, sin_config_del_proyecto):
        cliente = InSimClient(config={'tcp_port': 54321})
        app = InSimApp(config={'prefix': '$'})

        assert cliente.config['tcp_port'] == 54321
        assert app.config['prefix'] == '$'
        # y los defaults siguen presentes para el resto de claves
        assert cliente.config['insim_ver'] == 10
        assert app.config['udp_port'] == 30000

    def test_isi_se_construye_desde_los_defaults(self, sin_config_del_proyecto):
        cliente = InSimClient()
        cliente.set_isi_packet()

        assert cliente.isi.InSimVer == 10
        assert cliente.isi.Prefix == ord('!')
        assert cliente.isi.Interval == 10
        assert cliente.isi.Admin == ''
