#!/usr/bin/env python3
"""Count VM transitions in a fresh execution matching an owned sample capture."""
import argparse
from collections import Counter
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from interpreter import ROOT, installed_tools
from sample_owned_vm import digest, write
from summarize_owned_sample import require, runtime_options


def counts(profile, stats):
    kinds, sites = Counter(), []
    interpreted = native = 0
    for fid, f in enumerate(profile['functions']):
        ops = f['operations']
        require(len(ops) <= 1_000_000, 'unbounded function profile')
        for field in ['interpreted', 'jit_blocks', 'jit_block_ends',
                      'jit_tree_blocks', 'jit_tree_block_ends']:
            require(len(f[field]) == len(ops) and
                    all(type(n) is int and 0 <= n < 2**64 for n in f[field]),
                    'invalid profile vector')
        scalar = f.get('jit_scalar_hits', [0] * len(ops))
        require(len(scalar) == len(ops) and all(type(n) is int and 0 <= n < 2**64 for n in scalar),
                'invalid scalar profile vector')
        native += sum(scalar)
        for pc, (op, n) in enumerate(zip(ops, f['interpreted'])):
            require(isinstance(op, str), 'invalid rendered operation')
            if n:
                # The rendered variant labels group observations only. Never
                # infer addresses, operands or memory safety from Debug text.
                match = re.match(r'^([A-Z][A-Za-z0-9]*)(?: \{|$)', op)
                require(match, 'unrecognized rendered operation label')
                kinds[match[1]] += n
                interpreted += n
                sites.append(dict(function=fid, name=f['name'], pc=pc,
                                  operation=op, count=n))
        for hits, ends in [('jit_blocks', 'jit_block_ends'),
                           ('jit_tree_blocks', 'jit_tree_block_ends')]:
            for pc, n in enumerate(f[hits]):
                if n:
                    end = f[ends][pc]
                    require(pc < end <= len(ops), 'invalid native profile interval')
                    native += n * (end - pc)
    require(native == stats['jit_instructions'], 'native instruction totals disagree')
    require(interpreted + native == stats['instructions'], 'total instructions disagree')
    return dict(interpreted_instructions=interpreted, native_instructions=native,
                by_rendered_variant=dict(kinds.most_common()),
                top_interpreted_sites=sorted(sites, key=lambda s: -s['count'])[:40],
                interpreted_sites=len(sites), functions=len(profile['functions']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--sample-run', required=True)
    args = parser.parse_args()
    for value in [args.run_id, args.sample_run]:
        require(Path(value).name == value and value not in ('.', '..'), 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    require(shutil.disk_usage(ROOT).free >= 8 * 1024**3, 'less than 8 GiB free')
    sample = ROOT / '.work' / args.sample_run
    plan = json.loads((sample / 'plan.json').read_text())
    saved = json.loads((sample / 'summary.json').read_text())
    require(saved['source_unchanged'] and not saved['performance_measurement'], 'incomplete reference')
    first = saved['records'][0]
    require(first['identity']['returncode'] == 0, 'failed reference execution')
    original = first['identity']['command']
    options = runtime_options(plan, [original])
    require(options['jit_resumable_calls'] and not options['jit_native_calls'], 'expected resumable ABI')
    tool, key = installed_tools(saved['tool_key'])
    vm, artifact = tool / 'rust-interp-vm', Path(plan['artifact'])
    require(digest(vm) == saved['vm_sha256'] and digest(artifact) == saved['artifact_sha256'],
            'reference binary/artifact changed')
    frozen_paths = [Path(__file__).resolve(), ROOT / 'scripts/sample_owned_vm.py',
                    ROOT / 'scripts/summarize_owned_sample.py', ROOT / 'scripts/interpreter.py',
                    sample / 'plan.json', sample / 'summary.json', vm, artifact]
    frozen = {str(p.relative_to(ROOT)): digest(p) for p in frozen_paths}

    def verify():
        require(all(digest(ROOT / p) == h for p, h in frozen.items()), 'diagnostic input changed')

    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    command = original.copy()
    if '--jit-code-dump' in command:
        pos = command.index('--jit-code-dump')
        del command[pos:pos + 2]
    require('--profile' not in command and command[0] == str(vm), 'unexpected reference command')
    command[1:1] = ['--profile', str(work / 'profile.json')]
    write(work / 'plan.json', dict(reference=args.sample_run, command=command, frozen=frozen,
                                  performance_measurement=False))
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_')):
            env.pop(name)
    env['RUST_INTERP_VM_STATS'] = '1'
    verify()
    with (work / 'stdout').open('x') as out, (work / 'stderr').open('x') as err:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=err)
        identity = dict(pid=child.pid, parent_pid=os.getpid(), command=command, cwd=str(ROOT),
                        started_at=time.time(), status='running')
        try:
            identity['ps'] = subprocess.check_output(
                ['ps', '-p', str(child.pid), '-o', 'pid,ppid,lstart,tty,command'], text=True)
            write(work / 'process.json', identity)
        finally:
            code = child.wait()
            identity.update(status='finished', returncode=code, finished_at=time.time())
            write(work / 'process.json', identity)
    verify()
    require(code == 0 and (work / 'stdout').read_text().strip() == '0', 'original guest assertions failed')
    stats = {name: int(value) for name, value in re.findall(
        r'\b([a-z_]+)=(\d+)\b', (work / 'stderr').read_text())}
    require(stats['jit_declined_functions'] == 0 and stats['jit_resumable_calls'] > 0,
            'unexpected native decline or no resumable calls')
    require((work / 'profile.json').stat().st_size <= 256 * 1024**2, 'profile exceeds 256 MiB')
    attribution = counts(json.loads((work / 'profile.json').read_text()), stats)
    report = dict(status='passed', reference=args.sample_run, tool_key=key,
                  vm_sha256=digest(vm), artifact_sha256=digest(artifact), options=options,
                  statistics=stats, counts=attribution, process=identity,
                  frozen=frozen, evidence={str(p.relative_to(ROOT)): digest(p)
                      for p in sorted(work.iterdir()) if p.is_file()},
                  performance_measurement=False,
                  limitation='Instrumented whole-run counts, not latency. Rendered operation labels only; operand or safety analysis requires typed bytecode. Guest randomness is unchanged.')
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    write(out / 'summary.json', report)
    print(json.dumps(attribution['by_rendered_variant']), flush=True)


if __name__ == '__main__':
    main()
