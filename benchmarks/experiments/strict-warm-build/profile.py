#!/usr/bin/env python3
"""Attribute one real edited build; instrumented observations are not benchmarks.

Uses a task-owned source clone, immutable explicitly selected tools, unchanged
existing assertions and normal Cargo checking. New histories start with an
empty target. Explicit continuations reuse only a verified owned history and
compile a previously uncompiled edit. Only edited states receive instrumentation.
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
        profiles = []
        profile_directory = folder / 'self-profile'
        if profile_directory.exists():
            require(not profile_directory.is_symlink(), 'self-profile directory is a symlink')
            for path in sorted(profile_directory.rglob('*')):
                require(not path.is_symlink(), 'self-profile output is a symlink')
                if path.is_file():
                    profiles.append(dict(path=str(path), bytes=path.stat().st_size, sha256=digest(path)))
        record.update(phases=phases, self_profiles=profiles, stderr_sha256=digest(folder / 'stderr.log'),
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


def owned_report(path):
    path = Path(path)
    resolved = path.resolve(strict=True)
    require(not path.is_symlink() and resolved.parent.parent == ROOT / '.work' and
            resolved.name == 'report.json' and resolved.stat().st_size <= 128*1024*1024,
            'resume requires an ordinary report from this checkout .work')
    report = json.loads(resolved.read_text())
    require(report.get('schema_version') == 1 and report.get('owner') == str(ROOT) and
            report.get('performance_measurement') is False and report.get('status') == 'passed' and
            all(report.get(k) is True for k in ['source_restored', 'assertions_unchanged',
                'tool_inputs_unchanged', 'scripts_unchanged', 'std_mir_unchanged']),
            'resume report is not a passed, restored owned diagnostic')
    return resolved, report


def resume_target(path, expected, next_index, next_hash, case):
    """Validate the latest owned cache history without changing any source/cache."""
    path, previous = owned_report(path)
    require(all(previous.get(k) == value for k, value in expected.items()),
            'resume source, tool, compiler, sysroot, selection or build options differ')
    previous_index = len(previous['edits'])
    require(previous['edits'] == [e[0] for e in case['edits'][:previous_index]],
            'prior edit sequence differs from the current workflow')
    rows = previous['records']
    require([r['state'] for r in rows] in (['prime', 'edited', 'restored'], ['edited', 'restored']) and
            rows[-1]['source_sha256'] == expected['original_sha256'] and
            all(r['cargo']['returncode'] == r['vm']['returncode'] == 0 for r in rows),
            'prior history did not complete and restore successfully')
    target = Path(previous.get('target_directory', str(path.parent / 'target')))
    require(not target.is_symlink() and target.resolve(strict=True) == target and
            target.name == 'target' and target.parent.parent == ROOT / '.work' and target.is_dir(),
            'resume target is outside an owned diagnostic directory')
    restored = path.parent / 'restored'
    artifact, event = selected_artifact(restored, target, case['package'])
    require(event == rows[-1]['selected_cargo_event'] and digest(artifact) == rows[-1]['artifact_sha256'],
            'live cache no longer matches the prior restored artifact')
    witnesses = {}
    for suffix in ['', '.entries.json', '.calls.json']:
        live = Path(str(artifact) + suffix)
        snapshot = restored / ('program.rbc' + suffix)
        require(not live.is_symlink() and live.resolve(strict=True).is_relative_to(target) and
                live.read_bytes() == snapshot.read_bytes(), 'restored cache sidecar differs from its snapshot')
        witnesses[str(live)] = digest(live)
    selected_entry_catalog(artifact, case['tests'])
    suite, _ = read_report(restored / 'suite.json', rows[-1]['suite_sha256'])
    validate_report(suite, case['tests'], 'prepared', True)
    validate_runtime_limits(suite, 100000000000, 150000, required=True)
    history_path = target / '.strict-warm-profile-history.json'
    if history_path.exists() or history_path.is_symlink():
        require(not history_path.is_symlink() and history_path.stat().st_size <= 1024*1024,
                'invalid target history receipt')
        history = json.loads(history_path.read_text())
        require(history.get('schema_version') == 1 and history.get('owner') == str(ROOT) and
                history.get('kind') == 'strict-warm-diagnostic-target' and history.get('target') == str(target),
                'target history ownership differs')
        entries = history.get('entries')
        require(isinstance(entries, list) and 0 < len(entries) <= len(case['edits']), 'invalid cache history')
        for entry in entries:
            require(isinstance(entry, dict) and entry.get('status') == 'passed',
                    'target history contains an incomplete or failed attempt; automatic resume refused')
            saved_path, saved = owned_report(entry['report'])
            require(entry['status'] == 'passed' and entry['report_sha256'] == digest(saved_path) and
                    all(saved.get(k) == value for k, value in expected.items()) and
                    entry['edit_index'] == len(saved['edits']) and
                    saved['edits'] == [e[0] for e in case['edits'][:entry['edit_index']]] and
                    entry['edited_sha256'] == saved['edited_sha256'], 'cache history entry differs')
        indices = [entry['edit_index'] for entry in entries]
        require(indices == sorted(set(indices)) and all(1 <= index <= len(case['edits']) for index in indices),
                'cache history edit indices are not strictly increasing')
        require(entries[-1]['report'] == str(path),
                'resume must name the latest passed target history, not an earlier report')
        history_before = digest(history_path)
    else:
        # Only a legacy independent run can bootstrap a history. An absent
        # journal cannot silently discard the edits of a continuation.
        require('continuation' not in previous and target == path.parent / 'target' and
                [r['state'] for r in rows] == ['prime', 'edited', 'restored'],
                'continuation target has lost its history receipt')
        history = dict(schema_version=1, owner=str(ROOT), kind='strict-warm-diagnostic-target',
            target=str(target), entries=[dict(report=str(path), report_sha256=digest(path),
                edit_index=previous_index, edited_sha256=previous['edited_sha256'], status='passed')])
        entries = history['entries']
        history_before = None
    require(next_index > max(entry['edit_index'] for entry in entries) and
            next_hash not in {entry['edited_sha256'] for entry in entries} | {expected['original_sha256']},
            'continuation must compile a later, previously uncompiled source hash')
    proof = dict(kind='warm continuation; not an independent cold history',
        prior_report=str(path), prior_report_sha256=digest(path),
        prior_cargo_command=rows[-1]['cargo']['command'],
        history_receipt=str(history_path), history_before_sha256=history_before,
        previously_compiled_edit_indices=[entry['edit_index'] for entry in entries],
        previously_compiled_source_hashes=[entry['edited_sha256'] for entry in entries],
        verified_live_cache_sidecars=witnesses, prime_skipped=True,
        limitation='fresh relative to this recorded diagnostic target history; no 0.5 second acceptance evidence')
    return target, history, proof


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
    parser.add_argument('--profiling', choices=['passes', 'self'], default='passes')
    parser.add_argument('--resume-target-from', type=Path,
                        help='continue the latest passed owned diagnostic with a later, fresh edit')
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
        RUSTC_WRAPPER=str(wrapper), RUSTC_WORKSPACE_WRAPPER='',
        RUST_INTERP_EXPORT_PACKAGE=case['package'], RUST_INTERP_EXPORT_TEST='1',
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
    expected = dict(source=str(source), revision=revision, project=args.project,
        workflow=args.workflow, tests=case['tests'], original_sha256=hashlib.sha256(original).hexdigest(),
        compiler=compiler, compiler_sysroot=compiler_sysroot, rustc_path=rustc,
        std_mir_sysroot=str(args.std_mir_sysroot.resolve()) if args.std_mir_sysroot else None,
        std_mir_artifacts=std_proof, target=args.target, tool=tool_proof, jobs=args.jobs,
        suite_workers=args.suite_workers, borrowck_cache=args.borrowck_cache,
        function_cache=args.function_cache)
    continuation = None
    if args.resume_target_from:
        target, history, continuation = resume_target(args.resume_target_from, expected,
            args.edit_index, hashlib.sha256(edited).hexdigest(), case)
    else:
        target = work / 'target'
        history = dict(schema_version=1, owner=str(ROOT), kind='strict-warm-diagnostic-target',
                       target=str(target), entries=[])
    command = ['cargo', '+' + TOOLCHAIN, 'check', '--manifest-path', str(source / 'Cargo.toml'),
        '--package', case['package'], '--lib', '--profile', 'test', '--locked', '--offline',
        '--jobs', str(args.jobs), '--message-format=json-render-diagnostics', '--timings', '-vv']
    if args.target: command += ['--target', args.target]
    if continuation:
        require(command == continuation['prior_cargo_command'], 'continuation Cargo arguments differ')
    work.mkdir()
    if not continuation:
        target.mkdir()
    environment.update(CARGO_TARGET_DIR=str(target), RUST_INTERP_OUTPUT=str(target.parent / 'program.rbc'))
    history_path = target / '.strict-warm-profile-history.json'
    report = dict(schema_version=1, owner=str(ROOT), status='running', performance_measurement=False,
        purpose='per-compiler diagnosis of a real edited build; no 0.5 second acceptance evidence',
        history_kind='warm continuation; not independent' if continuation else 'independent empty-target diagnostic',
        profiling=args.profiling, edit_index=args.edit_index, target_directory=str(target),
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
    if continuation:
        report['continuation'] = continuation
    print(json.dumps(dict(status='diagnostic history selected', history_kind=report['history_kind'],
        prior_report_sha256=continuation['prior_report_sha256'] if continuation else None,
        target_directory=str(target), profiling=args.profiling, edit_index=args.edit_index)), flush=True)
    write_json(work / 'report.json', report)
    history_entry = dict(report=str(work / 'report.json'), edit_index=args.edit_index,
        edited_sha256=report['edited_sha256'], status='running', reserved_before_compilation=True)
    history['entries'].append(history_entry)
    source_changes = contextlib.ExitStack()
    try:
        # Reserve this source state before any compiler starts. Failed attempts
        # remain visible and cannot silently turn a later retry into a fresh edit.
        write_json(history_path, history)
        source_edit = source_changes.enter_context(SourceEdit(file, original))
        states = [('edited', edited), ('restored', original)]
        if not continuation:
            states.insert(0, ('prime', original))
        for name, contents in states:
            if name == 'prime':
                require_space(ROOT, 8)
            elif name == 'edited':
                require_space(ROOT, 2)
            require(source_edit.matches(source_edit.current), 'source changed outside this task')
            if contents != source_edit.current:
                source_edit.replace(contents)
            output = work / name
            output.mkdir()
            (output / 'units').mkdir()
            env = dict(environment, STRICT_WARM_PROFILE_UNITS=str(output / 'units'),
                       STRICT_WARM_PROFILE_MODE=args.profiling if name == 'edited' else 'off',
                       STRICT_WARM_PROFILE_PHASES='1' if name == 'edited' and args.profiling == 'passes' else '0')
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
            if name == 'edited':
                field = 'phases' if args.profiling == 'passes' else 'self_profiles'
                require(any(c[field] for c in compilers), 'edited build had no requested compiler profile output')
                require(args.profiling != 'self' or not any(c['phases'] for c in compilers),
                        'self-profile diagnostic unexpectedly enabled phase logging')
            require(all(c['returncode'] == 0 for c in compilers), 'compiler invocation failed')
            row = dict(state=name, source_sha256=digest(file), cargo=cargo, vm=vm,
                instrumented=name == 'edited', profiling=args.profiling if name == 'edited' else 'off',
                direct_cargo_to_validated_artifact_seconds=ready_seconds,
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
        report['previous_reports_unchanged'] = all(digest(Path(entry['report'])) == entry['report_sha256']
            for entry in history['entries'][:-1])
        if not all(report[name] for name in ['tool_inputs_unchanged', 'scripts_unchanged',
                                            'std_mir_unchanged', 'previous_reports_unchanged']):
            report.update(status='failed', error='profile inputs changed during this diagnostic')
        report['free_bytes_after'] = shutil.disk_usage(work).free
        report['finished_unix_ns'] = time.time_ns()
        write_json(work / 'report.json', report)
        history_entry.update(status=report['status'], report_sha256=digest(work / 'report.json'))
        write_json(history_path, history)
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    require(report['status'] == 'passed', report.get('error', 'diagnostic failed'))
    print(work / 'report.json', flush=True)


if __name__ == '__main__':
    main()
