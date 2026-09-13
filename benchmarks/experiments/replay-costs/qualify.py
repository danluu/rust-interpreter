"""Qualify observer parity, strict failures and option invalidation in real Cargo."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from suite_reports import read_report, validate_report
from workflow_io import SourceEdit, capture, require_space, write_json as write
from observe import messages, observation, require_cargo_export

BASELINE = 'e729a493261568d841d3ef212bcdfeef8fa4bf715cd26538f3cb9d1fa447e846'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    assert args.run_id.startswith('replay-costs-fixture-') and Path(args.run_id).name == args.run_id
    build_path = args.build.resolve(strict=True)
    build = json.loads(build_path.read_text())
    assert build['status'] == 'passed' and build['tests'] == {'test-debug': 75, 'test-release': 75}
    candidate, key = installed_tools(build['tool_key'])
    baseline, _ = installed_tools(BASELINE)
    for name in ['rust-interp-vm', 'rust-interp-rustc-wrapper']:
        assert sha(candidate / name) == sha(baseline / name) == build['binaries'][name]
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        template = HERE.parent / 'memory-lookup-main/fixture'
        fixture = work / 'fixture'
        shutil.copytree(template, fixture)
        write(fixture / '.rust-interp-owned.json', dict(owner=str(ROOT), run_id=args.run_id))
        paths = [build_path, *HERE.glob('*.py'), HERE / 'PLAN.md', *template.rglob('*')]
        paths += [ROOT / 'scripts' / p for p in ['interpreter.py', 'compare_saved_runtime.py', 'workflow_io.py', 'suite_reports.py']]
        paths += [p / n for p in [candidate, baseline] for n in build['binaries']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()}
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, expected_commands=26,
            modes=['retained', 'off', 'on'], performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
            and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                          'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1')
        records = []

        def run(label, command, run_env=env):
            require_space(ROOT, 8)
            child, out, err = capture(list(map(str, command)), cwd=fixture, env=run_env,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            row = dict(label=label, command=list(map(str, command)), pid=child.pid,
                       returncode=child.returncode, stdout=out, stderr=err)
            records.append(row)
            write(work / 'records.json', records)
            return row

        def command(mode, value, label, cache='auto'):
            cmd = [sys.executable, HERE / 'launcher.py']
            if value is not None:
                cmd += ['--replay-costs', value]
            return cmd + ['--manifest-path', fixture / 'Cargo.toml', '--package', 'host-mir-app',
                '--jobs', '2', '--tool-key', BASELINE if mode == 'retained' else key,
                '--cache-namespace', args.run_id + ':' + mode, '--test-body', '--test-filter', 'tests::',
                '--std-mir', '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                '--isolated-batch', 'prepared', '--suite-workers', '2', '--suite-report', work / (label + '-suite.json'),
                '--function-cache', cache, '--toolchain-lookup', 'cached', '--inline-leaves',
                '--trap-unsupported-calls', '--run-try-callbacks']

        def check(row, enabled, success=True, cold=False):
            assert (row['returncode'] == 0) == success
            require_cargo_export(row['stderr'], 'host-mir-app')
            launch, = messages(row['stderr'], 'rust-interp-launch')
            report, _ = read_report(Path(launch['suite_report_path']), launch['suite_report_sha256'])
            names = ['tests::checks_another_input', 'tests::checks_host_and_guest_dependencies']
            row['outcomes'] = sorted(validate_report(report, names, 'prepared', success))
            row['launch'] = launch
            row['observation'] = observation(row['stderr'], enabled)
            if enabled:
                assert (row['observation']['totals']['functions'] == 0) == cold
            for kind in ['artifact', 'entry_catalog']:
                path = Path(launch[kind + '_path'])
                assert sha(path) == launch[kind + '_sha256']
                saved = work / (row['label'] + '-' + kind + path.suffix)
                shutil.copy2(path, saved)
            write(work / 'records.json', records)
            return tuple(launch[k + '_sha256'] for k in ['artifact', 'entry_catalog'])

        assert run('lockfile', ['cargo', '+nightly-2026-09-08', 'generate-lockfile', '--offline'])['returncode'] == 0
        shared, app = fixture / 'shared/src/lib.rs', fixture / 'app/src/lib.rs'
        original_shared, original_app = shared.read_bytes(), app.read_bytes()
        states = [('original', original_shared, original_app, None),
            ('valid', original_shared.replace(b'x + 7', b'7 + x'), original_app, None),
            ('wrong', original_shared.replace(b'x + 7', b'x + 8'), original_app, None),
            ('type', original_shared, original_app + b'\npub fn uncalled_bad_type() -> u64 { true }\n', 'E0308'),
            ('borrow', original_shared, original_app + b'\npub fn uncalled_bad_borrow() { let mut x = 0u64; let a = &mut x; let b = &mut x; *a += *b; }\n', 'E0499'),
            ('restored', original_shared, original_app, None)]
        with contextlib.ExitStack() as stack:
            shared_edit = stack.enter_context(SourceEdit(shared, original_shared))
            app_edit = stack.enter_context(SourceEdit(app, original_app))
            for phase, shared_bytes, app_bytes, error in states:
                shared_edit.replace(shared_bytes)
                app_edit.replace(app_bytes)
                artifacts = []
                for mode, value in [('retained', None), ('off', '0'), ('on', '1')]:
                    label = phase + '-' + mode
                    row = run(label, command(mode, value, label))
                    if error:
                        assert row['returncode'] != 0 and error in row['stderr']
                        assert not (work / (label + '-suite.json')).exists()
                        assert not messages(row['stderr'], 'rust-interp-launch')
                    else:
                        artifacts.append(check(row, mode == 'on', phase != 'wrong', phase == 'original'))
                    print(label, 'expected outcome', flush=True)
                if artifacts:
                    assert len(set(artifacts)) == 1
            # No source writes between these calls: the diagnostic environment
            # alone must invalidate Cargo's exported artifact.
            for index, value in enumerate(['0', None, '1']):
                label = 'toggle-' + str(index)
                row = run(label, command('on', value, label))
                assert check(row, value == '1') == artifacts[0]
            for label, value, cache, incremental in [('empty', '', 'auto', None), ('invalid', '2', 'auto', None),
                    ('off-cache', '1', 'off', None), ('auto-no-incremental', '1', 'auto', '0')]:
                run_env = env if incremental is None else dict(env, CARGO_INCREMENTAL=incremental)
                row = run(label, command('on', value, label, cache), run_env)
                assert row['returncode'] != 0 and not (work / (label + '-suite.json')).exists()
                expected = 'RUST_INTERP_REPLAY_COSTS must be 0 or 1' if label in ['empty', 'invalid'] else 'replay costs require actual function reuse and strict checking'
                assert expected in row['stderr'] and not messages(row['stderr'], 'rust-interp-launch')
                print(label, 'expected rejection', flush=True)
        assert len(records) == 26
        assert shared.read_bytes() == original_shared and app.read_bytes() == original_app
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / args.run_id
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=26, tool_key=key,
            original_wrong_and_restored_parity=True, strict_errors=['E0308', 'E0499'],
            cold_and_warm_observer_coverage=True, unchanged_source_option_invalidation=True,
            invalid_options_and_missing_reuse_rejected=True, source_restored=True,
            performance_measurement=False, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json')))


if __name__ == '__main__':
    main()
