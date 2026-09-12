#!/usr/bin/env python3
"""Run a recorded Rust test check with frozen sources and the benchmark lock."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def prechecks(work, env, status, receipt):
    """Record formatting and the existing Python behavioral tests before Rust."""
    checks = []
    commands = [
        ('format', ['cargo', '+nightly-2026-09-08', 'fmt', '--all', '--', '--check']),
        ('python', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']),
    ]
    for name, command in commands:
        path = work / (name + '.log')
        with path.open('x') as output:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=subprocess.STDOUT)
            try:
                status.update(status='checking ' + name, child_pid=child.pid,
                              command=command, child_started_at=time.time())
                write(receipt, status)
            finally:
                code = child.wait()
        checks.append(dict(name=name, command=command, pid=child.pid, returncode=code,
                           log=str(path.relative_to(ROOT)), log_sha256=sha(path)))
        write(work / 'prechecks.json', checks)
        if code:
            raise RuntimeError(name + ' check failed; see ' + str(path))
    return checks


def install_tool(target, env, work, status, receipt, frozen):
    """Build after passing release tests and publish an immutable local tool."""
    command = ['cargo', '+nightly-2026-09-08', 'build', '--release', '--locked', '--offline',
        '--jobs', '2', '--target-dir', str(target), '-p', 'rust-interp-bytecode', '-p', 'rust-interp-mir-export']
    with (work / 'build.log').open('x') as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT)
        status.update(status='building release tool', child_pid=child.pid, command=command, child_started_at=time.time())
        write(receipt, status)
        code = child.wait()
    if code or any(sha(ROOT / p) != digest for p, digest in frozen.items()):
        raise RuntimeError('tool build failed or frozen source changed')
    paths = [ROOT / p for p in ['Cargo.toml', 'Cargo.lock']]
    for crate in ['bytecode', 'mir-export']:
        paths += sorted((ROOT / 'crates' / crate).rglob('*.rs'))
        paths.append(ROOT / 'crates' / crate / 'Cargo.toml')
    digest = hashlib.sha256()
    for p in paths:
        digest.update(str(p.relative_to(ROOT)).encode() + b'\0' + p.read_bytes())
    key = digest.hexdigest()
    directory = ROOT / '.work/interpreter-tools' / key
    from interpreter import CURRENT_TOOL_BINARIES
    binaries = {name: sha(target / 'release' / name) for name in CURRENT_TOOL_BINARIES}
    # Lock ordering matches the workflow driver: benchmark lock, then tool lock.
    with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
        fcntl.flock(publication, fcntl.LOCK_EX)
        if (directory / 'ready.json').exists():
            from interpreter import installed_tools
            installed_tools(key)
            if json.loads((directory / 'ready.json').read_text()) != binaries:
                raise RuntimeError('same source key produced different binaries; existing tool preserved')
        else:
            directory.mkdir(exist_ok=False)
            for name in binaries:
                shutil.copy2(target / 'release' / name, directory / name)
            probe = subprocess.run([str(directory / 'rust-interp-mir-export'), '--rust-interp-capabilities'],
                env=env, capture_output=True, text=True, check=True, timeout=10)
            capabilities = json.loads(probe.stdout)
            if capabilities.get('schema_version') != 1:
                raise RuntimeError('unknown exporter capability schema')
            capabilities.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
            write(directory / 'capabilities.json', capabilities)
            plan = json.loads((work / 'plan.json').read_text())
            compiler = subprocess.run(['rustc', '+nightly-2026-09-08', '-vV'], env=env,
                capture_output=True, text=True, check=True, timeout=10).stdout
            write(directory / 'source.json', dict(tool_key=key, source_commit=plan['source_commit'],
                files={str(p.relative_to(ROOT)): sha(p) for p in paths},
                source_archive=plan['source_archive'], toolchain='nightly-2026-09-08',
                compiler=compiler,
                target='aarch64-apple-darwin', test_plan_sha256=sha(work / 'plan.json'),
                key_algorithm='legacy source-only SHA256 with pathlib path ordering; compiler identity recorded separately'))
            write(directory / 'ready.json', binaries)
    return dict(tool_key=key, binaries=binaries, build_log=str((work / 'build.log').relative_to(ROOT)),
                build_log_sha256=sha(work / 'build.log'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--package', action='append')
    parser.add_argument('--release', action='store_true')
    parser.add_argument('--install-tool', action='store_true', help='publish a release tool after successful full-workspace release tests')
    parser.add_argument('--wait-for-lock', type=int, default=600)
    args = parser.parse_args()
    if args.install_tool and (not args.release or args.package):
        parser.error('--install-tool requires --release and the full workspace')
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('run-id must be a directory name')
    if not 0 <= args.wait_for_lock <= 3600:
        parser.error('wait-for-lock must be 0..3600')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    target = ROOT / '.work/diagnostic-builds' / args.run_id
    if target.exists():
        raise RuntimeError('test target already exists')
    receipt = work / 'status.json'
    status = dict(owner=str(ROOT), status='waiting for benchmark lock',
                  pid=os.getpid(), parent_pid=os.getppid(), cwd=str(ROOT), started_at=time.time())
    write(receipt, status)
    lock = (ROOT / '.work/benchmark.lock').open('a')
    deadline = time.monotonic() + args.wait_for_lock
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                status.update(status='failed', error='benchmark lock wait expired', finished_at=time.time())
                write(receipt, status)
                raise
            time.sleep(1)
    paths = [ROOT / p for p in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'rustfmt.toml']]
    paths += sorted((ROOT / 'scripts').glob('*.py'))
    paths += sorted((ROOT / 'tests').glob('test_*.py'))
    paths += [p for p in (ROOT / 'crates').rglob('*') if p.is_file() and
              (p.suffix == '.rs' or p.name == 'Cargo.toml')]
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    archive = work / 'source'
    for path in paths:
        destination = archive / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    command = ['cargo', '+nightly-2026-09-08', 'test', '--locked', '--offline', '--jobs', '2',
               '--target-dir', str(target)]
    command += [arg for package in args.package for arg in ['--package', package]] if args.package else ['--workspace']
    if args.release:
        command.append('--release')
    write(work / 'plan.json', dict(owner=str(ROOT), command=command, frozen=frozen,
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        source_archive=str(archive.relative_to(ROOT)), target=str(target.relative_to(ROOT)), performance_measurement=False))
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']:
            env.pop(name)
    env['CARGO_TERM_COLOR'] = 'never'
    log = work / 'test.log'
    try:
        checks = prechecks(work, env, status, receipt)
        with log.open('x') as output:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=subprocess.STDOUT)
            status.update(status='running', child_pid=child.pid, command=command, child_started_at=time.time())
            write(receipt, status)
            print('START', child.pid, flush=True)
            code = child.wait()
        unchanged = all(sha(ROOT / p) == digest for p, digest in frozen.items())
        tests = []
        label = None
        for line in log.read_text().splitlines():
            if line.strip().startswith(('Running ', 'Doc-tests ')):
                label = line.strip()
            match = re.search(r'test result: .*? (\d+) passed; (\d+) failed; (\d+) ignored;', line)
            if match:
                tests.append(dict(target=label, passed=int(match[1]), failed=int(match[2]), ignored=int(match[3])))
        passed = sum(t['passed'] for t in tests)
        success = code == 0 and unchanged and passed > 0 and not any(t['failed'] for t in tests)
        summary = dict(status='passed' if success else 'failed', command=command, returncode=code,
            prechecks=checks,
            frozen_sources_unchanged=unchanged, source_manifest_sha256=sha(work / 'plan.json'),
            workspace_passed=passed, workspace_ignored=sum(t['ignored'] for t in tests), tests=tests,
            raw_log=str(log.relative_to(ROOT)), raw_log_sha256=sha(log),
            source_archive=str(archive.relative_to(ROOT)), frozen=frozen, performance_measurement=False)
        write(work / 'test-summary.json', summary)
        if success and args.install_tool:
            summary['installed_tool'] = install_tool(target, env, work, status, receipt, frozen)
        output = ROOT / 'results' / args.run_id
        output.mkdir(exist_ok=False)
        write(output / 'summary.json', summary)
        status.update(status='finished' if success else 'failed', returncode=code,
                      finished_at=time.time(), report=str(output.relative_to(ROOT)))
        write(receipt, status)
        print(json.dumps(dict(success=success, passed=passed, returncode=code, unchanged=unchanged)), flush=True)
        if not success:
            raise SystemExit(1)
    except Exception as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(receipt, status)
        raise


if __name__ == '__main__':
    main()
