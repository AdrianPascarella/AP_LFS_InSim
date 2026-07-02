"""
Tests del DISPATCH de InSimClient (Fase 2, arquitectura de composición — P11).

Cubre lo que faltaba del ítem "dispatch" del plan (el registro de handlers
activos y los filtros pre/post-decode ya están en test_active_packet_registry.py):

  - orden de entrega: primero el cliente (self), luego las apps en orden
    de registro (client.register);
  - aislamiento de errores: un handler que explota no rompe el dispatch ni
    afecta a los demás handlers;
  - keep-alive reactivo: un ISP_TINY con SubT=NONE se contesta con otro igual;
  - dispatch de lifecycle (on_connect/on_tick/...): orden, aislamiento y
    apps sin el hook;
  - enrutado según use_thread_pool (inline vs executor).
"""
from unittest.mock import MagicMock, patch

import lfs_insim.insim_state as state
from lfs_insim.insim_client import InSimClient
from lfs_insim.insim_enums import TINY
from lfs_insim.packets import ISP_MSO, ISP_TINY


class _ClienteGrabador(InSimClient):
    """Cliente con un handler propio que apunta su turno en el diario."""

    def __init__(self, diario):
        super().__init__(config={})
        self._diario = diario

    def on_ISP_MSO(self, packet):
        self._diario.append('cliente')


class _AppGrabadora:
    """App mínima: apunta su etiqueta en el diario al recibir MSO."""

    def __init__(self, etiqueta, diario, explota=False):
        self.name = etiqueta
        self._etiqueta = etiqueta
        self._diario = diario
        self._explota = explota

    def on_ISP_MSO(self, packet):
        if self._explota:
            raise ValueError(f"boom en {self._etiqueta}")
        self._diario.append(self._etiqueta)


class _AppLifecycle:
    def __init__(self, etiqueta, diario, explota=False):
        self.name = etiqueta
        self._etiqueta = etiqueta
        self._diario = diario
        self._explota = explota

    def on_connect(self):
        if self._explota:
            raise RuntimeError(f"boom en {self._etiqueta}")
        self._diario.append(self._etiqueta)


class _Base:
    def setup_method(self):
        state.reset_insim_client()
        state.reset_sockets()

    def teardown_method(self):
        state.reset_insim_client()
        state.reset_sockets()


class TestRegister(_Base):

    def test_register_encola_y_asigna_el_cliente(self):
        client = InSimClient(config={})
        app_a = _AppGrabadora('A', [])
        app_b = _AppGrabadora('B', [])

        assert client.register(app_a) is app_a   # devuelve la app (chaining)
        client.register(app_b)

        assert client.apps == [app_a, app_b]
        assert app_a.client is client
        assert app_b.client is client

    def test_register_dos_veces_no_duplica(self):
        client = InSimClient(config={})
        app = _AppGrabadora('A', [])

        client.register(app)
        client.register(app)

        assert client.apps == [app]


class TestOrdenDeDispatch(_Base):

    def test_cliente_primero_luego_apps_en_orden(self):
        diario = []
        client = _ClienteGrabador(diario)
        client.register(_AppGrabadora('A', diario))
        client.register(_AppGrabadora('B', diario))
        client._active_handler_names = {'on_ISP_MSO'}

        client._dispatch_packet(ISP_MSO())

        assert diario == ['cliente', 'A', 'B']

    def test_paquete_none_no_hace_nada(self):
        diario = []
        client = _ClienteGrabador(diario)
        client.register(_AppGrabadora('A', diario))

        client._dispatch_packet(None)

        assert diario == []

    def test_app_sin_handler_se_salta_sin_error(self):
        diario = []
        client = _ClienteGrabador(diario)

        class SinHandler:
            name = 'muda'

        client.register(SinHandler())
        client.register(_AppGrabadora('B', diario))
        client._active_handler_names = {'on_ISP_MSO'}

        client._dispatch_packet(ISP_MSO())

        assert diario == ['cliente', 'B']


