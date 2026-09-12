#!/usr/bin/env python3
"""Compare two immutable VMs on a manifest of saved bytecode, without rebuilding."""
import argparse
import errno
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import statistics
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lock_wait_seconds(value):
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError('lock wait must be finite and nonnegative') from None
    if not math.isfinite(seconds) or seconds < 0:
        raise argparse.ArgumentTypeError('lock wait must be finite and nonnegative')
    return seconds


def acquire_lock(lock, wait_seconds):
    wait_seconds = lock_wait_seconds(wait_seconds)
    deadline = time.monotonic() + wait_seconds
    first_attempt = True
    while first_attempt or time.monotonic() < deadline:
        first_attempt = False
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN):
                raise
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(1.0, remaining))
    raise TimeoutError(f'timed out after {wait_seconds:g}s waiting for benchmark lock {lock.name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=300)
    parser.add_argument('--repetitions', type=int, default=6)
    parser.add_argument('--engines', nargs='+', choices=['interpreter', 'jit'], default=['interpreter', 'jit'])
    args = parser.parse_args()
    if args.repetitions < 2 or args.repetitions % 2:
        parser.error('use an even number of repetitions, at least two')
    if len(set(args.engines)) != len(args.engines):
        parser.error('specify each engine at most once')
    cases = json.loads(args.manifest.read_text())
    binaries = dict(baseline=args.baseline.resolve(), candidate=args.candidate.resolve())
    paths = [*binaries.values(), args.manifest.resolve(), Path(__file__).resolve()]
    paths += [Path(case['artifact']).resolve() for case in cases]
    frozen = {str(path): sha(path) for path in paths}
    with args.lock.open('a') as lock:
        acquire_lock(lock, args.lock_wait_seconds)
        args.output.mkdir(parents=True, exist_ok=False)
        plan = dict(binaries={k: str(v) for k, v in binaries.items()}, cases=cases,
                    frozen=frozen, repetitions=args.repetitions, engines=args.engines,
                    controller_pid=os.getpid(), parent_pid=os.getppid(),
                    cwd=os.getcwd(), started_at=time.time(),
                    scope='Saved-artifact runtime including VM startup; excludes export/build.')
        (args.output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(('RUST_INTERP_', 'RUSTDEV_')):
                env.pop(key)
        env['RUST_INTERP_VM_STATS'] = '1'
        samples = []
        with (args.output / 'commands.jsonl').open('x') as log:
            for case in cases:
                for engine in args.engines:
                    # First pair warms executable pages and artifacts; excluded from timings.
                    for repetition in range(-1, args.repetitions):
                        order = ['baseline', 'candidate']
                        if repetition % 2:
                            order.reverse()
                        pair = {}
                        for mode in order:
                            command = [str(binaries[mode]), '--engine', engine,
                                       '--instruction-limit', str(case.get('instruction_limit', 1000000000))]
                            if 'allocation_limit' in case:
                                command += ['--allocation-limit', str(case['allocation_limit'])]
                            if engine == 'jit':
                                command += ['--jit-resumable-calls', '--jit-persistent-registers']
                            command += [str(Path(case['artifact']).resolve()), *case.get('args', [])]
                            before = resource.getrusage(resource.RUSAGE_CHILDREN)
                            start = time.perf_counter()
                            child = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                     text=True)
                            record = dict(case=case['name'], engine=engine, mode=mode,
                                          repetition=repetition, command=command, child_pid=child.pid,
                                          started_at=time.time(), cwd=os.getcwd(), load=os.getloadavg(),
                                          status='running')
                            try:
                                (args.output / 'active.json').write_text(json.dumps(record, indent=2) + '\n')
                            finally:
                                # Even a failed receipt write must drain and reap our child.
                                stdout, stderr = child.communicate()
                            elapsed = time.perf_counter() - start
                            after = resource.getrusage(resource.RUSAGE_CHILDREN)
                            cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
                            stats = {}
                            for word in stderr.split():
                                if '=' in word:
                                    key, value = word.split('=', 1)
                                    if value.isdigit():
                                        stats[key] = int(value)
                            record.update(seconds=elapsed, cpu_seconds=cpu, returncode=child.returncode,
                                          stdout=stdout, stderr=stderr, statistics=stats,
                                          finished_at=time.time(), status='finished')
                            (args.output / 'active.json').write_text(json.dumps(record, indent=2) + '\n')
                            log.write(json.dumps(record) + '\n')
                            log.flush()
                            if child.returncode or stdout != case['stdout']:
                                raise RuntimeError(f'{case["name"]} {engine} {mode}: result mismatch; see commands.jsonl')
                            pair[mode] = record
                            samples.append(record)
                        for field in ['instructions', 'peak_guest_memory']:
                            if pair['baseline']['statistics'][field] != pair['candidate']['statistics'][field]:
                                raise RuntimeError(f'{case["name"]}: {field} changed')
                    print(case['name'], engine, 'passed', flush=True)
        if any(sha(path) != digest for path, digest in frozen.items()):
            raise RuntimeError('measured input changed')
        rows = []
        for case in cases:
            for engine in args.engines:
                selected = [s for s in samples if s['case'] == case['name'] and
                            s['engine'] == engine and s['repetition'] >= 0]
                row = dict(case=case['name'], engine=engine)
                for metric in ['seconds', 'cpu_seconds']:
                    baseline = [s[metric] for s in selected if s['mode'] == 'baseline']
                    candidate = [s[metric] for s in selected if s['mode'] == 'candidate']
                    paired = []
                    for repetition in range(args.repetitions):
                        pair = {s['mode']: s[metric] for s in selected if s['repetition'] == repetition}
                        paired.append(100 * (pair['candidate'] / pair['baseline'] - 1))
                    row[metric] = dict(baseline_median=statistics.median(baseline),
                                       candidate_median=statistics.median(candidate),
                                       paired_percent=paired, median_paired_percent=statistics.median(paired))
                rows.append(row)
        summary = dict(status='passed', inputs_unchanged=True, commands=len(samples), rows=rows,
                       raw_commands_sha256=sha(args.output / 'commands.jsonl'))
        (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        (args.output / 'active.json').write_text(json.dumps(dict(status='finished', finished_at=time.time())) + '\n')
        print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
