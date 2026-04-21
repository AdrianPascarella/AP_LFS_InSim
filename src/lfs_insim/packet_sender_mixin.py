"""
lfs_insim/packet_sender_mixin.py - Mixin de envío de paquetes.

Permite que cualquier clase (que NO sea InSimApp) pueda enviar paquetes
usando la misma API cómoda: self.send(packet) y self.send_ISP_XXX(**kwargs).
"""


class PacketSenderMixin:
    """
    Mixin ligero que añade capacidad de envío de paquetes a cualquier clase.

    Uso:
        class MiClase(PacketSenderMixin):
            def algo(self):
                self.send(ISP_MSL(Msg="Hola"))
                self.send_ISP_MSL(Msg="Hola")   # equivalente
    """

    def send(self, packet) -> None:
        from lfs_insim.insim_packet_sender import send_packet
        send_packet(packet)

    def __getattr__(self, name: str):
        if name.startswith('send_ISP_'):
            packet_name = name[5:]  # extrae 'ISP_XXX'
            from lfs_insim import insim_packet_class as _packets
            packet_class = getattr(_packets, packet_name, None)
            if packet_class is None:
                raise AttributeError(f"El paquete '{packet_name}' no existe en el protocolo.")

            def _send_wrapper(**kwargs):
                self.send(packet_class(**kwargs))

            return _send_wrapper

        raise AttributeError(f"'{self.__class__.__name__}' no tiene el atributo '{name}'")