class TestAislamientoDeErrores(_Base):

    def test_handler_que_explota_no_corta_a_los_demas(self):
        diario = []
        client = _ClienteGrabador(diario)
        client.register(_AppGrabadora('A', diario, explota=True))
        client.register(_AppGrabadora('B', diario))
        client._active_handler_names = {'on_ISP_MSO'}

        client._dispatch_packet(ISP_MSO())   # no debe propagar la excepción

        assert diario == ['cliente', 'B']

    def test_error_en_el_cliente_no_corta_a_las_apps(self):
        diario = []

        class ClienteQueExplota(InSimClient):
            def __init__(self):
                super().__init__(config={})
            def on_ISP_MSO(self, packet):
                raise ValueError('boom en el cliente')

        client = ClienteQueExplota()
        client.register(_AppGrabadora('A', diario))
        client._active_handler_names = {'on_ISP_MSO'}

        client._dispatch_packet(ISP_MSO())

        assert diario == ['A']


class TestKeepAliveReactivo(_Base):

    def test_tiny_none_se_contesta_con_tiny_none(self):
        client = InSimClient(config={})

        with patch.object(client, 'send') as mock_send:
            client.on_packet_received(ISP_TINY(SubT=TINY.NONE))

        assert mock_send.call_count == 1
        respuesta = mock_send.call_args[0][0]
        assert isinstance(respuesta, ISP_TINY)
        assert respuesta.SubT == TINY.NONE
        assert respuesta.ReqI == 0

    def test_tiny_con_otro_subt_no_se_contesta(self):
        client = InSimClient(config={})

        with patch.object(client, 'send') as mock_send:
            client.on_packet_received(ISP_TINY(ReqI=1, SubT=TINY.VER))

        mock_send.assert_not_called()

    def test_paquete_no_tiny_no_se_contesta(self):
        client = InSimClient(config={})

        with patch.object(client, 'send') as mock_send:
            client.on_packet_received(ISP_MSO())

        mock_send.assert_not_called()


class TestDispatchLifecycle(_Base):

    def test_orden_de_apps(self):
        diario = []
        client = InSimClient(config={})
        client.register(_AppLifecycle('A', diario))
        client.register(_AppLifecycle('B', diario))

        client._dispatch_lifecycle('on_connect')

        assert diario == ['A', 'B']

    def test_error_aislado_por_app(self):
        diario = []
        client = InSimClient(config={})
        client.register(_AppLifecycle('A', diario, explota=True))
        client.register(_AppLifecycle('B', diario))

        client._dispatch_lifecycle('on_connect')   # no debe propagar

        assert diario == ['B']

    def test_app_sin_hook_se_salta(self):
        diario = []
        client = InSimClient(config={})

        class SinHook:
            name = 'muda'

        client.register(SinHook())
        client.register(_AppLifecycle('B', diario))

        client._dispatch_lifecycle('on_connect')

        assert diario == ['B']

    def test_evento_inexistente_no_hace_nada(self):
        client = InSimClient(config={})
        client.register(_AppLifecycle('A', []))
        client._dispatch_lifecycle('on_evento_que_no_existe')


class TestRutaThreadPool(_Base):

    def test_sin_pool_despacha_inline(self):
        client = InSimClient(config={})
        assert client._executor is None

        pkt = ISP_MSO()
        with patch.object(client, '_dispatch_packet') as mock_dispatch:
            client.on_packet_received(pkt)

        mock_dispatch.assert_called_once_with(pkt)

    def test_con_pool_encola_en_el_executor(self):
        client = InSimClient(config={'use_thread_pool': True})
        client._executor.shutdown(wait=False)
        client._executor = MagicMock()

        pkt = ISP_MSO()
        client.on_packet_received(pkt)

        client._executor.submit.assert_called_once_with(client._dispatch_packet, pkt)
