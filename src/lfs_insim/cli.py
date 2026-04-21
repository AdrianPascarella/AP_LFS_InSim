#!/usr/bin/env python3
"""
lfs_insim/cli.py - Interfaz de línea de comandos para LFS InSim Framework.

Proporciona comandos para gestionar y ejecutar InSims.

Uso:
    lfs-insim run <nombre>      Ejecuta un InSim
    lfs-insim list              Lista InSims disponibles
    lfs-insim info <nombre>     Muestra información de un InSim
    lfs-insim init <nombre>     Crea un nuevo InSim
"""
import argparse
import json
import logging
import logging.config
import sys
import os
from pathlib import Path

# Añadir directorio actual al path para importar configuración local
sys.path.insert(0, os.getcwd())
from typing import Optional

# Aplicar configuración de logging del proyecto (escribe en logs/insim.log)
try:
    from config.settings import LOGGING_CONFIG
    logging.config.dictConfig(LOGGING_CONFIG)
except Exception:
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )

logger = logging.getLogger("lfs-insim")


def get_loader():
    """Obtiene el loader de InSims."""
    from .insim_loader import InSimLoader
    # Usar el directorio insims del proyecto actual
    project_insims = Path.cwd() / "insims"
    if project_insims.exists():
        return InSimLoader(insims_path=project_insims)
    else:
        return InSimLoader()


def cmd_run(args: argparse.Namespace) -> int:
    """Ejecuta un InSim."""
    loader = get_loader()
    
    try:
        logger.info(f"Cargando InSim: {args.name}")
        insim = loader.load(args.name)

        logger.info(f"Iniciando {insim.name} v{insim.version}")
        insim.start()  # start() llama a stop() en su propio finally

    except FileNotFoundError as e:
        logger.error(str(e))
        logger.info(f"InSims disponibles: {', '.join(i['name'] for i in loader.list_available())}")
        return 1
    except KeyboardInterrupt:
        logger.info("Detenido por el usuario")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        return 1

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Lista InSims disponibles."""
    loader = get_loader()
    insims = loader.list_available()
    
    if not insims:
        print("No se encontraron InSims.")
        print(f"Directorio de búsqueda: {loader.insims_path}")
        return 0
    
    print(f"\n{'Nombre':<20} {'Versión':<10} {'Descripción'}")
    print("-" * 60)
    
    for info in insims:
        desc = info['description'][:30] + "..." if len(info['description']) > 33 else info['description']
        print(f"{info['name']:<20} {info['version']:<10} {desc}")
    
    print(f"\nTotal: {len(insims)} InSim(s)")
    print(f"Ubicación: {loader.insims_path}\n")
    
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Muestra información detallada de un InSim."""
    loader = get_loader()
    manifest = loader.get_manifest(args.name)
    
    if manifest is None:
        logger.error(f"InSim '{args.name}' no encontrado")
        return 1
    
    print(f"\n{'='*50}")
    print(f"  {manifest.name} v{manifest.version}")
    print(f"{'='*50}")
    
    if manifest.description:
        print(f"\n  {manifest.description}")
    
    if manifest.author:
        print(f"\n  Autor: {manifest.author}")
    
    print(f"\n  Punto de entrada: {manifest.entry_point}")
    print(f"  Directorio: {manifest.directory}")
    
    if manifest.insim_dependencies:
        print(f"\n  Dependencias InSim:")
        for dep, version in manifest.insim_dependencies.items():
            print(f"    - {dep} {version}")
    
    if manifest.python_dependencies:
        print(f"\n  Dependencias Python:")
        for dep in manifest.python_dependencies:
            print(f"    - {dep}")
    
    print()
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Crea un nuevo InSim."""
    loader = get_loader()
    insim_dir = loader.insims_path / args.name
    
    if insim_dir.exists():
        logger.error(f"Ya existe un InSim llamado '{args.name}'")
        return 1
    
    # Crear directorio
    insim_dir.mkdir(parents=True)
    
    # Crear insim.json
    manifest = {
        "name": args.name,
        "version": "1.0.0",
        "description": f"InSim {args.name}",
        "author": "",
        "entry_point": "main.py",
        "insim_dependencies": {},
        "python_dependencies": []
    }
    
    with open(insim_dir / "insim.json", 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    # Crear __init__.py
    init_content = f'"""{args.name} InSim Package."""\n'
    with open(insim_dir / "__init__.py", 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    # Crear main.py con template
    main_content = f'''#!/usr/bin/env python3
"""
{args.name} - InSim para Live for Speed.

Descripción de tu InSim aquí.
"""
import logging

from lfs_insim import InSimApp

logger = logging.getLogger(__name__)


class App(InSimApp):
    """
    Tu InSim principal.

    Para depender de otros InSims, añádelos a 'dependencies':
        dependencies = ["player_tracker>=1.0.0"]
    """

    # Dependencias de otros InSims (opcional)
    dependencies = []

    def on_connect(self):
        """Llamado cuando se conecta a LFS."""
        logger.info(f"{{self.name}} conectado!")
        self.send_ISP_MSL(Msg="^2{args.name} ^7conectado")

    def on_disconnect(self):
        """Llamado cuando se desconecta."""
        logger.info(f"{{self.name}} desconectado")


# Para ejecución directa: python main.py
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = App()
    app.start()
'''
    
    with open(insim_dir / "main.py", 'w', encoding='utf-8') as f:
        f.write(main_content)
    
    print(f"\n✅ InSim '{args.name}' creado en: {insim_dir}")
    print(f"\nPróximos pasos:")
    print(f"  1. Edita {insim_dir / 'main.py'}")
    print(f"  2. Ejecuta: lfs-insim run {args.name}")
    print()
    
    return 0


def main(argv: Optional[list] = None) -> int:
    """Punto de entrada principal del CLI."""
    parser = argparse.ArgumentParser(
        prog="lfs-insim",
        description="LFS InSim Framework - Gestión de InSims componibles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  lfs-insim list                  Lista todos los InSims disponibles
  lfs-insim run mi_bot            Ejecuta el InSim 'mi_bot'
  lfs-insim init nuevo_insim      Crea un nuevo InSim llamado 'nuevo_insim'
  lfs-insim info ai_control       Muestra información del InSim 'ai_control'
"""
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Mostrar información de debug'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # Comando: run
    run_parser = subparsers.add_parser('run', help='Ejecutar un InSim')
    run_parser.add_argument('name', help='Nombre del InSim a ejecutar')
    run_parser.set_defaults(func=cmd_run)
    
    # Comando: list
    list_parser = subparsers.add_parser('list', help='Listar InSims disponibles')
    list_parser.set_defaults(func=cmd_list)
    
    # Comando: info
    info_parser = subparsers.add_parser('info', help='Mostrar información de un InSim')
    info_parser.add_argument('name', help='Nombre del InSim')
    info_parser.set_defaults(func=cmd_info)
    
    # Comando: init
    init_parser = subparsers.add_parser('init', help='Crear un nuevo InSim')
    init_parser.add_argument('name', help='Nombre del nuevo InSim')
    init_parser.set_defaults(func=cmd_init)
    
    args = parser.parse_args(argv)
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
