"""
lfs_insim/insim_packet_sender.py - Packet serialization and sending.

`encode_packet()` is the single serialization route (validate + prepare +
pack): a pure function with no socket involved. `send_packet()` encodes and
pushes the bytes through the global socket (P13: to be replaced by a
transport object owned by the client).
"""
import logging
import struct
import threading
from .insim_packet_class import PacketFunctions, ALLOWED_PACKETS
from .insim_state import get_socket_tcp, get_socket_udp
from .exceptions import InSimError, InSimPacketError, InSimConnectionError

logger = logging.getLogger(__name__)

# Global lock so packet sends are atomic per connection
_send_lock = threading.Lock()

# Packet types whose send logs are muted.
# Empty by default; each module adds its own with mute_send_logs().
_MUTED_SEND_TYPES: set[str] = set()


def mute_send_logs(*packet_types: str) -> None:
    """Mute the send logs (DEBUG) for the given packet types."""
    _MUTED_SEND_TYPES.update(packet_types)


def unmute_send_logs(*packet_types: str) -> None:
    """Re-enable the send logs (DEBUG) for the given packet types."""
    _MUTED_SEND_TYPES.difference_update(packet_types)


def encode_packet(packet: PacketFunctions) -> bytes:
    """
    Serialize a packet into the exact bytes LFS expects.

    Validates that the packet type is sendable, runs prepare() (string
    padding to 4-byte blocks, Size update) and packs every field
    little-endian. Pure function: no socket involved.
    """
    # 1. Safety check: is this a packet LFS accepts from an InSim program?
    if type(packet) not in ALLOWED_PACKETS:
        raise InSimPacketError(f"Packet {type(packet).__name__} is not in the allowed-send list.")

    # 2. Preparation: adjust strings (multiples of 4) and update Size
    packet.prepare()

    # 3. Get the instance's actual format and pack
    fmt_string = packet.get_struct_string()

    pkt_name = type(packet).__name__
    _muted = pkt_name in _MUTED_SEND_TYPES
    values = _extract_values(packet)
    if not _muted:
        logger.debug(f"Packing {pkt_name} with fmt={fmt_string}")
        logger.debug(f"Values to pack: {values}")

    try:
        return struct.pack(fmt_string, *values)
    except Exception as e:
        raise InSimPacketError(f"Error packing {pkt_name}: {e}",
                               packet_type=pkt_name) from e


def send_packet(packet: PacketFunctions, use_udp: bool = False):
    """
    Encode a packet and send it to LFS through the global socket.
    """
    data = encode_packet(packet)
    pkt_name = type(packet).__name__
    _muted = pkt_name in _MUTED_SEND_TYPES

    try:
        sock = get_socket_udp() if use_udp else get_socket_tcp()
        if sock:
            with _send_lock:
                sock.sendall(data)
            if not _muted:
                logger.debug(f"Packet {pkt_name} sent successfully.")
            return True
        else:
            raise InSimConnectionError("Could not send packet: socket not available (disconnected?)", host=None, port=None)
    except Exception as e:
        if isinstance(e, InSimError):
            raise
        logger.error(f"Network error sending packet {pkt_name}: {e}")
        raise InSimConnectionError(f"Network error sending packet {pkt_name}: {e}") from e

def _extract_values(obj):
    from dataclasses import fields
    import struct
    extracted = []

    for f in fields(obj):
        fmt_meta = f.metadata.get('fmt')
        if fmt_meta is None:
            continue

        val = getattr(obj, f.name)

        # --- MANEJO DE STRINGS (Optimizado) ---
        if isinstance(val, str):
            # Calcular target_size una vez
            if isinstance(fmt_meta, str):
                # Estático: '16s' -> 16
                target_size = int(fmt_meta[:-1])
            elif isinstance(fmt_meta, tuple):
                # Variable/Tupla: ('s', 128) o ('s', None)
                # La función prepare() de PacketFunctions ya debería haber ajustado el string
                # pero por seguridad recalculamos el padding de 4 bytes
                current_len = len(val) + 1 # +1 para null terminator
                target_size = (current_len + 3) & ~3
            else:
                target_size = len(val)

            # Codificación rápida y relleno
            try:
                # encode('latin-1') es más rápido que 'utf-8' y estándar en LFS
                b_val = val.encode('latin-1', 'replace')
                # Rellenar con ceros hasta el target_size (asegura null terminator si cabe)
                final_bytes = b_val.ljust(target_size, b'\x00')
                # Recortar si excede (no debería si prepare() se llamó antes, pero por seguridad)
                if len(final_bytes) > target_size:
                    final_bytes = final_bytes[:target_size]
                    # Asegurar último byte 0 si es texto estricto (opcional, LFS suele leer hasta \0)
                    if target_size > 0:
                        final_bytes = final_bytes[:-1] + b'\x00'

                extracted.append(final_bytes)
            except Exception:
                extracted.append(b'\x00' * target_size)

        # --- MANEJO DE LISTAS Y TUPLAS VARIABLES ---
        elif isinstance(fmt_meta, tuple):
            inner_fmt, limit = fmt_meta
            actual_items = val if val is not None else []

            # Si es un string ('s', limit), el string ya fue procesado arriba
            if inner_fmt == 's':
                pass
            else:
                # Ya no rellenamos (padding). Solo procesamos hasta el límite indicado.
                # Si limit es None, procesamos todo.
                if limit is not None:
                    items_to_process = actual_items[:limit]
                else:
                    items_to_process = actual_items

                for item in items_to_process:
                    if hasattr(item, 'get_fmt'):
                        extracted.extend(_extract_values(item))
                    else:
                        extracted.append(item)

        # --- SUBPAQUETES ---
        elif hasattr(val, 'get_fmt'):
            extracted.extend(_extract_values(val))

        # --- PRIMITIVOS (Convertir Enums a int) ---
        else:
            if hasattr(val, 'value'): # Es un Enum
                extracted.append(int(val.value))
            else:
                extracted.append(val)

    return extracted
