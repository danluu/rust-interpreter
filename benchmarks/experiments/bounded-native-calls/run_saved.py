#!/usr/bin/env python3
"""Smoke-test the experimental native path on two frozen real test artifacts."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import installed_tools


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--candidate-tool-key', required=True)
    parser.add_argument('--baseline-tool-key', required=True)
    parser.add_argument('--candidate-call-stubs', action='store_true')
    parser.add_argument('--profile-candidate', action='store_true')
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('run-id must be one directory name')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    receipt = work / 'status.json'
    status = dict(status='waiting for benchmark lock', pid=os.getpid(), parent_pid=os.getppid(), cwd=str(ROOT), started_at=time.time())
    write(receipt, status)
    lock = (ROOT / '.work/benchmark.lock').open('a')
    deadline = time.monotonic() + 600
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise RuntimeError('benchmark lock unavailable; no other work interrupted')
            time.sleep(1)
    tools = {mode: installed_tools(key)[0] for mode, key in
        [('baseline', args.baseline_tool_key), ('candidate', args.candidate_tool_key)]}
    artifacts = {label: ROOT / '.work/runs' / ('paired-scalar-packed-cache-' + label + '-01') / 'artifacts/candidate/0-0.rbc'
        for label in ['folded-literal-trie', 'token-phrase']}
    paths = [Path(__file__), ROOT / 'scripts/interpreter.py', *artifacts.values(),
        *[directory / 'rust-interp-vm' for directory in tools.values()]]
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    write(work / 'plan.json', dict(options=vars(args), frozen=frozen,
        purpose='Correctness/coverage smoke check using saved real artifacts. No source edits or frontend timing; not an end-to-end performance comparison.'))
    rows = []
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_')):
            env.pop(name)
    env['RUST_INTERP_VM_STATS'] = '1'
    try:
        for label, artifact in artifacts.items():
            for mode, directory in tools.items():
                if any(sha(ROOT / p) != digest for p, digest in frozen.items()):
                    raise RuntimeError('frozen smoke input changed')
                command = [str(directory / 'rust-interp-vm'), '--engine', 'jit',
                    '--instruction-limit', '100000000000', '--allocation-limit', '150000']
                if mode == 'candidate':
                    command.append('--jit-native-calls')
                    if args.candidate_call_stubs:command.append('--jit-native-call-stubs')
                    if args.profile_candidate:
                        command += ['--profile', str(work / (label + '-profile.json'))]
                command.append(str(artifact))
                before = resource.getrusage(resource.RUSAGE_CHILDREN)
                started = time.perf_counter()
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                status.update(status='running', case=label, mode=mode, child_pid=child.pid,
                    command=command, child_started_at=time.time())
                write(receipt, status)
                stdout, stderr = child.communicate()
                elapsed = time.perf_counter() - started
                after = resource.getrusage(resource.RUSAGE_CHILDREN)
                stats = {key: int(value) for key, value in re.findall(r'\b([a-z_]+)=([0-9]+)\b', stderr)}
                row = dict(label=label, mode=mode, pid=child.pid, command=command, returncode=child.returncode,
                    stdout=stdout, stderr=stderr, stats=stats, wall_seconds=elapsed,
                    cpu_seconds=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                    performance_measurement=False, profiled=mode == 'candidate' and args.profile_candidate)
                rows.append(row)
                write(work / 'commands.json', rows)
                if child.returncode != 0 or stdout.strip() != '0':
                    raise RuntimeError(label + '/' + mode + ' failed: ' + stderr[-2000:])
                if mode == 'candidate' and not (stats.get('jit_tree_entries', 0) + stats.get('jit_stub_calls', 0)):
                    raise RuntimeError('experimental path did not execute')
                print(label, mode, 'PASS', stats, flush=True)
        if any(sha(ROOT / p) != digest for p, digest in frozen.items()):
            raise RuntimeError('frozen smoke input changed')
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', commands=rows, frozen=frozen, performance_measurement=False))
        status.update(status='finished', returncode=0, finished_at=time.time(), report=str(out.relative_to(ROOT)))
        write(receipt, status)
    except Exception as error:
        status.update(status='failed', error=str(error), finished_at=time.time())
        write(receipt, status)
        raise


if __name__ == '__main__':
    main()
