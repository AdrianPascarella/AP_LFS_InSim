import logging
import struct
import time
import threading
from .insim_packet_class import PacketFunctions, ALLOWED_PACKETS
from .insim_state import get_socket_tcp, get_socket_udp
from .exceptions import InSimError, InSimPacketError, InSimConnectionError

logger = logging.getLogger(__name__)

# Lock global para asegurar que los envíos de paquetes sean atómicos por conexión
_send_lock = threading.Lock()

# Tipos de paquete cuyos logs de envío están silenciados.
# ISP_AIC se silencia por defecto (alta frecuencia — 1 por IA por tick).
_MUTED_SEND_TYPES: set[str] = {'ISP_AIC'}


def mute_send_logs(*packet_types: str) -> None:
    """Silencia los logs de envío (DEBUG) para los tipos de paquete indicados."""
    _MUTED_SEND_TYPES.update(packet_types)


def unmute_send_logs(*packet_types: str) -> None:
    """Re-activa los logs de envío (DEBUG) para los tipos de paquete indicados."""
    _MUTED_SEND_TYPES.difference_update(packet_types)


def send_packet(packet: PacketFunctions, use_udp: bool = False):
    """
    Prepara, valida y envía un paquete a LFS.
    """
    # 1. Verificación de seguridad: ¿Es un paquete que LFS permite enviar?
    # Usamos type(packet) para comparar la clase con la lista de permitidos
    if type(packet) not in ALLOWED_PACKETS:
        raise InSimPacketError(f"El paquete {type(packet).__name__} no está en la lista de permitidos para envío.")

    # 2. Preparación: Ajustar strings (múltiplos de 4) y actualizar Size
    packet.prepare()

    # 3. Obtener el formato real de la instancia y empaquetar
    fmt_string = packet.get_struct_string()
    
    # Extraemos los valores en el orden exacto del formato
    # Usamos una función auxiliar para aplanar los valores del objeto
    pkt_name = type(packet).__name__
    _muted = pkt_name in _MUTED_SEND_TYPES
    values = _extract_values(packet)
    if not _muted:
        logger.debug(f"Packing {pkt_name} with fmt={fmt_string}")
        logger.debug(f"Values to pack: {values}")

    try:
        data = struct.pack(fmt_string, *values)
    except Exception as e:
        raise InSimPacketError(f"Error al empaquetar {pkt_name}: {e}",
                              packet_type=pkt_name) from e

    # 4. Envío por el socket correspondiente
    try:
        sock = get_socket_udp() if use_udp else get_socket_tcp()
        if sock:
            with _send_lock:
                sock.sendall(data)
            if not _muted:
                logger.debug(f"Paquete {pkt_name} enviado con éxito.")
            return True
        else:
            raise InSimConnectionError("No se pudo enviar el paquete: Socket no disponible (¿desconectado?)", host=None, port=None)
    except Exception as e:
        if isinstance(e, InSimError):
            raise
        logger.error(f"Error de red al enviar paquete {pkt_name}: {e}")
        raise InSimConnectionError(f"Error de red al enviar paquete {pkt_name}: {e}") from e

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