import sys
import os
import logging

# Añadir raíz al path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

try:
    from config.settings import LFS_DIR, DESIRED_LFS_CONFIG
    from src.lfs_insim.configuration import LFSConfigManager
except ImportError as e:
    logging.error(f"Error importando módulos del proyecto: {e}")
    sys.exit(1)

def run_setup():
    print("=== Herramienta de Configuración LFS ===")
    print(f"Directorio LFS: {LFS_DIR}")
    
    manager = LFSConfigManager(LFS_DIR)
    
    if not manager.validate_path():
        print("❌ CRÍTICO: No se puede proceder sin un cfg.txt válido.")
        return

    current_config = manager.read_config()
    diffs = {}

    print("\nVerificando configuración...")
    all_ok = True
    
    for key, desired_val in DESIRED_LFS_CONFIG.items():
        current_val = current_config.get(key)
        
        # Comparación insensible a mayúsculas para valores hex a veces
        if current_val != desired_val:
            # Check especial para hex (ej: 80 vs 00000080)
            try:
                # Si ambos son hex válidos
                if int(current_val, 16) == int(desired_val, 16):
                    continue
            except:
                pass # No eran números comparables
            
            print(f"  [!] DIFERENCIA en {key}:")
            print(f"      Actual: {current_val}")
            print(f"      Deseado: {desired_val}")
            diffs[key] = desired_val
            all_ok = False
        else:
            print(f"  [✓] {key} está correcto ({current_val})")

    if all_ok:
        print("\n✅ Todo está correctamente configurado.")
    else:
        print("\n⚠️ Se encontraron diferencias.")
        resp = input("¿Quieres aplicar los cambios ahora? (y/n): ").strip().lower()
        
        if resp == 'y':
            print("Aplicando cambios...")
            if manager.update_config(diffs):
                print("\n✅ Configuración actualizada con éxito.")
                print("NOTA: Debes reiniciar LFS para que los cambios surtan efecto.")
            else:
                print("\n❌ Error al guardar la configuración.")
        else:
            print("Operación cancelada. No se hicieron cambios.")

if __name__ == "__main__":
    run_setup()
