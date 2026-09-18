#!/usr/bin/env python3
"""Copy qualified Oxc inputs without replacing any existing Cargo cache object."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import time

OWNER = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RROOT = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
ORIGINAL = OWNER / '.work/sources/oxc'
SOURCE = RROOT / '.work/sources/oxc'
PRIVATE = OWNER / '.work/oxc-native-setup-01/cargo'
CARGO_HOME = Path('/Users/danluu/.cargo')
REGISTRY = 'index.crates.io-1949cf8c6b5b557f'
REVISION = '4d5c812d6b16c23fa71d106cf87f7f20ddee69b1'
RHEAD = '1d202909849c65c123c318260da4f1f49cd25131'
WORK = OWNER / '.work/oxc-runtime-source-acquisition-02'
PLAN = HERE / 'acquisition-plan-04.json'
FROZEN = OWNER / '.work/oxc-runtime-acquisition-source-06/inputs.json'
QUALIFIED = OWNER / '.work/oxc-acquisition-continuation-01/registry-checksums.json'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def stamp(path):
    row = Path(path).lstat()
    return {key: getattr(row, 'st_' + key) for key in
            ['dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns']}


def ordinary(path, *, directory=False):
    path = Path(path)
    row = path.lstat()
    require(path.resolve(strict=True) == path and
            (stat.S_ISDIR(row.st_mode) if directory else stat.S_ISREG(row.st_mode) and row.st_nlink == 1),
            'expected an ordinary path: ' + str(path))
    return row


def frozen_input_file(path, executors):
    """Recorded executors may have system hardlinks; owned inputs may not."""
    path = Path(path)
    selected = [(Path(name), proof) for name, proof in executors.items() if proof['resolved'] == str(path)]
    if not selected:
        return ordinary(path)
    row = path.lstat()
    require(path.resolve(strict=True) == path and stat.S_ISREG(row.st_mode), 'indirect recorded executor')
    require(row.st_nlink == 1 or any(name == path for name, proof in selected),
            'hardlinked executor requires direct recorded identity')
    for name, proof in selected:
        require(str(name.resolve(strict=True)) == proof['resolved'] and stamp(name) == proof['stamp']
                and sha(name) == proof['sha256'], 'recorded executor route, links, or bytes changed')
    return row


def safe_relative(name):
    path = PurePosixPath(name)
    require(str(path) == name and bool(path.parts) and not path.is_absolute() and
            all(p not in ('', '.', '..') for p in path.parts) and
            not any(c in name for c in ['\\', '\x00', '\n', '\r']), 'unsafe relative path')
    return path


def absent(path):
    path = Path(path)
    require(not path.exists() and not path.is_symlink(), 'destination already exists: ' + str(path))


def file_record(path):
    before = stamp(path)
    ordinary(path)
    require(before['size'] <= 128 * 2**20, 'file size exceeds acquisition bound')
    digest = sha(path)
    require(stamp(path) == before, 'file changed while reading: ' + str(path))
    return dict(kind='file', bytes=before['size'], sha256=digest, mode=stat.S_IMODE(before['mode']))


def inventory(root, capacity=lambda: None):
    ordinary(root, directory=True)
    records, folded, size = {}, set(), 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        capacity()
        for name in sorted([*dirs, *files]):
            path = Path(directory) / name
            relative = str(path.relative_to(root))
            safe_relative(relative)
            require(relative.casefold() not in folded, 'case-colliding source path')
            folded.add(relative.casefold())
            before = stamp(path)
            if stat.S_ISLNK(before['mode']):
                target = os.readlink(path)
                resolved = path.resolve(strict=True)
                require(not Path(target).is_absolute() and resolved.is_relative_to(root)
                        and (resolved.is_file() or resolved.is_dir()), 'source link escapes its checkout')
                item = dict(kind='symlink', target=target)
            elif stat.S_ISDIR(before['mode']):
                ordinary(path, directory=True)
                item = dict(kind='directory', mode=stat.S_IMODE(before['mode']))
            else:
                item = file_record(path)
                size += item['bytes']
            require(stamp(path) == before, 'source path changed while reading')
            records[relative] = item
            require(len(records) <= 30000 and size <= 128 * 2**20, 'source inventory exceeds bound')
    return records


def copy_file(source, destination, expected):
    """Create exclusively, check readback, and never reuse the source inode."""
    ordinary(destination.parent, directory=True)
    require(file_record(source) == expected, 'copy source differs from its frozen record')
    before = stamp(source)
    absent(destination)
    # Exclusive creation is the final absence check, including against symlinks.
    with destination.open('xb') as output, source.open('rb') as incoming:
        while block := incoming.read(1024**2):
            output.write(block)
        output.flush()
        os.fsync(output.fileno())
        os.fchmod(output.fileno(), expected['mode'])
    require(stamp(source) == before and file_record(destination) == expected,
            'copy source/readback changed')
    require((before['dev'], before['ino']) != (destination.stat().st_dev, destination.stat().st_ino),
            'copy reused original inode')


def index_path(name):
    require(name and name == name.lower() and all(c.isascii() and (c.isalnum() or c in '-_') for c in name),
            'invalid registry package name')
    relative = ('1/' + name if len(name) == 1 else '2/' + name if len(name) == 2 else
                '3/' + name[0] + '/' + name if len(name) == 3 else name[:2] + '/' + name[2:4] + '/' + name)
    return 'registry/index/' + REGISTRY + '/.cache/' + relative


def index_record(path, name, version, checksum):
    payload = path.read_bytes()
    require(len(payload) <= 16 * 2**20 and payload[:5] == b'\x03\x02\x00\x00\x00',
            'unsupported sparse index cache format')
    fields = payload[5:].split(b'\x00')
    require(fields[-1] == b'' and len(fields) % 2 == 0, 'malformed sparse index cache')
    matches = []
    for offset in range(1, len(fields) - 1, 2):
        if fields[offset] == version.encode():
            item = json.loads(fields[offset + 1])
            require(item['name'] == name and item['vers'] == version and item['cksum'] == checksum,
                    'index record differs from locked archive identity')
            matches.append(fields[offset + 1].decode())
    require(len(matches) == 1, 'required index version missing or duplicated')
    return matches[0]


@contextmanager
def download_lock(path, expected_identity, *, wait_seconds=600, capacity=lambda: None, note=lambda row: None):
    """Cargo DownloadExclusive; no shared/mutate lock is acquired inside it."""
    ordinary(path)
    before = path.stat()
    require(dict(dev=before.st_dev, ino=before.st_ino) == expected_identity, 'Cargo lock identity changed')
    start = time.time()
    acquired = None
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), 'Cargo lock replaced at open')
        deadline = time.monotonic() + wait_seconds
        while True:
            capacity()
            current = ordinary(path)
            require((current.st_dev, current.st_ino) == (opened.st_dev, opened.st_ino), 'Cargo lock route changed')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = time.time()
                break
            except BlockingIOError:
                require(time.monotonic() < deadline, 'Cargo download-lock admission timed out')
                time.sleep(min(.25, max(0, deadline - time.monotonic())))
        note(dict(path=str(path), identity=expected_identity, started_at=start, acquired_at=acquired))
        yield
        current = ordinary(path)
        require((current.st_dev, current.st_ino) == (opened.st_dev, opened.st_ino), 'Cargo lock replaced while held')
    finally:
        os.close(fd)
        note(dict(path=str(path), identity=expected_identity, started_at=start, acquired_at=acquired,
                  released_at=time.time()))


class Acquisition:
    def __init__(self, expected):
        require(Path.cwd() == OWNER and sys.dont_write_bytecode and sys.flags.optimize == 0,
                'fixed owner and unoptimized Python -B required')
        require(sha(FROZEN) == expected, 'runtime acquisition freeze differs')
        self.expected, self.frozen, self.plan = expected, read(FROZEN), read(PLAN)
        require(self.plan['owner'] == str(OWNER) and self.plan['runtime_owner'] == str(RROOT)
                and self.plan['original'] == str(ORIGINAL) and self.plan['source'] == str(SOURCE)
                and self.plan['cargo_home'] == str(CARGO_HOME) and self.plan['revision'] == REVISION,
                'runtime acquisition ownership differs')
        require(dict(os.environ) == self.plan['environment'], 'controller environment differs')
        self.owned = load('oxc_runtime_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        self.registry = load('oxc_runtime_registry', OWNER / 'experiments/oxc-plugin-normalization/registry_cache.py')
        self.qualified = read(QUALIFIED)['archives']
        self.inputs()
        absent(WORK)
        absent(SOURCE)
        WORK.mkdir()
        self.record = dict(schema_version=1, status='waiting', owner=str(OWNER), runtime_owner=str(RROOT),
            pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), freeze_sha256=expected,
            children=[], exclusive_create_intents=0, source_acquired=False, runtime_compatible=False, benchmark=False)
        self.created_paths = []
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def capacity(self):
        return self.owned.disk(OWNER, 9)

    def inputs(self):
        require(sha(FROZEN) == self.expected, 'acquisition freeze changed')
        for name, digest in self.frozen['files'].items():
            frozen_input_file(name, self.plan['executors'])
            require(sha(name) == digest, 'frozen input changed: ' + name)
        python = self.frozen['python']
        require(str(Path(sys.executable).resolve()) == python['resolved'] and
                sha(sys.executable) == python['sha256'], 'controller Python changed')
        for name, proof in self.plan['executors'].items():
            path = Path(name)
            require(str(path.resolve(strict=True)) == proof['resolved'] and stamp(path) == proof['stamp']
                    and sha(path) == proof['sha256'], 'executor identity changed')
        require(list(os.uname()) == self.plan['platform'], 'platform changed')
        for name, proof in self.plan['configuration'].items():
            path = Path(name)
            require(not path.is_symlink() and path.exists() == proof['exists'], 'configuration route changed')
            if proof['exists']:
                require(file_record(path) == proof['record'], 'configuration changed')
        # This pins only scripts/HEAD, never peer .work outputs.
        for name, digest in self.plan['runtime_files'].items():
            require(sha(name) == digest, 'runtime owner scripts or HEAD changed')
        require({str(path) for path in (RROOT / 'scripts').rglob('*.py')} ==
                {name for name in self.plan['runtime_files'] if Path(name).is_relative_to(RROOT / 'scripts')},
                'runtime script membership changed')

    def budget(self):
        self.capacity()
        allocated = evidence = 0
        extra = [p for p in self.created_paths if not p.is_relative_to(SOURCE) and p.is_file()]
        for root in [WORK, SOURCE, *extra]:
            if not root.exists():
                continue
            paths = [root] if root.is_file() else (Path(d) / n for d, dirs, files in os.walk(root, followlinks=False)
                                                  for n in [*dirs, *files])
            for path in paths:
                amount = path.lstat().st_blocks * 512
                allocated += amount
                if path.is_relative_to(WORK):
                    evidence += amount
        require(allocated <= 640 * 2**20 and evidence <= 128 * 2**20, 'acquisition allocation bound exceeded')
        return dict(total=allocated, evidence=evidence)

    def created(self, path):
        self.created_paths.append(path)
        self.record['exclusive_create_intents'] += 1
        with (WORK / 'exclusive-create-intents.jsonl').open('a') as ledger:
            ledger.write(json.dumps(dict(path=str(path), time=time.time())) + '\n')

    def mkdir(self, path, mode=0o700):
        ordinary(path.parent, directory=True)
        absent(path)
        path.mkdir(mode=mode)
        os.chmod(path, mode)
        self.created(path)

    def parent(self, path, root):
        require(path.is_relative_to(root), 'copy parent outside admitted root')
        ordinary(root, directory=True)
        relative = path.relative_to(root)
        current = root
        for part in relative.parts:
            current = current / part
            if current.exists() or current.is_symlink():
                ordinary(current, directory=True)
            else:
                self.mkdir(current)

    def copy(self, source, target, proof):
        self.capacity()
        # Ledger includes the exclusive destination before a possible write failure.
        absent(target)
        self.created(target)
        copy_file(source, target, proof)

    def command(self, label):
        self.inputs()
        self.budget()
        index = len(self.record['children'])
        spec = self.plan['commands'][index]
        require(spec['label'] == label, 'acquisition command order differs')
        out = WORK / 'commands' / f'{index:02d}-{label}'
        try:
            self.owned.run(spec['argv'], cwd=spec['cwd'], env=self.plan['environment'], out=out,
                           capacity_root=OWNER)
        finally:
            if (out / 'receipt.json').exists():
                self.record['children'].append(dict(label=label, path=str(out), receipt=read(out / 'receipt.json')))
                self.save()
        self.inputs()
        self.budget()
        require((out / 'stderr').stat().st_size == 0 and (out / 'stdout').stat().st_size <= 8 * 2**20,
                'unexpected acquisition child diagnostics/output')
        return (out / 'stdout').read_text()

    def git_identity(self, phase):
        require(self.command(phase + '-head') == REVISION + '\n', 'source HEAD differs')
        require(self.command(phase + '-status') == '?? .rust-interp-owned.json\n', 'source status differs')

    def source_guard(self):
        actual = inventory(ORIGINAL, self.capacity)
        require(actual == self.plan['source_inventory'], 'qualified original source changed')
        baseline = read(OWNER / '.work/oxc-native-setup-01/source-inventory.json')
        files = {name: row for name, row in actual.items()
                 if row['kind'] != 'directory' and not name.startswith('.git/')}
        require(files == {name: row for name, row in baseline.items() if not name.startswith('.git/')},
                'original source differs from qualified native bytes')
        return actual

    def copy_source(self):
        self.parent(SOURCE.parent, RROOT)
        self.mkdir(SOURCE, self.plan['source_root_mode'])
        for name, item in sorted(self.plan['source_inventory'].items(), key=lambda pair: (len(Path(pair[0]).parts), pair[0])):
            safe_relative(name)
            target, source = SOURCE / name, ORIGINAL / name
            if name == '.rust-interp-owned.json':
                continue
            if item['kind'] == 'directory':
                self.mkdir(target, item['mode'])
            elif item['kind'] == 'file':
                self.copy(source, target, item)
            else:
                ordinary(target.parent, directory=True)
                absent(target)
                self.created(target)
                target.symlink_to(item['target'])
        marker = SOURCE / '.rust-interp-owned.json'
        self.created(marker)
        with marker.open('x') as output:
            json.dump(self.plan['ownership_marker'], output, sort_keys=True, indent=2)
            output.write('\n')
        os.chmod(marker, self.plan['source_inventory']['.rust-interp-owned.json']['mode'])
        expected = dict(self.plan['source_inventory'])
        expected['.rust-interp-owned.json'] = file_record(marker)
        require(inventory(SOURCE, self.capacity) == expected, 'copied source membership/bytes differ')
        for name, item in expected.items():
            if item['kind'] == 'file':
                a, b = (ORIGINAL / name).stat(), (SOURCE / name).stat()
                require((a.st_dev, a.st_ino) != (b.st_dev, b.st_ino), 'source copy shares an original inode')
        self.owned.write(WORK / 'acquired-source-inventory.json', expected)
        return expected

    def registry_verify(self, root, proof):
        archive = root / 'registry/cache' / REGISTRY / (proof['label'] + '.crate')
        directory = root / 'registry/src' / REGISTRY / proof['label']
        return self.registry.verify(archive, directory, proof['checksum'], capacity=self.capacity)

    def private_guard(self):
        for label, proof in self.plan['packages'].items():
            require(self.registry_verify(PRIVATE, proof) == self.qualified[label], 'qualified private package changed')
        for relative, proof in self.plan['indexes'].items():
            require(file_record(PRIVATE / relative) == proof['private'], 'private index changed')

    def cache_guard(self, *, complete=False):
        packages = {}
        for label, proof in self.plan['packages'].items():
            if proof['present'] or complete:
                actual = self.registry_verify(CARGO_HOME, proof)
                if proof['present']:
                    require(actual == proof['existing'], 'preexisting shared package changed')
                else:
                    wanted = dict(self.qualified[label])
                    wanted.update(archive=actual['archive'], root=actual['root'])
                    require(actual == wanted, 'new shared package differs from qualified bytes/modes')
                packages[label] = actual
            else:
                absent(CARGO_HOME / 'registry/cache' / REGISTRY / (label + '.crate'))
                absent(CARGO_HOME / 'registry/src' / REGISTRY / label)
        for relative, proof in self.plan['indexes'].items():
            path = CARGO_HOME / relative
            if proof['present'] or complete:
                require(file_record(path) == (proof['existing'] if proof['present'] else proof['private']),
                        'shared index changed')
                for selected in proof['records']:
                    require(index_record(path, selected['name'], selected['version'], selected['checksum']) ==
                            selected['record'], 'selected index record changed')
            else:
                absent(path)
        return packages

    def copy_cache(self):
        self.cache_guard()
        for label, proof in self.plan['packages'].items():
            if proof['present']:
                continue
            item = self.qualified[label]
            source, archive = Path(item['root']), Path(item['archive'])
            target = CARGO_HOME / 'registry/src' / REGISTRY / label
            self.mkdir(target, stat.S_IMODE(source.stat().st_mode))
            for relative in sorted(item['directories'], key=lambda name: (len(Path(name).parts), name)):
                self.mkdir(target / relative, stat.S_IMODE((source / relative).stat().st_mode))
            for relative in sorted(item['members']):
                self.copy(source / relative, target / relative, file_record(source / relative))
            # The marker is last, as in ordinary Cargo unpacking. The archive is
            # also published only after the completed extracted source exists.
            self.copy(source / '.cargo-ok', target / '.cargo-ok', file_record(source / '.cargo-ok'))
            self.copy(archive, CARGO_HOME / 'registry/cache' / REGISTRY / archive.name, file_record(archive))
            self.budget()
        for relative, proof in self.plan['indexes'].items():
            if not proof['present']:
                target = CARGO_HOME / relative
                self.parent(target.parent, CARGO_HOME / 'registry/index' / REGISTRY / '.cache')
                self.copy(PRIVATE / relative, target, proof['private'])
        return self.cache_guard(complete=True)

    def execute(self):
        try:
            with self.owned.workload_lock(self.plan['canonical_lock'], 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 16))
                self.save()
                self.inputs()
                require(sum(Path(name).stat().st_size for name in self.frozen['files']) <= 96 * 2**20,
                        'retained acquisition inputs exceed bound')
                for name, digest in self.frozen['files'].items():
                    destination = WORK / 'inputs' / name.lstrip('/')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with destination.open('xb') as output:
                        output.write(Path(name).read_bytes())
                    require(sha(destination) == digest, 'retained input differs')
                (WORK / 'tmp').mkdir()
                controls = self.command('controls')
                require('Ran 17 tests' in controls and controls.endswith('\nOK\n'), 'copy/lock controls incomplete')
                require(self.command('git-version-before') == self.plan['git_version'], 'Git version differs')
                self.git_identity('original-before')
                self.source_guard()
                self.private_guard()
                acquired = self.copy_source()
                self.git_identity('acquired')
                self.record['source_acquired'] = True
                self.save()
                def lock_note(proof):
                    self.record['cargo_download_lock'] = proof
                    self.save()
                with download_lock(CARGO_HOME / '.package-cache', self.plan['cargo_lock_identity'],
                                   capacity=self.capacity, note=lock_note):
                    self.inputs()
                    result = self.copy_cache()
                    self.owned.write(WORK / 'shared-registry-checksums.json', result)
                # No Cargo or launcher child executes with the cache lock held.
                self.git_identity('original-after')
                self.source_guard()
                self.private_guard()
                require(inventory(SOURCE, self.capacity) == acquired, 'acquired source changed')
                require(self.command('git-version-after') == self.plan['git_version'], 'final Git version differs')
                require(len(self.record['children']) == len(self.plan['commands']) == 9, 'acquisition history incomplete')
                self.inputs()
                self.record.update(status='passed', source_acquired=True, registry_packages=len(result),
                    copied_packages=sum(not p['present'] for p in self.plan['packages'].values()),
                    copied_index_files=sum(not p['present'] for p in self.plan['indexes'].values()),
                    source_inventory_sha256=sha(WORK / 'acquired-source-inventory.json'),
                    shared_registry_sha256=sha(WORK / 'shared-registry-checksums.json'),
                    allocation=self.budget(), free_bytes_after=self.capacity())
        except BaseException as error:
            self.record.update(status='failed', error=repr(error))
            raise
        finally:
            self.record['finished_at'] = time.time()
            self.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--frozen-sha256', required=True)
    Acquisition(parser.parse_args().frozen_sha256).execute()
