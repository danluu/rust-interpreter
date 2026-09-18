#!/usr/bin/env python3
"""Acquire one pinned local Ruff tree into the installed runtime's owner."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import time

OWNER = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PLAN = HERE / 'plan.json'
FROZEN = HERE / 'inputs.json'
WORK = OWNER / '.work/ruff-source-acquisition-02'
R_OWNER = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
SOURCE = R_OWNER / '.work/sources/ruff'
ORIGINAL = Path('/Users/danluu/dev/rust-interp/.work/sources/ruff')
REVISION = 'd136bd8d002a648de5f344df602e492658306f1e'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stamp(path):
    row = Path(path).lstat()
    return {key: getattr(row, 'st_' + key) for key in
            ['dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns']}


def tree_records(raw):
    result = {}
    folded = set()
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, blob = metadata.decode('ascii').split()
        name = name.decode('utf-8')
        path = PurePosixPath(name)
        require(name == str(path) and not path.is_absolute() and
                all(part not in ('', '.', '..', '.git') for part in path.parts) and
                '\\' not in name and '\n' not in name and '\r' not in name,
                'unsafe Git tree member')
        require(name not in result and name.casefold() not in folded,
                'duplicate or case-colliding Git member')
        require(kind == 'blob' and mode in ('100644', '100755', '120000') and
                len(blob) == 40 and all(c in '0123456789abcdef' for c in blob),
                'unsupported Git member')
        result[name] = dict(mode=mode, blob=blob)
        folded.add(name.casefold())
    require(0 < len(result) <= 20000, 'Git source count exceeds the bound')
    return result


def inspect_member(root, name, expected):
    path = root / name
    before = stamp(path)
    require(path.parent.resolve(strict=True) == path.parent, 'indirect source parent')
    mode = before['mode']
    if expected['mode'] == '120000':
        require(stat.S_ISLNK(mode), 'expected a source symlink')
        target = os.readlink(path)
        require(not Path(target).is_absolute() and path.resolve(strict=True).is_relative_to(root)
                and path.resolve(strict=True).is_file(), 'source link escapes its checkout')
        payload = os.fsencode(target)
        kind = dict(kind='symlink', target=target)
    else:
        require(stat.S_ISREG(mode) and before['nlink'] == 1 and before['size'] <= 8 * 2**20,
                'source must be an ordinary bounded single-link file')
        require(bool(mode & 0o111) == (expected['mode'] == '100755'), 'source executable mode differs')
        payload = path.read_bytes()
        kind = dict(kind='file')
    require(stamp(path) == before, 'source changed while reading: ' + name)
    cleaned = payload
    if expected.get('attributes', {}).get('eol') == 'crlf':
        require(expected['attributes'].get('text') in ('set', 'auto') and kind['kind'] == 'file',
                'unsupported Git checkout conversion')
        cleaned = payload.replace(b'\r\n', b'\n')
        require(cleaned.replace(b'\n', b'\r\n') == payload, 'mixed newline checkout conversion')
    blob = hashlib.sha1(b'blob ' + str(len(cleaned)).encode() + b'\0' + cleaned).hexdigest()
    require(blob == expected['blob'], 'tracked bytes differ from the pinned Git blob: ' + name)
    return dict(expected, **kind, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(), stamp=before)


class Acquisition:
    def __init__(self, expected):
        require(Path.cwd() == OWNER and sys.dont_write_bytecode and sys.flags.optimize == 0,
                'fixed owner and unoptimized Python -B required')
        require(sha(FROZEN) == expected, 'acquisition freeze differs')
        self.expected = expected
        self.frozen, self.plan = read(FROZEN), read(PLAN)
        require(self.plan['owner'] == str(OWNER) and self.plan['runtime_owner'] == str(R_OWNER)
                and self.plan['source'] == str(SOURCE) and self.plan['original'] == str(ORIGINAL)
                and self.plan['revision'] == REVISION, 'acquisition ownership differs')
        require(dict(os.environ) == self.plan['environment'], 'acquisition launch environment differs')
        self.sources()
        spec = importlib.util.spec_from_file_location('ruff_acquisition_owned',
            OWNER / 'experiments/stable-cgu/owned_stage.py')
        self.owned = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.owned)
        require(not WORK.exists() and not WORK.is_symlink() and not SOURCE.exists()
                and not SOURCE.is_symlink(), 'acquisition outputs must be fresh')
        WORK.mkdir(parents=True)
        self.record = dict(schema_version=1, status='waiting', owner=str(OWNER),
            runtime_owner=str(R_OWNER), pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
            source=str(SOURCE), revision=REVISION, freeze_sha256=expected,
            source_acquired=False, application_qualified=False, benchmark=False, children=[])
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def sources(self):
        require(sha(FROZEN) == self.expected, 'acquisition freeze changed')
        for name, digest in self.frozen['files'].items():
            path = Path(name)
            require(path.resolve(strict=True) == path and path.is_file() and sha(path) == digest,
                    'acquisition input changed: ' + name)
        python = self.frozen['python']
        require(str(Path(sys.executable).resolve()) == python['resolved'] and
                sha(python['resolved']) == python['sha256'], 'acquisition Python differs')
        for name, item in self.plan['executors'].items():
            path = Path(name)
            require(str(path.resolve(strict=True)) == item['resolved'] and stamp(path) == item['stamp']
                    and (os.readlink(path) if path.is_symlink() else None) == item['link_text']
                    and sha(path) == item['sha256'], 'acquisition executor changed: ' + name)
        require(list(os.uname()) == self.plan['platform'], 'acquisition host changed')
        for name, item in self.plan['configuration'].items():
            path = Path(name)
            require(path.exists() == item['exists'] and not path.is_symlink(), 'configuration route changed')
            if item['exists']:
                require(stamp(path) == item['stamp'] and sha(path) == item['sha256'], 'configuration changed')

    def original_stamps(self):
        for name, item in self.plan['tracked'].items():
            require(stamp(ORIGINAL / name) == item['stamp'], 'original source changed: ' + name)

    def destination_absent(self, *, require_parent=False):
        require(R_OWNER.resolve(strict=True) == R_OWNER and R_OWNER.is_dir(),
                'runtime owner is indirect or missing')
        for parent in [R_OWNER / '.work', SOURCE.parent]:
            require(not parent.is_symlink(), 'source parent is a symlink')
            if parent.exists():
                require(parent.is_dir() and parent.resolve(strict=True) == parent,
                        'source parent is not an ordinary directory')
            elif require_parent:
                raise RuntimeError('source parent disappeared before init')
        require(not SOURCE.exists() and not SOURCE.is_symlink(), 'source destination appeared before init')

    def inventory(self, root, *, original=False):
        result = {}
        total = 0
        for index, (name, item) in enumerate(self.plan['tracked'].items()):
            if index % 256 == 0:
                self.owned.disk(OWNER, 9)
            row = inspect_member(root, name, item)
            expected = item if original else {key: value for key, value in item.items() if key != 'stamp'}
            actual = row if original else {key: value for key, value in row.items() if key != 'stamp'}
            require(actual == expected, 'acquired tracked source differs: ' + name)
            if not original:
                require((row['stamp']['dev'], row['stamp']['ino']) !=
                        (item['stamp']['dev'], item['stamp']['ino']), 'source acquisition reused an inode')
            result[name] = row
            total += row['bytes']
        require(total == self.plan['tracked_bytes'] and total <= 128 * 2**20, 'tracked source byte count differs')
        return result

    def budget(self):
        self.owned.disk(OWNER, 9)
        allocated = evidence = 0
        for root in [WORK, SOURCE]:
            if not root.exists():
                continue
            for directory, dirs, files in os.walk(root, followlinks=False):
                for name in [*dirs, *files]:
                    row = (Path(directory) / name).lstat()
                    allocated += row.st_blocks * 512
                    if root == WORK:
                        evidence += row.st_blocks * 512
        require(allocated <= 512 * 2**20 and evidence <= 128 * 2**20, 'acquisition allocation bound exceeded')
        return allocated

    def command(self, label):
        self.sources()
        self.original_stamps()
        self.budget()
        index = len(self.record['children'])
        expected = self.plan['commands'][index]
        require(expected['label'] == label, 'acquisition command order differs')
        out = WORK / 'commands' / f'{index:02d}-{label}'
        try:
            if label == 'init':
                self.destination_absent(require_parent=True)
            self.owned.run(expected['argv'], cwd=expected['cwd'], env=self.plan['environment'],
                           out=out, capacity_root=OWNER)
        finally:
            if (out / 'receipt.json').exists():
                self.record['children'].append(dict(label=label, path=str(out), receipt=read(out / 'receipt.json')))
                self.save()
        self.sources()
        self.original_stamps()
        self.budget()
        require(all((out / name).stat().st_size <= 8 * 2**20 for name in ['stdout', 'stderr']),
                'acquisition command output exceeded the bound')
        return (out / 'stdout').read_bytes()

    def identity(self, prefix):
        require(self.command(prefix + '-head') == (REVISION + '\n').encode(), 'source revision differs')
        tree = self.command(prefix + '-tree')
        require(hashlib.sha256(tree).hexdigest() == self.plan['tree_sha256'] and
                tree_records(tree) == {name: {key: item[key] for key in ('mode', 'blob')}
                                      for name, item in self.plan['tracked'].items()}, 'source Git tree differs')
        status = self.command(prefix + '-status')
        require(status == (b'?? .rust-interp-owned.json\n' if prefix == 'acquired' else b''),
                'unexpected source changes')
        require(self.command(prefix + '-attributes') == self.plan['attributes_output'].encode(),
                'upstream checkout attributes differ')

    def execute(self):
        try:
            with self.owned.workload_lock(self.plan['canonical_lock'], 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 16))
                self.save()
                self.destination_absent()
                self.sources()
                self.original_stamps()
                self.inventory(ORIGINAL, original=True)
                total = 0
                for name, digest in self.frozen['files'].items():
                    self.owned.disk(OWNER, 9)
                    payload = Path(name).read_bytes()
                    total += len(payload)
                    require(total <= 96 * 2**20 and len(payload) <= 32 * 2**20,
                            'retained acquisition inputs exceed the bound')
                    target = WORK / 'inputs' / name.lstrip('/')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open('xb') as output:
                        output.write(payload)
                    require(sha(target) == digest and target.stat().st_nlink == 1, 'input copy differs')
                for name in ['home', 'tmp', 'empty-template']:
                    (WORK / name).mkdir()
                require(self.command('git-version-before') == self.plan['git_version'].encode(), 'Git version differs')
                self.identity('original-before')
                SOURCE.parent.mkdir(parents=True, exist_ok=True)
                for label in ['init', 'fetch', 'checkout']:
                    self.command(label)
                require(not (SOURCE / '.git/objects/info/alternates').exists(), 'acquisition used shared Git objects')
                marker = dict(owner=str(R_OWNER), revision=REVISION, source='https://github.com/astral-sh/ruff.git',
                              acquired_from=str(ORIGINAL), acquisition_owner=str(OWNER))
                with (SOURCE / '.rust-interp-owned.json').open('x') as output:
                    output.write(json.dumps(marker, sort_keys=True, indent=2) + '\n')
                self.identity('acquired')
                acquired = self.inventory(SOURCE)
                found = set()
                for directory, dirs, files in os.walk(SOURCE, followlinks=False):
                    if Path(directory) == SOURCE:
                        dirs.remove('.git')
                    for name in [*dirs, *files]:
                        path = Path(directory) / name
                        if path.is_symlink() or not path.is_dir():
                            found.add(str(path.relative_to(SOURCE)))
                require(found == set(acquired) | {'.rust-interp-owned.json'}, 'unexpected checkout members')
                self.identity('original-after')
                self.inventory(ORIGINAL, original=True)
                require(self.command('git-version-after') == self.plan['git_version'].encode(), 'final Git version differs')
                require(len(self.record['children']) == len(self.plan['commands']) == 17, 'acquisition command count differs')
                self.owned.write(WORK / 'acquired-inventory.json', acquired)
                self.record.update(status='passed', finished_at=time.time(), source_acquired=True,
                    tracked_files=len(acquired), tracked_bytes=self.plan['tracked_bytes'],
                    source_inventory=dict(path=str(WORK / 'acquired-inventory.json'), sha256=sha(WORK / 'acquired-inventory.json')),
                    marker=dict(path=str(SOURCE / '.rust-interp-owned.json'), sha256=sha(SOURCE / '.rust-interp-owned.json')),
                    allocated_bytes=self.budget(), free_bytes_after=self.owned.disk(OWNER, 9))
                self.save()
        except BaseException as error:
            self.record.update(status='failed', finished_at=time.time(), error=repr(error))
            self.save()
            raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--frozen-sha', required=True)
    args = parser.parse_args()
    Acquisition(args.frozen_sha).execute()


if __name__ == '__main__':
    main()
