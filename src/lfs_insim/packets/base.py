from dataclasses import dataclass, field, fields, is_dataclass
from typing import Optional, List, Any
import struct

def repeat(fmt: str|dict, times) -> list:
    return [fmt for _ in range(times)]

class PacketFunctions:

    _metadata_cache = None

    @classmethod
    def metadata_to_dict(cls) -> dict:
        """Genera y cachea la estructura estática del paquete."""
        if cls._metadata_cache is None:
            # Solo trabajamos si es un dataclass
            if not is_dataclass(cls):
                return {}
            
            # Construimos el mapa una sola vez
            cls._metadata_cache = {
                f.name: f.metadata.get('fmt') 
                for f in fields(cls) 
                if f.metadata.get('fmt') is not None
            }
        return cls._metadata_cache

    def get_fmt(self) -> dict:
        """
        Resuelve el formato real de ESTA instancia.
        """
        resolved = {}
        for f in fields(self):
            fmt = f.metadata.get('fmt')
            if fmt is None:
                continue
            
            # Obtenemos el valor real de la instancia para este campo
            val = getattr(self, f.name)

            # CASO VARIABLE O FIJO: {'fmt': (str|dict|type, None|int)}
            if isinstance(fmt, tuple):
                inner_fmt, limit = fmt
                actual_count = len(val) if val is not None else 0
                
                # Si se especifica un conteo (limit no es None), tratar como variable con límite
                if limit is not None:
                    # El conteo real es el número de elementos que tenga la instancia,
                    # pero sin exceder el límite establecido en el formato.
                    final_count = min(actual_count, limit)
                else:
                    # Si el límite es None, es puramente variable
                    final_count = actual_count

                if inner_fmt == 's':
                    resolved[f.name] = f"{final_count}s"
                else:
                    # Si es una clase, obtener su estructura
                    if isinstance(inner_fmt, type):
                        inner_fmt_struct = inner_fmt.metadata_to_dict()
                    else:
                        inner_fmt_struct = inner_fmt
                        
                    resolved[f.name] = repeat(inner_fmt_struct, final_count)

            # CASO SUBPAQUETE: {'fmt': type}
            elif isinstance(fmt, type):
                if hasattr(val, 'get_fmt'):
                    resolved[f.name] = val.get_fmt()
                else:
                    resolved[f.name] = fmt

            # CASO PRIMITIVO O LISTA FIJA
            else:
                resolved[f.name] = fmt
                
        return resolved

    def get_struct_string(self) -> str:
        """
        Convierte el diccionario de get_fmt() en un string compatible con struct.
        """
        fmt_dict = self.get_fmt()
        
        def flatten(structure):
            s = ""
            if isinstance(structure, str):
                s += structure
            elif isinstance(structure, dict):
                for v in structure.values():
                    s += flatten(v)
            elif isinstance(structure, list):
                for item in structure:
                    s += flatten(item)
            elif is_dataclass(structure) and isinstance(structure, type):
                # Tipo de sub-dataclass en una lista de repeat(SubClass, N)
                s += flatten(structure.metadata_to_dict())
            return s

        return "<" + flatten(fmt_dict)

    def get_size(self) -> int:
        """Calcula el tamaño real en bytes."""
        return struct.calcsize(self.get_struct_string())

    def validate_string_lengths(self) -> None:
        """Ajusta los strings según las reglas de LFS (padding, truncado)."""
        for f in fields(self):
            fmt = f.metadata.get('fmt')
            
            if isinstance(fmt, tuple) and fmt[0] == 's':
                _, limit = fmt
                current_val = getattr(self, f.name)
                
                if not isinstance(current_val, str):
                    continue

                new_val = current_val

                # 1. Truncar (dejamos espacio para el null terminator)
                if isinstance(limit, int):
                    if len(new_val) >= limit:
                        new_val = new_val[:limit - 1]

                # 2. Relleno (padding) a bloque de 4 con null bytes, incluyendo
                # el null terminator dentro del bloque alineado.
                if new_val:
                    new_val += "\x00"
                    remainder = len(new_val) % 4
                    if remainder != 0:
                        new_val += "\x00" * (4 - remainder)

                setattr(self, f.name, new_val)

    def set_insim_size(self) -> None:
        """Actualiza el byte 'Size' para InSim."""
        if hasattr(self, "Size"):
            real_bytes = self.get_size()
            self.Size = real_bytes // 4

    def prepare(self) -> None:
        """Prepara el paquete para ser enviado."""
        self.validate_string_lengths()
        self.set_insim_size()
