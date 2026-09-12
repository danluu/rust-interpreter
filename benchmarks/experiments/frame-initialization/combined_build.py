#!/usr/bin/env python3
"""Build the frozen current-main/fixed-clear pair at identical absolute paths."""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock
from interpreter import installed_tools
from workflow_io import write_json as write

COMMITS = dict(baseline='ae0a49e', candidate='46134e4')
EXPECTED_TESTS = dict(baseline=297, candidate=300)
FIXED = ['crates/bytecode/src/jit/resumable.rs', 'crates/bytecode/src/jit/resumable_tests.rs']
CONTROL = '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(commit):
    archive = subprocess.check_output(['git', 'archive', commit, 'Cargo.toml', 'Cargo.lock',
        'rust-toolchain.toml', 'crates'], cwd=ROOT)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if member.isdir():
                continue
            name = Path(member.name)
            require(member.isfile() and not name.is_absolute() and '..' not in name.parts,
                'unexpected source archive entry')
            files[member.name] = tar.extractfile(member).read()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'fixed-frame-clear-combined-build-\d{2}', args.run_id), 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        status = dict(owner=str(ROOT), pid=os.getpid(), parent_pid=os.getppid(),
            cwd=str(ROOT), status='preflight', started_at=time.time())
        write(work / 'status.json', status)
        try:
            free = shutil.disk_usage(ROOT).free
            require(free >= 10 * 1024**3, 'require 8GiB running floor plus 2GiB build reserve')
            sources = {mode: snapshot(commit) for mode, commit in COMMITS.items()}
            require(sources['baseline'].keys() == sources['candidate'].keys(), 'workspace file set changed')
            changed = sorted(p for p in sources['baseline'] if sources['baseline'][p] != sources['candidate'][p])
            require(changed == FIXED, 'integration includes unexpected source changes')
            original = snapshot('6f9e148')
            require(all(sources['candidate'][p] == original[p] for p in FIXED), 'fixed-clear implementation changed')
            manifests = {mode: {p: hashlib.sha256(b).hexdigest() for p, b in files.items()}
                for mode, files in sources.items()}
            frozen_paths = [Path(__file__), Path(__file__).with_name('FIXED-INTEGRATION.md'),
                ROOT / 'scripts/compare_saved_runtime.py', ROOT / 'scripts/interpreter.py', ROOT / 'scripts/workflow_io.py']
            frozen = {str(p.relative_to(ROOT)): sha(p) for p in frozen_paths}
            source, target = work / 'source', work / 'target'
            env = os.environ.copy()
            for key in list(env):
                if key.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or key in [
                    'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                    'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']:
                    env.pop(key)
            env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1')
            write(work / 'plan.json', dict(owner=str(ROOT), commits=COMMITS, sources=manifests,
                changed=changed, source=str(source), target=str(target), frozen=frozen,
                expected_tests=EXPECTED_TESTS, observed_free_bytes=free, minimum_free_bytes=8 * 1024**3,
                jobs=2, incremental=False, dev_debug=0, release_debug=1, performance_measurement=False))
            commands, tests, active_mode = [], {}, None

            def verify():
                require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'build recipe changed')
                require(all(sha(source / p) == h for p, h in manifests[active_mode].items()), 'build source changed')

            def invoke(label, command):
                verify()
                require(shutil.disk_usage(ROOT).free >= 8 * 1024**3, 'running disk floor reached')
                log_path = work / (label + '.log')
                with log_path.open('x') as log:
                    child = subprocess.Popen(command, cwd=source, env=env, stdin=subprocess.DEVNULL,
                        stdout=log, stderr=subprocess.STDOUT)
                    row = dict(label=label, command=command, pid=child.pid, parent_pid=os.getpid(),
                        cwd=str(source), started_at=time.time(), status='running',
                        identity=subprocess.run(['ps', '-p', str(child.pid), '-o', 'pid,ppid,lstart,tty,command'],
                            capture_output=True, text=True).stdout)
                    write(work / 'active-command.json', row)
                    print('START', label, child.pid, flush=True)
                    code = child.wait()
                row.update(status='finished', returncode=code, finished_at=time.time(),
                    log=str(log_path.relative_to(ROOT)), log_sha256=sha(log_path))
                commands.append(row)
                write(work / 'commands.json', commands)
                write(work / 'active-command.json', row)
                require(code == 0, 'command failed: ' + label)
                verify()
                return log_path.read_text()

            common = ['--locked', '--offline', '--jobs', '2', '--target-dir', str(target)]
            for mode in ['baseline', 'candidate']:
                for name, payload in sources[mode].items():
                    path = source / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if not path.exists() or path.read_bytes() != payload:
                        path.write_bytes(payload)
                active_mode = mode
                for profile in ['debug', 'release']:
                    label = mode + '-test-' + profile
                    output = invoke(label, ['cargo', '+nightly-2026-09-08', 'test', '--workspace',
                        *([] if profile == 'debug' else ['--release']), *common])
                    counts = [tuple(map(int, m)) for m in re.findall(
                        r'test result: .*? (\d+) passed; (\d+) failed; (\d+) ignored;', output)]
                    totals = tuple(sum(row[i] for row in counts) for i in range(3))
                    tests[label] = dict(passed=totals[0], failed=totals[1], ignored=totals[2])
                    require(totals == (EXPECTED_TESTS[mode], 0, 1), 'workspace test coverage differs: ' + label)
                invoke(mode + '-build', ['cargo', '+nightly-2026-09-08', 'build', '--release',
                    '-p', 'rust-interp-bytecode', *common])
                shutil.copy2(target / 'release/rust-interp-vm', work / (mode + '-vm'))
            summary = dict(status='passed', tests=tests, commits=COMMITS, manifests=manifests,
                vm_sha256={mode: sha(work / (mode + '-vm')) for mode in COMMITS},
                raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
                commands_sha256=sha(work / 'commands.json'), performance_measurement=False)
            write(work / 'build-summary.json', summary)
            retained, _ = installed_tools(CONTROL)
            old = json.loads((retained / 'ready.json').read_text())
            composed = {}
            with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
                acquire_lock(publication, 45)
                for mode in COMMITS:
                    binaries = {**old, 'rust-interp-vm': summary['vm_sha256'][mode]}
                    composition = dict(kind='workspace-tested-runtime-composition', schema_version=1,
                        exporter_wrapper_source_key=CONTROL, runtime_source_mode=mode,
                        runtime_source_manifest=str((work / 'plan.json').relative_to(ROOT)),
                        runtime_source_manifest_sha256=sha(work / 'plan.json'), binaries=binaries)
                    key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                    destination = ROOT / '.work/interpreter-tools' / key
                    destination.mkdir(exist_ok=False)
                    for name in binaries:
                        shutil.copy2(work / (mode + '-vm') if name == 'rust-interp-vm' else retained / name, destination / name)
                        require(sha(destination / name) == binaries[name], 'installed binary mismatch')
                    caps = json.loads((retained / 'capabilities.json').read_text())
                    caps.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
                    write(destination / 'capabilities.json', caps)
                    write(destination / 'source.json', dict(tool_key=key, composition=composition,
                        qualification=str((work / 'build-summary.json').relative_to(ROOT)),
                        qualification_sha256=sha(work / 'build-summary.json'),
                        key_algorithm='SHA256 canonical sorted compact composition JSON'))
                    write(destination / 'ready.json', binaries)
                    installed_tools(key)
                    composed[mode] = dict(tool_key=key, binaries=binaries)
            write(work / 'installed-tools.json', composed)
            out = ROOT / 'results' / args.run_id
            out.mkdir(exist_ok=False)
            # Per-file manifests remain in the immutable local plan.
            summary.pop('manifests')
            summary.update(installed_tools=composed, installed_tools_sha256=sha(work / 'installed-tools.json'),
                scope='Workspace tests and VM build only; broad runtime and performance integration gates pending.')
            write(out / 'summary.json', summary)
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work / 'status.json', status)
            print(json.dumps(dict(status='passed', tests=tests, tools=composed)), flush=True)
        except BaseException as error:
            status.update(status='failed', error=repr(error), finished_at=time.time())
            write(work / 'status.json', status)
            raise


if __name__ == '__main__':
    main()
