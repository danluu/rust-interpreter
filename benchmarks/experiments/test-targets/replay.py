#!/usr/bin/env python3
"""Replay all qualified fre integration assertions with a replacement VM."""
import argparse
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/tuned-native'))
from timing import environment, invoke, read, require, sha
from native_results import libtest_summary
from interpreter import installed_tools
from workflow_io import write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work / 'status.json', status)
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            deadline = time.monotonic() + 45
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(min(1, max(0, deadline - time.monotonic())))
            parent_path = ROOT / 'results/fre-integration-targets-02/summary.json'
            parent = read(parent_path)
            require(parent['status'] == 'passed' and parent['source_unchanged'] and
                parent['targets_passed'] == 10 and parent['original_tests_passed'] == 52 and
                not parent['custom_failures'], 'original qualification incomplete')
            records_path = ROOT / parent['raw'] / 'records.json'
            require(sha(records_path) == parent['records_sha256'], 'original records changed')
            previous = read(records_path)
            tools, key = installed_tools(args.tool_key)
            old_tools, _ = installed_tools(parent['tool_key'])
            binaries = read(tools / 'ready.json')
            old_binaries = read(old_tools / 'ready.json')
            for name in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']:
                require(binaries[name] == old_binaries[name], 'retained artifacts require the same frontend')
            inventory_path = ROOT / '.work/fre-unfiltered-native-01/inventory.json'
            require(sha(inventory_path) == parent['frozen'][str(inventory_path.relative_to(ROOT))], 'original inventory changed')
            targets = {Path(t['target']).stem: t['names'] for t in read(inventory_path)['native'] if t['kind'] == 'integration'}
            require(len(previous) == len(targets) == 10 and sum(map(len, targets.values())) == 52 and
                set(r['target'] for r in previous) == set(targets), 'original selection differs')
            source = ROOT / '.work/sources/fre'
            pin = read(ROOT / 'benchmarks/corpus.json')['projects']['fre']['revision']
            marker = read(source / '.rust-interp-owned.json')
            require(marker['owner'] == str(ROOT) and marker['revision'] == pin, 'source ownership changed')

            def source_check():
                require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == pin and not
                    subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(), 'source changed')

            source_check()
            paths = [Path(__file__), parent_path, records_path, inventory_path, tools / 'ready.json', old_tools / 'ready.json',
                ROOT / 'scripts/interpreter.py', ROOT / 'scripts/workflow_io.py', ROOT / 'scripts/workflow_controls.py',
                ROOT / 'scripts/workflow_measurements.py', ROOT / 'benchmarks/experiments/tuned-native/timing.py',
                ROOT / 'benchmarks/experiments/tuned-native/native_results.py', ROOT / 'benchmarks/corpus.json']
            frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
            for row in previous:
                require(row['status'] == 'passed' and row['tests'] == len(targets[row['target']]), 'target outcome changed')
                entries = [row['custom']['command'][i + 1] for i, v in enumerate(row['custom']['command']) if v == '--entry']
                require(entries == targets[row['target']], 'original assertion list differs')
                launch = row['launch']
                require(launch['tool_key'] == parent['tool_key'] and launch['engine'] == 'jit' and
                    launch['jit_resumable_calls'] and launch['jit_persistent_registers'] and
                    not launch['jit_native_calls'] and not launch['jit_native_call_stubs'] and
                    launch['inline_leaves'] and launch['trap_unsupported_calls'] and launch['run_try_callbacks'] and
                    launch['allocation_limit'] == 150000, 'original runtime configuration differs')
                cmd = row['custom']['command']
                require(cmd[cmd.index('--instruction-limit') + 1] == '100000000000', 'instruction limit differs')
                artifact = ROOT / row['snapshot']
                require(artifact.resolve().is_relative_to(ROOT / parent['raw'] / 'artifacts') and
                    sha(artifact) == launch['artifact_sha256'], 'retained bytecode differs')
                frozen[row['snapshot']] = launch['artifact_sha256']
                for mode in ['native', 'custom']:
                    for stream in ['stdout', 'stderr']:
                        frozen[row[mode][stream]] = row[mode][stream + '_sha256']

            def verify():
                source_check()
                require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'qualified evidence changed')
                installed_tools(key)

            required = 8 * 1024**3 + 128 * 1024**2
            free = shutil.disk_usage(ROOT).free
            write(work / 'plan.json', dict(owner=str(ROOT), source_pin=pin, parent=str(parent_path.relative_to(ROOT)),
                tool_key=key, binaries=binaries, frozen=frozen, fresh_exports=False, performance_measurement=False,
                native_jobs=18, native_test_threads='default', instruction_limit=100000000000, allocation_limit=150000,
                required_bytes=required, observed_free_bytes=free))
            require(free >= required, 'replay admission failed before commands')
            records = []
            env = environment('repository')
            status.update(status='running')
            write(work / 'status.json', status)
            for row in previous:
                verify()
                name = row['target']
                # Keep the original Cargo invocation, including package cwd,
                # native parallelism, test target and ordinary repository profile.
                expected = ['cargo', '+nightly-2026-09-08', 'test', '--manifest-path', str(source / 'Cargo.toml'),
                    '--package', 'fre-kernels', '--test', name, '--locked', '--offline', '--jobs', '18',
                    '--target-dir', str(ROOT / '.work/native-tuned-calibration-01/repository')]
                require(row['native']['command'] == expected, 'original native command differs')
                native, stdout, _ = invoke(work, name + '-native', expected, source, env)
                require(native['returncode'] == 0, 'native target failed: ' + name)
                suite = libtest_summary(stdout, selected=row['tests'])
                require(suite['filtered'] == suite['ignored'] == 0, 'native selection differs')
                command = [str(tools / 'rust-interp-vm'), '--engine', 'jit', '--jit-resumable-calls',
                    '--jit-persistent-registers', '--instruction-limit', '100000000000', '--allocation-limit', '150000',
                    str(ROOT / row['snapshot'])]
                custom, output, _ = invoke(work, name + '-custom', command, source, env)
                record = dict(target=name, tests=row['tests'], native=native, suite=suite, custom=custom,
                    snapshot=row['snapshot'], artifact_sha256=row['launch']['artifact_sha256'],
                    status='passed' if custom['returncode'] == 0 and output.strip() == '0' else 'failed')
                records.append(record)
                write(work / 'records.json', records)
                require(record['status'] == 'passed', 'candidate target failed: ' + name)
                print(name, row['tests'], 'passed', flush=True)
            verify()
            out = ROOT / 'results' / args.run_id
            out.mkdir(exist_ok=False)
            write(out / 'summary.json', dict(status='passed', tool_key=key, binaries=binaries, source_pin=pin,
                original_tests_passed=sum(r['tests'] for r in records), targets_passed=len(records), commands=2 * len(records),
                raw=str(work.relative_to(ROOT)), records_sha256=sha(work / 'records.json'), plan_sha256=sha(work / 'plan.json'),
                source_unchanged=True, artifacts_unchanged=True, fresh_exports=False, performance_measurement=False,
                scope='All original fre integration assertions replayed with a replacement VM and fresh native Cargo commands. No edit latency, complete libtest semantics or doc-test claim.'))
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work / 'status.json', status)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__':
    main()
