#!/opt/homebrew/bin/python3 -B
"""Capture actual compiler stderr; profile only the selected Ruff test compilation."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def main():
    original = sys.argv[1:]
    if not original or Path(original[0]).stem != 'rustc':
        raise RuntimeError('expected Cargo wrapper arguments beginning with rustc')
    directory = Path(os.environ['STRICT_WARM_PROFILE_UNITS']) / str(os.getpid())
    directory.mkdir()
    started = time.time_ns()
    # Cargo probes can have a crate name and stdin input, but real compilation
    # units have an emission request. Do not instrument informational probes.
    compilation = any(a == '--emit' or a.startswith('--emit=') for a in original[1:])
    requested = os.environ.get('STRICT_WARM_PROFILE_MODE',
        'passes' if os.environ.get('STRICT_WARM_PROFILE_PHASES') == '1' else 'off')
    if requested not in ('off', 'passes', 'self'):
        raise RuntimeError('unknown compiler profiling mode')
    selected = (compilation and os.environ.get('CARGO_PKG_NAME') == 'ruff_linter'
                and os.environ.get('CARGO_CRATE_NAME') == 'ruff_linter'
                and '--test' in original
                and '--target' in original
                and original[original.index('--target') + 1] == 'aarch64-apple-darwin')
    profiling = requested if selected else 'off'
    if any(a.startswith(('-Zself-profile', '-Ztime-passes')) for a in original):
        raise RuntimeError('profiling flags must be inserted only by the reviewed wrapper')
    flags = (['-Ztime-passes', '-Ztime-passes-format=json'] if profiling == 'passes' else
             ['-Zself-profile=' + str(directory / 'self-profile'),
              '-Zself-profile-events=default'] if profiling == 'self' else [])
    command = [os.environ['STRICT_WARM_PROFILE_REAL_WRAPPER'], original[0],
               *flags, *original[1:]]
    environment = os.environ.copy()
    # Only selected exports write this capture. It records final routed args,
    # including sysroot and guest MIR settings, in addition to the Cargo args.
    environment['RUST_INTERP_CAPTURE'] = str(directory / 'exporter-args.json')
    allowed = {'OUT_DIR', 'CARGO_MANIFEST_DIR', 'CARGO_MANIFEST_PATH',
               'CARGO_CRATE_NAME', 'CARGO_PRIMARY_PACKAGE', 'CARGO_BIN_NAME',
               'CARGO_MAKEFLAGS', 'MAKEFLAGS', 'NUM_JOBS', 'RUSTFLAGS',
               'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
               'RUSTC_WORKSPACE_WRAPPER', 'CARGO_TARGET_DIR'}
    captured_env = {k: v for k, v in environment.items() if k in allowed or
                    k.startswith(('CARGO_PKG_', 'CARGO_FEATURE_', 'CARGO_CFG_', 'RUST_INTERP_'))}
    record = dict(schema_version=1, wrapper_pid=os.getpid(), parent_pid=os.getppid(),
                  cwd=os.getcwd(), start_unix_ns=started, original_args=original,
                  forwarded_command=command, environment=captured_env,
                  compilation=compilation, selected=selected, profiling=profiling, diagnostic_flags=flags,
                  inherited_fds_preserved=True, status='starting')
    path = directory / 'invocation.json'
    write_json(path, record)
    before = time.perf_counter()
    # Cargo's inherited jobserver descriptors must reach rustc unchanged.
    # stdout also goes straight to Cargo; JSON artifact messages are untouched.
    overflow = False
    recorded_bytes = 0
    with (directory / 'stderr.log').open('xb') as log:
        process = subprocess.Popen(command, env=environment, stderr=subprocess.PIPE,
                                   close_fds=False)
        try:
            record.update(child_pid=process.pid, child_parent_pid=os.getpid(), status='running')
            write_json(path, record)
            while True:
                chunk = process.stderr.read1(65536)
                if not chunk:
                    break
                recorded_bytes += len(chunk)
                if recorded_bytes <= 64 * 1024 * 1024:
                    log.write(chunk)
                    log.flush()
                else:
                    overflow = True
                sys.stderr.buffer.write(chunk)
                sys.stderr.buffer.flush()
        finally:
            # Finish only this wrapper's child before publishing completion.
            # No process is stopped or signalled to make the host idle.
            try:
                # A failed receipt/log/relay write must not leave a child
                # blocked on its full stderr pipe while we wait for it.
                while process.stderr.read1(65536):
                    pass
            finally:
                code = process.wait()
            record.update(returncode=code, elapsed_seconds=time.perf_counter()-before,
                          finish_unix_ns=time.time_ns(), status='finished', stderr_overflow=overflow)
            write_json(path, record)
    if overflow:
        raise RuntimeError('compiler stderr exceeds the retained 64 MiB bound')
    if code < 0:
        # Preserve termination by a signal rather than returning a different
        # ordinary exit status to Cargo. This signals only the current wrapper.
        if -code not in (signal.SIGKILL, signal.SIGSTOP):
            signal.signal(-code, signal.SIG_DFL)
        os.kill(os.getpid(), -code)
    return code


if __name__ == '__main__':
    sys.exit(main())
