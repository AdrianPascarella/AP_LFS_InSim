"""
lfs_insim/insim_loader.py - Dynamic plugin loading.

Discovers InSims (directories with an insim.json manifest), resolves their
dependencies recursively and registers every loaded app into a single
InSimClient, in dependency order (dependencies before dependents).
"""

import importlib.util
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from .exceptions import InSimModuleError


def _parse_version(version_str: str) -> tuple:
    """Turn '1.2.3' into (1, 2, 3) for comparison."""
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
    Check whether `actual` satisfies `constraint`.
    Supports: >=, <=, >, <, ==, != and a bare version (exact match).
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
    """Represents an InSim manifest (insim.json)."""
    def __init__(self, path: Path):
        self.path = path
        self.directory = path.parent

        # Defaults
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
            logger.error(f"Error loading manifest at {self.path}: {e}")

class InSimLoader:
    """Dynamic plugin/module loading system."""

    def __init__(self, insims_path: Path = None, client: Any = None,
                 config: Optional[Dict[str, Any]] = None):
        if insims_path is None:
            insims_path = Path.cwd() / "insims"

        self.insims_path = insims_path
        self._client = client
        self._config = config
        self._instances: Dict[str, Any] = {}

    @property
    def client(self):
        """
        The single InSimClient every loaded app is registered into.
        Created lazily on first use (with the loader's `config` overrides,
        if any); an existing client can be injected through the constructor
        instead — then the loader's `config` is ignored.
        """
        if self._client is None:
            from .insim_client import InSimClient
            self._client = InSimClient(config=self._config)
        return self._client

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
        """List the names of the available InSims."""
        return [info['name'] for info in self.list_available()]

    def load(self, name: str):
        """
        Load an InSim and everything it depends on.

        Dependencies are loaded (and registered into the client) BEFORE the
        dependent module, so dispatch order follows dependency order: a
        tracker processes a packet before the app that consumes its state.
        Returns the app instance (cached: loading twice returns the same one).
        """
        if name in self._instances:
            return self._instances[name]

        manifest = self.get_manifest(name)
        if not manifest:
            raise InSimModuleError(f"InSim not found: {name}")

        # 1. RECURSIVE DEPENDENCY LOADING
        for dep_name, version_constraint in manifest.insim_dependencies.items():
            if dep_name not in self._instances:
                try:
                    self.load(dep_name)
                except Exception as e:
                    # P20: failures in dependencies are logged and swallowed
                    # (fail-fast pending; see PLAN.md Fase 2)
                    logger.error(f"Failed to load dependency '{dep_name}': {e}")

            # Validate the version once the module is loaded
            dep_instance = self._instances.get(dep_name)
            if dep_instance and version_constraint:
                actual_version = getattr(dep_instance, 'version', '0.0.0')
                if not _check_version(actual_version, version_constraint):
                    raise InSimModuleError(
                        f"'{name}' requires '{dep_name}{version_constraint}' "
                        f"but the installed version is {actual_version}"
                    )

        entry_file = manifest.directory / manifest.entry_point
        if not entry_file.exists():
            raise InSimModuleError(f"Entry point file not found: {entry_file}")

        try:
            # 2. IMPORT AND INSTANTIATION
            entry_stem = Path(manifest.entry_point).stem  # 'main', '__init__', etc.

            if entry_stem == '__init__':
                # The entry point is the package's own __init__.py
                spec = importlib.util.spec_from_file_location(
                    name, entry_file,
                    submodule_search_locations=[str(manifest.directory)]
                )
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
            else:
                # The entry point is a submodule (e.g. main.py).
                # Register the package first so relative imports work.
                init_file = manifest.directory / '__init__.py'
                pkg_spec = importlib.util.spec_from_file_location(
                    name,
                    init_file if init_file.exists() else None,
                    submodule_search_locations=[str(manifest.directory)]
                )
                pkg_module = importlib.util.module_from_spec(pkg_spec)
                sys.modules[name] = pkg_module
                if init_file.exists():
                    pkg_spec.loader.exec_module(pkg_module)

                sub_name = f"{name}.{entry_stem}"
                spec = importlib.util.spec_from_file_location(sub_name, entry_file)
                module = importlib.util.module_from_spec(spec)
                sys.modules[sub_name] = module
                spec.loader.exec_module(module)

            from .insim_app import InSimApp

            instance = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, InSimApp) and attr is not InSimApp:
                    # Apps inherit the client's effective config (defaults +
                    # project overrides), so self.config is consistent across
                    # the client and every app.
                    instance = attr(config=self.client.config,
                                    _loader=self, _insim_path=manifest.directory)
                    break

            if not instance:
                raise InSimModuleError(f"No InSimApp class found in {entry_file}")

            # 3. REGISTRATION: cache the instance and attach it to the client
            # (dependencies were registered first by the recursion above)
            self._instances[name] = instance
            self.client.register(instance)
            return instance

        except Exception as e:
            raise InSimModuleError(f"Error loading module {name}: {e}")
