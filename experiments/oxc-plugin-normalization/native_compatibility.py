#!/usr/bin/env python3
"""Qualify the unchanged complete Oxc library-test target with upstream Rust."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

import acquire
import registry_cache

OWNER, SOURCE, ACQUIRED = acquire.OWNER, acquire.SOURCE, acquire.WORK
WORK = OWNER / '.work/oxc-native-compatibility-01'
CONTINUATION = OWNER / '.work/oxc-acquisition-continuation-01'
FROZEN = OWNER / '.work/oxc-native-compatibility-source-01/inputs.json'
PLAN = acquire.HERE / 'native-compatibility-plan-01.json'
require, sha, read, load = acquire.require, acquire.sha, acquire.read, acquire.load
sys.path.insert(0, str(OWNER / 'scripts'))
from custom_cargo_libraries import library_closure, library_state, platform_identity
from workflow_io import SourceEdit
from workflow_measurements import source_states


class Compatibility(acquire.Acquisition):
    def __init__(self, expected):
        require(sha(FROZEN) == expected, 'native compatibility freeze differs')
        self.expected, self.frozen = expected, read(FROZEN)
        self.native, self.plan = read(PLAN), read(acquire.PLAN)
        require(self.native['owner'] == self.frozen['owner'] == str(OWNER), 'foreign native stage')
        self.owned = load('oxc_native_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        self.controls = load('oxc_native_controls', OWNER / 'scripts/workflow_controls.py')
        self.case = read(acquire.HERE / 'case.json')['case']
        self.identity = read(ACQUIRED / 'native-toolchain-identity.json')
        self.environment = self.controls.native_environment(self.native['environment'], 'repository', [],
                                                            compiler=self.identity)
        self.sources_guard()
        require(not WORK.exists() and not WORK.is_symlink(), 'native target/output must be fresh')
        WORK.mkdir()
        self.record = dict(schema_version=1, status='waiting', owner=str(OWNER), pid=os.getpid(),
            parent_pid=os.getppid(), started_at=time.time(), freeze_sha256=expected,
            children=[], states=[], benchmark=False, native_compatibility=False)
        self.probes = 0
        self.loader_probes = 0
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def sources_guard(self):
        require(sha(FROZEN) == self.expected, 'native freeze changed')
        for path, checksum in self.frozen['files'].items():
            require(sha(path) == checksum, 'native stage input changed: ' + path)
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['path'] and
                sha(sys.executable) == self.frozen['python']['sha256'], 'native controller Python changed')
        for path, proof in self.native['providers'].items():
            p = Path(path)
            require(str(p.resolve(strict=True)) == proof['resolved'] and sha(p) == proof['sha256'],
                    'SDK/tool provider bytes or route changed: ' + path)
        for name, path in self.native['path_routes'].items():
            require(shutil.which(name, path=self.native['environment']['PATH']) == path, 'native PATH route changed')
        require(platform_identity() == self.native['platform'], 'native system platform changed')

    def capacity(self):
        return self.owned.disk(OWNER, 9)

    def budget(self):
        self.capacity()
        target, evidence = 0, 0
        seen = set()
        for directory, dirs, files in os.walk(WORK, followlinks=False):
            for name in [*dirs, *files]:
                path = Path(directory) / name
                row = path.lstat()
                key = row.st_dev, row.st_ino
                if key in seen:
                    continue
                seen.add(key)
                if path.is_relative_to(WORK / 'target'):
                    target += row.st_blocks * 512
                else:
                    evidence += row.st_blocks * 512
        require(target <= self.native['target_budget_bytes'] and evidence <= self.native['evidence_budget_bytes'],
                'native target/evidence allocation bound exceeded')
        return dict(target=target, evidence=evidence)

    def run(self, label, argv, *, cwd=SOURCE, environment=None, expected=(0,), loader=False):
        self.sources_guard()
        self.budget()
        argv = list(map(str, argv))
        if loader:
            require(argv[:3] == ['/usr/bin/otool', '-arch', 'arm64'] and argv[3] in ['-L', '-l'] and len(argv) == 5,
                    'unplanned loader inspection')
            target = Path(argv[4])
            relative = str(target.resolve(strict=True).relative_to(Path(self.plan['rustc']).parents[1]))
            require(relative in self.toolchain and self.toolchain[relative]['kind'] == 'file' and
                    sha(target) == self.toolchain[relative]['sha256'], 'loader target is not an admitted toolchain file')
        elif label == 'test-list':
            require(argv == [str(self.executable), '--list', '--format', 'terse', '--exact', *self.case['tests']],
                    'unexpected test-discovery command')
        else:
            require(dict(command=argv, cwd=str(cwd)) == self.native['commands'].get(label),
                    'native command is outside its allowlist: ' + label)
        out = WORK / 'commands' / f'{len(self.record["children"]):03d}-{label}'
        try:
            result = self.owned.run(argv, cwd=cwd, env=environment or self.environment, out=out,
                                    capacity_root=OWNER, expected=expected)
        finally:
            if (out / 'receipt.json').exists():
                self.record['children'].append(dict(label=label, path=str(out), receipt=read(out / 'receipt.json')))
                self.save()
        self.budget()
        self.sources_guard()
        require(all((out / channel).stat().st_size <= 64 * 2**20 for channel in ['stdout', 'stderr']),
                'native command output exceeds bound')
        return dict(returncode=result['returncode'], stdout=(out / 'stdout').read_text(),
                    stderr=(out / 'stderr').read_text(), path=str(out))

    def native_probe(self, argv):
        self.probes += 1
        return self.run('identity-' + str(self.probes), argv,
                        environment=self.controls.native_identity_environment(self.native['environment']))

    def acquired_guard(self):
        require(read(CONTINUATION / 'receipt.json')['status'] == 'passed', 'completed acquisition proof required')
        self.toolchain = read(CONTINUATION / 'toolchain-inventory.json')
        require(self.inventory(Path(self.plan['rustc']).parents[1]) == self.toolchain, 'installed toolchain changed')
        for proof in read(CONTINUATION / 'registry-checksums.json')['archives'].values():
            require(registry_cache.verify(proof['archive'], proof['root'], proof['checksum'], capacity=self.capacity)
                    == proof, 'acquired registry input changed')

    def checkout_guard(self):
        # Git may refresh its index stat cache after a restored edit; every
        # non-.git source member remains bound to its original bytes and mode.
        def source_members(rows):
            return {name: row for name, row in rows.items() if not name.startswith('.git/')}
        require(source_members(self.inventory(SOURCE)) == source_members(read(ACQUIRED / 'source-inventory.json')),
                'upstream source/config/lock/profile/test bytes changed')
        self.source_guard()

    def sdk(self, phase):
        observed = {}
        for name in self.native['sdk_order']:
            command = self.native['commands'][phase + '-' + name]
            result = self.run(phase + '-' + name, command['command'], cwd=Path(command['cwd']))
            require(not result['stderr'], 'SDK identity probe emitted diagnostics')
            observed[name] = result['stdout']
        require(observed['sdk-path'].strip() == self.native['sdk_path'] and
                observed['clang-path'].strip() == self.native['clang_path'] and
                observed['ld-path'].strip() == self.native['ld_path'] and
                observed['otool-path'].strip() == self.native['otool_path'], 'SDK selected route differs')
        self.owned.write(WORK / (phase + '-sdk.json'), observed)
        return observed

    def loaders(self, phase):
        result = {}
        def inspect(argv, text=True):
            require(text, 'loader probe requires text')
            self.loader_probes += 1
            row = self.run(phase + '-loader-' + str(self.loader_probes), argv, loader=True)
            require(not row['stderr'], 'loader inspector emitted diagnostics')
            return row['stdout']
        for role in ['rustc', 'cargo']:
            closure, state = library_closure(Path(self.plan[role]), 'aarch64-apple-darwin', inspect=inspect)
            result[role] = dict(closure=closure, state=state)
        self.owned.write(WORK / (phase + '-loaders.json'), result)
        return result

    def artifact(self, result):
        events = []
        test_lines = []
        finished = False
        for line in result['stdout'].splitlines():
            if finished:
                test_lines.append(line)
            elif line:
                event = json.loads(line)
                events.append(event)
                if event.get('reason') == 'build-finished':
                    require(event['success'], 'native compilation failed')
                    finished = True
        artifacts = [e for e in events if e.get('reason') == 'compiler-artifact' and e.get('executable')
                     and e.get('profile', {}).get('test') and 'lib' in e.get('target', {}).get('kind', [])]
        require(finished and len(artifacts) == 1, 'expected exactly one complete library-test executable')
        item = artifacts[0]
        path = Path(item['executable'])
        require(item['target']['name'] == 'oxc_linter' and item['package_id'] == self.native['package_id'] and
                item['target']['src_path'] == str(SOURCE / 'crates/oxc_linter/src/lib.rs') and
                path.resolve(strict=True) == path and
                path.is_relative_to(WORK / 'target') and path.is_file(), 'foreign native test artifact')
        return path, dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size, artifact=item), '\n'.join(test_lines)

    def batch(self, label, state, expected_source):
        edited = SOURCE / self.case['file']
        require(edited.read_bytes() == expected_source, 'wrong native source state')
        command = self.native['commands'][label]
        result = self.run(label, command['command'], expected=(101,) if state == -1 else (0,))
        executable, proof, stdout = self.artifact(result)
        require(executable == self.executable, 'native artifact path changed between states')
        outcomes = re.findall(r'^test (\S+) \.\.\. (ok|FAILED|ignored)\s*$', stdout, re.M)
        wanted = 'FAILED' if state == -1 else 'ok'
        require(sorted(outcomes) == sorted((name, wanted) for name in self.case['tests']), 'test membership/outcome differs')
        summaries = re.findall(r'^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;', stdout, re.M)
        require(summaries == [('FAILED', '0', '3', '0') if state == -1 else ('ok', '3', '0', '0')],
                'native test summary differs')
        if state == -1:
            for name in self.case['tests']:
                match = re.search(r'^---- ' + re.escape(name) + r' stdout ----\n(.*?)(?=^---- |^failures:|\Z)', stdout, re.M | re.S)
                require(match and 'panicked at' in match[1] and 'assertion' in match[1], 'negative is not an assertion failure')
        if state != 0:
            require(not proof['artifact']['fresh'], 'edited/restored source was not compiled')
        require(edited.read_bytes() == expected_source and sha(executable) == proof['sha256'], 'source/artifact changed during state')
        self.record['states'].append(dict(label=label, state=state, source_sha256=sha(edited), executable=proof,
                                          tests=outcomes, child_path=result['path']))
        self.save()

    def execute(self):
        try:
            with self.owned.workload_lock(self.native['canonical_lock'], 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 24))
                self.save()
                self.sources_guard()
                require(sum(Path(p).stat().st_size for p in self.frozen['files']) <= 96 * 2**20, 'native input retention bound')
                for path, checksum in self.frozen['files'].items():
                    destination = WORK / 'inputs' / path.lstrip('/')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with destination.open('xb') as output:
                        output.write(Path(path).read_bytes())
                    require(sha(destination) == checksum, 'native input readback differs')
                self.acquired_guard()
                self.checkout_guard()
                self.controls.revalidate_native_toolchain(self.identity, self.native_probe,
                    environment=self.native['environment'], source=SOURCE)
                sdk = self.sdk('initial')
                loaders = self.loaders('initial')
                original = (SOURCE / self.case['file']).read_bytes()
                states = list(source_states(original.decode(), self.case, 1, ['native', 'interpreter', 'jit'], False))
                require([hashlib.sha256(s['source']).hexdigest() for s in states] == self.native['source_states'],
                        'native source edit derivation differs')
                command = self.native['commands']['discover-build']
                result = self.run('discover-build', command['command'])
                self.executable, artifact, ignored = self.artifact(result)
                require(not ignored.strip(), 'discovery build unexpectedly executed tests')
                self.owned.write(WORK / 'discovery-artifact.json', artifact)
                listing = self.run('test-list', [str(self.executable), '--list', '--format', 'terse', '--exact', *self.case['tests']])
                listing_lines = [line for line in listing['stdout'].splitlines()
                                 if line and line != '3 tests, 0 benchmarks']
                require(sorted(listing_lines) == sorted(name + ': test' for name in self.case['tests']),
                        'selected native tests are missing or duplicated')
                with SourceEdit(SOURCE / self.case['file'], original) as editor:
                    for state in states:
                        if state['state'] != 0:
                            editor.replace(state['source'])
                        self.batch('state-' + str(state['state']), state['state'], state['source'])
                self.batch('restored', 4, original)
                self.checkout_guard()
                self.acquired_guard()
                self.controls.revalidate_native_toolchain(self.identity, self.native_probe,
                    environment=self.native['environment'], source=SOURCE)
                require(self.sdk('final') == sdk, 'SDK identity changed across native history')
                require(self.loaders('final') == loaders, 'native compiler loader closure changed')
                for role, proof in loaders.items():
                    require(library_state(proof['closure']) == proof['state'], 'native loader file/search state changed')
                require(self.probes == 8 and len(self.record['states']) == 6, 'native history is incomplete')
                self.sources_guard()
                self.record.update(status='passed', native_compatibility=True, source_restored=True,
                    allocation=self.budget(), free_bytes_after=self.capacity(), benchmark=False,
                    runtime_compatibility=False, interpreter_compatibility=False)
        except BaseException as error:
            self.record.update(status='failed', error=repr(error))
            raise
        finally:
            self.record['finished_at'] = time.time()
            self.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--frozen-sha256', required=True)
    Compatibility(parser.parse_args().frozen_sha256).execute()
