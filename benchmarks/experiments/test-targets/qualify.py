#!/usr/bin/env python3
"""Exercise actual Cargo routing and strict rejection with retained guest tools."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/tuned-native'))
from timing import invoke, read, require, sha
from workflow_io import SourceEdit, require_space, write_json as write
from workflow_controls import native_environment

TOOL = '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'
RUN = 'integration-targets-fixture-01'


def main():
    global RUN
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', type=int, choices=range(1, 10), default=1)
    args = parser.parse_args()
    RUN = f'integration-targets-fixture-{args.attempt:02}'
    work = ROOT / '.work' / RUN
    work.mkdir(exist_ok=False)
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work / 'status.json', status)
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require_space(ROOT, 8)
            fixture = work / 'fixture'
            (fixture / 'src').mkdir(parents=True)
            (fixture / 'tests').mkdir()
            (fixture / 'Cargo.toml').write_text('[package]\nname="target-fixture"\nversion="0.0.0"\nedition="2024"\n[workspace]\n')
            (fixture / 'Cargo.lock').write_text('version = 4\n\n[[package]]\nname = "target-fixture"\nversion = "0.0.0"\n')
            original = b'pub fn next(n: u8) -> u8 { n + 1 }\n#[cfg(test)]\n#[test]\nfn same_name() { assert!(next(4) == 5); }\n'
            lib = fixture / 'src/lib.rs'
            lib.write_bytes(original)
            for name, value in [('target-a', 5), ('target-b', 6)]:
                (fixture / 'tests' / (name + '.rs')).write_text(f'#[test]\nfn same_name() {{ assert!(target_fixture::next(4) == {value}); }}\n')
            env = os.environ.copy()
            for key in list(env):
                if key.startswith(('RUST_INTERP_', 'CARGO_PROFILE_')) or key in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']:
                    env.pop(key)
            env = native_environment(env, 'o0-incremental', [])
            env.update(CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1')
            source = ROOT / '.work/test-targets-source'
            require(not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=source, text=True), 'source branch modified')
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
            paths = [Path(__file__), HERE / 'launcher.py', HERE / 'PLAN.md', source / 'scripts/interpreter.py']
            frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
            write(work / 'plan.json', dict(owner=str(ROOT), source_commit=commit, tool_key=TOOL, frozen=frozen))
            records = []

            def call(label, target, success, engine=None, diagnostic=None):
                target_args = ['--lib'] if target is None else ['--test', target]
                if engine is None:
                    command = ['cargo', '+nightly-2026-09-08', 'test', '--manifest-path', str(fixture / 'Cargo.toml'), '--package', 'target-fixture',
                        *target_args, '--locked', '--offline', '--jobs', '2', '--target-dir', str(work / 'native'), '--', '--exact', 'same_name']
                else:
                    command = [sys.executable, str(HERE / 'launcher.py'), '--manifest-path', str(fixture / 'Cargo.toml'), '--package', 'target-fixture',
                        '--entry', 'same_name', '--test-body', '--tool-key', TOOL, '--cache-namespace', RUN, '--jobs', '2', '--std-mir',
                        '--engine', engine, '--trap-unsupported-calls', '--run-try-callbacks']
                    if target is not None:
                        command += ['--test-target', target]
                    if engine == 'jit':
                        command += ['--jit-resumable-calls', '--jit-persistent-registers']
                row, stdout, stderr = invoke(work, label, command, fixture, env)
                row.update(engine=engine or 'native', target=target, source_sha256=sha(lib), expected_success=success)
                records.append(row)
                write(work / 'records.json', records)
                require((row['returncode'] == 0) == success, 'unexpected assertion outcome: ' + label)
                if engine is not None and success:
                    require(stdout.strip() == '0', 'wrong guest result')
                if engine is not None and not diagnostic:
                    launches = [json.loads(line.split(': ', 1)[1]) for line in stderr.splitlines() if line.startswith('rust-interp-launch: ')]
                    require(len(launches) == 1, 'missing executed artifact identity')
                    row['launch'] = launches[0]
                if engine is None and success:
                    require('1 passed; 0 failed' in stdout, 'native test did not run')
                if diagnostic:
                    require(diagnostic in stderr and stdout.strip() != '0', 'strict error missing or stale VM result')
                print(label, row['returncode'], flush=True)

            status.update(status='running')
            write(work / 'status.json', status)
            with SourceEdit(lib, original) as edit:
                call('native-a', 'target-a', True)
                call('jit-a', 'target-a', True, 'jit')
                call('interpreter-a', 'target-a', True, 'interpreter')
                call('native-b', 'target-b', False)
                call('jit-b', 'target-b', False, 'jit')
                call('jit-a-after-b', 'target-a', True, 'jit')
                call('native-lib', None, True)
                call('jit-lib', None, True, 'jit')
                edit.replace(original.replace(b'n + 1', b'n + 2'))
                call('wrong-native', 'target-a', False)
                call('wrong-jit', 'target-a', False, 'jit')
                edit.replace(original + b'pub fn uncalled() { let _: u8 = "wrong"; }\n')
                call('strict-type', 'target-a', False, 'jit', 'E0308')
                edit.replace(original + b'pub fn uncalled() { let mut v = vec![1u8]; let first = &v[0]; v.push(2); std::hint::black_box(first); }\n')
                call('strict-borrow', 'target-a', False, 'jit', 'E0502')
                edit.replace(original)
                call('restored-native', 'target-a', True)
                call('restored-jit', 'target-a', True, 'jit')
            require(lib.read_bytes() == original and all(sha(ROOT / p) == h for p, h in frozen.items()), 'source or inputs changed')
            executed = {r['label']: r for r in records if 'launch' in r}
            artifacts = {name: Path(r['launch']['artifact_path']) for name, r in executed.items()}
            cache = lambda p: next(parent for parent in p.parents if parent.name == 'target').parent
            shared = cache(artifacts['jit-a']) == cache(artifacts['jit-b'])
            require(shared and artifacts['jit-a'] != artifacts['jit-b'] and
                artifacts['jit-a-after-b'] == artifacts['jit-a'], 'target sidecar isolation or cache sharing differs')
            require(cache(artifacts['jit-lib']) != cache(artifacts['jit-a']), 'existing library cache changed')
            out = ROOT / 'results' / RUN
            out.mkdir(exist_ok=False)
            write(out / 'summary.json', dict(status='passed', raw=str(work.relative_to(ROOT)), commands=len(records),
                source_commit=commit, tool_key=TOOL, source_restored=True, native_controls=sum(r['engine']=='native' for r in records),
                custom_commands=sum(r['engine']!='native' for r in records),
                integration_dependency_cache_shared=shared, target_sidecars_distinct=True, library_cache_unchanged=True,
                target_switches_and_library_route=True, strict_uncalled_type_and_borrow_errors=True,
                records_sha256=sha(work / 'records.json'), frozen=frozen,
                note='Actual isolated Cargo integration-target routing, native/interpreter/custom-JIT assertions and stale-output rejection. No guest compiler or runtime changed; this fixture is not a real-project performance result.'))
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work / 'status.json', status)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__':
    main()
