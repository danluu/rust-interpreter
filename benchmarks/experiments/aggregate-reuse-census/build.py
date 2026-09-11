#!/usr/bin/env python3
"""Build a recorded isolated array-reuse observer with an unchanged parent VM."""
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
EXPERIMENT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import installed_tools
from tool_source_index import index
from verify_repeated_workflow import require


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def environment():
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']:
            env.pop(name)
    env['CARGO_TERM_COLOR'] = 'never'
    return env


def replace_once(path, old, new):
    value = path.read_text()
    require(value.count(old) == 1, 'diagnostic injection anchor changed: ' + str(path))
    path.write_text(value.replace(old, new))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--source-commit', default='d664bce')
    parser.add_argument('--parent-tool-key', default='e89de7f81c1122738e23e317a7f674b7742c0f550c2956ae548ce35e50530a6a')
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ('.', '..'), 'invalid run ID')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    status = dict(owner=str(ROOT), status='waiting for benchmark lock', pid=os.getpid(),
        parent_pid=os.getppid(), cwd=str(ROOT), started_at=time.time())
    receipt = work / 'status.json'
    write(receipt, status)
    lock = (ROOT / '.work/benchmark.lock').open('a')
    deadline = time.monotonic() + 600
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                status.update(status='failed', error='benchmark lock unavailable', finished_at=time.time())
                write(receipt, status)
                raise
            time.sleep(1)
    try:
        parent = index(args.source_commit)
        require(parent['tool_key'] == args.parent_tool_key, 'parent source/tool mismatch')
        parent_directory, _ = installed_tools(args.parent_tool_key)
        paths = [ROOT / p for p in parent['files']]
        paths += [Path(__file__), EXPERIMENT / 'observe.rs', EXPERIMENT / 'PLAN.md',
                  ROOT / 'scripts/interpreter.py', ROOT / 'scripts/tool_source_index.py']
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        require(all(frozen[p] == h for p, h in parent['files'].items()), 'production sources differ from parent')
        require(shutil.disk_usage(ROOT).free > 20 * 1024**3, 'insufficient disk headroom')
        source = work / 'tool-source'
        source.mkdir()
        archive = subprocess.check_output(['git', 'archive', parent['commit'],
            'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'crates', 'scripts/interpreter.py'], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar:
                path = Path(member.name)
                require(not path.is_absolute() and '..' not in path.parts, 'invalid archive path')
                if member.isfile():
                    output = source / path
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(tar.extractfile(member).read())
                else:
                    require(member.isdir(), 'unexpected non-file archive entry')
        frame = source / 'crates/mir-export/src/lower/scalar_frame.rs'
        old_signature = 'fn plan(shapes: &[(usize, usize)], mut eligible: Vec<bool>, mut events: Vec<Vec<Event>>, successors: &[Vec<usize>]) -> Option<(Vec<Slot>, usize)> {'
        wrapper = '''fn plan(shapes: &[(usize, usize)], eligible: Vec<bool>, events: Vec<Vec<Event>>, successors: &[Vec<usize>]) -> Option<(Vec<Slot>, usize)> {
    plan_with_eligibility(shapes, eligible, events, successors, None)
}
fn plan_with_eligibility(shapes: &[(usize, usize)], mut eligible: Vec<bool>, mut events: Vec<Vec<Event>>, successors: &[Vec<usize>], eligibility: Option<&mut Vec<bool>>) -> Option<(Vec<Slot>, usize)> {'''
        replace_once(frame, old_signature, wrapper)
        replace_once(frame, '    Some((slots, end))',
            '    if let Some(output) = eligibility { *output = eligible; }\n    Some((slots, end))')
        with frame.open('a') as output:
            output.write('''
#[path = "aggregate_reuse.rs"]
mod aggregate_reuse;
pub(super) fn observe_aggregate_reuse(lower: &Lower<'_, '_>) { aggregate_reuse::observe(lower); }
''')
        replace_once(source / 'crates/mir-export/src/lower.rs', '        scalar_frame::pack(&mut this)?;',
            '        scalar_frame::pack(&mut this)?;\n        scalar_frame::observe_aggregate_reuse(&this);')
        shutil.copy2(EXPERIMENT / 'observe.rs', source / 'crates/mir-export/src/lower/aggregate_reuse.rs')
        inputs = [source / p for p in ['Cargo.toml', 'Cargo.lock']]
        for crate in ['bytecode', 'mir-export']:
            inputs += sorted((source / 'crates' / crate).rglob('*.rs'))
            inputs.append(source / 'crates' / crate / 'Cargo.toml')
        fingerprint = hashlib.sha256()
        for path in inputs:
            fingerprint.update(str(path.relative_to(source)).encode() + b'\0' + path.read_bytes())
        key = fingerprint.hexdigest()
        copied = {str(p.relative_to(source)): sha(p) for p in inputs + [source / 'scripts/interpreter.py']}
        write(work / 'provenance.json', dict(parent_source_commit=parent['commit'], parent_tool_key=parent['tool_key'],
            source_key=key, source=str(source.relative_to(ROOT)), root_frozen=frozen, copied_inputs=copied,
            recipe_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            diagnostic_only=True, vm_copied_from_parent=True))

        def verify():
            require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'frozen root source changed')
            require(all(sha(source / p) == h for p, h in copied.items()), 'copied source changed')
            require(sha(parent_directory / 'rust-interp-vm') == parent['binaries']['rust-interp-vm'], 'parent VM changed')

        target = ROOT / '.work/diagnostic-builds' / args.run_id
        require(not target.exists(), 'target already exists')
        env = environment()
        records = []
        for label, action in [('exporter-tests', 'test'), ('build', 'build')]:
            verify()
            command = ['cargo', '+nightly-2026-09-08', action, '--release', '--locked', '--offline',
                '--jobs', '2', '--manifest-path', str(source / 'Cargo.toml'), '--target-dir', str(target),
                '-p', 'rust-interp-mir-export']
            with (work / (label + '.log')).open('x') as log:
                child = subprocess.Popen(command, cwd=source, env=env, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT)
                status.update(status='running', label=label, child_pid=child.pid,
                    command=command, child_cwd=str(source), child_started_at=time.time())
                write(receipt, status)
                code = child.wait()
            records.append(dict(command=command, pid=child.pid, parent_pid=os.getpid(), cwd=str(source),
                returncode=code, started_at=status['child_started_at'], finished_at=time.time(), log_sha256=sha(work / (label + '.log'))))
            write(work / 'commands.json', records)
            require(code == 0, label + ' failed')
        tests = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;', (work / 'exporter-tests.log').read_text())
        require(sum(int(n) for n, _ in tests) == 15 and all(f == '0' for _, f in tests), 'missing exporter/observer tests')
        verify()
        binaries = {'rust-interp-vm': parent['binaries']['rust-interp-vm'],
            'rust-interp-mir-export': sha(target / 'release/rust-interp-mir-export')}
        directory = ROOT / '.work/interpreter-tools' / key
        with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
            fcntl.flock(publication, fcntl.LOCK_EX)
            directory.mkdir(exist_ok=False)
            shutil.copy2(parent_directory / 'rust-interp-vm', directory / 'rust-interp-vm')
            shutil.copy2(target / 'release/rust-interp-mir-export', directory / 'rust-interp-mir-export')
            probe = subprocess.run([str(directory / 'rust-interp-mir-export'), '--rust-interp-capabilities'],
                env=env, capture_output=True, text=True, check=True, timeout=10)
            capability = json.loads(probe.stdout)
            require(capability['schema_version'] == 1, 'unexpected capability schema')
            capability.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
            write(directory / 'capabilities.json', capability)
            compiler = subprocess.check_output(['rustc', '+nightly-2026-09-08', '-vV'], env=env, text=True)
            write(directory / 'source.json', dict(tool_key=key, parent_source_commit=parent['commit'],
                parent_tool_key=parent['tool_key'], vm_copied_from_parent=True, compiler=compiler,
                source=str(source.relative_to(ROOT)), files=copied, provenance_sha256=sha(work / 'provenance.json')))
            require(all(sha(directory / name) == h for name, h in binaries.items()), 'published binary mismatch')
            write(directory / 'ready.json', binaries)
        verify()
        report = dict(status='passed', tool_key=key, parent_tool_key=parent['tool_key'], binaries=binaries,
            exporter_tests=15, source=str(source.relative_to(ROOT)), target=str(target.relative_to(ROOT)),
            root_unchanged=True, performance_measurement=False, artifact_qualification_pending=True,
            provenance=str((work / 'provenance.json').relative_to(ROOT)), provenance_sha256=sha(work / 'provenance.json'),
            commands=records)
        write(work / 'summary.json', report)
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', report)
        status.update(status='finished', returncode=0, finished_at=time.time())
        write(receipt, status)
        print(json.dumps(dict(tool_key=key, binaries=binaries, exporter_tests=15)), flush=True)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(receipt, status)
        raise


if __name__ == '__main__':
    main()
