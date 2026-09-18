"""Run current-main Python contracts with only the diagnostic parser fix added."""
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
PUB = ROOT / '.work/publication-main'
RUN = 'vmmap-main-contracts-01'
CHANGED = ['scripts/sample_owned_vm.py', 'scripts/summarize_owned_sample.py',
           'scripts/vmmap_ranges.py', 'tests/test_vmmap_ranges.py']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=PUB, text=True).strip()


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        assert git('status', '--porcelain') == ''
        revision, parent = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^')
        assert sorted(git('diff', '--name-only', 'HEAD^', 'HEAD').splitlines()) == sorted(CHANGED)
        assert all(sha(PUB / p) == sha(ROOT / p) for p in CHANGED)
        qualified = ROOT / 'results/vmmap-label-compatibility-01'
        receipt = json.loads((qualified / 'closure.json').read_text())
        assert receipt['status'] == 'closed' and receipt['all_hashes_verified']
        assert sha(qualified / 'summary.json') == receipt['summary_sha256']
        inputs = git('ls-files', 'scripts', 'tests', 'crates', 'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml').splitlines()
        frozen = {p: sha(PUB / p) for p in inputs}
        raw = ROOT / '.work' / RUN
        raw.mkdir(exist_ok=False)
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']
        write(raw / 'plan.json', dict(owner=str(ROOT), worktree=str(PUB), source_revision=revision,
            parent_revision=parent, changed_files=CHANGED, frozen=frozen, command=command,
            qualified_replay_summary_sha256=sha(qualified / 'summary.json'),
            minimum_child_gib=8, guest_commands=0, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_'))
               and k not in ['RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS', 'PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        child, out, err = capture(command, cwd=PUB, env=env, receipt_path=raw / 'active.json',
            receipt=dict(stage='merged main Python contracts'))
        (raw / 'stdout').write_text(out)
        (raw / 'stderr').write_text(err)
        write(raw / 'record.json', dict(command=command, cwd=str(PUB), pid=child.pid,
            returncode=child.returncode, stdout_sha256=sha(raw / 'stdout'), stderr_sha256=sha(raw / 'stderr')))
        assert child.returncode == 0, (out + err)[-5000:]
        count, = re.findall(r'Ran (\d+) tests? in ', err)
        skipped, = re.findall(r'^OK(?: \(skipped=(\d+)\))?$', err, re.M)
        assert int(count) >= 449
        assert err.count('test_vmmap_ranges.VmmapRanges.') == 6
        assert 'test_runtime_compiler' in err and 'test_isolated_launcher' in err
        assert all(sha(PUB / p) == h for p, h in frozen.items())
        assert git('rev-parse', 'HEAD') == revision and git('status', '--porcelain') == ''
        destination = ROOT / 'results' / RUN
        destination.mkdir(exist_ok=False)
        write(destination / 'summary.json', dict(status='passed', source_revision=revision,
            parent_revision=parent, changed_files=CHANGED, commands=1, guest_commands=0,
            python=dict(discovered=int(count), passed=int(count) - int(skipped or 0), skipped=int(skipped or 0)),
            source_files=len(frozen), all_frozen_hashes_verified=True, raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw / 'plan.json'), record_sha256=sha(raw / 'record.json'), performance_measurement=False))
        print('PASS:', count, 'merged Python contracts;', skipped or 0, 'skipped', flush=True)


if __name__ == '__main__':
    main()
