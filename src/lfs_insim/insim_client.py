"""
lfs_insim/insim_client.py - Framework orchestrator core.

Owns the physical connection with LFS and dispatches packets and lifecycle
events to every registered app (InSimApp). One client, N apps: apps are
attached with `client.register(app)` and receive packets in registration
order (dependencies first, since the loader registers them before their
dependents).

Threading model (contract for module authors):
  - `on_ISP_*` handlers run on the client's dispatch worker thread, one
    packet at a time in strict FIFO order — never on the transport's IO
    threads (P2). A slow handler does not block reception, but it delays
    the packets queued behind it.
  - Lifecycle hooks (`on_connect`, `on_tick`, `on_disconnect`,
    `on_reconnect`) run on the main thread (the one that called `start()`).
    `on_tick` fires every `tick_interval` seconds (default 0.1, min 0.01;
    best-effort, no catch-up) — the main loop's internal poll stays at
    <=100 ms regardless, so a slow tick never delays connection-loss
    detection or fail-fast errors. There is no cross-thread ordering
    guarantee between lifecycle hooks and packet handlers.
  - `send()` is thread-safe and may be called from any thread.
  - App errors follow the `handler_errors` config key: 'log' (default)
    isolates them — logged with traceback, the client keeps running;
    'raise' is fail-fast — the first error in a packet handler or
    lifecycle hook stops the client and re-raises out of start() (the
    dispatch worker hands the exception to the main thread). Exception:
    on_disconnect errors during stop() are always isolated so the
    shutdown sequence completes.
"""

import logging
import queue
import threading
import time
from typing import Any, List, Optional

from .config import build_config
from .exceptions import InSimConfigurationError, InSimConnectionError
from .insim_enums import OSO, TINY
from .insim_packet_decoders import decode_packet
from .insim_packet_sender import encode_packet
from .insim_state import set_insim_client
from .insim_transport import InSimTransport
from .packets import ISP_ISI, ISP_TINY

# Queued behind every pending packet to tell the dispatch worker to exit
# (see InSimClient._stop_dispatch_worker).
_DISPATCH_STOP = object()


