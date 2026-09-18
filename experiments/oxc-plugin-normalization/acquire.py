#!/usr/bin/env python3
"""Acquire the exact Oxc/native inputs once; never build or run an Oxc target."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time
import tomllib

OWNER = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLAN = HERE / 'acquisition-plan-01.json'
FROZEN = OWNER / '.work/oxc-acquisition-source-01/inputs.json'
WORK = OWNER / '.work/oxc-native-setup-01'
SOURCE = OWNER / '.work/sources/oxc'


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Acquisition:
    def __init__(self, expected):
        require(sha(FROZEN) == expected, 'acquisition freeze differs')
        self.expected = expected
        self.frozen = read(FROZEN)
        self.plan = read(PLAN)
        require(self.plan['owner'] == self.frozen['owner'] == str(OWNER), 'foreign acquisition')
        self.sources_guard()
        self.owned = load('oxc_acquisition_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        self.controls = load('oxc_acquisition_native', OWNER / 'scripts/workflow_controls.py')
        require(not WORK.exists() and not WORK.is_symlink(), 'setup work must be fresh')
        require(not SOURCE.exists() and not SOURCE.is_symlink(), 'source destination must be fresh')
        WORK.mkdir(parents=True)
        self.record = dict(schema_version=1, status='waiting', owner=str(OWNER), pid=os.getpid(),
            parent_pid=os.getppid(), started_at=time.time(), freeze_sha256=expected, children=[],
            source_acquired=False, native_compilation=False, benchmark=False)
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def sources_guard(self):
        require(sha(FROZEN) == self.expected, 'acquisition freeze changed')
        for path, digest in self.frozen['files'].items():
            require(sha(path) == digest, 'acquisition source/executor changed: ' + path)
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['path'] and
                sha(self.frozen['python']['path']) == self.frozen['python']['sha256'], 'acquisition Python changed')

    def capacity(self):
        return self.owned.disk(OWNER, 8)

    def budget(self):
        self.capacity()
        seen = set()
        allocated = 0
        evidence = 0
        for root in [WORK, SOURCE]:
            if not root.exists():
                continue
            for directory, dirs, files in os.walk(root, followlinks=False):
                for name in [*dirs, *files]:
                    row = (Path(directory) / name).lstat()
                    key = row.st_dev, row.st_ino
                    if key not in seen:
                        seen.add(key)
                        allocated += row.st_blocks * 512
                        path = Path(directory) / name
                        if root == WORK and path.relative_to(WORK).parts[0] not in {
                                'home', 'cargo', 'rustup', 'tmp', 'metadata-target'}:
                            evidence += row.st_blocks * 512
        require(allocated <= self.plan['allocation_budget_bytes'] + self.plan['evidence_budget_bytes'],
                'acquisition exceeded its retained allocation budget')
        require(evidence <= self.plan['evidence_budget_bytes'], 'acquisition evidence exceeds budget')
        return allocated

    def run(self, label, argv, *, cwd, environment=None):
        self.sources_guard()
        self.budget()
        argv = list(map(str, argv))
        env = self.plan['environment'] if environment is None else environment
        expected = self.plan['commands'].get(label)
        identity_probe = (len(argv) == 5 and argv[:4] ==
                          [self.plan['rustup'], 'which', '--toolchain', self.plan['toolchain']] and
                          argv[4] in ['rustc', 'cargo']) or (
                          len(argv) == 2 and argv[0] in [self.plan['rustc'], self.plan['cargo']] and argv[1] == '-vV')
        require(expected == dict(command=argv, cwd=str(cwd)) or label.startswith('identity-') and identity_probe,
                'acquisition command is outside its allowlist')
        out = WORK / 'commands' / f'{len(self.record["children"]):02d}-{label}'
        try:
            result = self.owned.run(argv, cwd=cwd, env=env, out=out, capacity_root=OWNER)
        finally:
            if (out / 'receipt.json').exists():
                self.record['children'].append(dict(label=label, path=str(out), receipt=read(out / 'receipt.json')))
                self.save()
        self.budget()
        self.sources_guard()
        require(all((out / name).stat().st_size <= 32 * 2**20 for name in ['stdout', 'stderr']),
                'acquisition child output exceeds evidence bound')
        return dict(returncode=result['returncode'], stdout=(out / 'stdout').read_text(),
                    stderr=(out / 'stderr').read_text(), path=str(out))

    def inventory(self, root):
        root = Path(root).resolve(strict=True)
        rows = {}
        for directory, dirs, files in os.walk(root, followlinks=False):
            self.capacity()
            for name in sorted([*dirs, *files]):
                path = Path(directory) / name
                row = path.lstat()
                relative = str(path.relative_to(root))
                if stat.S_ISLNK(row.st_mode):
                    rows[relative] = dict(kind='symlink', target=os.readlink(path))
                elif stat.S_ISREG(row.st_mode):
                    require(row.st_size <= 512 * 2**20, 'oversized acquired input: ' + str(path))
                    digest = sha(path)
                    after = path.lstat()
                    require((row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns) ==
                            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                            'acquired input changed during inventory')
                    rows[relative] = dict(kind='file', bytes=row.st_size, sha256=digest, mode=stat.S_IMODE(row.st_mode))
                else:
                    require(stat.S_ISDIR(row.st_mode), 'unsupported acquired input')
                require(len(rows) <= 250000, 'acquired inventory exceeds file-count budget')
        return rows

    def source_guard(self):
        revision = self.run('source-head', self.plan['commands']['source-head']['command'], cwd=SOURCE)['stdout'].strip()
        require(revision == self.plan['revision'], 'Oxc commit differs')
        status = self.run('source-status', self.plan['commands']['source-status']['command'], cwd=SOURCE)['stdout']
        require(status in ['', '?? .rust-interp-owned.json\n'], 'Oxc source acquired tracked/unexpected edits')
        review = read(OWNER / 'results/oxc-target-source-review-01/source-review.json')
        for name, item in review['input_sources'].items():
            path = SOURCE / name
            require(path.resolve(strict=True) == path and path.is_file() and path.stat().st_size == item['bytes']
                    and sha(path) == item['sha256'], 'Oxc reviewed source differs: ' + name)

    def execute(self):
        try:
            with self.owned.workload_lock(self.plan['canonical_lock'], 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 16))
                self.save()
                self.sources_guard()
                require(sum(Path(path).stat().st_size for path in self.frozen['files']) <= 48 * 2**20,
                        'acquisition source retention exceeds budget')
                for path, digest in self.frozen['files'].items():
                    destination = WORK / 'inputs' / path.lstrip('/')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with destination.open('xb') as output:
                        output.write(Path(path).read_bytes())
                    require(sha(destination) == digest, 'acquisition input readback differs')
                for name in ['home', 'cargo', 'rustup', 'tmp']:
                    (WORK / name).mkdir()
                SOURCE.mkdir(parents=True)
                self.owned.write(SOURCE / '.rust-interp-owned.json', dict(owner=str(OWNER), source=self.plan['repository']))
                for label in ['source-init', 'source-fetch', 'source-checkout']:
                    command = self.plan['commands'][label]
                    self.run(label, command['command'], cwd=Path(command['cwd']))
                self.source_guard()
                self.owned.write(SOURCE / '.rust-interp-owned.json',
                    dict(owner=str(OWNER), source=self.plan['repository'], revision=self.plan['revision']))
                self.record['source_acquired'] = True
                source_inventory = self.inventory(SOURCE)
                self.owned.write(WORK / 'source-inventory.json', source_inventory)
                command = self.plan['commands']['toolchain-install']
                self.run('toolchain-install', command['command'], cwd=Path(command['cwd']))
                counter = 0
                def probe(argv):
                    nonlocal counter
                    counter += 1
                    return self.run('identity-' + str(counter), argv, cwd=SOURCE,
                                    environment=self.controls.native_identity_environment(self.plan['environment']))
                identity = self.controls.inspect_native_toolchain(self.plan['toolchain'], probe,
                    environment=self.plan['environment'], source=SOURCE)
                version = identity['tools']['rustc']['version_stdout']
                require('\nrelease: 1.98.1\n' in version and '\nhost: aarch64-apple-darwin\n' in version,
                        'installed rustc does not match upstream 1.98.1/native host')
                require(identity['tools']['cargo']['resolved'] == self.plan['cargo'] and
                        identity['tools']['rustc']['resolved'] == self.plan['rustc'], 'installed executors differ')
                self.owned.write(WORK / 'native-toolchain-identity.json', identity)
                cargo_env = self.controls.native_environment(self.plan['environment'], 'repository', [], compiler=identity)
                for label in ['dependencies', 'resolved-metadata']:
                    command = self.plan['commands'][label]
                    output = self.run(label, command['command'], cwd=Path(command['cwd']), environment=cargo_env)
                    if label == 'resolved-metadata':
                        metadata = json.loads(output['stdout'])
                        self.owned.write(WORK / 'cargo-metadata.json', metadata)
                lock = tomllib.loads((SOURCE / 'Cargo.lock').read_text())
                checksums = {(p['name'], p['version'], p.get('source')): p.get('checksum') for p in lock['package']}
                registry = {}
                for package in metadata['packages']:
                    if not package.get('source'):
                        require(Path(package['manifest_path']).resolve().is_relative_to(SOURCE), 'nonlocal workspace package')
                        continue
                    require(package['source'].startswith('registry+'), 'unplanned Git dependency')
                    package_root = Path(package['manifest_path']).parent.resolve(strict=True)
                    require(package_root.is_relative_to(WORK / 'cargo/registry/src'), 'registry source is outside owned cache')
                    checksum = read(package_root / '.cargo-checksum.json')
                    require(checksum['package'] == checksums[(package['name'], package['version'], package['source'])],
                            'registry archive checksum differs from Cargo.lock')
                    archive = WORK / 'cargo/registry/cache' / package_root.parent.name / (package_root.name + '.crate')
                    require(archive.resolve(strict=True) == archive and sha(archive) == checksum['package'],
                            'downloaded registry archive differs from Cargo.lock')
                    for name, digest in checksum['files'].items():
                        path = package_root / name
                        require(path.resolve(strict=True) == path and path.is_relative_to(package_root)
                                and sha(path) == digest, 'registry source checksum differs')
                    registry[package['id']] = dict(root=str(package_root), archive=str(archive), checksum=checksum)
                self.owned.write(WORK / 'registry-checksums.json', registry)
                self.source_guard()
                require(self.inventory(SOURCE) == source_inventory, 'source checkout changed during acquisition')
                self.controls.revalidate_native_toolchain(identity, probe, environment=self.plan['environment'], source=SOURCE)
                self.owned.write(WORK / 'toolchain-inventory.json', self.inventory(Path(self.plan['rustc']).parents[1]))
                require(len(self.record['children']) == self.plan['expected_outer_children'], 'acquisition child count differs')
                self.record.update(status='passed', registry_packages=len(registry), metadata_packages=len(metadata['packages']),
                    allocated_bytes=self.budget(), free_bytes_after=self.capacity(), native_compilation=False,
                    native_compatibility=False, runtime_compatibility=False, benchmark=False)
        except BaseException as error:
            self.record.update(status='failed', error=repr(error))
            raise
        finally:
            self.record['finished_at'] = time.time()
            self.save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frozen-sha256', required=True)
    args = parser.parse_args()
    Acquisition(args.frozen_sha256).execute()


if __name__ == '__main__':
    main()
