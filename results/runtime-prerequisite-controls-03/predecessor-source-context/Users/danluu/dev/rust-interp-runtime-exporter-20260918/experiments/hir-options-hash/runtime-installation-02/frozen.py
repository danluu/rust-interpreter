"""Read-only complete union-freeze callbacks for runtime controller wiring."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def unique(pairs):
    result = {}
    for name,value in pairs:
        require(name not in result, 'duplicate JSON input key')
        result[name] = value
    return result


def identity(path):
    s = Path(path).lstat()
    return {key:getattr(s,'st_'+key) for key in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']}


def digest(path):
    path = Path(path); before = identity(path)
    require(path.resolve(strict=True) == path and stat.S_ISREG(before['mode']) and before['size'] <= 2**30,
            'ordinary bounded input required')
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        current = {key:getattr(os.fstat(stream.fileno()), 'st_'+key) for key in before}
        require(current == before, 'input changed during open')
        result = hashlib.file_digest(stream,'sha256').hexdigest()
        require({key:getattr(os.fstat(stream.fileno()), 'st_'+key) for key in before} == before,
                'input changed during read')
    require(identity(path) == before, 'input pathname changed during read')
    return result


def json_file(path):
    path = Path(path)
    require(path.stat().st_size <= 256*2**20, 'bounded JSON input required')
    return json.loads(path.read_bytes(), object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


class Frozen:
    def __init__(self, path, expected, *, output_root):
        self.path, self.expected = Path(path), expected
        require(digest(self.path) == expected, 'exact reviewed union freeze required')
        self.value = json_file(self.path)
        self.output_root = Path(output_root)
        self.environment = dict(os.environ)

    def file(self, path):
        path = Path(path)
        row = self.value['files'][str(path)]
        require(identity(path) == row['identity'] and digest(path) == row['sha256']
                and path.stat().st_size == row['size'], 'runtime frozen input differs: '+str(path))
        return path

    def output(self, path):
        path = Path(path)
        require(path.is_relative_to(self.output_root) and path.resolve(strict=True) == path
                and path.is_file(), 'unfrozen read must name actual owned stage output')
        return path

    def read_bytes(self, path, *, frozen=True):
        p = self.file(path) if frozen else self.output(path)
        require(p.stat().st_size <= 2**30, 'bounded actual native/raw file required')
        return p.read_bytes()

    def read_json(self, path, *, frozen=True):
        return json_file(self.file(path) if frozen else self.output(path))

    def sha(self, path, *, frozen=True):
        return digest(self.file(path) if frozen else self.output(path))

    def check(self, full=False):
        require(dict(os.environ) == self.environment and digest(self.path) == self.expected, 'runtime environment/freeze changed')
        for name,row in self.value['files'].items():
            require(identity(name) == row['identity'], 'runtime frozen identity changed')
            if full:
                self.file(name)
        for name,row in self.value['links'].items():
            path=Path(name); s=identity(path)
            stamp=[s[k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
            require(path.is_symlink() and stamp == row['stamp'] and os.readlink(path) == row['target']
                    and str(path.resolve(strict=True)) == row['resolved'], 'runtime frozen route changed')
        for name in self.value['absent_paths']:
            require(not Path(name).exists() and not Path(name).is_symlink(), 'runtime frozen absence changed')
        for name,resolved in self.value['executor_routes'].items():
            require(str(Path(name).resolve(strict=True)) == resolved, 'runtime executor route changed')
        for module in list(sys.modules.values()):
            path=getattr(module,'__file__',None)
            if path and path.startswith('/Users/danluu/dev/'):
                require(str(Path(path).resolve(strict=True)) in self.value['files'], 'unfrozen runtime imported source')
