#!/usr/bin/env python3
"""Strict Ruff off/on correctness history; no timing qualification."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from runtime_admission_v2 import RuntimeAdmission, OWNER, R_OWNER, read, validate_hir_flags
from run_ruff_diagnostic import provider, flags
sys.path.insert(0, str(HERE.parent / 'ruff-profile-02'))
from profile_helpers import source_inventory
from custom_compiler import require, file_digest
from workflow_cases import WORKFLOWS
from workflow_case_file import source_file
from workflow_measurements import source_states
from workflow_io import SourceEdit

NAME = 'ruff-runtime-strict-01'
POLICY = 'runtime-ruff-strict-history-v1'
WORK = OWNER / '.work' / NAME
SOURCE = R_OWNER / '.work/sources/ruff'
RUNTIME_KEY = 'eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03'
STD_KEY = 'e4d1cd29bf4dbac5f9cbf6a92c77a562b89f7079c4474653f180346a00f24b63'
TOOL_KEY = '7610e295912b132303c95db6a587f9288c03a7f84b691de8ea60093e2829622a'
FORBIDDEN = ['RUST_INTERP_TRAP_UNSUPPORTED_CALLS', 'RUST_INTERP_RUN_TRY_CALLBACKS']


def history(original):
    # Use the exact completed diagnostic's three-mode ordering, omitting its
    # native application baseline. Only the two custom calls are executed.
    states = list(source_states(original.decode(), WORKFLOWS['ruff'], 1,
                                ['native', 'baseline', 'candidate'], True))
    states.append(dict(cycle=1, state=-2, phase='restored-original',
                       label='restored-original', source=original,
                       modes=['baseline', 'candidate', 'native']))
    result = []
    for state in states:
        for mode in state['modes']:
            if mode != 'native':
                result.append(dict(state=state['state'], phase=state['phase'], mode=mode,
                    label=f'state-{state["state"]}-{mode}', source_sha256=hashlib.sha256(state['source']).hexdigest()))
    return states, result


def command(python, spec):
    result = [python, '-B', str(R_OWNER / 'scripts/interpreter.py'),
        '--manifest-path', str(SOURCE / 'Cargo.toml'), '--package', 'ruff_linter',
        '--jobs', '2', '--test-body', '--engine', 'jit',
        '--runtime-compiler-key', RUNTIME_KEY, '--tool-key', TOOL_KEY,
        '--std-mir', '--std-mir-policy', 'source-paths-v2-shared', '--std-mir-key', STD_KEY,
        '--toolchain-lookup', 'cached', '--workspace-cache-root', str(WORK / 'cache' / spec['mode']),
        '--cache-namespace', NAME + ':' + spec['mode'],
        '--compiler-argv-record-dir', str(WORK / 'compiler-argv' / spec['label']),
        '--function-cache', 'off', '--borrowck-cache', 'off',
        '--inline-leaves', '--jit-resumable-calls', '--jit-persistent-registers',
        '--instruction-limit', '1000000000', '--allocation-limit', '150000', '--timings']
    for entry in WORKFLOWS['ruff']['tests']:
        result += ['--entry', entry]
    return result + ['--rustflag=' + flag for flag in flags(spec['mode'])]


class Admission(RuntimeAdmission):
    def guard(self):
        super().guard()
        require(not any(name in self.environment for name in FORBIDDEN), 'diagnostic policy in launch environment')
        for name, proof in self.plan['providers'].items():
            require(provider(name) == proof, 'native/SDK provider changed: ' + name)
        for name, proof in self.plan['provider_directories'].items():
            path = Path(name)
            require(path.is_dir() and str(path.resolve(strict=True)) == proof['resolved']
                    and (os.readlink(path) if path.is_symlink() else None) == proof['link_text'],
                    'provider directory changed')

    def retain(self, source, destination, bound):
        require(source.resolve(strict=True) == source and source.is_file()
                and 0 < source.stat().st_size <= bound, 'invalid retained artifact')
        before = source.stat()
        payload = source.read_bytes()
        after = source.stat()
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                'artifact changed during read')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as output:
            output.write(payload)
        digest = hashlib.sha256(payload).hexdigest()
        require(file_digest(destination) == digest and destination.stat().st_nlink == 1, 'artifact copy differs')
        return dict(path=str(destination), bytes=len(payload), sha256=digest)

    def compiler_records(self, spec):
        from mono_qualification import decode_record, option
        directory = WORK / 'compiler-argv' / spec['label']
        paths = sorted(directory.iterdir())
        require(0 < len(paths) <= 1024, 'compiler record count differs')
        records = []
        for path in paths:
            require(path.resolve(strict=True) == path and path.is_file()
                    and path.suffix == '.argv' and path.stat().st_size <= 8 * 2**20,
                    'invalid compiler record')
            row = decode_record(path)
            require(row['compiler_sysroot'] == str(self.compiler.sysroot)
                    and row['argv'][0] == str(self.compiler.rustc), 'actual compiler route differs')
            if row['role'] == 'exported':
                require(option(row['argv'], '--crate-name') == 'ruff_linter'
                        and '--test' in row['argv'] and option(row['argv'], '--target') == self.compiler.host
                        and Path(row['cwd']).resolve(strict=True).is_relative_to(SOURCE),
                        'wrong selected library-test compiler')
                validate_hir_flags(row['argv'], 'on' if spec['mode'] == 'candidate' else 'off')
                require(row['argv'].count('-Zincremental-info=true') == 1, 'actual diagnostic compiler flag differs')
            records.append(dict(row, path=str(path), sha256=file_digest(path)))
        require(sum(row['role'] == 'exported' for row in records) == 1,
                'selected Ruff library-test crate was not freshly compiled once')
        return records

    def validate(self, row, spec):
        from mono_qualification import option
        from suite_reports import guest_test_failure
        from workflow_compiler import verify_runtime_call, verify_flags, runtime_receipt
        from interpreter import selected_entry_catalog
        reports = [json.loads(line.removeprefix('rust-interp-launch: '))
                   for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
        require(len(reports) == 1, 'strict launcher did not reach exactly one VM execution')
        launch = reports[0]
        call = dict(row, launch=launch)
        verify_runtime_call(call, runtime_receipt(self.compiler),
            dict(key=self.standard[2], sysroot=str(self.standard[0]), target=self.standard[1]))
        verify_flags(call, flags(spec['mode']), launcher=True)
        require(launch['tool_key'] == self.key and launch['toolchain_lookup'] ==
                dict(mode='cached', outcome='owned-manifest'), 'launcher tools/std lookup differs')
        require(launch.get('trap_unsupported_calls') is False and launch.get('run_try_callbacks') is False
                and 'call_report_path' not in launch and 'unavailable_calls' not in launch
                and not any(line.startswith('rust-interp-unavailable:') for line in row['stderr'].splitlines()),
                'diagnostic trap/callback policy or report present')
        require(launch['engine'] == 'jit' and launch['inline_leaves'] is True
                and launch['jit_resumable_calls'] is True and launch['jit_persistent_registers'] is True
                and launch['allocation_limit'] == 150000, 'execution configuration changed')
        require(not re.search(r'(?mi)stripping debug info with .?rust-objcopy.? failed|'
            r'failed to execute rust-objcopy|Library not loaded:|dyld\[', row['stdout'] + '\n' + row['stderr']),
            'strict application history contains a strip or loader failure')
        if spec['state'] == -1:
            require(row['returncode'] == 1 and guest_test_failure(row['stderr']),
                    'wrong edit did not reach a selected guest assertion')
        else:
            require(row['returncode'] == 0 and row['stdout'].strip() == '0', 'strict test batch failed')
        workspace, artifact = Path(launch['workspace_path']), Path(launch['artifact_path'])
        require(workspace.resolve(strict=True) == workspace
                and workspace.is_relative_to(WORK / 'cache' / spec['mode'])
                and artifact.resolve(strict=True) == artifact and artifact.is_relative_to(workspace / 'target')
                and file_digest(artifact) == launch['artifact_sha256'], 'artifact escaped its cache or changed')
        calls = Path(str(artifact) + '.calls.json')
        require(not calls.exists() and not calls.is_symlink(), 'strict export published a diagnostic call sidecar')
        records = self.compiler_records(spec)
        selected = [record for record in records if record['role'] == 'exported'][0]
        require(re.fullmatch(r'libruff_linter-[0-9a-f]+\.rmeta\.rbc', artifact.name)
                and option(selected['argv'], '--out-dir') == str(artifact.parent)
                and option(selected['argv'], '--emit') == 'dep-info,metadata', 'metadata/dep-info route differs')
        dep_info = artifact.parent / (artifact.name.removeprefix('lib').removesuffix('.rmeta.rbc') + '.d')
        require(dep_info.resolve(strict=True) == dep_info and dep_info.stat().st_size <= 8 * 2**20,
                'invalid selected dep-info')
        lines = dep_info.read_text().splitlines()
        require(any(line.startswith(str(artifact).removesuffix('.rbc') + ':') for line in lines),
                'dep-info does not identify selected metadata')
        environment = {}
        for line in lines:
            if line.startswith('# env-dep:'):
                key, separator, value = line.removeprefix('# env-dep:').partition('=')
                require(key not in environment, 'duplicate dep-info environment')
                environment[key] = value if separator else None
        require(all(key in environment and environment[key] is None for key in FORBIDDEN),
                'exporter did not observe both diagnostic policies unset')
        require(environment.get('RUST_INTERP_EXPORT_TEST') == '1'
                and environment.get('RUST_INTERP_INLINE_LEAVES') == '1'
                and 'RUST_INTERP_ENTRY' in environment and environment['RUST_INTERP_ENTRY'] is None
                and json.loads(environment.get('RUST_INTERP_ENTRIES', 'null')) == WORKFLOWS['ruff']['tests'],
                'exporter test/entry/inlining environment differs')
        catalog = selected_entry_catalog(artifact, WORKFLOWS['ruff']['tests'])
        prefix = WORK / 'artifacts' / spec['label']
        proof = dict(launch=launch, compiler_records=records, exporter_env_dependencies=environment,
            bytecode=self.retain(artifact, prefix.with_suffix('.rbc'), 64 * 2**20),
            catalog=self.retain(catalog, prefix.with_suffix('.entries.json'), 8 * 2**20),
            dep_info=self.retain(dep_info, prefix.with_suffix('.d'), 8 * 2**20))
        matches = re.findall(r'Timing report saved to (.+?\.html)', row['stderr'])
        require(len(matches) == 1, 'strict Cargo timing report missing or ambiguous')
        timing = Path(matches[0].strip('`')).resolve(strict=True)
        require(timing.is_relative_to(workspace / 'target/cargo-timings'), 'timing path escaped selected target')
        proof['cargo_timing'] = self.retain(timing, prefix.with_suffix('.cargo.html'), 32 * 2**20)
        return proof


def main():
    a = Admission(NAME, POLICY)
    case = WORKFLOWS['ruff']
    source = source_file(SOURCE, case)
    inventory = read(a.plan['source_inventory']['path'])
    require(file_digest(Path(a.plan['source_inventory']['path'])) == a.plan['source_inventory']['sha256'],
            'source inventory changed')
    original = source.read_bytes()
    require(hashlib.sha256(original).hexdigest() == inventory[case['file']]['sha256'], 'original source differs')
    states, schedule = history(original)
    require(schedule == a.plan['history'], 'strict history differs')
    result = dict(status='running', records=[], strict_compatibility=False, performance_qualified=False,
                  diagnostic_timing_only=True, unchanged_six_test_bodies=True)
    def save():
        a.owned.write(WORK / 'result.json', result)
    def source_check():
        return source_inventory(SOURCE, inventory, lambda: a.owned.disk(OWNER, 9))
    try:
        with a.admitted():
            source_check()
            for directory in ['tmp', 'cache', 'cache/baseline', 'cache/candidate', 'compiler-argv']:
                (WORK / directory).mkdir()
            save()
            previous = {}
            try:
                with SourceEdit(source, original) as editor:
                    for state in states:
                        if editor.current != state['source']:
                            editor.replace(state['source'])
                        for spec in [item for item in schedule if item['state'] == state['state']]:
                            require(editor.matches(state['source']) and file_digest(source) == spec['source_sha256'],
                                    'source differs before strict application launch')
                            require(previous.get(spec['mode']) != spec['source_sha256'], 'state did not edit previous mode input')
                            (WORK / 'compiler-argv' / spec['label']).mkdir()
                            row = a.invoke(spec['label'], command(a.plan['python'], spec), cwd=R_OWNER,
                                           expected=1 if spec['state'] == -1 else 0)
                            proof = a.validate(row, spec)
                            require(editor.matches(state['source']), 'source changed during strict application launch')
                            result['records'].append(dict(spec, receipt=row['receipt'], proof=proof))
                            previous[spec['mode']] = spec['source_sha256']
                            save()
            finally:
                result['source_restoration'] = source_check()
                save()
            prior = read(a.plan['prior_records']['path'])
            require(file_digest(Path(a.plan['prior_records']['path'])) == a.plan['prior_records']['sha256'],
                    'retained diagnostic history changed')
            for state in states:
                rows = [row for row in result['records'] if row['state'] == state['state']]
                require(len(rows) == 2 and rows[0]['proof']['bytecode']['sha256'] ==
                        rows[1]['proof']['bytecode']['sha256'], 'strict off/on bytecode differs')
            result['prior_diagnostic_bytecode_comparison'] = []
            for row in result['records']:
                matches = [old for old in prior if old['mode'] == row['mode'] and old['state'] == row['state']]
                require(len(matches) == 1 and matches[0]['source_sha256'] == row['source_sha256']
                        and matches[0]['tests'] == case['tests'], 'diagnostic source/assertion provenance differs')
                result['prior_diagnostic_bytecode_comparison'].append(dict(mode=row['mode'], state=row['state'],
                    strict_sha256=row['proof']['bytecode']['sha256'],
                    diagnostic_sha256=matches[0]['artifacts'][0]['sha256'],
                    equal=row['proof']['bytecode']['sha256'] == matches[0]['artifacts'][0]['sha256'],
                    scope='Descriptive only: strict export intentionally removes two compatibility policies.'))
            result.update(status='passed', strict_compatibility=True, trap_unsupported_calls=False,
                run_try_callbacks=False, commands=16, cross_mode_bytecode_equal=True,
                scope='One strict JIT batch history in each HIR mode; unchanged six-test batch rejects the wrong edit. No per-negative-test or latency-distribution claim.')
            save()
            a.finish(result)
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        save()
        a.failed(error)
        raise


if __name__ == '__main__':
    main()
