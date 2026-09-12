"""Explicit cache placement; each checkout owns a separate namespace."""
import hashlib
import json
from pathlib import Path


def cache_subdirectory(parent, *names):
    """Create ordinary directories without following replacement symlinks."""
    path = parent
    for name in names:
        if not name or name in ('.', '..') or Path(name).name != name:
            raise ValueError('invalid cache directory component')
        path = path / name
        if path.is_symlink():
            raise ValueError('cache directory is a symlink: ' + str(path))
        path.mkdir(exist_ok=True)
        if not path.is_dir():
            raise ValueError('cache path is not a directory: ' + str(path))
    return path


def external_cache_root(parent, owner):
    """Use an existing parent without adopting its files or another checkout."""
    parent = Path(parent).expanduser()
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError('cache parent must be an existing ordinary directory')
    parent = parent.resolve(strict=True)
    owner = str(owner.resolve())
    name = 'rust-interp-' + hashlib.sha256(owner.encode()).hexdigest()[:24]
    root = parent / name
    marker = root / '.rust-interp-cache.json'
    expected = dict(schema_version=1, kind='rust-interp-cache', owner=owner)
    if root.is_symlink():
        raise ValueError('cache namespace is a symlink')
    try:
        root.mkdir()
    except FileExistsError:
        # An unmarked directory belongs to someone else. In particular, do
        # not claim an existing empty directory or repair a partial marker.
        pass
    else:
        with marker.open('x') as output:
            output.write(json.dumps(expected, sort_keys=True) + '\n')
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 4096:
        raise ValueError('cache namespace has no valid ownership marker')
    try:
        actual = json.loads(marker.read_bytes())
    except (OSError, ValueError) as error:
        raise ValueError('cannot read cache namespace ownership marker') from error
    if actual != expected:
        raise ValueError('cache namespace belongs to a different checkout or format')
    return root


def workspace_cache_base(owner, parent=None):
    if parent is None:
        return owner / '.work/interpreter-workspaces'
    return cache_subdirectory(external_cache_root(parent, owner), 'workspaces')
