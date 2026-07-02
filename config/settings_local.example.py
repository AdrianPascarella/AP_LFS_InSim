"""
config/settings_local.example.py — Plantilla de configuración local.

Copia este archivo como `config/settings_local.py` (NO se versiona) y ajusta
los valores de tu máquina. `settings.py` lo carga automáticamente al final.
También puedes usar las variables de entorno LFS_ADMIN_PASS y LFS_DIR.
"""

# Ruta de tu instalación de LFS
LFS_DIR = 'C:/LFS'

# Overrides de INSIM_CONFIG (solo las claves que quieras cambiar)
INSIM_CONFIG_OVERRIDES = {
    'admin_pass': '',            # Contraseña /admin de tu LFS
    'user_name':  'TuUsuario',   # Tu nombre de usuario en LFS
}
