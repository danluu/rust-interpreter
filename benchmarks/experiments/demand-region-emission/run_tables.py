"""Qualify stable individual resume-slot publication, without guest execution."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
NAME = 'demand-resume-tables-01'


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        allocated = int(subprocess.check_output(['du', '-sk', str(target)], text=True).split()[0]) * 1024
        needed = max(14 * 1024**3, 8 * 1024**3 + 2 * allocated)
        assert shutil.disk_usage(ROOT).free >= needed, 'insufficient conservative build admission'
        paths = [ROOT / p for p in subprocess.check_output(['git', 'ls-files', 'crates', 'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'], text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
        paths += [ROOT / 'scripts' / p for p in ['compare_saved_runtime.py', 'workflow_io.py']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD']).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        work = ROOT / '.work' / NAME; work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
            target=str(target.relative_to(ROOT)), same_source_root=True, required_free_bytes=needed,
            allocated_target_bytes=allocated, minimum_child_gib=8, expected_commands=2,
            controls_per_profile=2, guest_commands=0, executable_code_publications=0, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0', CARGO_PROFILE_RELEASE_DEBUG='1', CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0', CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1', RUST_TEST_THREADS='2')
        cargo = ['cargo', '+nightly-2026-09-08', 'test', '--lib', '-p', 'rust-interp-bytecode',
                 '--locked', '--offline', '--jobs', '2', '--manifest-path', str(ROOT / 'Cargo.toml'), '--target-dir', str(target)]
        records = []
        for label in ['debug', 'release']:
            require_space(ROOT, 8)
            assert shutil.disk_usage(ROOT).free >= needed, 'build admission no longer holds'
            command = cargo + (['--release'] if label == 'release' else []) + ['jit::resumable::table_tests::']
            start = time.time()
            child, out, err = capture(command, cwd=ROOT, env=env, receipt_path=work / 'active.json', receipt=dict(label=label))
            for stream, payload in [('stdout', out), ('stderr', err)]: (work / (label + '.' + stream)).write_text(payload)
            records.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode, seconds=time.time() - start,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', records)
            assert child.returncode == 0, (out + err)[-6000:]
            assert 'test result: ok. 2 passed; 0 failed; 0 ignored;' in out
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, 'passed', flush=True)
        out = ROOT / 'results' / NAME; out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', commands=2, controls_per_profile=2,
            source_revision=revision, raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), cases=[], setup_seconds=sum(r['seconds'] for r in records),
            guest_commands=0, executable_code_publications=0, performance_measurement=False,
            scope='Focused stable table pointer/slot ownership and exact table-budget refusal; full demand VM integration is pending.'))


if __name__ == '__main__':
    main()
