#!/usr/bin/env python3
"""Compose a fresh complete native toolchain with its official LLVM component."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
import time

import acquire

OWNER, HERE = acquire.OWNER, acquire.HERE
WORK = OWNER / '.work/oxc-native-toolchain-composition-01'
PREFIX = WORK / 'toolchain'
PLAN = HERE / 'native-toolchain-composition-plan-01.json'
FROZEN = OWNER / '.work/oxc-native-toolchain-composition-source-01/inputs.json'
require, sha, read, load = acquire.require, acquire.sha, acquire.read, acquire.load
sys.path.insert(0, str(OWNER / 'scripts'))
from custom_cargo_libraries import library_closure, library_state, platform_identity


class Composition:
    def __init__(self, expected):
        require(sha(FROZEN) == expected, 'native composition freeze differs')
        self.expected, self.frozen, self.plan = expected, read(FROZEN), read(PLAN)
        require(self.frozen['owner'] == self.plan['owner'] == str(OWNER), 'foreign native composition')
        self.sources()
        self.owned = load('oxc_composition_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        self.controls = load('oxc_composition_controls', OWNER / 'scripts/workflow_controls.py')
        self.original = Path(self.plan['original_prefix'])
        self.original_inventory = read(self.plan['original_inventory'])
        self.component = read(self.plan['component_proof'])
        require(not WORK.exists() and not WORK.is_symlink(), 'native composition must be fresh')
        WORK.mkdir()
        self.record = dict(schema_version=1, status='waiting', owner=str(OWNER), pid=os.getpid(),
            parent_pid=os.getppid(), started_at=time.time(), freeze_sha256=expected, children=[],
            original_unchanged=False, application_compilation=False, benchmark=False)
        self.save()
        self.identity_count = self.loader_count = 0

    def sources(self):
        require(sha(FROZEN) == self.expected, 'native composition freeze changed')
        for path, checksum in self.frozen['files'].items():
            require(sha(path) == checksum, 'native composition input changed: ' + path)
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['path'] and
                sha(sys.executable) == self.frozen['python']['sha256'], 'native composition Python changed')
        for path, row in self.plan['providers'].items():
            require(str(Path(path).resolve(strict=True)) == row['resolved'] and sha(path) == row['sha256'],
                    'native composition provider changed')
        require(platform_identity() == self.plan['platform'], 'native composition platform changed')

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def capacity(self):
        return self.owned.disk(OWNER, 9)

    def inventory(self, path):
        return acquire.Acquisition.inventory(self, path)

    def budget(self):
        self.capacity()
        payload = evidence = 0
        for directory, dirs, files in os.walk(WORK, followlinks=False):
            for name in [*dirs, *files]:
                path = Path(directory) / name
                row = path.lstat()
                if path.is_relative_to(PREFIX):
                    payload += row.st_blocks * 512
                else:
                    evidence += row.st_blocks * 512
        require(payload <= self.plan['payload_budget_bytes'] and evidence <= self.plan['evidence_budget_bytes'],
                'native composition allocation bound exceeded')
        return dict(payload=payload, evidence=evidence)

    def run(self, label, argv, *, environment=None, loader=False):
        self.sources()
        self.budget()
        argv = list(map(str, argv))
        if loader:
            require(len(argv) == 5 and argv[:3] == ['/usr/bin/otool', '-arch', 'arm64'] and argv[3] in ['-L', '-l'],
                    'unplanned native loader command')
            path = Path(argv[4]).resolve(strict=True)
            name = str(path.relative_to(PREFIX))
            require(name in self.expected_inventory and sha(path) == self.expected_inventory[name]['sha256'],
                    'native loader path is not in the composed toolchain')
        else:
            require(argv == self.plan['commands'].get(label), 'unplanned native composition command: ' + label)
        out = WORK / 'commands' / f'{len(self.record["children"]):03d}-{label}'
        try:
            result = self.owned.run(argv, cwd=WORK, env=environment or self.plan['environment'],
                                    out=out, capacity_root=OWNER)
        finally:
            if (out / 'receipt.json').exists():
                self.record['children'].append(dict(label=label, path=str(out), receipt=read(out / 'receipt.json')))
                self.save()
        self.sources()
        self.budget()
        require(all((out / channel).stat().st_size <= 8*2**20 for channel in ['stdout', 'stderr']),
                'native composition output exceeds bound')
        return dict(returncode=result['returncode'], stdout=(out / 'stdout').read_text(),
                    stderr=(out / 'stderr').read_text(), path=str(out))

    def identity_probe(self, argv):
        self.identity_count += 1
        return self.run('identity-' + str(self.identity_count), argv,
            environment=self.controls.native_identity_environment(self.plan['environment']))

    def copy_file(self, source, target, proof):
        require(proof['kind'] == 'file' and source.resolve(strict=True) == source and
                source.is_file() and source.stat().st_nlink == 1, 'copy requires an ordinary source file')
        before = registry_stamp(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        require(target.parent.resolve(strict=True) == target.parent, 'copy destination traverses a link')
        digest = hashlib.sha256()
        with source.open('rb') as stream, target.open('xb') as output:
            for block in iter(lambda: stream.read(1024**2), b''):
                self.capacity()
                digest.update(block)
                output.write(block)
        target.chmod(proof['mode'])
        require(digest.hexdigest() == proof['sha256'] and target.stat().st_size == proof['bytes'] and
                registry_stamp(source) == before and sha(target) == proof['sha256'] and
                (source.stat().st_dev, source.stat().st_ino) != (target.stat().st_dev, target.stat().st_ino),
                'complete native copy differs or aliases its source')

    def compose(self):
        require(self.inventory(self.original) == self.original_inventory, 'original native toolchain changed')
        PREFIX.mkdir()
        self.expected_inventory = dict(self.original_inventory)
        for name, proof in self.original_inventory.items():
            require(str(PurePosixPath(name)) == name and '..' not in PurePosixPath(name).parts and
                    not PurePosixPath(name).is_absolute(), 'invalid original member')
            self.copy_file(self.original / name, PREFIX / name, proof)
        root = 'llvm-tools-1.98.1-aarch64-apple-darwin/' + self.component['component'] + '/'
        overlay = {}
        with tarfile.open(self.plan['component_archive'], 'r:xz') as archive:
            for name in self.component['declared_files']:
                proof = self.component['members'][root + name]
                member = archive.getmember(root + name)
                require(member.isfile() and member.size == proof['bytes'] and member.mode == proof['mode'],
                        'official component member differs')
                destination = PREFIX / name
                require(destination.is_relative_to(PREFIX) and destination.parent.resolve() == destination.parent,
                        'component destination escapes the new prefix')
                collision = name in self.original_inventory
                if collision:
                    require(self.original_inventory[name]['sha256'] == proof['sha256'] and
                            self.original_inventory[name]['bytes'] == proof['bytes'], 'conflicting official component file')
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                with archive.extractfile(member) as stream:
                    if collision:
                        for block in iter(lambda: stream.read(1024**2), b''):
                            self.capacity()
                            digest.update(block)
                    else:
                        with destination.open('xb') as output:
                            for block in iter(lambda: stream.read(1024**2), b''):
                                self.capacity()
                                digest.update(block)
                                output.write(block)
                        destination.chmod(stat.S_IMODE(proof['mode']))
                require(digest.hexdigest() == proof['sha256'] and sha(destination) == proof['sha256'],
                        'official component overlay differs')
                if not collision:
                    self.expected_inventory[name] = dict(kind='file', bytes=proof['bytes'],
                        mode=stat.S_IMODE(proof['mode']), sha256=proof['sha256'])
                overlay[name] = dict(sha256=proof['sha256'], collision=collision)
        require(self.inventory(PREFIX) == self.expected_inventory, 'composed complete inventory differs')
        self.owned.write(WORK / 'toolchain-inventory.json', self.expected_inventory)
        self.owned.write(WORK / 'composition.json', dict(original=str(self.original), prefix=str(PREFIX),
            original_inventory_sha256=sha(self.plan['original_inventory']),
            component_proof_sha256=sha(self.plan['component_proof']), component_files=overlay,
            original_members_preserved=len(self.original_inventory),
            policy='complete original copy plus all official LLVM-tools payload files; linked custom toolchain with external composition ledger; original installer bookkeeping preserved'))

    def loaders(self, phase):
        def inspect(argv, text=True):
            require(text, 'loader inspection must return text')
            self.loader_count += 1
            result = self.run(phase + '-loader-' + str(self.loader_count), argv, loader=True)
            require(not result['stderr'], 'native loader inspector diagnostic')
            return result['stdout']
        rows = {}
        for role, name in self.plan['loader_roles'].items():
            closure, state = library_closure(PREFIX / name, 'aarch64-apple-darwin', inspect=inspect)
            rows[role] = dict(closure=closure, state=state)
        self.owned.write(WORK / (phase + '-loaders.json'), rows)
        return rows

    def rlib_object(self):
        path = WORK / 'stripped.rlib'
        require(path.stat().st_size <= 16*2**20, 'strip control rlib exceeds bound')
        data = path.read_bytes()
        require(data.startswith(b'!<arch>\n'), 'strip control did not produce an ar archive')
        offset, names, objects = 8, b'', []
        while offset < len(data):
            header = data[offset:offset+60]
            require(len(header) == 60 and header[58:] == b'`\n', 'malformed control ar member')
            size = int(header[48:58].strip())
            require(0 <= size <= len(data)-offset-60, 'invalid control ar member size')
            payload = data[offset+60:offset+60+size]
            name = header[:16].rstrip()
            if name.startswith(b'#1/'):
                length = int(name[3:])
                require(0 < length <= len(payload), 'invalid BSD ar name')
                name, payload = payload[:length].rstrip(b'\0'), payload[length:]
            elif name == b'//':
                names = payload
            elif name.startswith(b'/') and name[1:].isdigit():
                start = int(name[1:])
                require(start < len(names) and b'/\n' in names[start:], 'invalid GNU ar name')
                name = names[start:].split(b'/\n', 1)[0]
            else:
                name = name.removesuffix(b'/')
            if name.endswith(b'.o'):
                require(payload.startswith(b'\xcf\xfa\xed\xfe'), 'control rlib object is not native Mach-O')
                objects.append((name.decode(), payload))
            offset += 60 + size + (size % 2)
        require(offset == len(data) and len(objects) == 1, 'expected one complete codegen-unit strip control object')
        name, payload = objects[0]
        with (WORK / 'rlib-object.o').open('xb') as output:
            output.write(payload)
        self.owned.write(WORK / 'rlib-object-proof.json', dict(archive_sha256=sha(path), member=name,
            bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest()))

    def execute(self):
        try:
            with self.owned.workload_lock(self.plan['canonical_lock'], 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 16))
                self.save()
                for directory in ['home', 'rustup', 'tmp']:
                    (WORK / directory).mkdir()
                for path, digest in self.frozen['files'].items():
                    if path == self.plan['component_archive']:
                        continue  # Preserve downloaded archive in its original owned stage.
                    destination = WORK / 'inputs' / path.lstrip('/')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with destination.open('xb') as output:
                        output.write(Path(path).read_bytes())
                    require(sha(destination) == digest, 'native composition input copy differs')
                self.compose()
                self.run('link-toolchain', self.plan['commands']['link-toolchain'])
                identity = self.controls.inspect_native_toolchain(self.plan['toolchain'], self.identity_probe,
                    environment=self.plan['environment'], source=acquire.SOURCE)
                original_identity = read(self.plan['original_identity'])
                for role in ['rustc', 'cargo']:
                    require(identity['tools'][role]['sha256'] == original_identity['tools'][role]['sha256'] and
                            identity['tools'][role]['version_stdout'] == original_identity['tools'][role]['version_stdout'],
                            'composed native compiler bytes/version differ')
                self.owned.write(WORK / 'native-toolchain-identity.json', identity)
                loaders = self.loaders('initial')
                (WORK / 'strip.rs').write_text(self.plan['strip_source'])
                (WORK / 'run.rs').write_text(self.plan['run_source'])
                for label in ['compile-debug-object', 'inspect-debug-object', 'strip-debug-object',
                              'inspect-stripped-object', 'compiler-strip-rlib', 'inspect-rlib-object',
                              'compiler-strip-binary', 'run-stripped-binary']:
                    if label == 'inspect-rlib-object':
                        self.rlib_object()
                    result = self.run(label, self.plan['commands'][label])
                    require(not result['stderr'], 'native strip control emitted diagnostics: ' + label)
                    if label == 'inspect-debug-object':
                        require(re.search(r'\bsectname __debug_\w+', result['stdout']), 'control object lacks debug sections')
                    elif label in ['inspect-stripped-object', 'inspect-rlib-object']:
                        require(not re.search(r'\bsectname __debug_\w+', result['stdout']), 'debug sections survived actual stripping')
                    elif label == 'run-stripped-binary':
                        require(result['stdout'] == '42\n', 'stripped native program differs')
                self.controls.revalidate_native_toolchain(identity, self.identity_probe,
                    environment=self.plan['environment'], source=acquire.SOURCE)
                require(self.loaders('final') == loaders, 'native composed loader closure changed')
                require(self.inventory(PREFIX) == self.expected_inventory and
                        self.inventory(self.original) == self.original_inventory, 'native payload changed across controls')
                for proof in loaders.values():
                    require(library_state(proof['closure']) == proof['state'], 'native loader file/search changed')
                self.sources()
                require(len(self.record['children']) == self.plan['expected_children'] and
                        self.identity_count == self.plan['expected_identity_children'] and
                        self.loader_count == self.plan['expected_loader_children'], 'native composition history count differs')
                self.record.update(status='passed', original_unchanged=True, original_members=len(self.original_inventory),
                    composed_members=len(self.expected_inventory), stripping_qualified=True,
                    allocation=self.budget(), free_bytes_after=self.capacity(),
                    artifacts={name: dict(bytes=(WORK/name).stat().st_size, sha256=sha(WORK/name))
                               for name in ['strip.rs', 'run.rs', 'debug.o', 'stripped.o', 'stripped.rlib',
                                            'rlib-object.o', 'stripped-program']})
        except BaseException as error:
            self.record.update(status='failed', error=repr(error))
            raise
        finally:
            self.record['finished_at'] = time.time()
            self.save()


def registry_stamp(path):
    row = path.lstat()
    return row.st_dev, row.st_ino, row.st_mode, row.st_nlink, row.st_size, row.st_mtime_ns, row.st_ctime_ns


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--frozen-sha256', required=True)
    Composition(parser.parse_args().frozen_sha256).execute()
