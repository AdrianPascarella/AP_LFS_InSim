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
from lfs_insim.insim_enums import ISF

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
    'tcp_host':   '127.0.0.1',
    'tcp_port':   29999,        # Debe coincidir con /insim en LFS
    'tcp_buffer': 4096,

    # --- Configuración del Paquete de Inicialización (ISI) ---
    'insim_name': 'InSimApp',
    'admin_pass': 'abc',
    'insim_ver':  10,           # InSim v10 para LFS 0.7F+
    'prefix':     '!',          # Prefijo para comandos de chat
    'interval':   10,           # Intervalo NLP/MCI en ms
    'flags':      0,

    # Configuración de usuario
    'user_name': 'AdrianPascarella',

    # --- UDP (OutSim / OutGauge) ---
    # Puerto en el que este proceso escucha paquetes UDP de LFS.
    # Debe coincidir con OutSim Port en cfg.txt de LFS.
    # El socket UDP solo se abre si algún módulo declara outsim_opts
    # en set_outsim() — este valor configura el puerto, no lo activa.
    'udp_port':   30000,
    'udp_host':   '0.0.0.0',
    'udp_buffer': 4096,
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
# FUNCIÓN DE CONFIGURACIÓN CONSOLIDADA
# ═══════════════════════════════════════════════════════════════════════════

def get_config(custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Retorna INSIM_CONFIG fusionado con cualquier override personalizado."""
    config = dict(INSIM_CONFIG)
    if custom_config:
        config.update(custom_config)
    return config