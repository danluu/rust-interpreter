#!/usr/bin/env python3
"""Qualify every original fre integration target with shared dependency metadata."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/tuned-native'))
from timing import environment, invoke, read, require, sha
from native_results import libtest_summary
from workflow_io import write_json as write

RUN = 'fre-integration-targets-01'
CACHE_NAMESPACE = RUN
TOOL = '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'


def main():
    global RUN
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', type=int, choices=range(1, 10), default=1)
    args = parser.parse_args()
    RUN = f'fre-integration-targets-{args.attempt:02}'
    work = ROOT / '.work' / RUN
    work.mkdir(exist_ok=False)
    (work / 'artifacts').mkdir()
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work / 'status.json', status)
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            qualified = read(ROOT / 'results/integration-targets-fixture-02/summary.json')
            require(qualified['status'] == 'passed' and qualified['integration_dependency_cache_shared'] and
                qualified['target_sidecars_distinct'], 'shared-target fixture not qualified')
            source_tree = ROOT / '.work/test-targets-source'
            source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source_tree, text=True).strip()
            require(source_commit == qualified['source_commit'] and not subprocess.check_output(
                ['git', 'status', '--porcelain', '--untracked-files=no'], cwd=source_tree, text=True), 'launcher source changed')
            source = ROOT / '.work/sources/fre'
            pin = read(ROOT / 'benchmarks/corpus.json')['projects']['fre']['revision']
            marker = read(source / '.rust-interp-owned.json')
            require(marker['owner'] == str(ROOT) and marker['revision'] == pin, 'fre source ownership changed')

            def source_check():
                require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == pin and not
                    subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(), 'fre source changed')

            source_check()
            baseline = read(ROOT / 'results/fre-unfiltered-native-01/summary.json')
            inventory_path = ROOT / baseline['raw'] / 'inventory.json'
            require(sha(inventory_path) == baseline['inventory_sha256'], 'native inventory changed')
            targets = [t for t in read(inventory_path)['native'] if t['kind'] == 'integration']
            require(len(targets) == 10 and sum(len(t['names']) for t in targets) == 52, 'target list changed')
            native_target = ROOT / '.work/native-tuned-calibration-01/repository'
            require(read(ROOT / '.work/fre-unfiltered-native-01/status.json')['status'] == 'failed' and
                read(ROOT / '.work/experiments/fre-unfiltered-native-01/status.json')['status'] == 'finished', 'native cache still active')
            reference = read(ROOT / 'results/parked-budget-e2e-token-phrase-candidate-archive-01/plan.json')
            reference_bytes = sum(g['bytes'] for g in reference['manifest']['groups'])
            needed = 8 * 1024**3 + (reference_bytes * 120 + 99) // 100 + 32 * 1024**2
            if args.attempt > 1:
                previous = read(ROOT / 'results/fre-integration-targets-01/summary.json')
                require(previous['source_commit'] == source_commit and previous['tool_key'] == TOOL and
                    read(ROOT / '.work/fre-integration-targets-01/status.json')['status'] == 'finished', 'reused cache qualification changed')
                needed = 8 * 1024**3 + 128 * 1024**2
            free = shutil.disk_usage(ROOT).free
            write(work / 'admission.json', dict(required_bytes=needed, observed_bytes=free,
                reference_cache_bytes=reference_bytes, incremental_target_margin_bytes=128 * 1024**2,
                note='Admit first shared cache from full historical fre cache size plus 20% and metadata. Re-admit each later target above 8GiB + 128MiB. Snapshot bytecode with APFS COW clones.'))
            require(free >= needed, 'initial shared cache does not fit')
            paths = [Path(__file__), HERE / 'launcher.py', HERE / 'PLAN.md', source_tree / 'scripts/interpreter.py',
                inventory_path, ROOT / 'results/integration-targets-fixture-02/summary.json',
                ROOT / 'benchmarks/experiments/tuned-native/timing.py', ROOT / 'scripts/workflow_io.py', ROOT / 'scripts/workflow_controls.py']
            frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
            write(work / 'plan.json', dict(owner=str(ROOT), source_commit=source_commit, tool_key=TOOL, source_pin=pin,
                frozen=frozen, targets=[t['target'] for t in targets], native_target=str(native_target.relative_to(ROOT)),
                jobs=18, native_test_threads='default', instruction_limit=100_000_000_000, allocation_limit=150_000,
                original_sources=True, performance_measurement=False, cache_namespace=CACHE_NAMESPACE,
                reused_checked_dependencies=args.attempt > 1))
            env = environment('repository')
            guest_env = dict(env, RUST_INTERP_LAUNCH_STATS='1', RUSTFLAGS='-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240')
            records = []
            status.update(status='running')
            write(work / 'status.json', status)
            for index, target in enumerate(targets):
                source_check()
                if index and shutil.disk_usage(ROOT).free < 8 * 1024**3 + 128 * 1024**2:
                    status.update(status='space-stop', completed_targets=len(records))
                    break
                name = Path(target['target']).stem
                entries = list(target['names'])
                native = ['cargo', '+nightly-2026-09-08', 'test', '--manifest-path', str(source / 'Cargo.toml'), '--package', 'fre-kernels',
                    '--test', name, '--locked', '--offline', '--jobs', '18', '--target-dir', str(native_target)]
                nrow, stdout, _ = invoke(work, name + '-native', native, source, env)
                require(nrow['returncode'] == 0, 'native integration target failed: ' + name)
                suite = libtest_summary(stdout, selected=len(entries))
                require(suite['filtered'] == suite['ignored'] == 0, 'native integration selection changed')
                command = [sys.executable, str(HERE / 'launcher.py'), '--manifest-path', str(source / 'Cargo.toml'), '--package', 'fre-kernels',
                    '--test-body', '--test-target', name, '--tool-key', TOOL, '--cache-namespace', CACHE_NAMESPACE, '--jobs', '18', '--std-mir',
                    '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers', '--inline-leaves', '--trap-unsupported-calls',
                    '--run-try-callbacks', '--instruction-limit', '100000000000', '--allocation-limit', '150000']
                for entry in entries:
                    # Native libtest names already match rustc's local def paths.
                    command += ['--entry', entry]
                grow, gout, gerr = invoke(work, name + '-custom', command, source, guest_env)
                launches = [json.loads(line.split(': ', 1)[1]) for line in gerr.splitlines() if line.startswith('rust-interp-launch: ')]
                record = dict(target=name, tests=len(entries), native=nrow, custom=grow,
                    status='passed' if grow['returncode'] == 0 and gout.strip() == '0' else 'custom-failed')
                if launches:
                    require(len(launches) == 1, 'multiple launcher results')
                    launch = launches[0]
                    artifact = Path(launch['artifact_path'])
                    require(artifact.is_file() and artifact.resolve().is_relative_to(ROOT / '.work/interpreter-workspaces' / TOOL), 'artifact ownership differs')
                    require(sha(artifact) == launch['artifact_sha256'], 'executed artifact changed')
                    snapshot = work / 'artifacts' / (name + '.rbc')
                    subprocess.run(['cp', '-c', str(artifact), str(snapshot)], check=True)
                    require(sha(snapshot) == launch['artifact_sha256'], 'snapshot clone differs')
                    record.update(launch=launch, snapshot=str(snapshot.relative_to(ROOT)))
                records.append(record)
                write(work / 'records.json', records)
                print(name, len(entries), record['status'], round(grow['seconds'], 3), flush=True)
            source_check()
            require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'experiment inputs changed')
            passed = [r for r in records if r['status'] == 'passed']
            caches = {str(next(p for p in Path(r['launch']['artifact_path']).parents if p.name == 'target')) for r in records if 'launch' in r}
            require(len(caches) <= 1, 'integration targets did not share their dependency cache')
            out = ROOT / 'results' / RUN
            out.mkdir(exist_ok=False)
            write(out / 'summary.json', dict(status='passed' if len(passed) == 10 else 'partial', raw=str(work.relative_to(ROOT)),
                source_commit=source_commit, tool_key=TOOL, targets_attempted=len(records), targets_passed=len(passed),
                original_tests_passed=sum(r['tests'] for r in passed), pending_targets=len(targets)-len(records),
                custom_failures=[r['target'] for r in records if r['status'] != 'passed'], shared_dependency_caches=len(caches),
                source_unchanged=True, records_sha256=sha(work / 'records.json'), frozen=frozen,
                note='Original native integration targets versus custom JIT batches. Coverage qualification only; no edit latency or full libtest/doc-test claim. Every executed guest artifact is preserved.'))
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work / 'status.json', status)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__':
    main()
