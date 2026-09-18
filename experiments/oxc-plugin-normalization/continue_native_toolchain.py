#!/usr/bin/env python3
"""Complete native stripping qualification after the retained rlib fixture failure."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

import acquire

OWNER, HERE = acquire.OWNER, acquire.HERE
WORK = OWNER / '.work/oxc-native-toolchain-composition-continuation-01'
COMPOSED = OWNER / '.work/oxc-native-toolchain-composition-01'
PREFIX = COMPOSED / 'toolchain'
PLAN = HERE / 'native-toolchain-composition-continuation-plan-01.json'
FROZEN = OWNER / '.work/oxc-native-toolchain-composition-continuation-source-01/inputs.json'
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
        self.expected_inventory = read(COMPOSED / 'toolchain-inventory.json')
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
        evidence = 0
        for directory, dirs, files in os.walk(WORK, followlinks=False):
            for name in [*dirs, *files]:
                path = Path(directory) / name
                row = path.lstat()
                evidence += row.st_blocks * 512
        require(evidence <= self.plan['evidence_budget_bytes'],
                'native composition allocation bound exceeded')
        return dict(evidence=evidence, existing_payload_modified=False)

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

    def prior_guard(self):
        previous = read(COMPOSED / 'receipt.json')
        require(previous['status'] == 'failed' and len(previous['children']) == 25 and
                previous['error'] == "RuntimeError('debug sections survived actual stripping')",
                'unexpected prior composition history')
        require(self.inventory(self.original) == self.original_inventory and
                self.inventory(PREFIX) == self.expected_inventory, 'native payload changed')
        for child in previous['children']:
            path = Path(child['path'])
            require(read(path / 'receipt.json') == child['receipt'] and child['receipt']['returncode'] == 0,
                    'previous child differs')
            for channel in ['stdout', 'stderr']:
                require(sha(path / channel) == child['receipt'][channel + '_sha256'], 'previous stream changed')
            require(not (path / 'stderr').read_bytes(), 'previous child diagnostic')
        by_label = {row['label']: Path(row['path']) for row in previous['children']}
        require(re.search(r'\bsectname __debug_\w+', (by_label['inspect-debug-object'] / 'stdout').read_text()) and
                not re.search(r'\bsectname __debug_\w+', (by_label['inspect-stripped-object'] / 'stdout').read_text()),
                'previous direct objcopy control did not strip debug sections')
        for name, digest in self.plan['prior_artifacts'].items():
            require(sha(COMPOSED / name) == digest, 'previous strip artifact changed')
        return read(COMPOSED / 'initial-loaders.json')

    def execute(self):
        try:
            with self.owned.workload_lock(self.plan['canonical_lock'], 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 16))
                self.save()
                self.sources()
                for path, digest in self.frozen['files'].items():
                    destination = WORK / 'inputs' / path.lstrip('/')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with destination.open('xb') as output:
                        output.write(Path(path).read_bytes())
                    require(sha(destination) == digest, 'native continuation input copy differs')
                loaders = self.prior_guard()
                for proof in loaders.values():
                    require(library_state(proof['closure']) == proof['state'], 'native loader state changed')
                identity = read(COMPOSED / 'native-toolchain-identity.json')
                self.controls.revalidate_native_toolchain(identity, self.identity_probe,
                    environment=self.plan['environment'], source=acquire.SOURCE)
                (WORK / 'run.rs').write_text(self.plan['run_source'])
                for label in ['compiler-strip-binary', 'run-stripped-binary']:
                    result = self.run(label, self.plan['commands'][label])
                    require(not result['stderr'], 'actual native binary strip emitted diagnostics')
                    if label == 'run-stripped-binary':
                        require(result['stdout'] == '42\n', 'stripped native program differs')
                self.controls.revalidate_native_toolchain(identity, self.identity_probe,
                    environment=self.plan['environment'], source=acquire.SOURCE)
                require(self.loaders('final') == loaders, 'native composed loader closure changed')
                require(self.prior_guard() == loaders, 'prior composition inputs changed')
                for proof in loaders.values():
                    require(library_state(proof['closure']) == proof['state'], 'native loader state changed')
                self.sources()
                require(len(self.record['children']) == self.plan['expected_children'] and
                        self.identity_count == self.plan['expected_identity_children'] and
                        self.loader_count == self.plan['expected_loader_children'], 'native continuation history count differs')
                self.record.update(status='passed', original_unchanged=True, original_members=len(self.original_inventory),
                    composed_members=len(self.expected_inventory), stripping_qualified=True,
                    allocation=self.budget(), free_bytes_after=self.capacity(),
                    prior_failed_receipt_sha256=sha(COMPOSED / 'receipt.json'),
                    qualified_inventory_sha256=sha(COMPOSED / 'toolchain-inventory.json'),
                    qualified_native_identity_sha256=sha(COMPOSED / 'native-toolchain-identity.json'),
                    artifacts={name: dict(bytes=(WORK/name).stat().st_size, sha256=sha(WORK/name))
                               for name in ['run.rs', 'stripped-program']})
        except BaseException as error:
            self.record.update(status='failed', error=repr(error))
            raise
        finally:
            self.record['finished_at'] = time.time()
            self.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--frozen-sha256', required=True)
    Composition(parser.parse_args().frozen_sha256).execute()
