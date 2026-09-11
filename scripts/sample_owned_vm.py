#!/usr/bin/env python3
"""Sample fresh, explicitly owned macOS VM executions; never report latency."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from interpreter import ROOT, installed_tools


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--artifact-sha256', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--duration', type=int, default=3)
    parser.add_argument('--instruction-limit', type=int, default=100_000_000_000)
    parser.add_argument('--allocation-limit', type=int, default=150_000)
    parser.add_argument('--jit-native-calls', action='store_true')
    parser.add_argument('--jit-native-call-stubs', action='store_true')
    args = parser.parse_args()
    if args.jit_native_call_stubs and not args.jit_native_calls:
        parser.error('--jit-native-call-stubs requires --jit-native-calls')
    if sys.platform != 'darwin':
        parser.error('this diagnostic requires macOS sample and vmmap')
    if Path(args.run_id).name != args.run_id or args.run_id in ('.', '..'):
        parser.error('run-id must be one directory name')
    if not 1 <= args.repetitions <= 10 or not 1 <= args.duration <= 30:
        parser.error('use 1..10 repetitions and 1..30 seconds per sample')
    if not 1 <= args.instruction_limit < 2**64 or not 0 <= args.allocation_limit <= 1_000_000:
        parser.error('invalid instruction or allocation limit')
    artifact = args.artifact.resolve()
    if digest(artifact) != args.artifact_sha256:
        parser.error('artifact hash does not match')
    (ROOT / '.work').mkdir(exist_ok=True)
    guard = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
    tool, key = installed_tools(args.tool_key)
    vm = tool / 'rust-interp-vm'
    vm_hash = digest(vm)
    paths = [ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', Path(__file__).resolve(), ROOT / 'scripts/interpreter.py']
    for crate in ['bytecode', 'mir-export']:
        paths += sorted((ROOT / 'crates' / crate).rglob('*.rs'))
        paths.append(ROOT / 'crates' / crate / 'Cargo.toml')
    frozen = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    work = ROOT / '.work' / args.run_id
    work.mkdir()
    write(work / 'plan.json', dict(tool_key=key, vm_sha256=vm_hash,
        artifact=str(artifact), artifact_sha256=args.artifact_sha256,
        source_files=frozen, repetitions=args.repetitions, sample_seconds=args.duration,
        instruction_limit=args.instruction_limit, allocation_limit=args.allocation_limit,
        jit_native_calls=args.jit_native_calls, jit_native_call_stubs=args.jit_native_call_stubs,
        performance_measurement=False))
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_')):
            env.pop(name)
    env['RUST_INTERP_VM_STATS'] = '1'

    def verify():
        if digest(vm) != vm_hash or digest(artifact) != args.artifact_sha256:
            raise RuntimeError('sampled binary or artifact changed')
        if any(digest(ROOT / p) != h for p, h in frozen.items()):
            raise RuntimeError('frozen diagnostic source changed')

    results = []
    for index in range(args.repetitions):
        verify()
        run = work / str(index); run.mkdir()
        command = [str(vm), '--engine', 'jit', '--instruction-limit', str(args.instruction_limit),
                   '--allocation-limit', str(args.allocation_limit)]
        if args.jit_native_calls:
            command.append('--jit-native-calls')
        if args.jit_native_call_stubs:
            command.append('--jit-native-call-stubs')
        command.append(str(artifact))
        with (run / 'vm.stdout').open('x') as stdout, (run / 'vm.stderr').open('x') as stderr:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
            identity = dict(pid=child.pid, parent_pid=os.getpid(), command=command, cwd=str(ROOT),
                            started_at=time.time(), status='running')
            write(run / 'active-vm.json', identity)
            records = []

            def diagnostic(label, argv):
                process = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                record = dict(pid=process.pid, parent_pid=os.getpid(), command=argv, cwd=str(ROOT),
                              started_at=time.time(), status='running')
                write(run / 'active-diagnostic.json', record)
                output, errors = process.communicate()
                record.update(status='finished', returncode=process.returncode, finished_at=time.time())
                (run / (label + '.stdout')).write_text(output)
                (run / (label + '.stderr')).write_text(errors)
                records.append(record)
                write(run / 'commands.json', records)
                write(run / 'active-diagnostic.json', record)
                return process.returncode, output

            mapped, sample_code = False, None
            try:
                if child.poll() is not None:
                    raise RuntimeError('owned VM exited before identity check')
                code, ps = diagnostic('identity', ['ps', '-p', str(child.pid), '-o', 'pid=,ppid=,lstart=,tty=,command='])
                columns = ps.split()
                if code != 0 or columns[:2] != [str(child.pid), str(os.getpid())] or str(vm) not in ps:
                    raise RuntimeError('owned VM identity check failed')
                identity['process_identity'] = ps
                write(run / 'active-vm.json', identity)
                code, cwd = diagnostic('cwd', ['/usr/sbin/lsof', '-a', '-p', str(child.pid), '-d', 'cwd', '-Fn'])
                if code != 0 or 'n' + str(ROOT) not in cwd.splitlines() or child.poll() is not None:
                    raise RuntimeError('owned VM working directory/liveness check failed')
                for attempt in range(8):
                    if child.poll() is not None:
                        break
                    code, mapping = diagnostic('vmmap-' + str(attempt), ['/usr/bin/vmmap', str(child.pid)])
                    if code == 0 and re.search(r'^VM_ALLOCATE\s+[0-9a-f]+-[0-9a-f]+.*?rwx/rwx', mapping, re.M):
                        (run / 'vmmap.stdout').write_text(mapping)
                        mapped = True
                        break
                if mapped and child.poll() is None:
                    print('SAMPLE', index, 'owned PID', child.pid, flush=True)
                    sample_code, _ = diagnostic('sample', ['/usr/bin/sample', str(child.pid), str(args.duration),
                        '1', '-mayDie', '-file', str(run / 'sample.txt')])
                else:
                    (run / 'mapping-failure.txt').write_text('No live arena captured; no sample attempted.\n')
            finally:
                # Let this bounded guest execution finish naturally even when
                # inspection fails. No signal or process-name lookup is used.
                code = child.wait()
                identity.update(status='finished', returncode=code, finished_at=time.time())
                write(run / 'active-vm.json', identity)
        verify()
        if code != 0 or (run / 'vm.stdout').read_text().strip() != '0':
            raise RuntimeError('sampled original test execution failed')
        stats = {name: int(value) for name, value in re.findall(
            r'\b([a-z_]+)=(\d+)\b', (run / 'vm.stderr').read_text())}
        if stats['jit_declined_functions'] != 0 or stats['instructions'] <= 0:
            raise RuntimeError('unexpected JIT decline or empty execution')
        if args.jit_native_call_stubs and stats.get('jit_stub_calls', 0) == 0:
            raise RuntimeError('native Call stubs did not execute')
        record = dict(index=index, identity=identity, mapped=mapped, sample_returncode=sample_code,
                      performance_measurement=False, statistics=stats,
                      files={p.name: digest(p) for p in run.iterdir() if p.is_file()})
        write(run / 'record.json', record)
        results.append(record)
        write(work / 'records.json', results)
    verify()
    write(work / 'summary.json', dict(status='Owned diagnostic executions complete', tool_key=key,
        vm_sha256=vm_hash, artifact_sha256=args.artifact_sha256, records=results,
        source_unchanged=True, performance_measurement=False))
    print(json.dumps(dict(work=str(work), executions=len(results), mapped=sum(r['mapped'] for r in results))), flush=True)


if __name__ == '__main__':
    main()
