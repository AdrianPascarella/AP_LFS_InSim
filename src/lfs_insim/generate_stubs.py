"""
lfs_insim/generate_stubs.py - Generador de Type Hints.

Analiza las clases de paquetes (dataclasses) y genera firmas de métodos 
para InSimApp, permitiendo autocompletado en métodos on_ISP_* y send_ISP_*.
"""

import sys
from pathlib import Path
from dataclasses import fields, is_dataclass
import inspect
from typing import Any

# Asegurar que podemos importar el framework localmente
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from lfs_insim.packets import RECEIVE, SEND
from lfs_insim import insim_enums

def _get_type_hint(field_obj) -> str:
    """Traduce tipos de Python/Enums a strings para el stub."""
    f_type = field_obj.type
    
    # Manejo de tipos opcionales o unions simples
    if hasattr(f_type, "__name__"):
        return f_type.__name__
    
    # Caso para tipos más complejos (listas, tuplas)
    return str(f_type).replace("typing.", "")

def generate_insim_app_stub() -> str:
    """Genera el contenido para insim_app.pyi"""
    
    header = [
        '"""',
        'ARCHIVO GENERADO AUTOMÁTICAMENTE - NO EDITAR MANUALMENTE',
        'Regenerar con: python -m lfs_insim.generate_stubs',
        '"""',
        'from typing import List, Optional, Any, Union, Dict',
        'from pathlib import Path',
        'from .insim_client import InSimClient',
        'from .packets import *',
        'from .insim_enums import *',
        '',
        'class InSimApp(InSimClient):',
        '    dependencies: List[str]',
        '    version: str',
        '    description: str',
        '    client: InSimClient',
        ''
    ]

    body = []

    # 1. Stubs para RECEPCIÓN (on_ISP_*)
    body.append("    # --- Handlers de Recepción ---")
    for pkt_name, pkt_class in vars(RECEIVE).items():
        if pkt_name.startswith('_'):
            continue
        body.append(f"    def on_{pkt_name}(self, packet: {pkt_name}) -> None: ...")

    body.append("")

    # 2. Stubs para ENVÍO (send_ISP_*)
    body.append("    # --- Métodos Dinámicos de Envío ---")
    for pkt_name, pkt_class in vars(SEND).items():
        if pkt_name.startswith('_'):
            continue
        if not is_dataclass(pkt_class):
            continue
            
        # Extraer campos para que el IDE sugiera los argumentos correctos
        params = []
        for field in fields(pkt_class):
            if field.name in ['Size', 'Type']: continue # Campos automáticos
            
            hint = _get_type_hint(field)
            # Intentar obtener valor por defecto
            default = "..." 
            params.append(f"{field.name}: {hint} = {default}")
        
        params_str = ", ".join(params)
        body.append(f"    def send_{pkt_name}(self, {params_str}) -> None: ...")

    footer = [
        '',
        '    def get_insim(self, name: str) -> Optional["InSimApp"]: ...',
        '    def _resolve_dependencies(self) -> None: ...'
    ]

    return "\n".join(header + body + footer)

def main():
    """Punto de entrada para la generación."""
    print("Generando archivos de interfaz (stubs)...")

    try:
        stub_content = generate_insim_app_stub()
        output_path = Path(__file__).parent / "insim_app.pyi"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(stub_content)

        print(f"Stub generado en: {output_path}")
        print("Reinicia tu IDE si no ves los cambios en el autocompletado.")

    except Exception as e:
        print(f"Error generando stubs: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()