"""
lfs_insim/packet_sender_mixin.py - Packet sending mixin.

Gives any class the convenient sending API: self.send(packet) and
self.send_ISP_XXX(**kwargs). Packets travel through a client (P13):
`self.client` when the host class has one (InSimApps get it from
client.register), or the process's default client as a fallback for helper
classes (e.g. utils.Command / CMDManager).
"""


class PacketSenderMixin:
    """
    Lightweight mixin that adds packet-sending capability to any class.

    Usage:
        class MyClass(PacketSenderMixin):
            def something(self):
                self.send(ISP_MSL(Msg="Hello"))
                self.send_ISP_MSL(Msg="Hello")   # equivalent
    """

    def send(self, packet) -> None:
        client = getattr(self, 'client', None)
        if client is None:
            from lfs_insim.insim_state import get_insim_client
            client = get_insim_client()
        if client is None:
            from lfs_insim.exceptions import InSimConnectionError
            raise InSimConnectionError(
                "No client available to send the packet: register the app with "
                "client.register(app) or create an InSimClient first.")
        client.send(packet)

    def __getattr__(self, name: str):
        if name.startswith('send_ISP_'):
            packet_name = name[5:]  # extracts 'ISP_XXX'
            from lfs_insim import packets as _packets
            packet_class = getattr(_packets, packet_name, None)
            if packet_class is None:
                raise AttributeError(f"Packet '{packet_name}' does not exist in the protocol.")

            def _send_wrapper(**kwargs):
                self.send(packet_class(**kwargs))

            return _send_wrapper

        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
