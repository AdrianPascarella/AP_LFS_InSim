"""
lfs_insim/insim_app.py - Clase base para módulos componibles.

Permite que cada "InSim" sea una pieza de un puzzle, declarando qué otros
módulos necesita para funcionar y facilitando el acceso a ellos.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from .insim_client import InSimClient
from .packet_sender_mixin import PacketSenderMixin

if TYPE_CHECKING:
    from .insim_loader import InSimLoader

logger = logging.getLogger(__name__)

class InSimApp(InSimClient, PacketSenderMixin):
    """
    Clase base para todos los módulos del framework.
    
    Attributes:
        dependencies: Lista de nombres de otros módulos requeridos.
        version: Versión del módulo (leída de insim.json).
        description: Descripción del módulo.
    """
    
    dependencies: List[str] = []
    version: str = "0.0.0"
    description: str = ""

    def __init__(
        self,
        config: Optional[dict] = None,
        name: Optional[str] = None,
        _loader: Optional['InSimLoader'] = None,
        _insim_path: Optional[Path] = None,
    ):
        # Si no se pasa nombre, usamos el de la clase
        name = name or self.__class__.__name__
        super().__init__(config=config, name=name)

        self._loader = _loader
        self._insim_path = _insim_path
        self._module_instances: Dict[str, 'InSimApp'] = {}

        # Copiar la lista de dependencias para que _load_metadata() no mute
        # el atributo de clase compartido entre todos los módulos.
        self.dependencies = list(self.__class__.dependencies)
        
        # 1. Cargar metadatos del archivo insim.json si existe
        if self._insim_path:
            self._load_metadata()

    def _load_metadata(self):
        """Carga la configuración y metadatos desde el directorio del módulo."""
        manifest_path = self._insim_path / "insim.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.version = data.get("version", self.version)
                    self.description = data.get("description", self.description)
                    # Si el JSON define dependencias, las añadimos a las de la clase
                    json_deps = data.get("insim_dependencies", {})
                    for dep_name in json_deps.keys():
                        if dep_name not in self.dependencies:
                            self.dependencies.append(dep_name)
            except Exception as e:
                self.logger.warning(f"No se pudo cargar el manifiesto: {e}")

    def _resolve_dependencies(self):
        """
        Solicita al loader las instancias de los módulos declarados.
        Este método es llamado automáticamente por el Loader.
        """
        if not self._loader:
            return

        for dep_spec in self.dependencies:
            # Extraer solo el nombre (por si viene como "tracker>=1.0")
            dep_name = dep_spec.split('>')[0].split('=')[0].split('<')[0].strip()
            
            try:
                # El loader devuelve la instancia (nueva o de la caché)
                instance = self._loader.load(dep_name)
                self._module_instances[dep_name] = instance
                self.logger.debug(f"Dependencia '{dep_name}' resuelta para {self.name}")
            except Exception as e:
                self.logger.error(f"Error crítico: {self.name} requiere '{dep_name}' pero no se pudo cargar: {e}")
                raise

    def get_insim(self, name: str) -> Optional['InSimApp']:
        """
        Obtiene la instancia de un módulo del que dependemos.
        
        Uso: 
            tracker = self.get_insim("player_tracker")
            p = tracker.get_player(6)
        """
        # 1. Buscar en dependencias directas
        if name in self._module_instances:
            return self._module_instances[name]
        
        # 2. Si el loader tiene la instancia globalmente, la pedimos
        if self._loader and name in self._loader._instances:
            return self._loader._instances[name]
            
        return None

    # send_ISP_*() y __getattr__ heredados de PacketSenderMixin