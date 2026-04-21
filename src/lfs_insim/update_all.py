"""Utilities to update generated artifacts in the repository.

This module provides a `main()` entrypoint that runs the stub
generator and the README insims updater so developers can run a
single command to refresh all generated files.
"""
from pathlib import Path
import runpy
import importlib
import sys


def main() -> None:
    root = Path(__file__).resolve().parents[2]

    # 1) Run the stub generator from the package
    try:
        gen = importlib.import_module('lfs_insim.generate_stubs')
        gen.main()
    except Exception as e:
        print(f"Error running generate_stubs: {e}")
        raise

    # 2) Run the tools/update_insims_readme.py by path
    updater = root / 'tools' / 'update_insims_readme.py'
    if updater.exists():
        try:
            runpy.run_path(str(updater), run_name='__main__')
        except Exception as e:
            print(f"Error running update_insims_readme.py: {e}")
            raise
    else:
        print(f"Updater script not found at: {updater}")


if __name__ == '__main__':
    main()
