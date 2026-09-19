#!/usr/bin/env python3
"""Sample fresh, explicitly owned macOS VM executions; never report latency."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from interpreter import ROOT, installed_tools
from compare_saved_runtime import acquire_lock, lock_wait_seconds
from vmmap_ranges import anonymous_executable_ranges


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
    parser.add_argument('--jit-persistent-registers', action='store_true')
    parser.add_argument('--jit-native-calls', action='store_true')
    parser.add_argument('--jit-native-call-stubs', action='store_true')
    parser.add_argument('--jit-resumable-calls', action='store_true')
    parser.add_argument('--jit-scalar-calls', action='store_true')
    parser.add_argument('--jit-indirect-calls', action='store_true')
    parser.add_argument('--dump-code', action='store_true', help='save emitted code from each sampled process after execution')
    parser.add_argument('--jit-operation-map', action='store_true', help='also reconstruct and verify per-operation spans after execution')
    parser.add_argument('--select-test', help='run one exact catalog test without instruction profiling')
    parser.add_argument('--suite-catalog', type=Path)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=0)
    parser.add_argument('--minimum-free-bytes', type=int, default=0)
    parser.add_argument('--expected-jit-declines', type=int, default=0,
                        help='exact predeclared declined-function count from qualified fallback behavior')
    args = parser.parse_args()
    if args.jit_scalar_calls and not args.jit_resumable_calls:
        parser.error('--jit-scalar-calls requires --jit-resumable-calls')
    if args.jit_indirect_calls and not args.jit_resumable_calls:
        parser.error('--jit-indirect-calls requires --jit-resumable-calls')
    if args.jit_resumable_calls and (args.jit_native_calls or args.jit_native_call_stubs):
        parser.error('--jit-resumable-calls cannot be combined with native tree/stub calls')
    if args.jit_native_call_stubs and not args.jit_native_calls:
        parser.error('--jit-native-call-stubs requires --jit-native-calls')
    if args.jit_operation_map and (not args.dump_code or args.jit_native_calls or args.jit_native_call_stubs):
        parser.error('--jit-operation-map requires --dump-code and ordinary/resumable execution')
    if sys.platform != 'darwin':
        parser.error('this diagnostic requires macOS sample and vmmap')
    if Path(args.run_id).name != args.run_id or args.run_id in ('.', '..'):
        parser.error('run-id must be one directory name')
    if not 1 <= args.repetitions <= 10 or not 1 <= args.duration <= 30:
        parser.error('use 1..10 repetitions and 1..30 seconds per sample')
    if not 1 <= args.instruction_limit < 2**64 or not 0 <= args.allocation_limit <= 1_000_000:
        parser.error('invalid instruction or allocation limit')
    if args.minimum_free_bytes < 0:
        parser.error('minimum free bytes must be nonnegative')
    if args.expected_jit_declines < 0:
        parser.error('expected JIT declines must be nonnegative')
    if (args.select_test is None) != (args.suite_catalog is None):
        parser.error('--select-test and --suite-catalog must be supplied together')
    artifact = args.artifact.resolve()
    if digest(artifact) != args.artifact_sha256:
        parser.error('artifact hash does not match')
    selection = None
    if args.select_test is not None:
        catalog = args.suite_catalog.resolve(strict=True)
        if not catalog.is_file() or catalog.stat().st_size > 8 * 1024 * 1024:
            parser.error('catalog is not a bounded regular file')
        contents = json.loads(catalog.read_text())
        entries = [entry for entry in contents['entries'] if entry['name'] == args.select_test]
        if contents['artifact_sha256'] != args.artifact_sha256 or len(entries) != 1:
            parser.error('test must belong to this exact artifact catalog')
        selection = dict(name=args.select_test, function=entries[0]['function'], catalog=str(catalog),
                         catalog_sha256=digest(catalog), artifact_sha256=args.artifact_sha256)
    (ROOT / '.work').mkdir(exist_ok=True)
    guard = (ROOT / '.work/benchmark.lock').open('a')
    acquire_lock(guard, args.lock_wait_seconds)
    tool, key = installed_tools(args.tool_key)
    vm = tool / 'rust-interp-vm'
    vm_hash = digest(vm)
    paths = [ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', Path(__file__).resolve(), ROOT / 'scripts/interpreter.py',
             ROOT / 'scripts/compare_saved_runtime.py', ROOT / 'scripts/vmmap_ranges.py']
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
        jit_persistent_registers=args.jit_persistent_registers, jit_native_calls=args.jit_native_calls, jit_native_call_stubs=args.jit_native_call_stubs,
        jit_resumable_calls=args.jit_resumable_calls,
        jit_scalar_calls=args.jit_scalar_calls,
        jit_indirect_calls=args.jit_indirect_calls,
        jit_operation_map=args.jit_operation_map,
        dump_code=args.dump_code, selection=selection,
        minimum_free_bytes=args.minimum_free_bytes,
        expected_jit_declines=args.expected_jit_declines,
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
        if selection and digest(Path(selection['catalog'])) != selection['catalog_sha256']:
            raise RuntimeError('selected test catalog changed')

    results = []
    for index in range(args.repetitions):
        verify()
        if shutil.disk_usage(ROOT).free < args.minimum_free_bytes:
            raise RuntimeError('disk floor; no new sample execution started')
        run = work / str(index); run.mkdir()
        command = [str(vm), '--engine', 'jit', '--instruction-limit', str(args.instruction_limit),
                   '--allocation-limit', str(args.allocation_limit)]
        if args.jit_persistent_registers:
            command.append('--jit-persistent-registers')
        if args.jit_native_calls:
            command.append('--jit-native-calls')
        if args.jit_native_call_stubs:
            command.append('--jit-native-call-stubs')
        if args.jit_resumable_calls:
            command.append('--jit-resumable-calls')
        if args.jit_scalar_calls:
            command.append('--jit-scalar-calls')
        if args.jit_indirect_calls:
            command.append('--jit-indirect-calls')
        if args.dump_code:
            command += ['--jit-code-dump', str(run / 'jit-code')]
        if args.jit_operation_map:
            command.append('--jit-operation-map')
        if selection:
            command += ['--select-test', selection['name'], '--suite-catalog', selection['catalog']]
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
                # A newly published Mach-O can still be in loader setup after
                # several fast vmmap calls. Bound elapsed readiness time, not
                # a small count of immediate inspections; never signal it.
                mapping_deadline = time.monotonic() + 5
                for attempt in range(64):
                    if child.poll() is not None:
                        break
                    code, mapping = diagnostic('vmmap-' + str(attempt), ['/usr/bin/vmmap', str(child.pid)])
                    if code == 0 and anonymous_executable_ranges(mapping, child.pid):
                        (run / 'vmmap.stdout').write_text(mapping)
                        mapped = True
                        break
                    if time.monotonic() >= mapping_deadline:
                        break
                    time.sleep(.05)
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
        if selection:
            selected = [json.loads(line.split(': ', 1)[1]) for line in (run / 'vm.stderr').read_text().splitlines()
                        if line.startswith('rust-interp-test-selection: ')]
            if len(selected) != 1 or any(selected[0][k] != selection[k] for k in
                                         ['name', 'function', 'catalog_sha256', 'artifact_sha256']):
                raise RuntimeError('executed test selection differs from the plan')
        stats = {name: int(value) for name, value in re.findall(
            r'\b([a-z_]+)=(\d+)\b', (run / 'vm.stderr').read_text())}
        if stats['jit_declined_functions'] != args.expected_jit_declines or stats['instructions'] <= 0:
            raise RuntimeError('unexpected JIT decline or empty execution')
        if args.jit_native_call_stubs and stats.get('jit_stub_calls', 0) == 0:
            raise RuntimeError('native Call stubs did not execute')
        if args.jit_resumable_calls and (stats.get('jit_resumable_calls', 0) == 0 or
                                         stats.get('jit_resumable_returns', 0) == 0):
            raise RuntimeError('resumable native Calls/Returns did not execute')
        record = dict(index=index, identity=identity, mapped=mapped, sample_returncode=sample_code,
                      performance_measurement=False, statistics=stats,
                      files={str(p.relative_to(run)): digest(p) for p in run.rglob('*') if p.is_file()})
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
