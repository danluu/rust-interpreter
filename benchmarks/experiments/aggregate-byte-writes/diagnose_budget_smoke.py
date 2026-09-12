#!/usr/bin/env python3
"""Check logical accounting and unchanged-VM variability with original randomness."""
import fcntl
import os
from pathlib import Path
import re
import subprocess
import time

from build import ROOT, environment, read, require, sha, write


def account(profile):
    total, random_events = 0, 0
    for function in profile['functions']:
        operations = function['operations']
        n = len(operations)
        require(len(function['interpreted']) == n, 'profile shape differs')
        require(all(type(v) is int and v >= 0 for v in function['interpreted']), 'invalid count')
        total += sum(function['interpreted'])
        random_pcs = [i for i, op in enumerate(operations) if op.startswith('RandomBytes {')]
        random_events += sum(function['interpreted'][i] for i in random_pcs)
        for hits_key, ends_key in [('jit_blocks','jit_block_ends'), ('jit_tree_blocks','jit_tree_block_ends')]:
            hits, ends = function[hits_key], function[ends_key]
            require(len(hits) == len(ends) == n, 'profile block shape differs')
            for start, (hit, end) in enumerate(zip(hits, ends)):
                require(type(hit) is int and hit >= 0 and type(end) is int and 0 <= end <= n, 'invalid block count')
                if hit:
                    require(start < end, 'hit outside a compiled block')
                    total += hit*(end-start)
                    random_events += hit*sum(start <= pc < end for pc in random_pcs)
    return dict(instructions=total, random_events=random_events)


def main():
    run = 'budget-register-randomness-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        work = ROOT/'.work'/run
        work.mkdir(exist_ok=False)
        status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
        write(work/'status.json', status)
        try:
            old = ROOT/'.work/budget-register-smoke-04'
            prior = read(old/'commands.json')
            require(len(prior) == 14 and all(r['returncode'] == 0 for r in prior[10:14]), 'unexpected original smoke history')
            frozen = read(old/'plan.json')['frozen']
            frozen = {**frozen, str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}
            require(all(sha(ROOT/p) == h for p,h in frozen.items()), 'original inputs changed')
            command = list(prior[11]['command'])
            require(prior[11]['mode'] == 'baseline' and prior[11]['profiled'], 'expected profiled unchanged VM')
            command[command.index('--profile')+1] = str(work/'profile.json')
            env = environment()
            env['RUST_INTERP_VM_STATS'] = '1'
            with (work/'stdout').open('x') as out, (work/'stderr').open('x') as err:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
                try:
                    status.update(status='running', command=command, child_pid=child.pid, child_started_at=time.time())
                    write(work/'status.json', status)
                finally:
                    code = child.wait()
            require(code == 0 and (work/'stdout').read_text().strip() == '0', 'unchanged VM assertions failed')
            executions = []
            for label, profile_path, stderr_path in [
                    ('original-control',old/'11-profile.json',old/'11.stderr'),
                    ('original-candidate',old/'13-profile.json',old/'13.stderr'),
                    ('repeated-control',work/'profile.json',work/'stderr')]:
                counted = account(read(profile_path))
                stats = {k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',stderr_path.read_text())}
                require(counted['instructions'] == stats['instructions'] and counted['random_events'] > 0,
                        'logical accounting or actual randomness missing')
                executions.append(dict(label=label, **counted, files={str(p.relative_to(ROOT)):sha(p) for p in [profile_path,stderr_path]}))
            require(all(sha(ROOT/p) == h for p,h in frozen.items()), 'inputs changed during diagnostic')
            result = dict(status='passed', executions=executions, command=command, pid=child.pid,
                same_control_counts_differ=executions[0]['instructions'] != executions[2]['instructions'],
                original_assertions_pass=True, randomness_unchanged=True, frozen=frozen, performance_measurement=False,
                note='Actual RandomBytes operations and independent entropy remain. Counts reconcile within each execution; independent executions need not take identical paths. No runtime or performance gate changed.')
            out = ROOT/'results'/run
            out.mkdir(exist_ok=False)
            write(out/'summary.json', result)
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work/'status.json', status)
            print({k:result[k] for k in ['status','same_control_counts_differ','executions']}, flush=True)
        except BaseException as error:
            status.update(status='failed', error=repr(error), finished_at=time.time())
            write(work/'status.json', status)
            raise


if __name__ == '__main__':
    main()
