#!/usr/bin/env python3
"""Run the pinned workflow corpus serially with explicit native controls."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from verify_repeated_workflow import verify

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def acquire(deadline, status, receipt):
    while True:
        lock = (ROOT / '.work/benchmark.lock').open('a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock
        except BlockingIOError:
            lock.close()
        status.update(status='waiting for benchmark lock', updated_at=time.time())
        write(receipt, status)
        if time.monotonic() >= deadline:
            raise RuntimeError('benchmark lock wait expired; no other work was interrupted')
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--candidate-tool-key', required=True)
    parser.add_argument('--baseline-tool-key', required=True)
    parser.add_argument('--candidate-jit-native-call-stubs', action='store_true')
    parser.add_argument('--candidate-jit-resumable-calls', action='store_true')
    parser.add_argument('--candidate-jit-persistent-registers', action='store_true')
    parser.add_argument('--candidate-jit-native-calls', action='store_true')
    parser.add_argument('--only', action='append', help='case label; repeat to select a subset')
    parser.add_argument('--cycles', type=int, default=3)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--native-jobs', type=int, default=18)
    parser.add_argument('--native-profile', choices=['repository', 'o0-incremental'], default='o0-incremental')
    parser.add_argument('--native-test-threads', default='default')
    parser.add_argument('--native-rustflag', action='append', default=[])
    parser.add_argument('--lock-wait-seconds', type=int, default=600)
    parser.add_argument('--minimum-free-gib', type=int, default=30)
    args = parser.parse_args()
    if args.candidate_jit_native_call_stubs and not args.candidate_jit_native_calls:
        parser.error('--candidate-jit-native-call-stubs requires --candidate-jit-native-calls')
    if args.candidate_jit_resumable_calls and (args.candidate_jit_native_calls or args.candidate_jit_native_call_stubs):
        parser.error('--candidate-jit-resumable-calls cannot be combined with native tree/stub calls')
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..'] or len(args.run_id) > 120:
        parser.error('run-id must be one short directory name')
    if not 3 <= args.cycles <= 30 or min(args.jobs, args.native_jobs) < 1 or max(args.jobs, args.native_jobs) > 256:
        parser.error('cycles must be 3..30 and jobs 1..256')
    if args.lock_wait_seconds < 0 or args.minimum_free_gib < 1:
        parser.error('invalid wait/disk bound')
    config = read(ROOT / 'benchmarks/workflow-corpus.json')
    if args.only and set(args.only) - {c['label'] for c in config['cases']}:
        parser.error('unknown case label')
    cases = [c for c in config['cases'] if not args.only or c['label'] in args.only]
    work = ROOT / '.work/corpus-runs' / args.run_id
    work.mkdir(parents=True, exist_ok=False)
    paths = ['scripts/bench_e2e_workflow.py', 'scripts/interpreter.py',
             'scripts/workflow_cases.py', 'scripts/workflow_controls.py',
             'scripts/workflow_measurements.py', 'scripts/workflow_io.py', 'scripts/std_mir.py',
             'scripts/verify_repeated_workflow.py', 'scripts/bench_workflow_corpus.py',
             'benchmarks/workflow-corpus.json']
    frozen = {p: sha(ROOT / p) for p in paths}
    plan = dict(schema_version=1, options=vars(args), cases=cases, frozen=frozen,
        purpose='Repeated complete-command control comparison; preserve original assertions, wrong edits, cache histories and all regressions. No fastest-native, significance or retention decision is automatic.')
    write(work / 'plan.json', plan)
    status = dict(status='starting', pid=os.getpid(), parent_pid=os.getppid(),
                  cwd=str(ROOT), started_at=time.time(), completed=[])
    receipt = work / 'status.json'
    write(receipt, status)

    def check_frozen():
        if any(sha(ROOT / p) != digest for p, digest in frozen.items()):
            raise RuntimeError('corpus scripts changed during the run')

    try:
        for case in cases:
            # A receipt for the next case must not carry the preceding child's
            # exit status or identity. Recovery readers may inspect it while
            # this controller is waiting for the shared lock.
            for field in ['child_pid', 'command', 'child_started_at',
                          'child_returncode', 'child_finished_at']:
                status.pop(field, None)
            status.update(status='preparing workflow', case=case['label'], updated_at=time.time())
            write(receipt, status)
            lock = acquire(time.monotonic() + args.lock_wait_seconds, status, receipt)
            try:
                check_frozen()
                if sha(ROOT / case['reference_report']) != case['reference_report_sha256']:
                    raise RuntimeError('reference report changed')
                disk = os.statvfs(ROOT)
                if disk.f_bavail * disk.f_frsize < args.minimum_free_gib * 1024**3:
                    raise RuntimeError('insufficient free disk; no automatic cleanup attempted')
            finally:
                lock.close()
            run_id = args.run_id + '-' + case['label']
            command = [sys.executable, str(ROOT / 'scripts/bench_e2e_workflow.py'),
                '--run-id', run_id, '--project', case['project'], '--workflow', case['workflow'],
                '--cycles', str(args.cycles), '--jobs', str(args.jobs),
                '--native-jobs', str(args.native_jobs), '--native-profile', args.native_profile,
                '--native-test-threads', args.native_test_threads, '--check-floor',
                '--candidate-tool-key', args.candidate_tool_key,
                '--baseline-tool-key', args.baseline_tool_key,
                '--comparison-engine', 'jit', '--expect-identical-bytecode', *case['flags'],
                *['--native-rustflag=' + flag for flag in args.native_rustflag]]
            if args.candidate_jit_resumable_calls:command.append('--candidate-jit-resumable-calls')
            if args.candidate_jit_persistent_registers:command.append('--candidate-jit-persistent-registers')
            if args.candidate_jit_native_calls:command.append('--candidate-jit-native-calls')
            if args.candidate_jit_native_call_stubs:command.append('--candidate-jit-native-call-stubs')
            # The child acquires its own benchmark lock. If another task wins
            # the small release/start race, keep that failed attempt; do not
            # steal the lock or retry a possibly partially edited workflow.
            with (work / (case['label'] + '.log')).open('x') as log:
                child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT)
                status.update(status='running', child_pid=child.pid, command=command,
                              child_started_at=time.time(), updated_at=time.time())
                try:
                    write(receipt, status)
                    print('START', case['label'], child.pid, flush=True)
                finally:
                    code = child.wait()
            status.update(status='verifying workflow', child_returncode=code,
                          child_finished_at=time.time(), updated_at=time.time())
            write(receipt, status)
            if code:
                raise RuntimeError('workflow failed; retained log: ' + case['label'])
            lock = acquire(time.monotonic() + args.lock_wait_seconds, status, receipt)
            try:
                check_frozen()
                path = ROOT / 'results' / run_id / 'summary.json'
                report = read(path)
                verification = verify(report)
                if report['case_sha256'] != read(ROOT / case['reference_report'])['case_sha256']:
                    raise RuntimeError('workflow case changed')
                if report['check_floor'] is None or len(report['check_floor']['samples']) != args.cycles * (len(report['edits']) + 2):
                    raise RuntimeError('missing checking controls')
                verification_path = path.with_name('verification.json')
                if verification_path.exists():
                    raise RuntimeError('verification output already exists')
                write(verification_path, verification)
                status['completed'].append(dict(label=case['label'], report=str(path.relative_to(ROOT)),
                    report_sha256=sha(path), native_control=report['native_control'],
                    medians=report['median_seconds'], cpu_medians=report['median_cpu_seconds'],
                    check_median_seconds=report['check_floor']['median_seconds'],
                    cross_cycle_bytecode_identical=verification['cross_cycle_bytecode_identical']))
                status.update(status='workflow verified', updated_at=time.time())
                write(receipt, status)
            finally:
                lock.close()
            print('PASS', case['label'], flush=True)
        output = ROOT / 'results' / args.run_id
        output.mkdir()
        write(output / 'summary.json', dict(plan=plan, workflows=status['completed'],
            status='All requested workflows completed; compare separate workload groups before selecting a native configuration or runtime direction'))
        status.update(status='finished', finished_at=time.time(), updated_at=time.time(), report=str(output.relative_to(ROOT)))
        write(receipt, status)
    except Exception as error:
        status.update(status='failed', error=str(error), finished_at=time.time(), updated_at=time.time())
        write(receipt, status)
        raise


if __name__ == '__main__':
    main()
