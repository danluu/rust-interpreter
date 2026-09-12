#!/usr/bin/env python3
"""Compare the two VMs on exact original-source benchmark artifacts."""
import argparse
import fcntl
import os
from pathlib import Path
import re
import subprocess
import time

from build import ROOT, environment, installed_tools, read, require, sha, write
from build_budget_register import CONTROL


def counters(text):
    result = {}
    for line in text.splitlines():
        if re.fullmatch(r'[a-z_]+=\d+(?: [a-z_]+=\d+)*', line):
            for name, value in re.findall(r'([a-z_]+)=(\d+)', line):
                require(name not in result, 'duplicate VM statistic')
                result[name] = int(value)
    require(result.get('instructions', 0) > 0, 'missing instruction count')
    require(result.get('jit_resumable_calls', 0) > 0, 'native calls not exercised')
    require(result.get('jit_declined_functions') == 0, 'unexpected JIT decline')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'budget-register-smoke-[0-9]{2}', args.run_id), 'invalid run ID')
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        work = ROOT/'.work'/args.run_id
        work.mkdir(exist_ok=False)
        status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
        write(work/'status.json', status)
        try:
            build_path = ROOT/'results/budget-register-build-02/summary.json'
            build = read(build_path)
            proof = read(ROOT/build['provenance'])
            require(build['status'] == 'passed' and build['control_tool_key'] == CONTROL,
                    'unqualified candidate')
            require(sha(ROOT/build['provenance']) == build['provenance_sha256'], 'build proof changed')
            tools = {mode: installed_tools(key)[0] for mode, key in
                     [('baseline', CONTROL), ('candidate', build['tool_key'])]}
            require(all(sha(tools['candidate']/n) == h for n, h in build['binaries'].items()),
                    'candidate binary changed')
            for name in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']:
                require(sha(tools['baseline']/name) == sha(tools['candidate']/name), 'frontend differs')
            paths = [Path(__file__), build_path, ROOT/build['provenance']]
            paths += [directory/name for directory in tools.values() for name in build['binaries']]
            frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
            frozen.update(proof['root_frozen'])
            artifacts = {}
            for label in ['folded-literal-trie', 'token-phrase']:
                records = ROOT/'.work/runs'/('aggregate-relocation-e2e-01-'+label)/'records.json'
                rows = [r for r in read(records) if r['cycle'] == r['state'] == 0 and r['mode'] == 'candidate']
                require(len(rows) == 1 and len(rows[0]['artifacts']) == 1, 'original source record missing')
                artifact = records.parent/'artifacts/candidate/cycle-0/0-0.rbc'
                require(sha(artifact) == rows[0]['artifacts'][0]['sha256'], 'original artifact changed')
                artifacts[label] = artifact
                frozen.update({str(p.relative_to(ROOT)): sha(p) for p in [records, artifact]})
            write(work/'plan.json', dict(frozen=frozen, tools={k:str(v.relative_to(ROOT)) for k,v in tools.items()},
                performance_measurement=False, original_source_artifacts=True))

            def verify():
                require(all(sha(ROOT/p) == h for p,h in frozen.items()), 'frozen input changed')
                require(all(sha(ROOT/proof['source']/p) == h for p,h in proof['copied_inputs'].items()),
                        'candidate source changed')

            commands, cases = [], []
            env = environment()
            env['RUST_INTERP_VM_STATS'] = '1'

            def run(label, mode, budget, profile=False):
                verify()
                fs = os.statvfs(ROOT)
                require(fs.f_bavail*fs.f_frsize >= 8*1024**3, 'pre-command space floor')
                index = len(commands)
                profile_path = work/(str(index)+'-profile.json')
                command = [str(tools[mode]/'rust-interp-vm'), '--engine', 'jit',
                    '--jit-resumable-calls', '--jit-persistent-registers',
                    '--instruction-limit', str(budget), '--allocation-limit', '150000']
                if profile:
                    command += ['--profile', str(profile_path)]
                command.append(str(artifacts[label]))
                start = time.time()
                with (work/(str(index)+'.stdout')).open('x') as out, (work/(str(index)+'.stderr')).open('x') as err:
                    child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
                    try:
                        status.update(status='running', child_pid=child.pid, child_started_at=start, command=command)
                        write(work/'status.json', status)
                    finally:
                        code = child.wait()
                stdout, stderr = Path(out.name).read_text(), Path(err.name).read_text()
                paths = [Path(out.name), Path(err.name)] + ([profile_path] if profile_path.exists() else [])
                row = dict(label=label, mode=mode, budget=budget, profiled=profile, command=command,
                    pid=child.pid, parent_pid=os.getpid(), started_at=start, finished_at=time.time(), returncode=code,
                    files={str(p.relative_to(ROOT)):sha(p) for p in paths})
                commands.append(row)
                write(work/'commands.json', commands)
                return code, stdout, stderr, profile_path

            for label in artifacts:
                observed, profiles = {}, {}
                for mode in tools:
                    for profiled in [False, True]:
                        code, stdout, stderr, profile_path = run(label, mode, 100_000_000_000, profiled)
                        require(code == 0 and stdout.strip() == '0', 'original assertions failed')
                        stats = counters(stderr)
                        # Code size changes; compilation timings are nondeterministic.
                        observed[mode, profiled] = {k:v for k,v in stats.items()
                            if k not in ['jit_bytes', 'jit_compile_ns', 'jit_tree_compile_ns']}
                        if profiled:
                            profiles[mode] = read(profile_path)
                require(all(v == observed['baseline', False] for v in observed.values()), 'observable counters differ')
                require(profiles['baseline'] == profiles['candidate'], 'exact per-PC profiles differ')
                total = observed['baseline', False]['instructions']
                for budget in [0, 1, total-1]:
                    failures = [run(label, mode, budget)[:3] for mode in tools]
                    require(all(code != 0 and not out.strip() and err.strip() == 'rust-interp-vm: interpreter instruction limit exceeded'
                                for code,out,err in failures), 'short budget did not produce the exact limit fault')
                cases.append(dict(label=label, artifact=str(artifacts[label].relative_to(ROOT)),
                    artifact_sha256=sha(artifacts[label]), counters=observed['baseline', False],
                    profiles_identical=True, original_assertions_pass=True, short_budgets=[0,1,total-1]))
                print(label, 'PASS', flush=True)
            verify()
            result = dict(status='passed', tool_key=build['tool_key'], control_tool_key=CONTROL,
                cases=cases, commands=commands, frozen=frozen, performance_measurement=False,
                note='Exact original artifacts, unchanged assertions, matched counters/profiles and short budgets. No compilation timing or performance claim.')
            out = ROOT/'results'/args.run_id
            out.mkdir(exist_ok=False)
            write(out/'summary.json', result)
            status.update(status='finished', returncode=0, finished_at=time.time())
            write(work/'status.json', status)
        except BaseException as error:
            status.update(status='failed', error=repr(error), finished_at=time.time())
            write(work/'status.json', status)
            raise


if __name__ == '__main__':
    main()
