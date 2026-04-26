"""
config/settings.py - Configuración central del proyecto
"""

from pathlib import Path
import logging
import logging.handlers
import os
import re
from typing import Dict, Any


class _InsimRotatingHandler(logging.handlers.RotatingFileHandler):
    """RotatingFileHandler que nombra los backups como insim1.log, insim2.log, ..."""

    @staticmethod
    def _namer(name: str) -> str:
        # name = "/path/insim.log.1"  →  "/path/insim1.log"
        return re.sub(r'^(.+?)(\.[^.]+)\.(\d+)$', r'\1\3\2', name)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.namer = self._namer


class _HighFreqFilter(logging.Filter):
    """Descarta registros generados por paquetes de alta frecuencia (MCI, NLP, OutSim)."""

    # Patrones específicos de los logs de alta frecuencia, no nombres de tipo genéricos.
    # 'ISP_MCI'/'ISP_NLP' eran demasiado amplios y filtraban logs legítimos (p.ej.
    # "Tipos de paquete activos: ..., ISP_MCI, ...").
    _PATTERNS = frozenset({'MCI PLID', 'NLP PLID', 'OutSim', 'OutGauge'})

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(p in msg for p in self._PATTERNS)
from lfs_insim.insim_enums import OSO, ISF

# ═══════════════════════════════════════════════════════════════════════════
# DIRECTORIOS
# ═══════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.parent  # Carpeta raíz del proyecto
LOGS_DIR = BASE_DIR / 'logs'             # Carpeta de logs

# Crear carpeta si no existe
LOGS_DIR.mkdir(exist_ok=True)

LFS_DIR = 'C:/LFS'

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE InSim (Conexión a LFS)
# ═══════════════════════════════════════════════════════════════════════════

INSIM_CONFIG: Dict[str, Any] = {
    # --- Conexión TCP (InSim Principal) ---
    'tcp_host': '127.0.0.1',        
    'tcp_port': 29999,              # Debe coincidir con /insim en LFS
    'tcp_buffer': 4096,             # 4KB es suficiente para la mayoría de paquetes
    
    # --- Conexión UDP (OutSim / NLP) ---
    'udp_host': '0.0.0.0',          # Escuchar en todas las interfaces
    'udp_port': 30000,              # Puerto local para recibir UDP (OutSim)
    'udp_buffer': 4096,

    # --- Configuración del Paquete de Inicialización (ISI) ---
    'insim_name': 'InSimApp',       # Nombre de la aplicación en LFS
    'admin_pass': 'abc',               # Contraseña de admin (si se requiere privilegios)
    
    # IMPORTANTE: Versión 10 para LFS 0.7F+
    'insim_ver': 10,                 
    
    'prefix': '!',             # Prefijo para comandos de chat (ej: !help)
    'interval': 10,                 # Intervalo para paquetes NLP/MCI (ms) - 10ms para control fluido
    'flags': 0,                     # Configurar con ISF
    
    # Configuración de usuario
    'user_name': 'AdrianPascarella'
}

OUT_CONFIG: Dict[str, Any] = {
    # Opciones de OutSim2 (qué bloques de datos envía LFS por UDP)
    # Combinación de flags OSO.* — ver insim_enums.OSO
    'outsim_opts': OSO.MAIN | OSO.INPUTS | OSO.TIME | OSO.DRIVE,

    # ID del OutSim (debe coincidir con "OutSim ID" en cfg.txt)
    'outsim_id': 1,

    # IP de destino del stream OutSim (normalmente el mismo host)
    'outsim_ip': '127.0.0.1',
}


# ═══════════════════════════════════════════════════════════════════════════
# SISTEMA DE LOGGING
# ═══════════════════════════════════════════════════════════════════════════

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'no_high_freq': {
            '()': 'config.settings._HighFreqFilter',
        },
    },
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            'datefmt': '%H:%M:%S'
        },
        'detailed': {
            'format': '[%(asctime)s] [%(name)s] [%(funcName)s] [%(levelname)s]: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'INFO',
            'filters': ['no_high_freq'],
        },
        'file': {
            'class': 'config.settings._InsimRotatingHandler',
            'filename': str(LOGS_DIR / 'insim.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 3,
            'formatter': 'detailed',
            'level': 'DEBUG',
            'encoding': 'utf-8',
            'filters': ['no_high_freq'],
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console', 'file'],
    },
}

def get_logger(name: str, log_filename: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Crea un logger configurado. 
    Si se especifica log_filename, crea un archivo separado para este logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter('[%(asctime)s] [%(name)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if log_filename:
        file_path = LOGS_DIR / log_filename
        fh = _InsimRotatingHandler(file_path, maxBytes=1024*1024, backupCount=1, encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    
    return logger

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DESEADA DE LFS (Para setup_lfs.py)
# ═══════════════════════════════════════════════════════════════════════════

# Definimos aquí qué opciones de cfg.txt necesitamos forzar.
# Usamos los enums para componer los flags hexadecimales.

DESIRED_LFS_CONFIG = {
    # OutSim (UDP Packet output)
    "OutSim ID": "1", # Activar OutSim
    "OutSim Opts": format(
        # Componer flags usando OSO (OutSim Opts)
        # OSO.TCP_HTTP (0x40) + OSO.UDP (0x80) suele ser común si queremos OutGauge o similar,
        # Pero para InSim/OutSim puro, suele bastar con OSO.UDP si usamos NLP.
        # Ajusta según necesidad. Si '0' deshabilita todo, queremos algo activo.
        OSO.MAIN | OSO.INPUTS | OSO.TIME | OSO.DRIVE, # STANDARD PACKET
        'x'
    ),
    "OutSim IP": "127.0.0.1",
    "OutSim Port": str(INSIM_CONFIG['udp_port']), # Debe coincidir con nuestra escucha
}


# ═══════════════════════════════════════════════════════════════════════════
# FUNCIÓN DE CONFIGURACIÓN CONSOLIDADA
# ═══════════════════════════════════════════════════════════════════════════

def get_config(custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Obtiene la configuración combinando INSIM_CONFIG con valores personalizados.
    
    Args:
        custom_config: Diccionario opcional con valores adicionales o de override
        
    Returns:
        Configuración completa combinada
    """
    config = {**INSIM_CONFIG, **OUT_CONFIG}

    # Aplicar configuración personalizada
    if custom_config:
        config.update(custom_config)

    return config