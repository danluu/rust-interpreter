#!/usr/bin/env python3
"""Build matched baseline/candidate VMs and qualify exact frame clearing."""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[3]
BASELINE = '0189a06'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id.startswith('fixed-frame-clear-') and Path(args.run_id).name == args.run_id
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        deadline = time.monotonic() + 45
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
        assert shutil.disk_usage(ROOT).free >= 2 * 1024**3
        work = ROOT / '.work' / args.run_id
        work.mkdir()
        source = work / 'source'
        source.mkdir()
        target = work / 'target'
        archive = subprocess.check_output(['git', 'archive', BASELINE, 'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'crates'], cwd=ROOT)
        baseline, candidate = {}, {}
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar.getmembers():
                if member.isdir():
                    continue
                assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
                path = source / member.name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(tar.extractfile(member).read())
                baseline[member.name] = sha(path)
                candidate[member.name] = sha(ROOT / member.name)
        # Both builds use identical absolute source/target paths and flags.
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or key in [
                'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']:
                env.pop(key)
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1')
        write(work / 'plan.json', dict(baseline_commit=BASELINE, baseline=baseline, candidate=candidate,
            source=str(source), target=str(target), release_debug=1, dev_debug=0, incremental=False,
            jobs=2, performance_measurement=False, runner_sha256=sha(Path(__file__))))
        commands = []
        active_sources = baseline

        def verify():
            assert all(sha(source / p) == h for p, h in active_sources.items())
            assert all(sha(ROOT / p) == h for p, h in candidate.items())

        def invoke(label, command):
            verify()
            with (work / (label + '.stdout')).open('x') as out, (work / (label + '.stderr')).open('x') as err:
                child = subprocess.Popen(command, cwd=source, env=env, stdout=out, stderr=err)
                record = dict(label=label, command=command, pid=child.pid, parent_pid=os.getpid(),
                              cwd=str(source), started_at=time.time(), status='running')
                record['identity'] = subprocess.run(['ps', '-p', str(child.pid), '-o',
                    'pid,ppid,lstart,tty,command'], capture_output=True, text=True).stdout
                write(work / 'active-command.json', record)
                print('START', label, child.pid, flush=True)
                code = child.wait()
            record.update(status='finished', returncode=code, finished_at=time.time())
            write(work / 'active-command.json', record)
            commands.append(record)
            write(work / 'commands.json', commands)
            assert code == 0, (label, code)
            verify()

        common = ['--locked', '--offline', '--jobs', '2', '-p', 'rust-interp-bytecode', '--target-dir', str(target)]
        invoke('baseline-build', ['cargo', '+nightly-2026-09-08', 'build', '--release', *common])
        vm = target / 'release/rust-interp-vm'
        shutil.copy2(vm, work / 'baseline-vm')
        for name in candidate:
            (source / name).write_bytes((ROOT / name).read_bytes())
        active_sources = candidate
        for mode in [[], ['--release']]:
            invoke('candidate-test-release' if mode else 'candidate-test-debug',
                   ['cargo', '+nightly-2026-09-08', 'test', *mode, *common])
        invoke('candidate-build', ['cargo', '+nightly-2026-09-08', 'build', '--release', *common])
        shutil.copy2(vm, work / 'candidate-vm')
        write(work / 'summary.json', dict(status='passed', performance_measurement=False,
            baseline_vm_sha256=sha(work / 'baseline-vm'), candidate_vm_sha256=sha(work / 'candidate-vm'),
            evidence={str(p.relative_to(ROOT)): sha(p) for p in [work / 'plan.json', work / 'commands.json',
                work / 'candidate-test-debug.stdout', work / 'candidate-test-release.stdout']}))
        print('QUALIFIED', args.run_id, flush=True)


if __name__ == '__main__':
    main()
