"""Update README insims section dynamically.

Scans the `insims/` directory and replaces the block between
`<!-- INSIMS-START -->` and `<!-- INSIMS-END -->` in README.md with
an updated markdown list of insims.

Usage:
    python tools/update_insims_readme.py
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent
INSIMS_DIR = ROOT / 'insims'
README = ROOT / 'README.md'

def generate_insims_list():
    items = []
    if not INSIMS_DIR.exists():
        return 'No hay insims en el directorio `insims/`.'

    for p in sorted(INSIMS_DIR.iterdir()):
        if p.is_dir():
            # check for insim.json or main.py to consider valid
            if (p / 'insim.json').exists() or (p / 'main.py').exists():
                items.append(f"- `{p.name}/`: {get_description(p)}")

    if not items:
        return 'No hay insims en el directorio `insims/`.'

    header = 'Cada carpeta en `insims/` representa una funcionalidad independiente y reutilizable.\n'
    lines = [header]
    lines.extend(items)
    lines.append('\nNota: Ejecuta `python tools/update_insims_readme.py` para regenerar esta lista.')
    return '\n'.join(lines)


def get_description(p: Path) -> str:
    # Try to read insim.json description
    manifest = p / 'insim.json'
    if manifest.exists():
        try:
            import json
            data = json.loads(manifest.read_text(encoding='utf-8'))
            desc = data.get('description', '').strip()
            if desc:
                return desc
        except Exception:
            pass
    # Fallback: look for README.md
    readme = p / 'README.md'
    if readme.exists():
        first = readme.read_text(encoding='utf-8').splitlines()[0:2]
        return ' '.join(l.strip() for l in first if l.strip())
    return 'Plantilla o ejemplo.'


def update_readme():
    text = README.read_text(encoding='utf-8')
    start_marker = '<!-- INSIMS-START -->'
    end_marker = '<!-- INSIMS-END -->'
    if start_marker not in text or end_marker not in text:
        raise RuntimeError('Markers not found in README.md')

    before, rest = text.split(start_marker, 1)
    _, after = rest.split(end_marker, 1)

    new_block = start_marker + '\n' + generate_insims_list() + '\n' + end_marker
    new_text = before + new_block + after
    README.write_text(new_text, encoding='utf-8')
    print('README.md updated with current insims list')

if __name__ == '__main__':
    update_readme()