class InSimClient:
    def __init__(
        self,
        config: Optional[dict] = None,
        name: str = "DeepInSim",
        transport: Optional[InSimTransport] = None,
    ):
        self.config = build_config(config)
        self.name = name
        self.logger = logging.getLogger(f"InSim.{name}")
        self.running = False

        # Error policy: fail fast on a bad value, whatever the policy is.
        policy = self.config.get("handler_errors", "log")
        if policy not in ("log", "raise"):
            raise InSimConfigurationError(
                f"Invalid 'handler_errors' value: {policy!r} "
                "(expected 'log' or 'raise')"
            )

        # Tick cadence: validated here so a bad value fails at creation,
        # not minutes later inside start().
        raw_tick = self.config.get("tick_interval", 0.1)
        try:
            tick = float(raw_tick)
        except (TypeError, ValueError):
            tick = None
        if tick is None or tick < 0.01:
            raise InSimConfigurationError(
                f"Invalid 'tick_interval' value: {raw_tick!r} "
                "(expected a number >= 0.01 seconds)"
            )

        # With handler_errors='raise', the dispatch worker parks the first
        # handler exception here and exits; the main loop in start()
        # re-raises it so the client dies with the original traceback.
        self._handler_error: Optional[BaseException] = None

        # Guards the running check-and-set in stop(): two threads stopping
        # at once (e.g. a handler and a Ctrl+C) must not both run the
        # shutdown sequence, or on_disconnect would be dispatched twice.
        self._stop_lock = threading.Lock()

        # True while there is a live session with LFS (TCP up + ISI sent).
        # Cleared on connection loss and on stop().
        self.connected = False

        # Set by the transport (from its dying receiver thread) when the TCP
        # connection drops unexpectedly; the main loop in start() reacts to
        # it, dispatching on_disconnect and reconnecting (P12).
        self._connection_lost = threading.Event()

        # Reconnection streak state (P24): set whenever a session comes up;
        # lets _reconnect distinguish a stable session (fresh backoff) from
        # one that died right after the ISI (resume the escalating backoff).
        self._session_started_at: Optional[float] = None
        self._reconnect_attempt = 0
        self._reconnect_delay: Optional[float] = None

        # True once ANY data arrived from LFS in the current session. LFS
        # sends nothing back when it rejects an ISI (e.g. admin password
        # mismatch) — it just closes the socket — so "died young AND silent"
        # is the signature of a rejected ISI and gets an explicit hint in
        # the log (see _handle_connection_lost; incident S12).
        self._session_received_data = False

        # Initialization packet (ISI) state
        self.isi = ISP_ISI()

        # Apps (InSimApp instances) listening on this client, in dispatch order
        self.apps: List[Any] = []

        # Transport: owns the sockets and receiver threads of this connection.
        # Injectable for tests or custom transports.
        self.transport = transport or InSimTransport()
        self.transport.on_raw = self._on_raw_bytes
        self.transport.on_connection_lost = self._connection_lost.set

        # Dispatch queue + worker (P2): the IO threads only decode and
        # enqueue; a dedicated worker thread delivers packets to the apps in
        # FIFO order, so a slow handler never blocks reception. The thread
        # is created in start() and stopped in stop().
        self._dispatch_queue: "queue.Queue[Any]" = queue.Queue()
        self._dispatch_thread: Optional[threading.Thread] = None

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
        # Any bytes from LFS prove the ISI was accepted (counted BEFORE the
        # barrier: filtered packet types are still LFS talking to us).
        self._session_received_data = True

        # Pre-decode barrier: skip struct.unpack + dataclass creation for
        # types nobody handles. Only applies to InSim TCP packets
        # (data[0]*4 == len(data)); UDP OutSim/OutGauge frames do not match
        # that signature and always pass.
        active_ids = getattr(self, "_active_type_ids", None)
        if (
            active_ids is not None
            and len(data) >= 2
            and data[0] * 4 == len(data)
            and data[1] not in active_ids
        ):
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
        from .insim_enums import ISP
        from .packets import INSIM_PACKETS

        handler_names: set[str] = set()
        for instance in [self] + self.apps:
            for name in dir(type(instance)):  # MRO walk: includes mixins
                if name.startswith("on_ISP_"):
                    handler_names.add(name)

        # Reverse map: "ISP_MCI" -> 38
        cls_to_id = {cls.__name__: tid for tid, cls in INSIM_PACKETS.items()}
        active_ids: set[int] = set()
        for h in handler_names:
            tid = cls_to_id.get(h[3:])  # "on_ISP_MCI" -> "ISP_MCI"
            if tid is not None:
                active_ids.add(tid)

        # Always active
        active_ids.update({int(ISP.TINY), int(ISP.VER)})
        handler_names.update({"on_ISP_TINY", "on_ISP_VER"})

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
        from .packets import OUTSIM_PACKETS
        from .packets.outsim import build_outsim_pack2

        OutSimPack2 = build_outsim_pack2(combined_oso)
        OUTSIM_PACKETS[OutSimPack2().get_size()] = OutSimPack2

        udp_port = self.config.get("udp_port", 30000)
        udp_host = self.config.get("udp_host", "0.0.0.0")
        udp_buffer = self.config.get("udp_buffer", 4096)
        self.transport.connect_udp(udp_host, udp_port, udp_buffer)

        oso_names = " | ".join(
            f.name
            for f in OSO
            if f in combined_oso
            and f.value > 0
            and f.name is not None
            and f.name not in ("ALL", "ALL_NOID")
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
        self.isi.UDPPort = self.config.get("insim_udp_port", 0)
        self.isi.Flags = 0  # Filled dynamically by aggregation
        self.isi.InSimVer = self.config.get("insim_ver", 10)

        # Robust Prefix handling (int or str)
        prefix_val = self.config.get("prefix", "!")
        if isinstance(prefix_val, int):
            self.isi.Prefix = prefix_val
        else:
            self.isi.Prefix = ord(prefix_val)

        self.isi.Interval = self.config.get("interval", 100)  # ms
        self.isi.Admin = self.config.get("admin_pass", "")
        self.isi.IName = self.config.get("insim_name", "LFS-InSim")

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

            # Dispatch worker (P2): handlers run on this dedicated thread,
            # never on the transport's IO threads. Started before connecting
            # so the first packets already flow through the queue.
            self._start_dispatch_worker()

            # 1. Physical TCP connection
            host = self.config.get("tcp_host", "127.0.0.1")
            port = self.config.get("tcp_port", 29999)
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
                        self.logger.debug(
                            f" -> +Flags from '{app.name}': {added} (Total: {self.isi.Flags})"
                        )

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
            self._session_received_data = False  # reset BEFORE the ISI can be answered
            self.send(self.isi)
            self.connected = True
            # Fresh reconnection-streak state (P24): if this session dies
            # before `reconnect_stable_time`, _reconnect resumes from here.
            self._session_started_at = time.monotonic()
            self._reconnect_attempt = 0
            self._reconnect_delay = float(self.config.get("reconnect_delay", 1.0))

            # 4. Notify every app about the connection
            self.on_connect()  # own hook
            self._dispatch_lifecycle("on_connect")

            self.logger.info(f"Client '{self.name}' started and listening...")

            # 5. Main loop
            # NOTE: keep-alive is reactive (see on_packet_received below)
            # on_tick fires every `tick_interval` seconds, with no catch-up
            # after a stall (a reconnection must not be followed by a burst
            # of owed ticks). The loop itself polls at <=100 ms so
            # connection-loss detection and fail-fast handler errors never
            # wait on a slow tick.
            tick_interval = float(self.config.get("tick_interval", 0.1))
            poll = min(0.1, tick_interval)
            next_tick = time.monotonic()  # first tick fires immediately
            while self.running:
                if self._handler_error is not None:
                    # Fail-fast policy (handler_errors='raise'): a handler
                    # raised on the dispatch worker. Re-raise it here so
                    # start() dies with the original traceback.
                    error, self._handler_error = self._handler_error, None
                    raise error
                if self._connection_lost.is_set():
                    # Connection dropped: handle it (and reconnect) from the
                    # main thread; on_tick pauses until the session is back.
                    self._handle_connection_lost()
                    continue
                if time.monotonic() >= next_tick:
                    self.on_tick()  # own hook
                    self._dispatch_lifecycle("on_tick")
                    next_tick = time.monotonic() + tick_interval
                time.sleep(poll)

        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by the user.")
        except Exception as e:
            self.logger.error(f"Critical error in the main loop: {e}", exc_info=True)
            raise
        finally:
            self.stop()

    def stop(self):
        """Stop the client, closing threads and sockets."""
        # Atomic check-and-set: only ONE caller runs the shutdown sequence.
        # The lock covers just the flag flip, so a reentrant stop() from an
        # on_disconnect hook returns immediately instead of deadlocking.
        with self._stop_lock:
            if not self.running:
                return
            self.running = False
        self.logger.info("Stopping framework...")

        # Notify disconnection (skip when the connection-loss path already
        # did). Errors are isolated even with handler_errors='raise': the
        # shutdown must complete and every app must get its on_disconnect.
        if self.connected:
            self.connected = False
            self._dispatch_lifecycle("on_disconnect", isolate=True)
            self.on_disconnect()

        # Close sockets and receiver threads (no more packets get enqueued)
        self.transport.close()

        # Stop the dispatch worker: the sentinel queues BEHIND any pending
        # packets, so they are still delivered before the worker exits.
        self._stop_dispatch_worker()

        self.logger.info("Framework stopped.")

    # ------------------------------------------------------------------ #
    # Reconnection (P12)
    # ------------------------------------------------------------------ #

    def _handle_connection_lost(self):
        """
        React to an unexpected connection loss. Runs in the MAIN thread
        (called from the loop in start()), so on_disconnect/on_reconnect are
        dispatched from the same thread as on_connect and on_tick.
        """
        self._connection_lost.clear()
        self.connected = False
        self.logger.warning("Connection with LFS lost.")

        # Diagnostic hint (S12): LFS gives no feedback on the socket when it
        # rejects an ISI — it just closes. A session that dies young without
        # a single packet received is almost certainly a rejected ISI.
        uptime = (
            time.monotonic() - self._session_started_at
            if self._session_started_at is not None
            else None
        )
        stable_time = float(self.config.get("reconnect_stable_time", 10.0))
        if (
            uptime is not None
            and uptime < stable_time
            and not self._session_received_data
        ):
            self.logger.warning(
                f"The session died after {uptime:.1f}s without receiving a "
                "single packet from LFS — the ISI was likely rejected. Check "
                "'admin_pass' (LFS 'Game Admin' password) and the InSim "
                "version; LFS gives no feedback on the socket when it "
                "rejects an ISI."
            )

        self._dispatch_lifecycle("on_disconnect")
        self.on_disconnect()

        if not self.config.get("reconnect", True):
            self.logger.error("Auto-reconnect is disabled; stopping the client.")
            self.stop()
            return

        self._reconnect()

    def _reconnect(self):
        """Retry the TCP connection with exponential backoff and restore
        the session. Gives up (stopping the client) only when
        `reconnect_max_attempts` > 0 is exhausted.

        A reconnect is only PROVISIONAL: LFS may accept the TCP connection
        and drop it right after the ISI (e.g. admin password mismatch) —
        nothing confirms the ISI was accepted. If the restored session dies
        before `reconnect_stable_time` seconds, this method resumes the
        previous backoff (waiting BEFORE the next attempt, and counting the
        streak towards `reconnect_max_attempts`) instead of starting fresh;
        otherwise a rejected ISI would turn into a full-speed connection
        storm against LFS (P24, seen live in S12: "InSim - TCP excess")."""
        host = self.config.get("tcp_host", "127.0.0.1")
        port = self.config.get("tcp_port", 29999)
        delay = float(self.config.get("reconnect_delay", 1.0))
        backoff = float(self.config.get("reconnect_backoff", 2.0))
        max_delay = float(self.config.get("reconnect_max_delay", 30.0))
        max_attempts = int(self.config.get("reconnect_max_attempts", 0))
        stable_time = float(self.config.get("reconnect_stable_time", 10.0))

        attempt = 0
        uptime = (
            time.monotonic() - self._session_started_at
            if self._session_started_at is not None
            else None
        )
        if (
            uptime is not None
            and uptime < stable_time
            and self._reconnect_delay is not None
        ):
            # The previous session died young: the streak continues. Wait
            # before reconnecting and keep escalating instead of hammering.
            attempt = self._reconnect_attempt
            delay = self._reconnect_delay
            self.logger.warning(
                f"Session died after {uptime:.1f}s (< {stable_time:.0f}s); "
                f"resuming backoff: waiting {delay:.1f}s before reconnecting."
            )
            self._sleep_while_running(delay)
            delay = min(delay * backoff, max_delay)

        while self.running:
            attempt += 1
            if max_attempts and attempt > max_attempts:
                self.logger.error(
                    f"Could not reconnect after {max_attempts} attempts; stopping the client."
                )
                self.stop()
                return

            self.logger.info(
                f"Reconnecting to LFS at {host}:{port} (attempt {attempt})..."
            )
            try:
                # Anything signalled before this instant belongs to the dead
                # connection; events set from here on come from the new one.
                self._connection_lost.clear()
                self.transport.connect_tcp(host, port)
                self._restore_session()
            except InSimConnectionError as e:
                self.logger.warning(f"Reconnect attempt {attempt} failed: {e}")
                self._sleep_while_running(delay)
                delay = min(delay * backoff, max_delay)
                continue

            # Provisional success: keep the streak state so a session that
            # dies before stable_time resumes this backoff (see docstring).
            self._reconnect_attempt = attempt
            self._reconnect_delay = delay
            self._session_started_at = time.monotonic()
            self.logger.info(f"Reconnected to LFS after {attempt} attempt(s).")
            return

        # running went False mid-backoff (stop() during the wait): leave an
        # explicit trace — a silent end here already misled one diagnosis.
        self.logger.info("Reconnection abandoned: the client is stopping.")

    def _restore_session(self):
        """Resend the ISI and re-request the state after reconnecting."""
        self._session_received_data = False  # reset BEFORE the ISI can be answered
        self.send(self.isi)
        self.connected = True
        # on_reconnect BEFORE re-requesting the state (P22): apps reset their
        # per-session memory here, so the NCN/NPL replies triggered below can
        # never race against that cleanup and get wiped.
        self.on_reconnect()  # own hook
        self._dispatch_lifecycle("on_reconnect")
        # Ask LFS for connections and players again so app trackers
        # (on_ISP_NCN / on_ISP_NPL handlers) rebuild their state.
        self.send(ISP_TINY(ReqI=1, SubT=TINY.NCN))
        self.send(ISP_TINY(ReqI=1, SubT=TINY.NPL))

    def _sleep_while_running(self, seconds: float) -> None:
        """Sleep up to `seconds`, waking early if the client stops."""
        deadline = time.monotonic() + seconds
        while self.running and time.monotonic() < deadline:
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))

    def on_packet_received(self, packet: Any):
        """
        Entry point for every decoded packet, called from the transport's
        IO threads: replies to keep-alive pings and hands the packet to the
        dispatch worker, so handlers never block reception (P2).
        """
        # 1. Keep-alive pings: answered right here on the IO thread, so a
        # busy dispatch queue can never delay them (LFS drops the connection
        # when the ping is not answered in time). The packet still goes
        # through the queue afterwards, in case some app handles ISP_TINY.
        if isinstance(packet, ISP_TINY) and packet.SubT == TINY.NONE:
            self.send(ISP_TINY(ReqI=0, SubT=TINY.NONE))

        # 2. Enqueue for the dispatch worker (FIFO)
        self._dispatch_queue.put(packet)

    # ------------------------------------------------------------------ #
    # Dispatch worker (P2)
    # ------------------------------------------------------------------ #

    @property
    def _fail_fast(self) -> bool:
        """True when handler_errors='raise' (fail-fast error policy)."""
        return self.config.get("handler_errors", "log") == "raise"

    def _start_dispatch_worker(self) -> None:
        """Start the dispatch worker thread (idempotent)."""
        if self._dispatch_thread is not None and self._dispatch_thread.is_alive():
            return
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop,
            name="InSim_Dispatch_Worker",
            daemon=True,
        )
        self._dispatch_thread.start()

    def _stop_dispatch_worker(self) -> None:
        """Ask the worker to exit once the queue is drained, and wait for it."""
        thread = self._dispatch_thread
        if thread is None or not thread.is_alive():
            self._dispatch_thread = None
            return
        self._dispatch_queue.put(_DISPATCH_STOP)
        # A handler itself may call stop(); never join our own thread.
        if thread is not threading.current_thread():
            thread.join(timeout=2.0)
            if thread.is_alive():
                self.logger.warning(
                    "Dispatch worker did not finish in time (a handler may be blocked)."
                )
        self._dispatch_thread = None

    def _dispatch_loop(self) -> None:
        """
        Dispatch worker main loop. Takes decoded packets from the queue and
        delivers them in FIFO order. With handler_errors='log', handler
        errors are already isolated in _execute_handler and the guard here
        keeps the worker alive against anything unexpected; with 'raise',
        the first error stops the worker (pending packets are deliberately
        dropped) and is handed to the main thread, which re-raises it.
        """
        while True:
            item = self._dispatch_queue.get()
            if item is _DISPATCH_STOP:
                break
            try:
                self._dispatch_packet(item)
            except Exception as e:
                if self._fail_fast:
                    self._handler_error = e
                    self.logger.critical(
                        f"Error in a handler for {type(item).__name__} with "
                        f"handler_errors='raise'; stopping the client: {e}"
                    )
                    break
                self.logger.error(
                    f"Error dispatching {type(item).__name__}: {e}", exc_info=True
                )

    def _dispatch_packet(self, packet: Any):
        """Deliver the packet to this client and then to every app."""
        if packet is None:
            return

        packet_class_name = type(packet).__name__
        handler_name = f"on_{packet_class_name}"

        # Post-decode barrier: if the registry exists and nobody handles this
        # type, skip the app loop (second line of defense after _process_raw_bytes).
        if (
            hasattr(self, "_active_handler_names")
            and handler_name not in self._active_handler_names
        ):
            return

        # 1. Run the client's own handler (if any)
        self._execute_handler(self, handler_name, packet)

        # 2. Run the handlers of every registered app, in registration order
        for app in self.apps:
            self._execute_handler(app, handler_name, packet)

    def _dispatch_lifecycle(self, event_name: str, isolate: bool = False):
        """Propagate lifecycle events (on_connect, on_tick, ...) to the apps.

        Follows the handler_errors policy; `isolate=True` forces the 'log'
        behavior regardless — used from stop(), where the shutdown sequence
        must complete and every app must still get its on_disconnect.
        """
        for app in self.apps:
            if hasattr(app, event_name):
                try:
                    getattr(app, event_name)()
                except Exception as e:
                    if self._fail_fast and not isolate:
                        raise
                    self.logger.error(
                        f"Error in {app.name}.{event_name}: {e}", exc_info=True
                    )

    def _execute_handler(self, instance: Any, handler_name: str, packet: Any):
        """Run a handler, applying the handler_errors policy to any error:
        'log' isolates it (logged with traceback, dispatch continues);
        'raise' propagates it (fail-fast — the dispatch worker hands it to
        the main thread, which stops the client)."""
        handler = getattr(instance, handler_name, None)
        if handler and callable(handler):
            try:
                handler(packet)
            except Exception as e:
                if self._fail_fast:
                    raise
                self.logger.error(
                    f"Error in {handler_name} of {instance.name}: {e}", exc_info=True
                )

    # Empty hooks for subclasses
    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_reconnect(self):
        pass

    def on_tick(self):
        pass
