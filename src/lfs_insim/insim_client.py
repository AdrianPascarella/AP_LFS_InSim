"""
lfs_insim/insim_client.py - Núcleo Orquestador del Framework.

Gestiona la conexión física con LFS y distribuye paquetes y eventos de ciclo 
de vida a todos los módulos (InSimApps) registrados.
"""

import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Any, Optional

from .insim_packet_io import connect_tcp_lfs, connect_udp_lfs, stop_all_threads
from .insim_state import set_insim_client
from .insim_packet_sender import send_packet
from .insim_packet_class import ISP_ISI, ISP_TINY
from .insim_enums import ISF, TINY
from .exceptions import InSimError

class InSimClient:
    def __init__(self, config: Optional[dict] = None, name: str = "DeepInSim"):
        from config.settings import get_config
        self.config = get_config(config)
        self.name = name
        self.logger = logging.getLogger(f"InSim.{name}")
        self.running = False
        
        # Estado del paquete de inicialización (ISI)
        self.isi = ISP_ISI()
        
        # Lista de módulos (InSimApps) que "escuchan" este cliente
        self.modules: List[Any] = []
        
        # Configuración del pool de hilos para procesamiento asíncrono
        self.use_thread_pool = self.config.get('use_thread_pool', False)
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.get('max_workers', 5)
        ) if self.use_thread_pool else None

        # Registrar este cliente como el Principal en el estado global
        set_insim_client(self)

    def send(self, packet: Any) -> None:
        """
        Envia un paquete a LFS.
        Este método es el puente que usan los módulos (self.send) para acceder
        a la función global send_packet.
        """
        send_packet(packet)

    def set_isi_packet(self):
        """
        Configura el paquete de inicialización (ISI) base.
        Los módulos hijos pueden extender esto mediante fusión de flags.
        """
        self.isi.ReqI = 0
        self.isi.UDPPort = self.config.get('udp_port', 0)
        self.isi.Flags = 0 # Se llenará dinámicamente
        self.isi.InSimVer = self.config.get('insim_ver', 10)

        # Corrección: Manejo robusto de Prefix (int o str)
        prefix_val = self.config.get('prefix', '!')
        if isinstance(prefix_val, int):
            self.isi.Prefix = prefix_val
        else:
            self.isi.Prefix = ord(prefix_val)

        self.isi.Interval = self.config.get('interval', 100) # ms
        self.isi.Admin = self.config.get('admin_pass', '')
        self.isi.IName = self.config.get('insim_name', 'LFS-InSim')

    def start(self):
        """Inicia la conexión y el bucle principal."""
        if self.running:
            return

        self.running = True
        try:
            # 1. Conexión TCP Física
            host = self.config.get('tcp_host', '127.0.0.1')
            port = self.config.get('tcp_port', 29999)
            connect_tcp_lfs(host, port)

            # 2. Configuración UDP (Opcional)
            udp_port = self.config.get('udp_port')
            if udp_port:
                udp_host = self.config.get('udp_host', '0.0.0.0')
                udp_buffer = self.config.get('udp_buffer', 4096)
                connect_udp_lfs(udp_host, udp_port, udp_buffer)

            # =================================================================
            # LÓGICA DE FUSIÓN DE FLAGS (Flag Aggregation)
            # =================================================================
            
            # A) Configurar la base del Maestro (este cliente)
            self.set_isi_packet()
            self.logger.info(f"Flags base del Maestro ({self.name}): {self.isi.Flags}")

            # B) Recorrer módulos hijos para sumar sus requisitos
            if self.modules:
                self.logger.info(f"Fusionando requisitos de {len(self.modules)} módulos...")
                
                for module in self.modules:
                    module.set_isi_packet()
                    
                    old_flags = self.isi.Flags
                    self.isi.Flags |= module.isi.Flags
                    
                    if self.isi.Flags != old_flags:
                        added = self.isi.Flags ^ old_flags
                        self.logger.debug(f" -> +Flags de '{module.name}': {added} (Total: {self.isi.Flags})")

            # =================================================================

            # 3. Enviar el paquete de Inicialización (ISI) DEFINITIVO
            self.logger.info(f"Enviando ISI Definitivo con Flags: {self.isi.Flags}")
            self.send(self.isi)

            # 4. Notificar conexión a todos los módulos
            self.on_connect() # Hook propio
            self._dispatch_lifecycle('on_connect')
            
            self.logger.info(f"Cliente '{self.name}' iniciado y escuchando...")
            
            # 5. Bucle principal
            # NOTA: El Keep-Alive ahora es reactivo (ver on_ISP_TINY abajo)
            while self.running:
                self.on_tick() # Hook propio
                self._dispatch_lifecycle('on_tick')
                time.sleep(0.1) # 10 ticks/s base para no saturar CPU
                
        except KeyboardInterrupt:
            self.logger.info("Cierre solicitado por el usuario.")
        except Exception as e:
            self.logger.error(f"Error crítico en el bucle principal: {e}", exc_info=True)
            raise
        finally:
            self.stop()

    def stop(self):
        """Detiene el cliente, cierra hilos y sockets."""
        if not self.running:
            return
            
        self.running = False
        self.logger.info("Deteniendo framework...")
        
        # Notificar desconexión
        self._dispatch_lifecycle('on_disconnect')
        self.on_disconnect()
        
        # Cerrar pool de hilos
        if self._executor:
            self._executor.shutdown(wait=False)
            
        # Cerrar sockets
        stop_all_threads()
        
        self.logger.info("Framework detenido.")

    def on_packet_received(self, packet: Any):
        """
        Callback llamado desde el hilo de IO cuando llega un paquete.
        """
        # 1. Manejo interno (Keep Alive, Pings vacíos)
        # Algunos paquetes del sistema podrían manejarse aquí antes de despachar
        
        if isinstance(packet, ISP_TINY) and packet.SubT == TINY.NONE:
            self.send(ISP_TINY(ReqI=0, SubT=TINY.NONE))
        
        # 2. Distribuir a los módulos
        if self.use_thread_pool and self._executor:
            self._executor.submit(self._dispatch_packet, packet)
        else:
            self._dispatch_packet(packet)

    def _dispatch_packet(self, packet: Any):
        """Entrega el paquete a este cliente y a todos sus módulos."""
        if packet is None:
            return

        # Corrección: Usamos el nombre de la CLASE para el evento
        packet_class_name = type(packet).__name__
        handler_name = f"on_{packet_class_name}"

        # 1. Ejecutar en el cliente principal (self)
        self._execute_handler(self, handler_name, packet)

        # 2. Ejecutar en módulos registrados
        for module in self.modules:
            self._execute_handler(module, handler_name, packet)

    def _dispatch_lifecycle(self, event_name: str):
        """Propaga eventos como on_connect, on_tick, etc."""
        for module in self.modules:
            if hasattr(module, event_name):
                try:
                    getattr(module, event_name)()
                except Exception as e:
                    self.logger.error(f"Error en {module.name}.{event_name}: {e}")

    def _execute_handler(self, instance: Any, handler_name: str, packet: Any):
        """Ejecuta el handler de forma segura."""
        handler = getattr(instance, handler_name, None)
        if handler and callable(handler):
            try:
                handler(packet)
            except Exception as e:
                self.logger.error(f"Error en {handler_name} de {instance.name}: {e}", exc_info=True)            

    # Hooks vacíos para herencia
    def on_connect(self): pass
    def on_disconnect(self): pass
    def on_tick(self): pass