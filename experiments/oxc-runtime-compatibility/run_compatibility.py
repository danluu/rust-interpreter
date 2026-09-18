#!/usr/bin/env python3
"""Ordinary interpreter/JIT compatibility for the unchanged Oxc plugin case."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

import acquire_runtime_source as acquisition

OWNER, RROOT, SOURCE = acquisition.OWNER, acquisition.RROOT, acquisition.SOURCE
HERE = Path(__file__).resolve().parent
WORK = OWNER / '.work/oxc-runtime-compatibility-01'
RUNTIME_KEY = 'eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03'
STD_KEY = 'e4d1cd29bf4dbac5f9cbf6a92c77a562b89f7079c4474653f180346a00f24b63'
CASE_PATH = OWNER / 'experiments/oxc-plugin-normalization/case.json'
require, read, sha = acquisition.require, acquisition.read, acquisition.sha


def flags():
    return ['-Zmir-opt-level=3', '-Zhir-body-cache-capture=false', '-Zhir-body-cache-reuse=false']


def command(tool_key, python, engine, entries, label):
    require(engine in ['interpreter', 'jit'], 'unsupported engine')
    result = [python, '-B', str(RROOT / 'scripts/interpreter.py'), '--manifest-path', str(SOURCE / 'Cargo.toml'),
        '--package', 'oxc_linter', '--test-body', '--jobs', '2', '--engine', engine,
        '--runtime-compiler-key', RUNTIME_KEY, '--tool-key', tool_key, '--std-mir',
        '--std-mir-policy', 'source-paths-v2-shared', '--std-mir-key', STD_KEY,
        '--toolchain-lookup', 'cached', '--workspace-cache-root', str(WORK / 'cache' / engine),
        '--cache-namespace', 'oxc-runtime-compatibility-01:' + engine,
        '--compiler-argv-record-dir', str(WORK / 'compiler-argv' / label),
        '--function-cache', 'off', '--borrowck-cache', 'off', '--trap-unsupported-calls', '--run-try-callbacks',
        '--instruction-limit', '1000000000', '--allocation-limit', '150000']
    if engine == 'jit':
        result += ['--jit-resumable-calls', '--jit-persistent-registers']
    for entry in entries:
        result += ['--entry', entry]
    return result + ['--rustflag=' + value for value in flags()]


def provider(path):
    path = Path(path)
    resolved = path.resolve(strict=True)
    before, target = acquisition.stamp(path), acquisition.stamp(resolved)
    require(resolved.is_file(), 'provider is not a file')
    result = dict(resolved=str(resolved), link_text=os.readlink(path) if path.is_symlink() else None,
                  stamp=before, target_stamp=target, sha256=sha(resolved))
    require(acquisition.stamp(path) == before and acquisition.stamp(resolved) == target and
            path.resolve(strict=True) == resolved, 'provider changed during hashing')
    return result


def history(tool_key, python, tests):
    result = []
    for state in [0, -1, 1, 2, 3, 4]:
        for engine in ['interpreter', 'jit']:
            selections = [[entry] for entry in tests] if state == -1 else [tests]
            for index, entries in enumerate(selections):
                label = f'state-{state}-{engine}' + (f'-{index}' if state == -1 else '')
                result.append(dict(label=label, state=state, engine=engine, entries=entries,
                    expected_returncode=1 if state == -1 else 0,
                    argv=command(tool_key, python, engine, entries, label)))
    return result


def validate_flags(argv):
    unstable = []
    for index, value in enumerate(argv):
        require(not value.startswith('@'), 'response file in compiler invocation')
        if value == '-Z':
            require(index + 1 < len(argv), 'missing unstable flag argument')
            unstable.append('-Z' + argv[index + 1].replace('_', '-'))
        elif value.startswith('-Z'):
            unstable.append('-Z' + value[2:].replace('_', '-'))
    for wanted in flags():
        require([value for value in unstable if value.split('=')[0] == wanted.split('=')[0]] == [wanted],
                'actual application compiler flag differs: ' + wanted)
    require(not any(value.split('=')[0] in ['-Zthreads', '-Zcache-proc-macros',
                '-Zproc-macro-execution-strategy', '-Zstable-mono-cgu-partitioning'] for value in unstable),
            'mixed compiler experiment')


class Compatibility:
    def __init__(self, plan_path, freeze_path, expected):
        require(Path.cwd() == OWNER and sys.dont_write_bytecode and not sys.flags.optimize,
                'fixed owner and unoptimized Python -B required')
        self.plan_path, self.freeze_path, self.expected = plan_path, freeze_path, expected
        require(sha(freeze_path) == expected, 'compatibility freeze differs')
        self.plan, self.frozen = read(plan_path), read(freeze_path)
        require(self.plan['owner'] == str(OWNER) and self.plan['runtime_owner'] == str(RROOT)
                and self.plan['runtime_key'] == RUNTIME_KEY and self.plan['std_key'] == STD_KEY,
                'compatibility owner/runtime selection differs')
        require(dict(os.environ) == self.plan['environment'], 'compatibility environment differs')
        self.owned = acquisition.load('oxc_compatibility_owned', OWNER / 'experiments/stable-cgu/owned_stage.py')
        self.registry = acquisition.load('oxc_compatibility_registry',
                                         OWNER / 'experiments/oxc-plugin-normalization/registry_cache.py')
        self.case = read(CASE_PATH)['case']
        require(self.plan['commands'] == history(self.plan['tool_key'], self.plan['python']['path'], self.case['tests']),
                'compatibility plan changed the fixed engine/source/test history')
        self.input_guard()
        sys.path.insert(0, str(RROOT / 'scripts'))
        from runtime_compiler import load_runtime_compiler
        from runtime_tools import validate_tool_runtime
        from interpreter import installed_tools
        from std_mir_source_paths import load as load_std, namespace_for, tree_files
        self.load_compiler, self.validate_tools, self.installed_tools = load_runtime_compiler, validate_tool_runtime, installed_tools
        self.load_std, self.namespace_for, self.tree_files = load_std, namespace_for, tree_files
        self.compiler = load_runtime_compiler(RROOT, RUNTIME_KEY)
        self.tools, self.key = installed_tools(self.plan['tool_key'])
        self.standard = load_std(RROOT, STD_KEY, self.compiler, namespace_for('source-paths-v2-shared', 'unused'), rehash=True)
        self.std_selection = dict(key=self.standard[2], sysroot=str(self.standard[0]), target=self.standard[1])
        self.source_inventory = read(self.plan['source_inventory']['path'])
        require(sha(self.plan['source_inventory']['path']) == self.plan['source_inventory']['sha256'],
                'source acquisition inventory changed')
        acquisition.absent(WORK)
        WORK.mkdir()
        self.record = dict(schema_version=1, status='waiting', owner=str(OWNER), runtime_owner=str(RROOT),
            pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), freeze_sha256=expected,
            children=[], states=[], benchmark=False, performance_qualified=False,
            runtime_compatibility=False, source_restored=False, policy=self.plan['policy'])
        self.save()

    def save(self):
        self.owned.write(WORK / 'receipt.json', self.record)

    def capacity(self):
        return self.owned.disk(OWNER, 9)

    def input_guard(self):
        require(sha(self.freeze_path) == self.expected and str(self.plan_path) in self.frozen['files'],
                'compatibility plan/freeze changed')
        for name, digest in self.frozen['files'].items():
            acquisition.frozen_input_file(name, self.plan['executors'])
            require(sha(name) == digest, 'compatibility input changed: ' + name)
        python = self.plan['python']
        require(str(Path(sys.executable).resolve()) == python['resolved'] and sha(sys.executable) == python['sha256'],
                'compatibility Python differs')
        require(list(os.uname()) == self.plan['platform'], 'compatibility platform changed')
        for name, proof in self.plan['executors'].items():
            require(provider(name) == proof, 'compatibility executor changed: ' + name)
        for name, proof in self.plan['configuration'].items():
            path = Path(name)
            require(not path.is_symlink() and path.exists() == proof['exists'], 'configuration route changed')
            if proof['exists']:
                require(sha(path) == proof['sha256'], 'configuration bytes changed')
        for module in list(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename and filename.startswith('/Users/danluu/dev/rust-interp'):
                require(str(Path(filename).resolve()) in self.frozen['files'], 'unfrozen compatibility import: ' + filename)

    def guard(self):
        self.input_guard()
        require(self.load_compiler(RROOT, RUNTIME_KEY) == self.compiler, 'runtime compiler identity changed')
        require(self.installed_tools(self.key) == (self.tools, self.key), 'published tool bytes changed')
        self.validate_tools(self.tools, self.key, self.compiler)
        require(read(self.tools / 'compiler.json') == self.plan['runtime_composition'], 'tool composition changed')
        require(self.load_std(RROOT, STD_KEY, self.compiler,
                    self.namespace_for('source-paths-v2-shared', 'unused')) == self.standard, 'prepared std identity changed')

    def full_payloads(self):
        self.guard()
        require(self.tree_files(self.compiler.sysroot) == self.compiler.identity['files'], 'runtime bytes changed')
        require(self.tree_files(self.standard[0]) == self.standard[3]['sysroot_files'], 'prepared std bytes changed')
        for name, proof in self.plan['providers'].items():
            self.capacity()
            require(provider(name) == proof, 'native/SDK provider changed: ' + name)
        for name, proof in self.plan['provider_directories'].items():
            path = Path(name)
            require(path.is_dir() and str(path.resolve(strict=True)) == proof['resolved'] and
                    (os.readlink(path) if path.is_symlink() else None) == proof['link_text'], 'provider directory changed')
        for proof in read(self.plan['registry_inventory']['path']).values():
            require(self.registry.verify(proof['archive'], proof['root'], proof['checksum'], capacity=self.capacity) == proof,
                    'qualified shared registry package changed')

    def source_guard(self):
        def unchanged(rows):
            # Git's index stat cache can refresh without changing tracked bytes.
            return {name: row for name, row in rows.items() if name != '.git/index'}
        require(unchanged(acquisition.inventory(SOURCE, self.capacity)) == unchanged(self.source_inventory),
                'source membership/bytes differ from acquired original')

    def budget(self):
        self.capacity()
        cache = evidence = 0
        for directory, dirs, files in os.walk(WORK, followlinks=False):
            for name in [*dirs, *files]:
                path = Path(directory) / name
                size = path.lstat().st_blocks * 512
                if path.is_relative_to(WORK / 'cache'):
                    cache += size
                else:
                    evidence += size
        require(cache <= 12 * 2**30 and evidence <= 2 * 2**30, 'compatibility allocation bound exceeded')
        return dict(cache=cache, evidence=evidence)

    def retain(self, source, destination, limit):
        acquisition.ordinary(source)
        require(source.stat().st_size <= limit, 'retained compatibility artifact exceeds bound')
        destination.parent.mkdir(parents=True, exist_ok=True)
        acquisition.copy_file(source, destination, acquisition.file_record(source))
        return dict(path=str(destination), bytes=destination.stat().st_size, sha256=sha(destination))

    def retain_input(self, source, destination, expected):
        self.capacity()
        acquisition.frozen_input_file(source, self.plan['executors'])
        before = acquisition.stamp(source)
        require(before['size'] <= 32 * 2**20, 'retained input exceeds bound')
        payload = source.read_bytes()
        require(hashlib.sha256(payload).hexdigest() == expected, 'retained input bytes differ')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as output:
            output.write(payload)
        acquisition.ordinary(destination)
        require(acquisition.stamp(source) == before and sha(destination) == expected, 'retained input copy changed')

    def compiler_arguments(self, label):
        from mono_qualification import decode_record, option
        rows = []
        for path in sorted((WORK / 'compiler-argv' / label).iterdir()):
            acquisition.ordinary(path)
            require(path.suffix == '.argv' and path.stat().st_size <= 8 * 2**20, 'unexpected compiler record')
            row = decode_record(path)
            require(row['compiler_sysroot'] == str(self.compiler.sysroot) and row['argv'][0] == str(self.compiler.rustc),
                    'actual compiler route differs')
            if row['role'] == 'exported':
                require(option(row['argv'], '--crate-name') == 'oxc_linter' and '--test' in row['argv'] and
                        option(row['argv'], '--target') == self.compiler.host, 'wrong exported Cargo unit')
                require(Path(row['cwd']).resolve(strict=True).is_relative_to(SOURCE), 'foreign application compiler cwd')
                validate_flags(row['argv'])
            rows.append(dict(row, path=str(path), sha256=sha(path)))
        require(sum(row['role'] == 'exported' for row in rows) == 1, 'selected library-test crate was not freshly compiled')
        self.owned.write(WORK / 'proofs' / (label + '-compiler.json'), rows)
        return rows

    def validate_launch(self, result, spec):
        from suite_reports import guest_test_failure
        from workflow_compiler import verify_flags, verify_runtime_call, runtime_receipt
        reports = [json.loads(line.removeprefix('rust-interp-launch: ')) for line in result['stderr'].splitlines()
                   if line.startswith('rust-interp-launch: ')]
        require(len(reports) == 1, 'ordinary launcher did not reach one VM execution')
        report = reports[0]
        call = dict(result, command=spec['argv'], launch=report)
        verify_runtime_call(call, runtime_receipt(self.compiler), self.std_selection)
        verify_flags(call, flags(), launcher=True)
        require(report['tool_key'] == self.key and report['toolchain_lookup'] == dict(mode='cached', outcome='owned-manifest'),
                'ordinary launcher tool/std lookup differs')
        workspace, artifact = Path(report['workspace_path']), Path(report['artifact_path'])
        require(workspace.resolve(strict=True) == workspace and workspace.is_relative_to(WORK / 'cache' / spec['engine'])
                and artifact.resolve(strict=True) == artifact and artifact.is_relative_to(workspace / 'target') and
                sha(artifact) == report['artifact_sha256'], 'selected bytecode escaped its owned cache or changed')
        require(report['allocation_limit'] == 150000, 'effective allocation limit changed')
        require(not re.search(r'(?mi)stripping debug info with .?rust-objcopy.? failed|failed to execute rust-objcopy|'
                              r'Library not loaded:|dyld\[', result['stdout'] + '\n' + result['stderr']),
                'successful application compilation had a strip/loader failure')
        require(not any(line.startswith(('[hir-body-capture]', '[hir-body-reuse]'))
                        for line in result['stderr'].splitlines()), 'cache-off compatibility emitted HIR cache events')
        if spec['state'] == -1:
            require(result['returncode'] == 1 and guest_test_failure(result['stderr']),
                    'negative did not reach the selected guest assertion')
        else:
            require(result['returncode'] == 0 and result['stdout'].strip() == '0', 'original/refactored guest tests failed')
        proof = dict(launch=report, bytecode=self.retain(artifact, WORK / 'artifacts' / (spec['label'] + '.rbc'), 64 * 2**20))
        if len(spec['entries']) > 1:
            catalog_path = Path(str(artifact) + '.entries.json')
            catalog = read(catalog_path)
            require(catalog['schema_version'] == 1 and catalog['bytecode_version'] == 5 and
                    catalog['artifact_sha256'] == report['artifact_sha256'] and catalog['target'] == self.compiler.host and
                    [entry['name'] for entry in catalog['entries']] == spec['entries'], 'selected test catalog differs')
            proof['catalog'] = self.retain(catalog_path, WORK / 'artifacts' / (spec['label'] + '.entries.json'), 8 * 2**20)
        call_path = Path(report['call_report_path'])
        require(call_path == Path(str(artifact) + '.calls.json'), 'call sidecar route differs')
        calls = read(call_path)
        require(calls['artifact_sha256'] == report['artifact_sha256'] and calls['strict_frontend'] is True and
                calls['trap_unsupported_calls'] is True and calls['run_try_callbacks'] is True and
                calls['unavailable_calls'] == report['unavailable_calls'], 'runtime support-policy receipt differs')
        proof['unavailable_calls'] = self.retain(call_path, WORK / 'artifacts' / (spec['label'] + '.calls.json'), 8 * 2**20)
        proof['compiler_records'] = self.compiler_arguments(spec['label'])
        return proof

    def invoke(self, spec, payload):
        require(spec == self.plan['commands'][len(self.record['children'])], 'compatibility command order differs')
        require((SOURCE / self.case['file']).read_bytes() == payload, 'source state differs before launch')
        require(spec['argv'] == command(self.key, self.plan['python']['path'], spec['engine'], spec['entries'], spec['label']),
                'ordinary compatibility command differs from recipe')
        self.guard()
        self.budget()
        (WORK / 'compiler-argv' / spec['label']).mkdir()
        out = WORK / 'commands' / f'{len(self.record["children"]):02d}-{spec["label"]}'
        try:
            receipt = self.owned.run(spec['argv'], cwd=RROOT, env=self.plan['environment'], out=out,
                                     capacity_root=OWNER, expected=(spec['expected_returncode'],))
        finally:
            if (out / 'receipt.json').exists():
                self.record['children'].append(dict(label=spec['label'], path=str(out), receipt=read(out / 'receipt.json')))
                self.save()
        require(all((out / name).stat().st_size <= 64 * 2**20 for name in ['stdout', 'stderr']), 'launcher output exceeded bound')
        result = dict(returncode=receipt['returncode'], stdout=(out / 'stdout').read_text(), stderr=(out / 'stderr').read_text())
        proof = self.validate_launch(result, spec)
        require((SOURCE / self.case['file']).read_bytes() == payload, 'source changed during ordinary launch')
        self.record['states'].append(dict(label=spec['label'], state=spec['state'], engine=spec['engine'],
            entries=spec['entries'], source_sha256=hashlib.sha256(payload).hexdigest(), proof=proof))
        self.save()
        self.guard()
        self.budget()

    def execute(self):
        from workflow_io import SourceEdit
        from workflow_measurements import source_states
        try:
            with self.owned.workload_lock(self.plan['canonical_lock'], 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER, 24))
                self.save()
                self.full_payloads()
                self.source_guard()
                total = 0
                for name, digest in self.frozen['files'].items():
                    total += Path(name).stat().st_size
                    require(total <= 96 * 2**20, 'compatibility input retention exceeds bound')
                    self.retain_input(Path(name), WORK / 'inputs' / name.lstrip('/'), digest)
                for name in ['tmp', 'cache', 'cache/interpreter', 'cache/jit', 'compiler-argv', 'proofs']:
                    (WORK / name).mkdir()
                original = (SOURCE / self.case['file']).read_bytes()
                states = list(source_states(original.decode(), self.case, 1, ['native', 'interpreter', 'jit'], False))
                states.append(dict(state=4, source=original))
                require([hashlib.sha256(row['source']).hexdigest() for row in states] == self.plan['source_states'],
                        'runtime/native edit history differs')
                by_state = {state['state']: state['source'] for state in states}
                with SourceEdit(SOURCE / self.case['file'], original) as editor:
                    for state in states[:-1]:
                        if state['state'] != 0:
                            editor.replace(state['source'])
                        for spec in self.plan['commands']:
                            if spec['state'] == state['state']:
                                self.invoke(spec, state['source'])
                for spec in self.plan['commands']:
                    if spec['state'] == 4:
                        self.invoke(spec, by_state[4])
                self.source_guard()
                self.full_payloads()
                require(len(self.record['children']) == len(self.record['states']) == len(self.plan['commands']) == 16,
                        'ordinary compatibility history incomplete')
                for engine in ['interpreter', 'jit']:
                    negative = [row['entries'] for row in self.record['states'] if row['engine'] == engine and row['state'] == -1]
                    require(negative == [[entry] for entry in self.case['tests']], 'negative test coverage incomplete')
                self.record.update(status='passed', runtime_compatibility=True, interpreter_compatibility=True,
                    jit_compatibility=True, source_restored=True, allocation=self.budget(), free_bytes_after=self.capacity(),
                    benchmark=False, performance_qualified=False)
        except BaseException as error:
            self.record.update(status='failed', error=repr(error))
            raise
        finally:
            failed_before_final_guard = self.record['status'] == 'failed'
            final_error = None
            try:
                self.source_guard()
                self.record['source_restored'] = True
            except BaseException as error:
                final_error = error
                self.record['status'] = 'failed'
                self.record['source_restored'] = False
                self.record['source_validation_error'] = repr(error)
            self.record['finished_at'] = time.time()
            self.save()
            if final_error is not None and not failed_before_final_guard:
                raise final_error


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--frozen-sha256', required=True)
    args = parser.parse_args()
    Compatibility(args.plan, args.freeze, args.frozen_sha256).execute()
