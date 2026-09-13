#!/usr/bin/env python3
"""Real cached identity, edited Cargo and strict-checking qualification."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SOURCE / 'scripts'))
import interpreter
from compare_saved_runtime import acquire_lock, sha
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import SourceEdit, capture, require_space, write_json as write

TOOLCHAIN = 'nightly-2026-09-08'
NAMES = ['tests::checks_another_input', 'tests::checks_host_and_guest_dependencies']


def native_outcomes(stdout, success):
    found = re.findall(r'^test (.+) \.\.\. (ok|FAILED|ignored)$', stdout, re.M)
    assert len(found) == 2 and set(dict(found)) == set(NAMES)
    statuses = dict(found)
    assert 'ignored' not in statuses.values()
    failed = sum(v == 'FAILED' for v in statuses.values())
    assert (failed == 0) == success
    assert re.findall(r'test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;', stdout) == [
        ('ok' if success else 'FAILED', str(2-failed), str(failed), '0')]
    return sorted((name, 'passed' if status == 'ok' else 'failed') for name, status in found)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--harness', type=Path, required=True)
    args = parser.parse_args()
    root = SOURCE.resolve(strict=True)
    interpreter.ROOT = root
    assert re.fullmatch(r'memory-lookup-main-cargo-\d{2}', args.run_id)
    proof_path = args.harness.resolve(strict=True)
    proof = json.loads(proof_path.read_text())
    assert proof['status'] == 'passed' and proof['tests'] == 102
    build_path = args.build.resolve(strict=True)
    build = json.loads(build_path.read_text())
    assert build['status'] == 'passed'
    assert build['tests']['test-debug'] == build['tests']['test-release'] == dict(passed=428, ignored=1)
    keys = dict(baseline=build['tool_key'], candidate=build['tool_key'])
    tools = {mode: interpreter.installed_tools(key)[0] for mode, key in keys.items()}
    manifests = {mode: json.loads((path / 'ready.json').read_text()) for mode, path in tools.items()}
    assert manifests['baseline'] == manifests['candidate']
    assert build['binaries'] == manifests['candidate']
    harness_inputs = root / proof['raw'] / 'inputs.json'
    assert sha(harness_inputs) == proof['inputs_sha256']
    assert all(sha(root / p) == h for p, h in json.loads(harness_inputs.read_text()).items())
    with (root / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(root, 8)
        work = root / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        template = Path(__file__).with_name('fixture')
        fixture = work / 'fixture'
        shutil.copytree(template, fixture)
        write(fixture / '.rust-interp-owned.json', dict(owner=str(root), run_id=args.run_id, purpose='toolchain lookup qualification'))
        paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), proof_path, build_path, harness_inputs,
            SOURCE / 'scripts/suite_reports.py', SOURCE / 'scripts/workflow_io.py',
            SOURCE / 'scripts/interpreter.py', SOURCE / 'scripts/compare_saved_runtime.py']
        paths += [p for p in template.rglob('*') if p.is_file()]
        paths += [root / 'scripts' / name for name in ['interpreter.py', 'workspace_cache.py', 'std_mir.py',
            'test_discovery.py', 'suite_reports.py', 'native_suite.py', 'workflow_io.py', 'toolchain_lookup.py']]
        frozen = {str(p.relative_to(root)): sha(p) for p in paths}
        write(work / 'plan.json', dict(owner=str(root), source=str(SOURCE), frozen=frozen, tools=manifests,
            tool_keys=keys, tests=NAMES, cargo_workers=2, runtime_workers=2,
            phases=['original', 'valid-edit', 'wrong-edit', 'type-error', 'borrow-error', 'restored'],
            performance_measurement=False, identity_mode='fresh versus cached; same exact compiler tools'))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
            and k not in ['RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS',
                'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env['CARGO_TERM_COLOR'] = 'never'
        records = []

        def run(label, command, run_env):
            require_space(root, 8)
            child, stdout, stderr = capture(list(map(str, command)), cwd=fixture, env=run_env,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            row = dict(label=label, command=list(map(str, command)), pid=child.pid,
                returncode=child.returncode, stdout=stdout, stderr=stderr)
            records.append(row)
            write(work / 'records.json', records)
            return row

        probe = run('identity-parity', [sys.executable, '-c', "import json, sys\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nfrom std_mir import checked_std_mir\nfrom toolchain_lookup import compiler_identity\ncompiler, original, fresh = compiler_identity('nightly-2026-09-08')\ncache = Path(sys.argv[1]).parent/'.work/toolchain-lookup'\na = compiler_identity('nightly-2026-09-08', cache)\nb = compiler_identity('nightly-2026-09-08', cache)\nassert a[:2] == b[:2] == (compiler, original) and b[2] == 'hit'\nnormal = checked_std_mir('nightly-2026-09-08')\nobserved = {}\ncached = checked_std_mir('nightly-2026-09-08', lookup='cached', lookup_stats=observed)\nassert normal == cached and observed == dict(mode='cached', outcome='hit')\nprint(json.dumps(dict(status='passed', first=a[2], second=b[2], std_mir_key=cached[2])))\n", root / 'scripts'], dict(env, RUST_INTERP_LAUNCH_STATS='1'))
        assert probe['returncode'] == 0, probe['stderr']
        identity = json.loads(probe['stdout'])
        assert identity['status'] == 'passed' and identity['second'] == 'hit'
        lockfile = run('lockfile', ['cargo', '+'+TOOLCHAIN, 'generate-lockfile', '--offline'], env)
        assert lockfile['returncode'] == 0
        frozen[str((fixture / 'Cargo.lock').relative_to(root))] = sha(fixture / 'Cargo.lock')
        shared = fixture / 'shared/src/lib.rs'
        app = fixture / 'app/src/lib.rs'
        original_shared, original_app = shared.read_bytes(), app.read_bytes()
        valid = original_shared.replace(b'x + 7', b'7 + x')
        wrong = original_shared.replace(b'x + 7', b'x + 8')
        assert valid != original_shared != wrong
        states = [
            ('original', original_shared, original_app, None),
            ('valid-edit', valid, original_app, None),
            ('wrong-edit', wrong, original_app, None),
            ('type-error', original_shared, original_app + b'\npub fn uncalled_bad_type() -> u64 { true }\n', 'E0308'),
            ('borrow-error', original_shared, original_app + b'\npub fn uncalled_bad_borrow() { let mut x = 0u64; let a = &mut x; let b = &mut x; *a += *b; }\n', 'E0499'),
            ('restored', original_shared, original_app, None),
        ]
        with contextlib.ExitStack() as stack:
            shared_edit = stack.enter_context(SourceEdit(shared, original_shared))
            app_edit = stack.enter_context(SourceEdit(app, original_app))
            for phase, shared_bytes, app_bytes, error in states:
                shared_edit.replace(shared_bytes)
                app_edit.replace(app_bytes)
                assert original_app.split(b'#[cfg(test)]', 1)[1] in app.read_bytes()
                success = phase != 'wrong-edit'
                state_rows = {}
                for mode in ['native', 'baseline', 'candidate']:
                    run_env = dict(env)
                    suite = work / (phase+'-'+mode+'-suite.json')
                    if mode == 'native':
                        command = ['cargo', '+'+TOOLCHAIN, 'test', '--locked', '--offline', '--jobs', '2',
                            '--target-dir', work / 'native', '-p', 'host-mir-app', '--lib']
                    else:
                        run_env['RUST_INTERP_LAUNCH_STATS'] = '1'
                        command = [sys.executable, root / 'scripts/interpreter.py', '--manifest-path', fixture / 'Cargo.toml',
                            '--package', 'host-mir-app', '--jobs', '2', '--tool-key', keys[mode],
                            '--cache-namespace', args.run_id+':'+mode, '--test-body', '--test-filter', 'tests::',
                            '--std-mir', '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                            '--isolated-batch', 'prepared', '--suite-workers', '2', '--suite-report', suite,
                            '--function-cache', 'auto', '--inline-leaves', '--trap-unsupported-calls', '--run-try-callbacks']
                    if mode == 'candidate': command += ['--toolchain-lookup', 'cached']
                    row = run(phase+'-'+mode, command, run_env)
                    row.update(phase=phase, mode=mode, shared_sha256=sha(shared), app_sha256=sha(app))
                    if error:
                        assert row['returncode'] != 0 and error in row['stderr'] and not suite.exists()
                        assert 'test result:' not in row['stdout']
                    else:
                        assert (row['returncode'] == 0) == success
                        if mode == 'native':
                            row['outcomes'] = native_outcomes(row['stdout'], success)
                        else:
                            trace, = [json.loads(s.split(': ', 1)[1]) for s in row['stderr'].splitlines()
                                if s.startswith('rust-interp-launch: ')]
                            assert trace['tool_key'] == keys[mode]
                            assert trace['toolchain_lookup'] == dict(mode='cached' if mode == 'candidate' else 'fresh', outcome='hit' if mode == 'candidate' else 'fresh')
                            report, digest = read_report(suite, trace['suite_report_sha256'])
                            names = [test['name'] for test in report['tests']]
                            assert sorted(names) == NAMES
                            row['outcomes'] = sorted(validate_report(report, names, 'prepared', success))
                            validate_runtime_limits(report, required=True)
                            row['suite_sha256'] = digest
                            row['launch'] = trace
                            saved = work / (phase+'-'+mode+'.rbc')
                            shutil.copy2(trace['artifact_path'], saved)
                            assert sha(saved) == trace['artifact_sha256']
                            row['artifact'] = dict(path=str(saved.relative_to(root)), sha256=sha(saved))
                            for kind in ['entry_catalog', 'test_selection']:
                                path = work / (phase+'-'+mode+'-'+kind+'.json')
                                shutil.copy2(trace[kind+'_path'], path)
                                assert sha(path) == trace[kind+'_sha256']
                                row[kind+'_sha256'] = sha(path)
                    write(work / 'records.json', records)
                    state_rows[mode] = row
                    print(phase, mode, 'expected outcome', flush=True)
                if error is None:
                    assert state_rows['native']['outcomes'] == state_rows['baseline']['outcomes'] == state_rows['candidate']['outcomes']
                    for field in ['artifact', 'entry_catalog_sha256', 'test_selection_sha256']:
                        a, b = state_rows['baseline'][field], state_rows['candidate'][field]
                        assert (a['sha256'] if field == 'artifact' else a) == (b['sha256'] if field == 'artifact' else b)
        assert shared.read_bytes() == original_shared and app.read_bytes() == original_app
        assert all(sha(root / p) == digest for p, digest in frozen.items())
        for key in keys.values():
            interpreter.installed_tools(key)
        write(work / 'frozen.json', frozen)
        result = root / 'results' / args.run_id
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=len(records), primary_commands=18,
            native_commands=6, custom_commands=12,
            phases=[s[0] for s in states], tests=NAMES, tool_keys=keys, tools=manifests,
            source_restored=True, test_source_unchanged=True, identity=identity, cache_hits_verified=True,
            strict_uncalled_errors=['E0308', 'E0499'], artifact_pairs=4,
            performance_measurement=False, raw=str(work.relative_to(root)),
            evidence={name: sha(work / (name + '.json')) for name in ['plan', 'records', 'frozen']}))


if __name__ == '__main__':
    main()
