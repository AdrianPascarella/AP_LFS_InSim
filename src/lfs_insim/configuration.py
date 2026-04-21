import os
import shutil
import logging
from typing import Dict, Any, Optional
from .exceptions import InSimConfigurationError

class LFSConfigManager:
    """
    Gestor para leer y modificar el archivo cfg.txt de LFS de forma segura.
    """
    
    def __init__(self, lfs_dir: str):
        self.lfs_dir = lfs_dir
        self.cfg_path = os.path.join(lfs_dir, "cfg.txt")
        self.logger = logging.getLogger("LFSConfigManager")

    def validate_path(self) -> bool:
        """Verifica si el archivo cfg.txt existe."""
        if not os.path.exists(self.cfg_path):
            raise InSimConfigurationError(f"Archivo crítico no encontrado: {self.cfg_path}. Verifica la ruta de LFS.")
        return True

    def read_config(self) -> Dict[str, str]:
        """
        Lee el archivo cfg.txt y retorna un dict con las claves y valores encontrados.
        Nota: LFS usa formato 'Clave Valor'.
        """
        config = {}
        self.validate_path()  # lanza InSimConfigurationError si no existe

        try:
            with open(self.cfg_path, 'r', encoding='latin-1') as f:
                for line in f:
                    line = line.strip()
                    # Ignorar comentarios y líneas vacías //
                    if not line or line.startswith('//') or line.startswith(';'):
                        continue
                        
                    # Intentar separar por primer espacio
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        key, value = parts
                        config[key] = value
        except Exception as e:
            raise InSimConfigurationError(f"Error al leer la configuración de LFS ({self.cfg_path}): {e}") from e
            
        return config

    def update_config(self, updates: Dict[str, str], backup: bool = True) -> bool:
        """
        Actualiza claves específicas en cfg.txt manteniendo el resto del contenido y formato.
        
        Args:
            updates: Dict con { "Clave": "NuevoValor" }
            backup: Si es True, crea cfg.txt.bak antes de guardar.
        """
        self.validate_path()  # lanza InSimConfigurationError si no existe

        if backup:
            backup_path = self.cfg_path + ".bak"
            try:
                shutil.copy2(self.cfg_path, backup_path)
                self.logger.info(f"Backup creado: {backup_path}")
            except Exception as e:
                raise InSimConfigurationError(f"Fallo al crear el backup de seguridad de cfg.txt: {e}") from e

        try:
            # Leemos todas las líneas para reescribirlas ordenadas
            with open(self.cfg_path, 'r', encoding='latin-1') as f:
                lines = f.readlines()

            new_lines = []
            keys_updated = set()

            for line in lines:
                original_line = line
                stripped = line.strip()
                
                # Si es comentario o vacío, lo dejamos igual
                if not stripped or stripped.startswith('//') or stripped.startswith(';'):
                    new_lines.append(original_line)
                    continue

                # Chequeamos si esta línea corresponde a alguna key a actualizar
                parts = stripped.split(maxsplit=1)
                
                # Lógica de coincidencia robusta (LFS keys a veces tienen espacios, pero cfg.txt suele ser Key Value)
                # En cfg.txt las claves multi-palabra como "OutSim Opts" suelen empezar la línea.
                # Estrategia: Ver si la línea EMPIEZA con alguna de las claves de updates
                
                matched_key = None
                for key in updates:
                    # Buscamos coincidencia exacta del inicio de la línea con la key + espacio
                    # Ej: "OutSim Opts ffx000" -> startswith("OutSim Opts")
                    if stripped.startswith(key):
                        # Verificar que lo que sigue es un espacio o tab, para no matchear parcialmente
                        # "OutSim" vs "OutSim Opts"
                        remaining = stripped[len(key):]
                        if remaining and remaining[0].isspace():
                            matched_key = key
                            break
                            
                if matched_key:
                    # Reemplazamos
                    new_value = updates[matched_key]
                    # Mantenemos indentación original si hubiera? cfg.txt suele ser plano.
                    new_lines.append(f"{matched_key} {new_value}\n")
                    keys_updated.add(matched_key)
                    self.logger.info(f"Actualizando '{matched_key}': {new_value}")
                else:
                    new_lines.append(original_line)

            # (Opcional) Si hay keys en updates que NO estaban en el archivo, ¿las agregamos al final?
            # Por seguridad en LFS, mejor no agregar cosas arbitrarias si no existen, a menos que sepamos que es seguro.
            # Lo dejaremos así por ahora: solo actualiza si existe.

            # Escribir cambios
            with open(self.cfg_path, 'w', encoding='latin-1') as f:
                f.writelines(new_lines)
                
            return True

        except Exception as e:
            raise InSimConfigurationError(f"Error al escribir cambios en cfg.txt de LFS: {e}") from e
