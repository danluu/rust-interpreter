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


def entropy_inputs(qualification_path, cases):
    """Validate explicit, fixture-qualified replay inputs without executing code."""
    qualification = json.loads(qualification_path.read_text())
    if qualification.get('status') != 'passed' or qualification.get('commands') != 17 or qualification.get('expected_rejections') != 10:
        raise RuntimeError('entropy replay fixture qualification differs')
    library = Path(qualification['library']).resolve()
    if sha(library) != qualification['library_sha256']:
        raise RuntimeError('qualified entropy library changed')
    paths = [qualification_path.resolve(), library]
    for case in cases:
        tapes = case.get('entropy_tapes')
        if not isinstance(tapes, list) or len(tapes) != 2:
            raise RuntimeError(f'{case["name"]}: two recorded entropy tapes are required')
        for tape in tapes:
            path = Path(tape['path']).resolve()
            if sha(path) != tape['sha256']:
                raise RuntimeError(f'{case["name"]}: entropy tape changed')
            for field, limit in [('calls', 4096), ('bytes', 16 * 1024**2)]:
                if type(tape[field]) is not int or not 0 <= tape[field] <= limit:
                    raise RuntimeError(f'{case["name"]}: invalid entropy {field}')
            paths.append(path)
    return library, paths


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
    parser.add_argument('--entropy-qualification', type=Path,
                        help='fixture-qualified replay library; each manifest case must supply two entropy tapes')
    args = parser.parse_args()
    if args.repetitions < 2 or args.repetitions % 2:
        parser.error('use an even number of repetitions, at least two')
    if len(set(args.engines)) != len(args.engines):
        parser.error('specify each engine at most once')
    cases = json.loads(args.manifest.read_text())
    if args.entropy_qualification is not None and args.repetitions != 6:
        parser.error('entropy comparisons use six pairs with the fixed two-stream assignment')
    if args.entropy_qualification is None and any('entropy_tapes' in c for c in cases):
        parser.error('entropy tapes require an explicit qualified replay library')
    for case in cases:
        for field, minimum in [('instruction_limit', 1), ('allocation_limit', 0)]:
            if field in case and (type(case[field]) is not int or not minimum <= case[field] < 2**64):
                parser.error(f'{case["name"]}: {field} must be an explicit integer in range; omit it to use the default')
    binaries = dict(baseline=args.baseline.resolve(), candidate=args.candidate.resolve())
    paths = [*binaries.values(), args.manifest.resolve(), Path(__file__).resolve()]
    paths += [Path(case['artifact']).resolve() for case in cases]
    entropy_library = None
    if args.entropy_qualification is not None:
        entropy_library, entropy_paths = entropy_inputs(args.entropy_qualification, cases)
        paths += entropy_paths
    frozen = {str(path): sha(path) for path in paths}
    with args.lock.open('a') as lock:
        acquire_lock(lock, args.lock_wait_seconds)
        for case in cases:
            artifact = str(Path(case['artifact']).resolve())
            expected = case.get('artifact_sha256')
            if expected is not None and frozen[artifact] != expected:
                raise RuntimeError(f'{case["name"]}: artifact differs from declared provenance')
        if any(sha(path) != digest for path, digest in frozen.items()):
            raise RuntimeError('input changed before benchmark lock was acquired')
        args.output.mkdir(parents=True, exist_ok=False)
        plan = dict(binaries={k: str(v) for k, v in binaries.items()}, cases=cases,
                    frozen=frozen, repetitions=args.repetitions, engines=args.engines,
                    controller_pid=os.getpid(), parent_pid=os.getppid(),
                    cwd=os.getcwd(), started_at=time.time(),
                    scope='Saved-artifact runtime including VM startup; excludes export/build.')
        if entropy_library is not None:
            plan['entropy'] = dict(library=str(entropy_library), qualification=str(args.entropy_qualification.resolve()),
                warmup_stream=0, measured_streams=[0, 1, 1, 0, 0, 1],
                scope='Conditional on two real recorded streams; no fresh-entropy or whole-workflow timing claim.')
        (args.output / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(('RUST_INTERP_', 'RUSTDEV_')):
                env.pop(key)
        env['RUST_INTERP_VM_STATS'] = '1'
        if entropy_library is not None:
            if any(k.startswith('DYLD_') for k in env):
                raise RuntimeError('existing dynamic-loader instrumentation is out of scope')
            env.update(DYLD_INSERT_LIBRARIES=str(entropy_library), RUST_INTERP_ENTROPY_MODE='replay')
        samples = []
        entropy_references = {}
        with (args.output / 'commands.jsonl').open('x') as log:
            for case in cases:
                for engine in args.engines:
                    # First pair warms executable pages and artifacts; excluded from timings.
                    for repetition in range(-1, args.repetitions):
                        tape = None
                        selected_env = env
                        if entropy_library is not None:
                            stream = 0 if repetition < 0 else [0, 1, 1, 0, 0, 1][repetition]
                            tape = case['entropy_tapes'][stream]
                            selected_env = dict(env, RUST_INTERP_ENTROPY_TAPE=str(Path(tape['path']).resolve()))
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
                            child = subprocess.Popen(command, env=selected_env, stdin=subprocess.DEVNULL,
                                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                     text=True)
                            record = dict(case=case['name'], engine=engine, mode=mode,
                                          repetition=repetition, command=command, child_pid=child.pid,
                                          started_at=time.time(), cwd=os.getcwd(), load=os.getloadavg(),
                                          status='running')
                            if tape is not None:
                                record['entropy'] = dict(stream=stream, tape_sha256=tape['sha256'],
                                    expected_calls=tape['calls'], expected_bytes=tape['bytes'])
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
                            if tape is not None and (stats.get('entropy_calls') != tape['calls'] or stats.get('entropy_bytes') != tape['bytes']):
                                raise RuntimeError(f'{case["name"]}: recorded entropy was not completely replayed')
                            if tape is not None:
                                counts = {k: stats[k] for k in ['instructions', 'peak_guest_memory', 'entropy_calls', 'entropy_bytes']}
                                key = (case['name'], stream)
                                if entropy_references.setdefault(key, counts) != counts:
                                    raise RuntimeError(f'{case["name"]}: identical entropy changed counters across executions or engines')
                            pair[mode] = record
                            samples.append(record)
                        for field in ['instructions', 'peak_guest_memory'] + (['entropy_calls', 'entropy_bytes'] if tape is not None else []):
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
        if entropy_library is not None:
            summary['entropy_replay'] = dict(streams_per_case=2, complete_consumption_verified=True,
                counters_equal_across_modes_engines_and_repetitions=True,
                scope='Runtime including startup and the identical replay library; conditional on the recorded inputs.')
        (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        (args.output / 'active.json').write_text(json.dumps(dict(status='finished', finished_at=time.time())) + '\n')
        print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
