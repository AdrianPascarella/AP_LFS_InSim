"""
insim_packet_decoders.py - Motor de decodificación de paquetes InSim/OutSim.

Este módulo contiene la lógica recursiva para deserializar los bytes
recibidos de LFS en objetos Python tipados.

Arquitectura:
    1. decode_packet() - Punto de entrada, identifica el tipo de paquete
    2. _unpacker() - Inicia la cadena de decodificación
    3. _decode_recursive() - Motor recursivo que maneja todos los casos
    4. _get_static_size() - Calcula tamaños para campos de longitud variable
"""
import struct
import logging
from typing import Any, Optional, Tuple, Type, Union

from .insim_packet_class import INSIM_PACKETS, OUTSIM_PACKETS
from .exceptions import InSimPacketError

logger = logging.getLogger(__name__)


def decode_packet(data: bytes) -> Optional[Any]:
    """
    Punto de entrada principal para decodificar paquetes.
    """
    if not data:
        return None

    packet_len = len(data)

    # --- PRIORIDAD 1: INSIM (Identificación por Firma Matemática TCP) ---
    # En InSim, el primer byte (Size) multiplicado por 4 SIEMPRE es el tamaño total.
    # Usamos esta firma fuerte antes de intentar adivinar por el tamaño de OutSim.
    if packet_len >= 2 and data[0] * 4 == packet_len and data[1] in INSIM_PACKETS:
        packet_type = data[1]
        cls = INSIM_PACKETS[packet_type]
        try:
            return _unpacker(data, cls)
        except Exception as e:
            raise InSimPacketError(f"Fallo al decodificar paquete InSim tipo {packet_type}: {e}", 
                                   packet_type=packet_type, data=data.hex()) from e

    # --- PRIORIDAD 2: OUTSIM / OUTGAUGE (Identificación por tamaño UDP) ---
    # Si no cumple la regla estricta de InSim, asumimos que es un flujo UDP ciego.
    if packet_len in OUTSIM_PACKETS:
        cls = OUTSIM_PACKETS[packet_len]
        try:
            return _unpacker(data, cls)
        except Exception as e:
            logger.debug(f"OutSim decode failed for size {packet_len}: {e}")

    logger.warning(f"Paquete desconocido recibido: len={packet_len}, hex={data[:8].hex()}...")
    return None


def _unpacker(data: bytes, cls: Type) -> Any:
    """
    Crea una instancia de la clase y lanza la decodificación recursiva.
    
    Args:
        data: Bytes a decodificar
        cls: Clase del paquete (ej: ISP_MCI, OutSimPack)
        
    Returns:
        Instancia poblada del paquete
    """
    obj, _ = _decode_recursive(data, cls)
    return obj


def _decode_recursive(buffer: bytes, fmt: Any) -> Tuple[Any, int]:
    """
    Motor de decodificación recursivo.
    
    Maneja los siguientes casos de formato:
    - str: Formato struct primitivo ('B', 'I', 'f', '24s', etc.)
    - type: Subpaquete/clase (Vec, CompCar, etc.)
    - tuple: Repetición o variable ((cls, count) o ('s', length))
    - list: Secuencia fija de formatos [fmt1, fmt2, ...]
    
    Args:
        buffer: Bytes restantes por procesar
        fmt: Especificación del formato a decodificar
        
    Returns:
        Tupla (valor_decodificado, bytes_consumidos)
    """
    # --- CASO 1: FORMATO PRIMITIVO (str: 'B', 'I', 'f', etc.) ---
    if isinstance(fmt, str):
        size = struct.calcsize('<' + fmt)
        if len(buffer) < size:
            return None, 0
        
        val = struct.unpack('<' + fmt, buffer[:size])[0]
        
        # Limpieza de strings
        if fmt.endswith('s') and isinstance(val, bytes):
            val = val.decode('latin-1', errors='replace').split('\x00')[0].strip()
        
        return val, size

    # --- CASO 2: SUBPAQUETE / CLASE (type: Vec, Vector, CompCar...) ---
    elif isinstance(fmt, type):
        obj_instance = fmt()
        structure = fmt.metadata_to_dict()

        total_consumed = 0
        for field_name, field_fmt in structure.items():
            try:
                val, consumed = _decode_recursive(buffer[total_consumed:], field_fmt)
            except Exception as e:
                raise InSimPacketError(
                    f"Fallo al decodificar campo '{field_name}' en {fmt.__name__}: {e}"
                ) from e
            setattr(obj_instance, field_name, val)
            total_consumed += consumed

        return obj_instance, total_consumed

    # --- CASO 3: REPETICIÓN O VARIABLE (tuple: ('s', 16) o (Clase, None)) ---
    elif isinstance(fmt, tuple):
        inner_fmt, limit = fmt
        
        # Strings con longitud fija
        if inner_fmt == 's':
            size = limit if limit else len(buffer)
            val = buffer[:size].decode('latin-1', errors='replace').split('\x00')[0].strip()
            return val, size
        
        # Listas de subpaquetes
        items = []
        total_consumed = 0
        item_size = _get_static_size(inner_fmt)
        
        if item_size > 0:
            max_count = limit if limit is not None else (len(buffer) // item_size)
            for _ in range(max_count):
                if len(buffer[total_consumed:]) < item_size:
                    break
                val, consumed = _decode_recursive(buffer[total_consumed:], inner_fmt)
                if val is not None:
                    items.append(val)
                    total_consumed += consumed
        return items, total_consumed

    # --- CASO 4: LISTA FIJA (list: [fmt1, fmt2, ...]) ---
    elif isinstance(fmt, list):
        items = []
        total_consumed = 0
        for item_fmt in fmt:
            val, consumed = _decode_recursive(buffer[total_consumed:], item_fmt)
            items.append(val)
            total_consumed += consumed
        return items, total_consumed

    return None, 0


def _get_static_size(fmt: Any) -> int:
    """
    Calcula el tamaño en bytes de un formato.
    
    Usado para determinar cuántos elementos caben en un buffer
    cuando se decodifican listas de longitud variable.
    
    Args:
        fmt: Especificación del formato
        
    Returns:
        Tamaño en bytes, o 0 si es variable/desconocido
    """
    if isinstance(fmt, str):
        return struct.calcsize('<' + fmt)
    
    if isinstance(fmt, type):
        structure = fmt.metadata_to_dict()
        return sum(_get_static_size(v) for v in structure.values())
    
    if isinstance(fmt, list):
        return sum(_get_static_size(v) for v in fmt)
    
    if isinstance(fmt, tuple):
        inner_fmt, limit = fmt
        if limit:
            return _get_static_size(inner_fmt) * limit
        return 0

    return 0