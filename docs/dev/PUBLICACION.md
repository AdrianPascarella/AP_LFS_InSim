# 📦 Publicación en PyPI

> Estado: **preparado, NO publicado.** El nombre `lfs-insim` está libre en PyPI
> (verificado en S14). Decisión acordada: **preparar sí, disparar el publish real
> tras el merge a `main`** (acción pública e irreversible: una versión liberada no
> se reutiliza y el nombre queda reclamado).

## Qué hay ya preparado (S17)

- **Metadata completa** en `pyproject.toml` (S14): licencia SPDX, `readme`,
  keywords, classifiers, URLs (incluida `Changelog`), versión de fuente única.
- **Build validado en local:** `python -m build` produce sdist + wheel
  (`py3-none-any`) y `twine check` pasa en ambos.
- **Extra `[publish]`** (`build`, `twine`) para el ensayo local reproducible.
- **Workflow `.github/workflows/publish.yml`** con Trusted Publishing (OIDC, sin
  tokens). **Inerte hasta que se dispare a propósito** y, además, solo operable
  desde la rama por defecto (`main`) — hasta el merge, el ensayo se hace en local.

---

## 1. Ensayo en TestPyPI (en local, se puede hacer YA)

Necesitas una cuenta en **test.pypi.org** y un **API token** suyo (Account
settings → API tokens). Luego, desde la raíz del proyecto:

```bash
pip install -e ".[publish]"
python -m build                          # sdist + wheel en dist/
twine check dist/*                       # valida metadata y render
twine upload --repository testpypi dist/*   # te pedirá user=__token__ y el token
```

Comprobar que se instala desde TestPyPI (en un venv limpio):

```bash
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ lfs-insim
lfs-insim list
```

> `dist/` está gitignorado: los artefactos no se commitean. Borra `dist/` entre
> builds para no subir wheels viejos (`rm -rf dist build src/*.egg-info`).
> TestPyPI **tampoco** permite reusar un número de versión: si repites el ensayo,
> sube un `0.2.0.devN` o incrementa (solo en el ensayo; no commitees ese bump).

---

## 2. Configurar Trusted Publishing (para el CI, antes del publish real)

El workflow no usa tokens: usa OIDC. Hay que declarar un "trusted publisher" en
cada índice (se puede hacer **antes** de que el proyecto exista, como *pending
publisher*):

En **test.pypi.org** y en **pypi.org** → *Your projects* → *Publishing* (o
*Pending publishers*), añade un publicador de **GitHub Actions** con:

| Campo | Valor |
|---|---|
| Owner | `AdrianPascarella` |
| Repository | `AP_LFS_InSim` |
| Workflow name | `publish.yml` |
| Environment | `testpypi` (en TestPyPI) · `pypi` (en PyPI) |

Los environments `pypi`/`testpypi` se crean solos en GitHub al correr el job; si
quieres, añádeles reglas de protección (aprobación manual) en *Settings →
Environments*.

---

## 3. Publicación real en PyPI (DESPUÉS del merge a `main`)

1. **Merge** de `refactor/estabilizacion` a `main` (autorízalo tú; criterio en
   `PLAN.md § Merge`). El workflow solo es operable desde `main`.
2. Asegura la **versión** deseada en `src/lfs_insim/__init__.py` (`__version__`);
   reinstala editable si la cambias (el test de versión única lo exige).
3. Crea un **GitHub Release** con tag `v<versión>` (p. ej. `v0.2.0`). El evento
   `release: published` dispara el job `pypi` → publica en PyPI vía OIDC.
4. Verifica: `pip install lfs-insim` en un venv limpio.

> El job de TestPyPI se dispara aparte, a mano (*Actions → publish → Run
> workflow*), útil para reensayar ya en el CI antes de crear el Release real.

---

## Recordatorios (semver)

- **Una versión liberada no se reutiliza.** Si un release sale mal, se publica
  una nueva versión (`0.2.1`), no se re-sube la misma.
- Fuente única de versión: `lfs_insim.__version__`. Tras un bump, `pip install -e`
  de nuevo para que la metadata instalada coincida.
- Convención de versionado y changelog: ver `CHANGELOG.md`.
