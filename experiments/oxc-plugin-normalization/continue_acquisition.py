#!/usr/bin/env python3
"""Finish acquisition proof from saved bytes; no download, extraction, or build."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import tomllib

import acquire
import registry_cache

OWNER, SOURCE, ACQUIRED = acquire.OWNER, acquire.SOURCE, acquire.WORK
WORK = OWNER / '.work/oxc-acquisition-continuation-01'
FROZEN = OWNER / '.work/oxc-acquisition-continuation-source-01/inputs.json'
PLAN = acquire.HERE / 'continuation-plan-01.json'
require, sha, read, load = acquire.require, acquire.sha, acquire.read, acquire.load


class Continuation(acquire.Acquisition):
    def __init__(self, expected):
        require(sha(FROZEN) == expected, 'continuation freeze differs')
        self.expected, self.frozen = expected, read(FROZEN)
        self.continuation, self.plan = read(PLAN), read(acquire.PLAN)
        require(self.continuation['owner'] == self.frozen['owner'] == str(OWNER), 'foreign continuation')
        self.sources_guard()
        self.owned = load('oxc_continuation_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        self.controls = load('oxc_continuation_native', OWNER / 'scripts/workflow_controls.py')
        require(not WORK.exists() and not WORK.is_symlink(), 'continuation output must be fresh')
        WORK.mkdir()
        self.record = dict(schema_version=1, status='waiting', owner=str(OWNER), pid=os.getpid(),
            parent_pid=os.getppid(), started_at=time.time(), freeze_sha256=expected, children=[],
            prior_receipt_sha256=sha(ACQUIRED / 'receipt.json'), native_compilation=False, benchmark=False)
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def sources_guard(self):
        require(sha(FROZEN) == self.expected, 'continuation freeze changed')
        for path, checksum in self.frozen['files'].items():
            require(sha(path) == checksum, 'continuation input changed: ' + path)
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['path'] and
                sha(sys.executable) == self.frozen['python']['sha256'], 'continuation Python differs')

    def capacity(self):
        return self.owned.disk(OWNER, 9)

    def budget(self):
        original = super().budget()
        evidence = sum(path.lstat().st_blocks * 512 for path in WORK.rglob('*'))
        require(evidence <= self.continuation['evidence_budget_bytes'], 'continuation evidence bound exceeded')
        return original + evidence

    def run(self, label, argv, *, cwd, environment=None):
        self.sources_guard()
        self.budget()
        argv = list(map(str, argv))
        require(dict(command=argv, cwd=str(cwd)) == self.continuation['commands'].get(label),
                'continuation command is outside its allowlist')
        out = WORK / 'commands' / f'{len(self.record["children"]):02d}-{label}'
        try:
            result = self.owned.run(argv, cwd=cwd, env=environment or self.plan['environment'],
                                    out=out, capacity_root=OWNER)
        finally:
            if (out / 'receipt.json').exists():
                self.record['children'].append(dict(label=label, path=str(out), receipt=read(out / 'receipt.json')))
                self.save()
        self.budget()
        self.sources_guard()
        require(all((out / name).stat().st_size <= 32 * 2**20 for name in ['stdout', 'stderr']),
                'continuation output bound exceeded')
        return dict(returncode=result['returncode'], stdout=(out / 'stdout').read_text(),
                    stderr=(out / 'stderr').read_text(), path=str(out))

    def prior_guard(self):
        prior = read(ACQUIRED / 'receipt.json')
        require(prior['status'] == 'failed' and prior['source_acquired'] and
                not prior['native_compilation'] and not prior['benchmark'] and
                prior['freeze_sha256'] == sha(acquire.FROZEN), 'unexpected prior outcome')
        labels = ['source-init', 'source-fetch', 'source-checkout', 'source-head', 'source-status',
                  'toolchain-install', 'identity-1', 'identity-2', 'identity-3', 'identity-4',
                  'dependencies', 'resolved-metadata']
        require([row['label'] for row in prior['children']] == labels, 'unexpected prior child sequence')
        for row in prior['children']:
            directory = Path(row['path'])
            require(directory.resolve(strict=True).is_relative_to(ACQUIRED / 'commands'), 'foreign prior child')
            child = read(directory / 'receipt.json')
            require(child == row['receipt'] and child['status'] == 'finished' and child['returncode'] == 0,
                    'prior child did not succeed')
            for channel in ['stdout', 'stderr']:
                require(sha(directory / channel) == child[channel + '_sha256'], 'prior raw output changed')
        metadata = read(ACQUIRED / 'cargo-metadata.json')
        require(metadata == read(Path(prior['children'][-1]['path']) / 'stdout'), 'saved metadata differs from child')
        return metadata

    def registry(self, metadata):
        lock = tomllib.loads((SOURCE / 'Cargo.lock').read_text())
        source_id = 'registry+https://github.com/rust-lang/crates.io-index'
        locked = {}
        for package in lock['package']:
            if package.get('source'):
                require(package['source'] == source_id, 'unplanned dependency source')
                name = package['name'] + '-' + package['version']
                require(name not in locked, 'ambiguous registry package root')
                locked[name] = package['checksum']
        registry = ACQUIRED / 'cargo/registry'
        cache, extracted = registry / 'cache', registry / 'src'
        registry_name = 'index.crates.io-1949cf8c6b5b557f'
        require(sorted(p.name for p in cache.iterdir()) == [registry_name] and
                sorted(p.name for p in extracted.iterdir()) == [registry_name], 'unexpected registry cache')
        archives = sorted((cache / registry_name).iterdir())
        roots = sorted((extracted / registry_name).iterdir())
        require(all(p.suffix == '.crate' for p in archives) and
                [p.stem for p in archives] == [p.name for p in roots], 'cache/archive membership differs')
        require(len(archives) == self.continuation['expected_archives'], 'acquired archive count changed')
        verified, total = {}, 0
        for archive, root in zip(archives, roots):
            self.capacity()
            require(root.name in locked, 'download is not in Cargo.lock')
            proof = registry_cache.verify(archive, root, locked[root.name], capacity=self.capacity)
            total += proof['unpacked_bytes']
            require(total <= self.plan['allocation_budget_bytes'], 'registry byte budget exceeded')
            verified[root.name] = proof
        package_ids = {}
        for package in metadata['packages']:
            manifest = Path(package['manifest_path'])
            require(manifest.resolve(strict=True) == manifest, 'metadata manifest traverses a link')
            if package.get('source'):
                name = package['name'] + '-' + package['version']
                require(package['source'] == source_id and name in verified and
                        manifest == extracted / registry_name / name / 'Cargo.toml', 'metadata registry mismatch')
                package_ids[package['id']] = name
            else:
                require(manifest.is_relative_to(SOURCE), 'nonlocal workspace package')
        require(len(package_ids) == self.continuation['expected_metadata_registry_packages'] and
                len(metadata['packages']) == self.continuation['expected_metadata_packages'], 'metadata count changed')
        self.owned.write(WORK / 'registry-checksums.json', dict(archives=verified, metadata_registry=package_ids))
        return len(verified), len(package_ids), total

    def execute(self):
        try:
            with self.owned.workload_lock(self.plan['canonical_lock'], 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 16))
                self.save()
                self.sources_guard()
                require(sum(Path(p).stat().st_size for p in self.frozen['files']) <= 48 * 2**20,
                        'continuation input retention exceeds budget')
                for path, checksum in self.frozen['files'].items():
                    destination = WORK / 'inputs' / path.lstrip('/')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with destination.open('xb') as output:
                        output.write(Path(path).read_bytes())
                    require(sha(destination) == checksum, 'continuation input readback differs')
                command = self.continuation['commands']['validator-controls']
                self.run('validator-controls', command['command'], cwd=Path(command['cwd']),
                         environment=self.continuation['control_environment'])
                metadata = self.prior_guard()
                require(self.inventory(SOURCE) == read(ACQUIRED / 'source-inventory.json'), 'saved source changed')
                archives, packages, total = self.registry(metadata)
                self.source_guard()
                require(self.inventory(SOURCE) == read(ACQUIRED / 'source-inventory.json'), 'source changed during proof')
                identity = read(ACQUIRED / 'native-toolchain-identity.json')
                counter = 0
                def probe(argv):
                    nonlocal counter
                    counter += 1
                    return self.run('identity-' + str(counter), argv, cwd=SOURCE,
                        environment=self.controls.native_identity_environment(self.plan['environment']))
                self.controls.revalidate_native_toolchain(identity, probe, environment=self.plan['environment'], source=SOURCE)
                self.owned.write(WORK / 'toolchain-inventory.json', self.inventory(Path(self.plan['rustc']).parents[1]))
                self.sources_guard()
                require(len(self.record['children']) == 7, 'continuation child count differs')
                self.record.update(status='passed', archives=archives, metadata_registry_packages=packages,
                    metadata_packages=len(metadata['packages']), unpacked_registry_bytes=total,
                    allocated_bytes=self.budget(), free_bytes_after=self.capacity(), native_compatibility=False,
                    runtime_compatibility=False, benchmark=False)
        except BaseException as error:
            self.record.update(status='failed', error=repr(error))
            raise
        finally:
            self.record['finished_at'] = time.time()
            self.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--frozen-sha256', required=True)
    Continuation(parser.parse_args().frozen_sha256).execute()
