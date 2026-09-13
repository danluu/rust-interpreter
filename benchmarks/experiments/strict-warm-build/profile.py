#!/usr/bin/env python3
"""Attribute one real edited build; instrumented observations are not benchmarks.

Uses a task-owned source clone, a fresh target, immutable explicitly selected
tools, unchanged existing assertions and normal Cargo checking. Only the edited
state receives rustc phase instrumentation. Prime/restoration are retained too.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from cargo_timing_data import units_from_html, timeline
from interpreter import TOOLCHAIN, selected_entry_catalog
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_cases import WORKFLOWS, WORKFLOW_VARIANTS
from workflow_case_file import source_file
from workflow_controls import exporter_seconds
from workflow_io import SourceEdit, require_space


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def usage():
    item = resource.getrusage(resource.RUSAGE_CHILDREN)
    return item.ru_utime, item.ru_stime


def run(command, source, environment, output, label):
    before_cpu = usage()
    before = time.perf_counter()
    record = dict(command=command, cwd=str(source), started_unix_ns=time.time_ns(),
                  parent_pid=os.getpid(), label=label)
    print(json.dumps(dict(status='starting', label=label)), flush=True)
    with (output / (label + '.stdout')).open('xb') as stdout, (
            output / (label + '.stderr')).open('xb') as stderr:
        process = subprocess.Popen(command, cwd=source, env=environment,
                                   stdout=stdout, stderr=stderr, close_fds=False)
        try:
            record['pid'] = process.pid
            record['identity'] = subprocess.run(
                ['ps', '-p', str(process.pid), '-o', 'pid=,ppid=,lstart=,tty=,command='],
                capture_output=True, text=True).stdout.strip()
            write_json(output / (label + '.json'), record)
        finally:
            # Do not restore edited source while this task's compiler still
            # reads it, including when identity/receipt publication fails.
            record['returncode'] = process.wait()
    record.update(seconds=time.perf_counter()-before, finished_unix_ns=time.time_ns(),
                  child_user_seconds=usage()[0]-before_cpu[0],
                  child_system_seconds=usage()[1]-before_cpu[1],
                  stdout_sha256=digest(output / (label + '.stdout')),
                  stderr_sha256=digest(output / (label + '.stderr')))
    write_json(output / (label + '.json'), record)
    print(json.dumps(dict(status='finished', label=label,
                          returncode=record['returncode'], seconds=record['seconds'])), flush=True)
    require(record['returncode'] == 0, label + ' failed; inspect ' + str(output))
    return record


def installed(directory, key, options):
    require(re.fullmatch('[0-9a-f]{64}', key) is not None, 'invalid tool key')
    require(directory.name == key, 'tool directory name must match its immutable key')
    ready = json.loads((directory / 'ready.json').read_text())
    require(set(ready) == {'rust-interp-vm', 'rust-interp-mir-export',
                           'rust-interp-rustc-wrapper'}, 'unexpected installed binary set')
    require(all(digest(directory / name) == expected for name, expected in ready.items()),
            'installed binary hashes differ')
    capability = json.loads((directory / 'capabilities.json').read_text())
    require(capability['schema_version'] == 1 and capability['tool_key'] == key and
            capability['bytecode_version'] == 5 and
            capability['exporter_sha256'] == ready['rust-interp-mir-export'] and
            set(options) <= set(capability['export_options']), 'tool capability mismatch')
    return dict(tool_key=key, directory=str(directory), binaries=ready,
                capabilities_sha256=digest(directory / 'capabilities.json'),
                source_sha256=digest(directory / 'source.json') if (directory / 'source.json').exists() else None)


def selected_artifact(output, target, package):
    selected = []
    for line in (output / 'cargo.stdout').read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue  # Raw stdout is retained, including any non-JSON output.
        if (event.get('reason') == 'compiler-artifact' and
                event.get('profile', {}).get('test') is True and
                event.get('target', {}).get('name') == package.replace('-', '_') and
                event.get('target', {}).get('kind') == ['lib']):
            for name in event.get('filenames', []):
                if name.endswith('.rmeta'):
                    selected.append((Path(name + '.rbc'), event))
    require(len(selected) == 1, 'Cargo did not select exactly one requested test artifact')
    artifact, event = selected[0]
    require(event['fresh'] is False, 'edited/prime/restoration target unexpectedly reused a fresh Cargo artifact')
    require(not artifact.is_symlink() and artifact.resolve(strict=True).is_relative_to(target) and
            0 < artifact.stat().st_size <= 64*1024*1024, 'invalid selected artifact')
    return artifact, event


def compiler_records(directory):
    records = []
    for folder in sorted(directory.iterdir()):
        record = json.loads((folder / 'invocation.json').read_text())
        require(record['status'] == 'finished', 'compiler wrapper did not finish: ' + str(folder))
        phases = []
        for line in (folder / 'stderr.log').read_text(errors='replace').splitlines():
            if line.startswith('time: {'):
                phase = json.loads(line[6:])
                require(isinstance(phase.get('pass'), str) and isinstance(phase.get('time'), (int, float)),
                        'invalid rustc phase output')
                phases.append(phase)
        record.update(phases=phases, stderr_sha256=digest(folder / 'stderr.log'),
                      record_path=str(folder / 'invocation.json'))
        records.append(record)
    return records


def sysroot_proof(sysroot, target):
    library = sysroot / 'lib/rustlib' / target / 'lib'
    files = sorted(library.glob('*.rmeta'))
    require(files and all(any(p.name.startswith('lib' + crate + '-') for p in files)
                          for crate in ['core', 'alloc', 'std', 'test']),
            'explicit metadata sysroot is incomplete')
    return {p.name: dict(sha256=digest(p), bytes=p.stat().st_size) for p in files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--tool-dir', type=Path, required=True)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--std-mir-sysroot', type=Path)
    parser.add_argument('--target', help='required with explicit std-MIR sysroot')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--project', choices=WORKFLOWS, default='nushell')
    parser.add_argument('--workflow', default='type-relations')
    parser.add_argument('--edit-index', type=int, default=1)
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--suite-workers', type=int, default=2)
    parser.add_argument('--borrowck-cache', choices=['off', 'verify', 'reuse'], default='off')
    parser.add_argument('--function-cache', choices=['off', 'reuse', 'auto'], default='auto')
    parser.add_argument('--lock-wait-seconds', type=int, default=1800)
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id) is not None, 'invalid run ID')
    require(1 <= args.jobs <= 256 and 1 <= args.suite_workers <= 64 and
            0 <= args.lock_wait_seconds <= 7200, 'invalid worker count or lock wait')
    require(bool(args.std_mir_sysroot) == bool(args.target), 'supply both sysroot and target, or neither')
    case = WORKFLOWS[args.project] if args.workflow == 'default' else WORKFLOW_VARIANTS.get((args.project, args.workflow))
    require(case is not None and 1 <= args.edit_index <= len(case['edits']), 'unknown workflow or edit')
    source = args.source.resolve(strict=True)
    require(source.is_relative_to(ROOT / '.work') and not args.source.is_symlink(),
            'source must be an ordinary task-owned clone under this checkout .work')
    revision = json.loads((ROOT / 'benchmarks/corpus.json').read_text())['projects'][args.project]['revision']
    marker = json.loads((source / '.rust-interp-owned.json').read_text())
    require(marker['owner'] == str(ROOT) and marker['revision'] == revision, 'source ownership/pin mismatch')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == revision,
            'source HEAD differs from corpus pin')
    require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(),
            'source clone has tracked modifications')
    file = source_file(source, case)
    original = file.read_bytes()
    candidate = original.decode()
    tests_marker = '\n#[cfg(test)]\nmod tests {'
    require(candidate.count(tests_marker) == 1, 'expected exactly one original test module')
    original_tests = candidate.split(tests_marker)[1]
    for label, old, new in case['edits'][:args.edit_index]:
        require(old != new and candidate.count(old) == 1, 'edit does not change one occurrence: ' + label)
        candidate = candidate.replace(old, new)
    require(candidate.count(tests_marker) == 1 and candidate.split(tests_marker)[1] == original_tests,
            'edit changed original test assertions')
    edited = candidate.encode()
    tools = args.tool_dir.resolve(strict=True)
    options = ['inline-leaves', 'trap-unsupported-calls', 'run-try-callbacks', 'entry-catalog']
    if args.function_cache != 'off': options.append('function-cache-' + args.function_cache)
    if args.borrowck_cache != 'off': options.append('borrowck-cache')
    tool_proof = installed(tools, args.tool_key, options)
    work = ROOT / '.work' / args.run_id
    require(not work.exists(), 'run directory already exists')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    deadline = time.monotonic() + args.lock_wait_seconds
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            require(time.monotonic() < deadline, 'shared benchmark lock wait expired')
            print(json.dumps(dict(status='waiting for shared benchmark lock')), flush=True)
            time.sleep(min(30, max(0.01, deadline-time.monotonic())))
    work.mkdir()
    (work / 'target').mkdir()
    target = (work / 'target').resolve()
    environment = os.environ.copy()
    for name in list(environment):
        if name.startswith(('RUST_INTERP_', 'CARGO_PROFILE_', 'STRICT_WARM_PROFILE_')) or name in {
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET'}:
            environment.pop(name)
    rustc = subprocess.check_output(['rustup', 'which', '--toolchain', TOOLCHAIN, 'rustc'], text=True).strip()
    compiler = subprocess.check_output([rustc, '-vV'], text=True)
    compiler_sysroot = subprocess.check_output([rustc, '--print', 'sysroot'], text=True).strip()
    wrapper = Path(__file__).with_name('profile_wrapper.py')
    require(os.access(wrapper, os.X_OK), 'diagnostic wrapper must be executable')
    environment.update(CARGO_TERM_COLOR='never', RUSTC=rustc,
        RUSTC_WRAPPER=str(wrapper), RUSTC_WORKSPACE_WRAPPER='', CARGO_TARGET_DIR=str(target),
        RUST_INTERP_EXPORT_PACKAGE=case['package'], RUST_INTERP_EXPORT_TEST='1',
        RUST_INTERP_OUTPUT=str(work / 'program.rbc'),
        RUST_INTERP_ENTRIES=json.dumps(case['tests'], separators=(',', ':')),
        RUST_INTERP_INLINE_LEAVES='1', RUST_INTERP_TRAP_UNSUPPORTED_CALLS='1',
        RUST_INTERP_RUN_TRY_CALLBACKS='1', RUST_INTERP_EXPORT_TIMINGS='1',
        RUST_INTERP_BORROWCK_CACHE=args.borrowck_cache,
        STRICT_WARM_PROFILE_REAL_WRAPPER=str(tools / 'rust-interp-rustc-wrapper'))
    if args.function_cache != 'off':
        environment['RUST_INTERP_FUNCTION_CACHE'] = args.function_cache
    std_proof = None
    if args.std_mir_sysroot:
        sysroot = args.std_mir_sysroot.resolve(strict=True)
        require((sysroot / 'lib/rustlib' / args.target / 'lib').is_dir(), 'invalid explicit metadata sysroot')
        std_proof = sysroot_proof(sysroot, args.target)
        environment.update(RUST_INTERP_STD_SYSROOT=str(sysroot), RUST_INTERP_STD_TARGET=args.target)
    command = ['cargo', '+' + TOOLCHAIN, 'check', '--manifest-path', str(source / 'Cargo.toml'),
        '--package', case['package'], '--lib', '--profile', 'test', '--locked', '--offline',
        '--jobs', str(args.jobs), '--message-format=json-render-diagnostics', '--timings', '-vv']
    if args.target: command += ['--target', args.target]
    report = dict(schema_version=1, owner=str(ROOT), status='running', performance_measurement=False,
        purpose='per-compiler diagnosis of a real edited build; no 0.5 second acceptance evidence',
        source=str(source), revision=revision, project=args.project, workflow=args.workflow,
        tests=case['tests'], edits=[e[0] for e in case['edits'][:args.edit_index]],
        original_sha256=hashlib.sha256(original).hexdigest(), edited_sha256=hashlib.sha256(edited).hexdigest(),
        compiler=compiler, compiler_sysroot=compiler_sysroot, rustc_path=rustc,
        std_mir_sysroot=str(args.std_mir_sysroot.resolve()) if args.std_mir_sysroot else None,
        std_mir_artifacts=std_proof,
        target=args.target, tool=tool_proof, jobs=args.jobs, suite_workers=args.suite_workers,
        borrowck_cache=args.borrowck_cache, function_cache=args.function_cache,
        lock=str((ROOT / '.work/benchmark.lock').resolve()), supervisor_pid=os.getpid(),
        free_bytes_before=shutil.disk_usage(work).free,
        frozen_scripts={str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), wrapper,
            ROOT / 'scripts/workflow_cases.py', ROOT / 'scripts/suite_reports.py',
            ROOT / 'scripts/cargo_timing_data.py', ROOT / 'scripts/interpreter.py',
            ROOT / 'scripts/workflow_io.py']}, records=[])
    write_json(work / 'report.json', report)
    source_changes = contextlib.ExitStack()
    try:
        source_edit = source_changes.enter_context(SourceEdit(file, original))
        for name, contents in [('prime', original), ('edited', edited), ('restored', original)]:
            if name == 'prime':
                require_space(ROOT, 8)
            require(source_edit.matches(source_edit.current), 'source changed outside this task')
            if contents != source_edit.current:
                source_edit.replace(contents)
            output = work / name
            output.mkdir()
            (output / 'units').mkdir()
            env = dict(environment, STRICT_WARM_PROFILE_UNITS=str(output / 'units'),
                       STRICT_WARM_PROFILE_PHASES='1' if name == 'edited' else '0')
            before_ready = time.perf_counter()
            cargo = run(command, source, env, output, 'cargo')
            artifact, event = selected_artifact(output, target, case['package'])
            catalog = selected_entry_catalog(artifact, case['tests'])
            payload = artifact.read_bytes()
            artifact_hash = hashlib.sha256(payload).hexdigest()
            calls = json.loads(Path(str(artifact) + '.calls.json').read_text())
            require(calls['strict_frontend'] is True and calls['artifact_sha256'] == artifact_hash,
                    'unavailable-call report not bound to strict selected artifact')
            ready_seconds = time.perf_counter() - before_ready
            shutil.copy2(artifact, output / 'program.rbc')
            shutil.copy2(catalog, output / 'program.rbc.entries.json')
            shutil.copy2(Path(str(artifact) + '.calls.json'), output / 'program.rbc.calls.json')
            suite = output / 'suite.json'
            vm_command = [str(tools / 'rust-interp-vm'), '--engine', 'jit', '--jit-resumable-calls',
                '--jit-persistent-registers', '--instruction-limit', '100000000000',
                '--allocation-limit', '150000', '--isolated-batch', 'prepared',
                '--suite-workers', str(args.suite_workers), '--suite-report', str(suite),
                '--suite-catalog', str(catalog), str(artifact)]
            vm_environment = {k: v for k, v in environment.items() if not k.startswith(('RUST_INTERP_', 'STRICT_WARM_PROFILE_'))}
            vm = run(vm_command, source, vm_environment, output, 'vm')
            suite_data, suite_hash = read_report(suite)
            validate_report(suite_data, case['tests'], 'prepared', True)
            validate_runtime_limits(suite_data, 100000000000, 150000, required=True)
            stderr = (output / 'cargo.stderr').read_text()
            matches = re.findall(r'Timing report saved to (.+?\.html)', stderr)
            require(len(matches) == 1, 'expected exactly one Cargo timing report')
            timing = Path(matches[0].strip('`')).resolve(strict=True)
            require(timing.is_relative_to(target / 'cargo-timings'), 'timing report escapes target')
            timing_bytes = timing.read_bytes()
            (output / 'cargo-timing.html').write_bytes(timing_bytes)
            units = units_from_html(timing_bytes)
            compilers = compiler_records(output / 'units')
            require(name != 'edited' or any(c['phases'] for c in compilers), 'edited build had no compiler phase output')
            require(all(c['returncode'] == 0 for c in compilers), 'compiler invocation failed')
            row = dict(state=name, source_sha256=digest(file), cargo=cargo, vm=vm,
                instrumented=name == 'edited', direct_cargo_to_validated_artifact_seconds=ready_seconds,
                scope='excludes Python startup, tool/sysroot verification and artifact snapshots; not launcher timing',
                artifact_sha256=artifact_hash, artifact_bytes=len(payload), suite_sha256=suite_hash,
                selected_cargo_event=event, cargo_units=units, cargo_timeline=timeline(units),
                compiler_invocations=compilers, exporter_stages=exporter_seconds(stderr),
                cargo_timing_sha256=hashlib.sha256(timing_bytes).hexdigest())
            report['records'].append(row)
            write_json(work / 'report.json', report)
        report.update(status='passed', source_restored=True, assertions_unchanged=True)
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        # The original was staged before any edit. Restore atomically only
        # after every launched compiler/VM has been waited for.
        source_changes.close()
        report['source_restored'] = file.read_bytes() == original
        report['tool_inputs_unchanged'] = installed(tools, args.tool_key, options) == tool_proof
        report['scripts_unchanged'] = all(digest(ROOT / name) == value for
                                         name, value in report['frozen_scripts'].items())
        report['std_mir_unchanged'] = (std_proof is None or
            sysroot_proof(args.std_mir_sysroot.resolve(), args.target) == std_proof)
        if not all(report[name] for name in ['tool_inputs_unchanged', 'scripts_unchanged', 'std_mir_unchanged']):
            report.update(status='failed', error='profile inputs changed during this diagnostic')
        report['free_bytes_after'] = shutil.disk_usage(work).free
        report['finished_unix_ns'] = time.time_ns()
        write_json(work / 'report.json', report)
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    require(report['status'] == 'passed', report.get('error', 'diagnostic failed'))
    print(work / 'report.json', flush=True)


if __name__ == '__main__':
    main()
