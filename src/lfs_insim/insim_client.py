"""
lfs_insim/insim_client.py - Framework orchestrator core.

Owns the physical connection with LFS and dispatches packets and lifecycle
events to every registered app (InSimApp). One client, N apps: apps are
attached with `client.register(app)` and receive packets in registration
order (dependencies first, since the loader registers them before their
dependents).
"""

import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Any, Optional

from .insim_transport import InSimTransport
from .insim_state import set_insim_client
from .insim_packet_sender import encode_packet
from .insim_packet_decoders import decode_packet
from .insim_packet_class import ISP_ISI, ISP_TINY
from .insim_enums import ISF, TINY, OSO
from .exceptions import InSimError

class InSimClient:
    def __init__(self, config: Optional[dict] = None, name: str = "DeepInSim",
                 transport: Optional[InSimTransport] = None):
        from config.settings import get_config  # P14: core still reads CWD config
        self.config = get_config(config)
        self.name = name
        self.logger = logging.getLogger(f"InSim.{name}")
        self.running = False

        # Initialization packet (ISI) state
        self.isi = ISP_ISI()

        # Apps (InSimApp instances) listening on this client, in dispatch order
        self.apps: List[Any] = []

        # Transport: owns the sockets and receiver threads of this connection.
        # Injectable for tests or custom transports.
        self.transport = transport or InSimTransport()
        self.transport.on_raw = self._on_raw_bytes

        # Optional thread pool for asynchronous packet dispatch
        self.use_thread_pool = self.config.get('use_thread_pool', False)
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.get('max_workers', 5)
        ) if self.use_thread_pool else None

        # OutSim: client base opts; apps contribute theirs via set_outsim()
        self.outsim_opts: OSO = OSO.NONE

        # Optional sugar: the first client created becomes the process's
        # default client (fallback for PacketSenderMixin helper classes)
        set_insim_client(self)

    def register(self, app: Any) -> Any:
        """
        Attach an app to this client.

        Apps receive packets and lifecycle events in registration order.
        Registering twice is a no-op. Returns the app for chaining.
        """
        if app not in self.apps:
            self.apps.append(app)
            app.client = self
            self.logger.debug(f"App '{app.name}' registered")
        return app

    def send(self, packet: Any) -> None:
        """Serialize a packet and send it through this client's transport."""
        self.transport.send(encode_packet(packet))

    def _on_raw_bytes(self, data: bytes) -> None:
        """
        Turn raw bytes into a packet object and dispatch it.
        Called from the transport's IO threads for every received packet.
        """
        # Pre-decode barrier: skip struct.unpack + dataclass creation for
        # types nobody handles. Only applies to InSim TCP packets
        # (data[0]*4 == len(data)); UDP OutSim/OutGauge frames do not match
        # that signature and always pass.
        active_ids = getattr(self, '_active_type_ids', None)
        if (active_ids is not None
                and len(data) >= 2
                and data[0] * 4 == len(data)
                and data[1] not in active_ids):
            return

        packet = decode_packet(data)
        if packet:
            self.on_packet_received(packet)

    def _build_active_handlers(self) -> None:
        """
        Scan the client and every app through their MROs and build two sets:
          _active_handler_names: {"on_ISP_MCI", "on_ISP_MSO", ...}
          _active_type_ids:      {38, 11, ...}  (numeric ISP type ids)

        TINY (3) and VER (2) are always active: they are required for the
        keep-alive and the reply to the initial ISI.

        Note: detects class methods (mixins included via MRO). Handlers added
        dynamically as instance attributes are NOT detected.
        """
        from .packets import INSIM_PACKETS
        from .insim_enums import ISP

        handler_names: set[str] = set()
        for instance in [self] + self.apps:
            for name in dir(type(instance)):        # MRO walk: includes mixins
                if name.startswith('on_ISP_'):
                    handler_names.add(name)

        # Reverse map: "ISP_MCI" -> 38
        cls_to_id = {cls.__name__: tid for tid, cls in INSIM_PACKETS.items()}
        active_ids: set[int] = set()
        for h in handler_names:
            tid = cls_to_id.get(h[3:])              # "on_ISP_MCI" -> "ISP_MCI"
            if tid is not None:
                active_ids.add(tid)

        # Always active
        active_ids.update({int(ISP.TINY), int(ISP.VER)})
        handler_names.update({'on_ISP_TINY', 'on_ISP_VER'})

        self._active_handler_names: set[str] = handler_names
        self._active_type_ids: set[int] = active_ids

    def set_outsim(self) -> None:
        """Empty hook. Subclasses may override to declare outsim_opts."""
        pass

    def _activate_outsim(self, combined_oso: OSO) -> None:
        """
        Build OutSimPack2 for combined_oso, register it in OUTSIM_PACKETS
        and open the UDP socket.
        """
        from .packets.outsim import build_outsim_pack2
        from .packets import OUTSIM_PACKETS

        OutSimPack2 = build_outsim_pack2(combined_oso)
        OUTSIM_PACKETS[OutSimPack2().get_size()] = OutSimPack2

        udp_port   = self.config.get('udp_port',   30000)
        udp_host   = self.config.get('udp_host',   '0.0.0.0')
        udp_buffer = self.config.get('udp_buffer', 4096)
        self.transport.connect_udp(udp_host, udp_port, udp_buffer)

        oso_names = ' | '.join(
            f.name for f in OSO
            if f in combined_oso and f.value > 0 and f.name not in ('ALL', 'ALL_NOID')
        )
        self.logger.info(f"OutSim active (OSO={int(combined_oso):#x}): {oso_names}")
        self.logger.info(
            f"  → required cfg.txt: OutSim Opts {int(combined_oso):x}"
            f" | OutSim IP 127.0.0.1 | OutSim Port {udp_port}"
        )

    def set_isi_packet(self):
        """
        Build the base initialization packet (ISI) from config.
        Apps contribute their needs through flag merging (see start()).
        """
        self.isi.ReqI = 0
        # UDPPort = 0 → LFS sends NLP/MCI over TCP (default and safe path).
        # If != 0, LFS redirects NLP/MCI ONLY to that UDP port, which requires
        # the UDP socket to be open. Use 'insim_udp_port' in config to get
        # NLP/MCI over UDP explicitly; 'udp_port' belongs to OutSim.
        self.isi.UDPPort = self.config.get('insim_udp_port', 0)
        self.isi.Flags = 0  # Filled dynamically by aggregation
        self.isi.InSimVer = self.config.get('insim_ver', 10)

        # Robust Prefix handling (int or str)
        prefix_val = self.config.get('prefix', '!')
        if isinstance(prefix_val, int):
            self.isi.Prefix = prefix_val
        else:
            self.isi.Prefix = ord(prefix_val)

        self.isi.Interval = self.config.get('interval', 100)  # ms
        self.isi.Admin = self.config.get('admin_pass', '')
        self.isi.IName = self.config.get('insim_name', 'LFS-InSim')

    def start(self):
        """Open the connection and run the main loop."""
        if self.running:
            return

        self.running = True
        try:
            # =================================================================
            # ACTIVE PACKET REGISTRY
            # Built BEFORE opening the socket to avoid a race.
            # =================================================================
            self._build_active_handlers()
            active_names = sorted(h[3:] for h in self._active_handler_names)
            self.logger.info(
                f"Active packet types ({len(active_names)}): {', '.join(active_names)}"
            )

            # 1. Physical TCP connection
            host = self.config.get('tcp_host', '127.0.0.1')
            port = self.config.get('tcp_port', 29999)
            self.transport.connect_tcp(host, port)

            # =================================================================
            # ISI FLAG AGGREGATION
            # =================================================================

            # A) Client base ISI from config
            self.set_isi_packet()
            self.logger.info(f"Client base flags ({self.name}): {self.isi.Flags}")

            # B) Merge the requirements of every registered app
            if self.apps:
                self.logger.info(f"Merging requirements from {len(self.apps)} apps...")

                for app in self.apps:
                    app.set_isi_packet()

                    old_flags = self.isi.Flags
                    self.isi.Flags |= app.isi.Flags

                    if self.isi.Flags != old_flags:
                        added = self.isi.Flags ^ old_flags
                        self.logger.debug(f" -> +Flags from '{app.name}': {added} (Total: {self.isi.Flags})")

            # =================================================================
            # OUTSIM OPTS AGGREGATION
            # =================================================================
            self.set_outsim()
            combined_oso: OSO = self.outsim_opts
            for app in self.apps:
                app.set_outsim()
                combined_oso |= app.outsim_opts

            if combined_oso:
                self._activate_outsim(combined_oso)
            else:
                self.logger.debug("OutSim disabled (no app requires it)")
            # =================================================================

            # 3. Send the FINAL initialization packet (ISI)
            self.logger.info(f"Sending final ISI with flags: {self.isi.Flags}")
            self.send(self.isi)

            # 4. Notify every app about the connection
            self.on_connect()  # own hook
            self._dispatch_lifecycle('on_connect')

            self.logger.info(f"Client '{self.name}' started and listening...")

            # 5. Main loop
            # NOTE: keep-alive is reactive (see on_packet_received below)
            while self.running:
                self.on_tick()  # own hook
                self._dispatch_lifecycle('on_tick')
                time.sleep(0.1)  # 10 base ticks/s to avoid hogging the CPU

        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by the user.")
        except Exception as e:
            self.logger.error(f"Critical error in the main loop: {e}", exc_info=True)
            raise
        finally:
            self.stop()

    def stop(self):
        """Stop the client, closing threads and sockets."""
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping framework...")

        # Notify disconnection
        self._dispatch_lifecycle('on_disconnect')
        self.on_disconnect()

        # Shut down the thread pool
        if self._executor:
            self._executor.shutdown(wait=False)

        # Close sockets and receiver threads
        self.transport.close()

        self.logger.info("Framework stopped.")

    def on_packet_received(self, packet: Any):
        """
        Callback invoked from the IO thread when a packet arrives.
        """
        # 1. Internal handling (keep-alive pings)
        if isinstance(packet, ISP_TINY) and packet.SubT == TINY.NONE:
            self.send(ISP_TINY(ReqI=0, SubT=TINY.NONE))

        # 2. Dispatch to the apps
        if self.use_thread_pool and self._executor:
            self._executor.submit(self._dispatch_packet, packet)
        else:
            self._dispatch_packet(packet)

    def _dispatch_packet(self, packet: Any):
        """Deliver the packet to this client and then to every app."""
        if packet is None:
            return

        packet_class_name = type(packet).__name__
        handler_name = f"on_{packet_class_name}"

        # Post-decode barrier: if the registry exists and nobody handles this
        # type, skip the app loop (second line of defense after _process_raw_bytes).
        if (hasattr(self, '_active_handler_names')
                and handler_name not in self._active_handler_names):
            return

        # 1. Run the client's own handler (if any)
        self._execute_handler(self, handler_name, packet)

        # 2. Run the handlers of every registered app, in registration order
        for app in self.apps:
            self._execute_handler(app, handler_name, packet)

    def _dispatch_lifecycle(self, event_name: str):
        """Propagate lifecycle events (on_connect, on_tick, ...) to the apps."""
        for app in self.apps:
            if hasattr(app, event_name):
                try:
                    getattr(app, event_name)()
                except Exception as e:
                    self.logger.error(f"Error in {app.name}.{event_name}: {e}")

    def _execute_handler(self, instance: Any, handler_name: str, packet: Any):
        """Run a handler, isolating any error it raises."""
        handler = getattr(instance, handler_name, None)
        if handler and callable(handler):
            try:
                handler(packet)
            except Exception as e:
                self.logger.error(f"Error in {handler_name} of {instance.name}: {e}", exc_info=True)

    # Empty hooks for subclasses
    def on_connect(self): pass
    def on_disconnect(self): pass
    def on_tick(self): pass
