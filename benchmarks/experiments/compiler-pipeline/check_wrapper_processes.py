#!/usr/bin/env python3
"""Check the installed wrapper's exec routing, descriptors and manifest integrity."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import interpreter
from workflow_io import require_space, write_json


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--workspace-root', type=Path, help='existing owning workspace for installed tools, lock and receipts')
    parser.add_argument('--host-mir-candidate', action='store_true', help='also verify host-only library MIR omission')
    args = parser.parse_args()
    if args.workspace_root is not None:
        ROOT = args.workspace_root.resolve(strict=True)
        require((ROOT / '.work/benchmark.lock').is_file(), 'owning workspace has no benchmark lock')
        interpreter.ROOT = ROOT
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    require_space(ROOT / '.work', 8)
    tools, key = interpreter.installed_tools(args.tool_key)
    manifest = json.loads((tools / 'ready.json').read_text())
    require(set(manifest) == set(interpreter.CURRENT_TOOL_BINARIES), 'new wrapper build required')
    raw = ROOT / '.work/runs' / args.run_id
    out = ROOT / 'results' / args.run_id
    require(not raw.exists() and not out.exists(), 'run already exists')
    raw.mkdir()
    local = raw / 'tools with spaces'
    local.mkdir()
    wrapper = local / 'rust-interp-rustc-wrapper'
    shutil.copy2(tools / wrapper.name, wrapper)
    require(sha(wrapper) == manifest[wrapper.name], 'wrapper copy differs')
    fake = '''import json, os, pathlib, sys
read_fd, write_fd = map(int, os.environ['WRAPPER_TEST_FDS'].split(','))
token = os.read(read_fd, 1)
os.write(write_fd, token)
print(json.dumps(dict(kind=pathlib.Path(__file__).name, args=sys.argv[1:],
    cwd=os.getcwd(), pid=os.getpid(), parent_pid=os.getppid(), token=token.hex(),
    makeflags=os.environ['CARGO_MAKEFLAGS'], marker=os.environ['WRAPPER_TEST_MARKER'])))
sys.exit(int(os.environ.get('WRAPPER_TEST_EXIT', '0')))
'''
    for name in ['rustc', 'rust-interp-mir-export']:
        path = local / name
        path.write_text('#!' + sys.executable + '\n' + fake)
        path.chmod(0o755)
    rows = []
    source_paths = [Path(__file__), Path(interpreter.__file__), ROOT / 'scripts/workflow_io.py']
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}

    def run(label, command, env, pass_fds=()):
        child = subprocess.Popen(command, cwd=raw, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, pass_fds=pass_fds)
        receipt = dict(label=label, command=command, pid=child.pid, parent_pid=os.getpid(),
            cwd=str(raw), started_at=time.time(), status='running')
        try:
            write_json(raw / 'active-command.json', receipt)
        finally:
            stdout, stderr = child.communicate()
        receipt.update(status='finished', returncode=child.returncode, stdout=stdout,
                       stderr=stderr, finished_at=time.time())
        rows.append(receipt)
        write_json(raw / 'active-command.json', receipt)
        write_json(raw / 'records.json', rows)
        return receipt

    base = {k: v for k, v in os.environ.items() if not k.startswith('RUST_INTERP_')}
    dylibs = run('linked-libraries', ['otool', '-L', str(wrapper)], base)
    require(dylibs['returncode'] == 0 and 'rustc_driver' not in dylibs['stdout'], 'wrapper loads rustc_driver')
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b'x')
        base.update(WRAPPER_TEST_FDS=f'{read_fd},{write_fd}',
            CARGO_MAKEFLAGS=f'--jobserver-auth={read_fd},{write_fd} -j', WRAPPER_TEST_MARKER='unchanged value')
        selected = dict(RUST_INTERP_EXPORT_PACKAGE='example', CARGO_PKG_NAME='example',
            CARGO_PRIMARY_PACKAGE='1', RUST_INTERP_EXPORT_MANIFEST=str(raw), CARGO_MANIFEST_DIR=str(raw))
        std = dict(RUST_INTERP_STD_SYSROOT='/MIR sysroot', RUST_INTERP_STD_TARGET='aarch64-apple-darwin')
        prefix = [str(local / 'rustc'), '--crate-name', 'example']
        lib = ['--crate-type', 'lib', '--emit=metadata']

        def probe(label, flags, env_changes, export=False, expected_flags=None, code=0):
            env = dict(base, **env_changes)
            result = run(label, [str(wrapper), *prefix, *flags], env, (read_fd, write_fd))
            require(result['returncode'] == code and not result['stderr'], 'unexpected probe exit: ' + label)
            observed = json.loads(result['stdout'])
            expected = [*prefix, *flags] if export else [*prefix[1:], *(flags if expected_flags is None else expected_flags)]
            require(observed['args'] == expected and observed['kind'] == ('rust-interp-mir-export' if export else 'rustc'), 'incorrect route/argv: ' + label)
            require(observed['pid'] == result['pid'] and observed['parent_pid'] == os.getpid(), 'wrapper spawned instead of exec: ' + label)
            require(observed['cwd'] == str(raw) and observed['token'] == '78' and
                observed['marker'] == base['WRAPPER_TEST_MARKER'] and observed['makeflags'] == base['CARGO_MAKEFLAGS'], 'cwd/environment/jobserver changed: ' + label)

        probe('ordinary-query', ['-vV'], {})
        probe('ordinary-library', lib, {}, expected_flags=[*lib, '-Zalways-encode-mir=yes'])
        probe('host-build-script', ['--crate-type', 'bin'], dict(selected, **std))
        probe('host-proc-macro', ['--crate-type', 'proc-macro', '--sysroot', '/host'], dict(selected, **std))
        probe('selected-library-original-argv', [*lib, '--target=aarch64-apple-darwin'], dict(selected, **std), export=True)
        probe('selected-test', ['--test'], dict(selected, RUST_INTERP_EXPORT_TEST='1'), export=True)
        probe('selected-custom-harness', ['--cfg', 'test'], dict(selected, RUST_INTERP_EXPORT_TEST='1'), export=True)
        flags = [*lib, '--target=aarch64-apple-darwin', '-Zalways-encode-mir=no']
        probe('unselected-target-sysroot', flags, dict(selected, **std, CARGO_PKG_NAME='dependency'),
            expected_flags=[*flags, '--sysroot', '/MIR sysroot', '-Zalways-encode-mir=yes'])
        probe('different-manifest', lib, dict(selected, CARGO_MANIFEST_DIR='/different'), expected_flags=[*lib, '-Zalways-encode-mir=yes'])
        if args.host_mir_candidate:
            host = dict(selected, **std, CARGO_PKG_NAME='dependency')
            probe('host-library-no-forced-mir', lib, host, expected_flags=lib)
            for value in ['yes', 'no']:
                flags = [*lib, '-Zalways-encode-mir='+value, '--sysroot', '/host']
                probe('host-library-explicit-mir-'+value, flags, host, expected_flags=flags)
            probe('selected-host-library-original-argv', lib, dict(selected, **std), export=True)
        probe('ordinary-nonzero-exit', ['-vV'], dict(WRAPPER_TEST_EXIT='23'), code=23)
        for label, flags, changes, fragment in [
            ('target-conflict', ['--target=other'], std, 'target does not match'),
            ('sysroot-conflict', ['--target=aarch64-apple-darwin', '--sysroot=/other'], std, 'conflicts'),
        ]:
            result = run(label, [str(wrapper), *prefix, *flags], dict(base, **changes), (read_fd, write_fd))
            require(result['returncode'] == 2 and not result['stdout'] and fragment in result['stderr'], 'conflict failed to stop execution')
        for label, command, env, code in [
            ('missing-compiler', [str(wrapper), str(raw / 'absent/rustc'), '-vV'], base, 127),
            ('missing-wrapper-argument', [str(wrapper)], base, 2),
        ]:
            result = run(label, command, env, (read_fd, write_fd))
            require(result['returncode'] == code and not result['stdout'], 'invalid invocation was executed')
    finally:
        os.close(read_fd)
        os.close(write_fd)

    # Isolate malformed manifests under a fake ROOT; never alter installed tools.
    fake_root = raw / 'manifest-fixture'
    fake_key = 'a' * 64
    directory = fake_root / '.work/interpreter-tools' / fake_key
    directory.mkdir(parents=True)
    valid = {}
    for name in interpreter.CURRENT_TOOL_BINARIES:
        (directory / name).write_bytes(name.encode())
        valid[name] = sha(directory / name)
    checks = []
    previous_root = interpreter.ROOT
    try:
        interpreter.ROOT = fake_root
        for label, value, good in [
            ('legacy-pair', {k: valid[k] for k in interpreter.LEGACY_TOOL_BINARIES}, True),
            ('new-triple', valid, True),
            ('unknown-extra', dict(valid, unknown='0' * 64), False),
            ('missing-vm', {k: v for k, v in valid.items() if k != 'rust-interp-vm'}, False),
            ('changed-wrapper-digest', dict(valid, **{'rust-interp-rustc-wrapper': '0' * 64}), False),
        ]:
            write_json(directory / 'ready.json', value)
            try:
                interpreter.installed_tools(fake_key)
                accepted = True
            except RuntimeError:
                accepted = False
            require(accepted == good, 'manifest validation differs: ' + label)
            checks.append(dict(label=label, accepted=accepted))
    finally:
        interpreter.ROOT = previous_root
    interpreter.installed_tools(key)
    require(all(sha(ROOT / p) == digest for p, digest in frozen.items()), 'driver source changed')
    out.mkdir()
    write_json(out / 'summary.json', dict(status='passed', tool_key=key, binaries=manifest,
        host_mir_candidate=args.host_mir_candidate,
        commands=len(rows), process_probe_commands=len(rows)-1, manifest_checks=checks,
        raw=str(raw.relative_to(ROOT)), frozen=frozen, dylibs=dylibs['stdout'],
        fake_compilers=True, real_guest_execution=False,
        note='Real exec/PID/argv/cwd/environment/pipe-descriptor and error checks use fake compiler endpoints. They supplement, not replace, real Cargo/strict-checking/stale-sidecar qualification. No signal is sent to any process.'))
    print(json.dumps(dict(commands=len(rows), manifest_checks=len(checks))))


if __name__ == '__main__':
    main()
