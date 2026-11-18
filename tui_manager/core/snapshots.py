"""
Snapshots de configuración (WM/bar) basados en copias ``.bak-tm``.

* ``snapshot_config(name, paths)`` guarda el contenido actual de cada archivo
  en un almacén inyectable y crea, si no existe, un sidecar ``<archivo>.bak-tm``.
  Ese sidecar es el backups original: si ya existía **no se sobrescribe**.
* ``restore_config(name)`` vuelve a copiar el contenido guardado en cada
  archivo original, sin tocar nunca los sidecars ``.bak-tm``.

Seguridad: nunca se hacen snapshots del sistema. Se rechazan rutas que
apuntan a subvolúmenes btrfs/zfs (``@home``, ``.snapshots``, ``btrfs``, ...)
y a raíces del sistema (``/proc``, ``/sys``, ``/dev``, ``/run``, ``/boot``).

El directorio de almacén se puede inyectar con ``base_dir``; los tests usan
``tmp_path`` para no escribir fuera de su espacio temporal.
"""
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Union

PathLike = Union[str, Path]

SNAPSHOT_SUFFIX = '.bak-tm'
DEFAULT_SNAPSHOT_DIR = Path.home() / '.tui-manager' / 'snapshots'
_MANIFEST_FILE = 'snapshot.json'
_VALID_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')

# Marcadores de subvolúmenes / snapshots de sistemas de archivos.
_FS_PARTS = frozenset({
    'btrfs', 'zfs', '.btrfs', '.zfs', 'subvolumes', '.snapshots',
})
_SYSTEM_ROOTS = frozenset({'proc', 'sys', 'dev', 'run', 'boot'})


class UnsafePathError(ValueError):
    """La ruta pertenece al sistema (btrfs/zfs) o no es un archivo válido."""


class SnapshotNotFoundError(FileNotFoundError):
    """No existe el snapshot solicitado."""


def _validate_name(name: str) -> None:
    if (not isinstance(name, str) or name in ('.', '..')
            or not _VALID_NAME.fullmatch(name)):
        raise ValueError(f"Nombre de snapshot inválido: {name!r}")


def _base_dir(base_dir: PathLike = None) -> Path:
    return Path(base_dir) if base_dir is not None else DEFAULT_SNAPSHOT_DIR


def _assert_safe_path(path: Path) -> None:
    """Rechaza rutas de sistema; nunca se snapshottea btrfs/zfs."""
    parts = [part.lower() for part in path.parts]
    if path.is_absolute() and len(parts) > 1 and parts[1] in _SYSTEM_ROOTS:
        raise UnsafePathError(f"Ruta del sistema no snapshotable: {path}")
    for part in parts:
        if (part in _FS_PARTS or part.startswith('@')
                or part.startswith('.zfs') or part.startswith('.btrfs')):
            raise UnsafePathError(
                f"Ruta de subvolumen btrfs/zfs no snapshotable: {path}")


def _as_paths(paths: Iterable[PathLike]) -> List[Path]:
    if isinstance(paths, (str, Path)):
        paths = [paths]
    return [Path(raw).expanduser() for raw in paths]


def snapshot_config(name: str, paths: Iterable[PathLike],
                    *, base_dir: PathLike = None) -> Dict:
    """Crea el snapshot `name` de los archivos en `paths`.

    Por cada archivo se guarda una copia ``.bak-tm`` en el almacén del
    snapshot y se asegura el sidecar ``<archivo>.bak-tm`` original (si ya
    existía, se conserva intacto).

    Args:
        name: identificador del snapshot (caracteres alfanuméricos,
            ``_``, ``.`` o ``-``).
        paths: archivos a snapshotear (str o Path). Nunca rutas btrfs/zfs.
        base_dir: directorio del almacén; inyectable en tests (tmp_path).

    Returns:
        El manifiesto del snapshot (dict con nombre y lista de archivos).

    Raises:
        ValueError: nombre inválido.
        UnsafePathError: ruta de sistema o que no es un archivo regular.
        FileNotFoundError: alguno de los archivos no existe.
    """
    _validate_name(name)
    store = _base_dir(base_dir) / name
    manifest: Dict = {'name': name, 'items': []}

    for path in _as_paths(paths):
        _assert_safe_path(path)
        if not path.is_file():
            if path.exists():
                raise UnsafePathError(
                    f"Sólo se pueden snapshotear archivos regulares: {path}")
            raise FileNotFoundError(f"No existe el archivo a snapshotear: {path}")

        # Sidecar junto al original: se crea una vez y se conserva siempre.
        sidecar = Path(str(path) + SNAPSHOT_SUFFIX)
        if not sidecar.exists():
            shutil.copy2(path, sidecar)

        encoded = hashlib.sha256(str(path).encode('utf-8')).hexdigest()[:20]
        store.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, store / f'{encoded}{SNAPSHOT_SUFFIX}')
        manifest['items'].append({
            'original': str(path),
            'encoded': encoded,
            'sidecar': str(sidecar),
        })

    store.mkdir(parents=True, exist_ok=True)
    (store / _MANIFEST_FILE).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return manifest


def restore_config(name: str, *, base_dir: PathLike = None) -> Dict[str, bool]:
    """Restaura los archivos del snapshot `name` a su contenido guardado.

    Los sidecars ``.bak-tm`` originales no se modifican ni se borran.

    Returns:
        ``{ruta_original: True}`` por cada archivo restaurado.

    Raises:
        ValueError: nombre inválido.
        SnapshotNotFoundError: no existe el snapshot o alguna de sus copias.
        UnsafePathError: la ruta guardada dejó de ser segura.
    """
    _validate_name(name)
    store = _base_dir(base_dir) / name
    manifest_path = store / _MANIFEST_FILE
    if not manifest_path.is_file():
        raise SnapshotNotFoundError(f"No existe el snapshot {name!r}")

    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    restored: Dict[str, bool] = {}
    for item in manifest['items']:
        path = Path(item['original'])
        _assert_safe_path(path)
        source = store / f"{item['encoded']}{SNAPSHOT_SUFFIX}"
        if not source.is_file():
            raise SnapshotNotFoundError(
                f"Falta la copia del snapshot {name!r} para {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, path)
        restored[str(path)] = True
    return restored
