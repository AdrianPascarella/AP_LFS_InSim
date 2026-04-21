import importlib.util
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from .exceptions import InSimModuleError
import lfs_insim.insim_state as insim_state


def _parse_version(version_str: str) -> tuple:
    """Convierte '1.2.3' en (1, 2, 3) para comparación."""
    parts = re.split(r'[.\-]', version_str.strip())
    result = []
    for p in parts[:3]:
        try:
            result.append(int(p))
        except ValueError:
            result.append(0)
    while len(result) < 3:
        result.append(0)
    return tuple(result)


def _check_version(actual: str, constraint: str) -> bool:
    """
    Comprueba si `actual` satisface `constraint`.
    Soporta: >=, <=, >, <, ==, != y versión exacta sin operador.
    """
    constraint = constraint.strip()
    if not constraint:
        return True

    match = re.match(r'^(>=|<=|>|<|==|!=)?\s*(.+)$', constraint)
    if not match:
        return True

    op, required_str = match.group(1), match.group(2)
    actual_t = _parse_version(actual)
    required_t = _parse_version(required_str)

    if op is None or op == '==':
        return actual_t == required_t
    if op == '!=':
        return actual_t != required_t
    if op == '>=':
        return actual_t >= required_t
    if op == '<=':
        return actual_t <= required_t
    if op == '>':
        return actual_t > required_t
    if op == '<':
        return actual_t < required_t
    return True

logger = logging.getLogger(__name__)

class InSimManifest:
    """Representa el manifiesto (insim.json) de un InSim."""
    def __init__(self, path: Path):
        self.path = path
        self.directory = path.parent
        
        # Valores por defecto
        self.name = self.directory.name
        self.version = "0.0.0"
        self.description = ""
        self.author = "Unknown"
        self.entry_point = "main.py"
        self.insim_dependencies = {}
        self.python_dependencies = []
        
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.name = data.get('name', self.name)
                self.version = data.get('version', self.version)
                self.description = data.get('description', self.description)
                self.author = data.get('author', self.author)
                self.entry_point = data.get('entry_point', self.entry_point)
                self.insim_dependencies = data.get('insim_dependencies', {})
                self.python_dependencies = data.get('python_dependencies', [])
        except Exception as e:
            logger.error(f"Error cargando manifiesto en {self.path}: {e}")

class InSimLoader:
    """Sistema de carga dinámica de plugins/módulos."""

    def __init__(self, insims_path: Path = None):
        if insims_path is None:
            insims_path = Path.cwd() / "insims"
        
        self.insims_path = insims_path
        self._instances: Dict[str, Any] = {} 

    def get_manifest(self, name: str) -> Optional[InSimManifest]:
        target_dir = self.insims_path / name
        manifest_path = target_dir / "insim.json"
        
        if manifest_path.exists():
            return InSimManifest(manifest_path)
        return None

    def list_available(self) -> List[dict]:
        result = []
        if not self.insims_path.exists():
            return result

        for item in self.insims_path.iterdir():
            if item.is_dir() and (item / "insim.json").exists():
                manifest = InSimManifest(item / "insim.json")
                name = manifest.name or item.name
                result.append({
                    "name": name,
                    "version": manifest.version,
                    "description": manifest.description,
                    "dependencies": list(manifest.insim_dependencies.keys())
                })
        return result

    def discover(self) -> List[str]:
        """Lista solo los nombres de InSims disponibles."""
        return [info['name'] for info in self.list_available()]

    def load(self, name: str):
        """
        Carga dinámicamente el módulo Python.
        Estrategia: El último módulo cargado (el dependiente) asume el rol de Master (Cliente Principal),
        y las dependencias cargadas previamente se convierten en módulos subordinados.
        """
        if name in self._instances:
            return self._instances[name]

        manifest = self.get_manifest(name)
        if not manifest:
            raise InSimModuleError(f"No se encontró el InSim: {name}")

        # 1. CARGA RECURSIVA DE DEPENDENCIAS
        for dep_name, version_constraint in manifest.insim_dependencies.items():
            if dep_name not in self._instances:
                try:
                    self.load(dep_name)
                except Exception as e:
                    logger.error(f"Falló la carga de la dependencia '{dep_name}': {e}")

            # Validar versión una vez que el módulo está cargado
            dep_instance = self._instances.get(dep_name)
            if dep_instance and version_constraint:
                actual_version = getattr(dep_instance, 'version', '0.0.0')
                if not _check_version(actual_version, version_constraint):
                    raise InSimModuleError(
                        f"'{name}' requiere '{dep_name}{version_constraint}' "
                        f"pero la versión instalada es {actual_version}"
                    )

        entry_file = manifest.directory / manifest.entry_point
        if not entry_file.exists():
            raise InSimModuleError(f"Archivo de entrada no encontrado: {entry_file}")

        try:
            # 2. PREPARAR EL TRONO (GOLPE DE ESTADO)
            # Si ya había un cliente registrado (ej: users_management), lo destronamos temporalmente
            # para que el nuevo módulo (tutorial_basics) pueda tomar el mando.
            previous_master = insim_state.get_insim_client()
            if previous_master:
                insim_state.reset_insim_client()

            # 3. IMPORTACIÓN E INSTANCIACIÓN
            spec = importlib.util.spec_from_file_location(name, entry_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            
            from .insim_app import InSimApp
            
            instance = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, InSimApp) and attr is not InSimApp:
                    # Al instanciarse, este nuevo objeto llamará a set_insim_client()
                    # y como pusimos la variable a None, se convertirá en el nuevo Master.
                    instance = attr(_loader=self, _insim_path=manifest.directory)
                    break
            
            if not instance:
                # Si fallamos, restauramos al rey anterior por si acaso
                if previous_master:
                    insim_state.force_set_insim_client(previous_master)
                raise InSimModuleError(f"No se encontró una clase InSimApp en {entry_file}")

            # 4. REORGANIZACIÓN DE SÚBDITOS
            # Ahora 'instance' es el Master. Debemos añadir al antiguo Master como un módulo normal.
            if previous_master:
                # Añadimos al antiguo master como módulo del nuevo
                if previous_master not in instance.modules:
                    instance.modules.append(previous_master)
                    logger.debug(f"🔄 '{previous_master.name}' degradado a módulo de '{instance.name}'")
                
                # También robamos los módulos que el antiguo master pudiera tener (aplanamos la lista)
                for sub_mod in previous_master.modules:
                    if sub_mod not in instance.modules and sub_mod != instance:
                        instance.modules.append(sub_mod)
                
                # Limpiamos al antiguo para evitar duplicidades lógicas
                previous_master.modules = []

            # 5. REGISTRO FINAL
            self._instances[name] = instance
            return instance

        except Exception as e:
            if previous_master:
                insim_state.force_set_insim_client(previous_master)
                logger.warning(f"Rollback: '{previous_master.name}' restaurado como Master tras fallo en '{name}'")
            raise InSimModuleError(f"Error cargando módulo {name}: {e}")