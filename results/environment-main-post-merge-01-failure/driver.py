"""Check the publication merge while preserving newer compiler routing."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        source = ROOT / '.work/publication-main'
        assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=source).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
        work = ROOT / '.work/environment-main-post-merge-01'; work.mkdir(exist_ok=False)
        paths = [source / p for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0')
                 if p and (p.endswith('.py') or p.endswith('.rs') or p.endswith('Cargo.toml') or p.endswith('Cargo.lock') or p == 'rust-toolchain.toml')]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        for p in (source / 'crates/bytecode').rglob('*'):
            if p.is_file() and (p.suffix == '.rs' or p.name == 'Cargo.toml'):
                assert p.read_bytes() == (ROOT / p.relative_to(source)).read_bytes(), p
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        commands = [('python', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'])]
        for label, profile in [('debug', []), ('release', ['--release'])]:
            commands.append((label, ['cargo', '+nightly-2026-09-08', 'test', *profile, '--locked', '--offline',
                '--jobs', '2', '--target-dir', str(target), '-p', 'rust-interp-mir-export']))
        write(work / 'plan.json', dict(owner=str(ROOT), source=str(source), source_commit=revision,
            frozen=frozen, commands=commands, control='results/environment-main-final-audit-01/summary.json',
            scope='Check merged root launcher contracts and complete exporter/wrapper tests; prior159 real controls and114 parser tests remain bound to b08f39e2.',
            performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1', PYTHONDONTWRITEBYTECODE='1')
        records, totals = [], {}
        for label, command in commands:
            require_space(ROOT, 8)
            child, out, err = capture(command, cwd=source, env=env,
                                     receipt_path=work / 'active.json', receipt=dict(label=label))
            (work / (label + '.stdout')).write_text(out); (work / (label + '.stderr')).write_text(err)
            records.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', records)
            assert child.returncode == 0, (label, err[-3000:])
            if label == 'python':
                count, = re.findall(r'Ran (\d+) tests? in ', err)
                skips = re.findall(r'OK \(skipped=(\d+)\)', err)
                assert err.rstrip().endswith('OK') or skips
                totals[label] = dict(tests=int(count), skipped=int(skips[0]) if skips else 0)
            else:
                groups = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;', out + err)
                assert groups and all(int(f) == 0 for _, f in groups)
                totals[label] = sum(int(n) for n, _ in groups)
                assert totals[label] >= 98
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, totals[label], 'passed', flush=True)
        assert totals['debug'] == totals['release']
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == revision
        result = ROOT / 'results/environment-main-post-merge-01'; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', source_commit=revision, commands=3,
            tests=totals, unchanged_bytecode_sources=True, frozen_source_files=len(frozen),
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), performance_measurement=False))


if __name__ == '__main__':
    main()
