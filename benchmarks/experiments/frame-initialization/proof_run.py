#!/usr/bin/env python3
"""Build/test the diagnostic and inspect saved bytecode; never execute the guest."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
ARTIFACT = ROOT / '.work/fre-integration-es8-edit-01/artifacts/restored.rbc'
ARTIFACT_SHA = 'd35688bd1714620b4fc4fd06f0220881ebe9d2a6aa8d66def4561012bec0041d'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id.startswith('frame-initialization-proof-') or Path(args.run_id).name != args.run_id:
        parser.error('invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        work = ROOT / '.work' / args.run_id
        work.mkdir()
        target = work / 'target'
        # This small diagnostic uses no incremental/debug metadata and no guest
        # or large-project compilation. Full benchmark disk guards are separate.
        assert shutil.disk_usage(ROOT).free >= 2 * 1024**3
        assert sha(ARTIFACT) == ARTIFACT_SHA
        files = list((ROOT / 'crates/bytecode').rglob('*.rs'))
        files += [p for p in SOURCE.iterdir() if p.is_file()]
        files += [ROOT / 'crates/bytecode/Cargo.toml', ROOT / 'rust-toolchain.toml', ARTIFACT]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in files}
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or key in [
                'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']:
                env.pop(key)
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='0')
        write(work / 'plan.json', dict(source_commit=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), frozen=frozen,
            profile='debug/release tests; release diagnostic; no debug info or incremental state',
            performance_measurement=False, guest_commands=0, minimum_free_bytes=2 * 1024**3))
        commands = []

        def invoke(label, command):
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            with (work / (label + '.stdout')).open('x') as out, (work / (label + '.stderr')).open('x') as err:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=out, stderr=err)
                record = dict(label=label, command=command, pid=child.pid, parent_pid=os.getpid(),
                              cwd=str(ROOT), started_at=time.time(), status='running')
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
            assert all(sha(ROOT / p) == h for p, h in frozen.items())

        common = ['--locked', '--offline', '--jobs', '2', '--manifest-path', str(SOURCE / 'Cargo.toml'),
                  '--target-dir', str(target)]
        for mode in [[], ['--release']]:
            invoke('test-release' if mode else 'test-debug', ['cargo', '+nightly-2026-09-08', 'test', *mode, *common])
        invoke('build', ['cargo', '+nightly-2026-09-08', 'build', '--release', *common])
        binary = target / 'release/frame-initialization-census'
        invoke('es8-proof', [str(binary), '--proof', str(ARTIFACT)])
        functions = json.loads((work / 'es8-proof.stdout').read_text())
        summary = dict(status='passed', performance_measurement=False, guest_commands=0,
            functions=len(functions), eligible_functions=sum(f['proof']['eligible'] for f in functions),
            direct_calls=sum(len(f['calls']) for f in functions),
            eligible_call_sites=sum(c['eligible'] for f in functions for c in f['calls']),
            binary_sha256=sha(binary), evidence={str(p.relative_to(ROOT)): sha(p) for p in
                [work / 'plan.json', work / 'commands.json', work / 'es8-proof.stdout']})
        write(work / 'summary.json', summary)
        print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
