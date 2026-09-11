#!/usr/bin/env python3
"""Run predeclared real source edits with the isolated aggregate-relocating compiler."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from build_relocation import ROOT, PARENT, installed_tools
from check_comparison import expected_tools
from interpreter import installed_tools
from verify_repeated_workflow import require
from verify_relocation import verify
from workflow_space import required_bytes, admit

HERE = Path(__file__).resolve().parent
TOOLS = expected_tools()
KEY=TOOLS['candidate']['tool_key']


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def write(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(path)


def assess(report):
    verification = verify(report, TOOLS)
    require(verification['commands'] == 63 and verification['check_commands'] == 21 and
            verification['edited_pairs'] == 15 and verification['exact_artifact_hashes_verified'] == 42,
            'unexpected workflow coverage')
    rows = read(ROOT / report['raw'] / 'records.json')
    paired = []
    for cycle in range(3):
        for state in range(1, 6):
            modes = {r['mode']: r for r in rows if r['cycle'] == cycle and r['state'] == state}
            ordinary, enlarged = modes['candidate'], modes['baseline']
            pair = dict(cycle=cycle, state=state,
                wall_ratio=ordinary['seconds'] / enlarged['seconds'],
                cpu_ratio=ordinary['cpu_seconds'] / enlarged['cpu_seconds'])
            paired.append(pair)
    median = statistics.median
    wall, cpu = (median(p[k] for p in paired) for k in ('wall_ratio', 'cpu_ratio'))
    limit = .9 if report['workflow'] == 'folded-literal-trie' else 1.05
    cpu_limit = 1.0 if limit == .9 else 1.05
    stages = {}
    for mode in ['baseline', 'candidate']:
        launches = [r['calls'][0]['launch'] for r in rows if r['state'] > 0 and r['mode'] == mode]
        stages[mode] = {key: median(l[key] for l in launches) for key in
                       ['cargo_seconds', 'execution_seconds', 'launcher_seconds', 'artifact_bytes']}
    return dict(verification=verification, wall_ratio_candidate_over_baseline=wall,
        cpu_ratio_candidate_over_baseline=cpu, wall_limit=limit, cpu_limit=cpu_limit,
        passed=wall <= limit and (cpu < cpu_limit if cpu_limit == 1 else cpu <= cpu_limit),
        median_seconds=report['median_seconds'], median_cpu_seconds=report['median_cpu_seconds'],
        stages=stages, exporter_seconds=report['exporter_seconds'], pairs=paired,
        limitation='Compiler settings change artifacts, lowering, frame layout and instruction count. Original native/assertion controls pass; artifact semantic equivalence is not formally proven. Three cycles are descriptive, not independent statistical trials.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['folded-literal-trie', 'token-phrase'], required=True)
    args = parser.parse_args()
    run = 'aggregate-relocation-e2e-01-' + args.case
    work = ROOT / '.work' / run
    work.mkdir(exist_ok=False)
    status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
    write(work / 'status.json', status)
    try:
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            qualified = read(ROOT / 'results/aggregate-relocation-controls-01/summary.json')
            require(qualified['status'] == 'passed' and qualified['historical_reports'] == 6 and
                    len(qualified['rejected']) == 19, 'compiler comparison verifier not qualified')
            require(all(sha(ROOT / p) == digest for p, digest in qualified['sources'].items()), 'qualified verifier changed')
            if args.case == 'token-phrase':
                require(read(ROOT / '.work/aggregate-relocation-e2e-01-folded-literal-trie/status.json')['status'] == 'finished',
                        'fixed preceding workflow not finished')
            for mode,t in TOOLS.items():
                directory,_=installed_tools(t['tool_key'])
                for name,field in [('rust-interp-vm','vm_sha256'),('rust-interp-mir-export','exporter_sha256'),('rust-interp-rustc-wrapper','wrapper_sha256')]:
                    require(sha(directory/name)==t[field],'bound tool changed')
            require(read(ROOT/'results/aggregate-relocation-smoke-01/summary.json')['status']=='passed','original smoke incomplete')
            focused=read(ROOT/'results/aggregate-relocation-fixtures-01/summary.json')
            require(focused['status']=='passed' and focused['vm_executions']==1024 and focused['strict_rejections']==2,'focused qualification incomplete')
            case = next(c for c in read(ROOT / 'benchmarks/workflow-corpus.json')['cases'] if c['label'] == args.case)
            estimate = required_bytes(cache_bytes=4 * 1024**3, growth_percent=20, command_floor_bytes=8 * 1024**3,
                archive_reserve_bytes=2 * 1024**3, evidence_reserve_bytes=256 * 1024**2)
            fs = os.statvfs(ROOT); free = fs.f_bavail * fs.f_frsize
            admission = dict(checked_at=time.time(), observed_free_bytes=free, estimate=estimate, passed=admit(free, estimate))
            write(work / 'admission.json', admission)
            require(admission['passed'], 'insufficient space; benchmark not started')
            command = [sys.executable, str(ROOT / 'scripts/bench_e2e_workflow.py'), '--run-id', run,
                '--project', case['project'], '--workflow', case['workflow'], '--cycles', '3', '--jobs', '4',
                '--native-jobs', '18', '--native-profile', 'o0-incremental', '--native-test-threads', 'default',
                '--check-floor', '--minimum-free-gib', '8', '--candidate-tool-key', KEY, '--baseline-tool-key', PARENT,
                '--comparison-engine', 'jit', '--candidate-jit-resumable-calls', '--candidate-jit-persistent-registers',
                '--baseline-jit-resumable-calls', '--baseline-jit-persistent-registers',
                *case['flags']]
            paths = [HERE / name for name in ['RELOCATION-NEXT.md', 'check_comparison.py', 'verify_relocation.py', 'run_relocation.py', 'build_relocation.py']]
            paths += [ROOT / 'scripts' / name for name in ['bench_e2e_workflow.py', 'interpreter.py', 'workflow_cases.py',
                'workflow_case_file.py', 'workflow_controls.py', 'workflow_measurements.py', 'workflow_io.py',
                'std_mir.py', 'workflow_jobs.py', 'verify_repeated_workflow.py', 'workflow_space.py']]
            paths += [ROOT / 'benchmarks/workflow-corpus.json', ROOT / 'results/aggregate-relocation-controls-01/summary.json']
            frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
            write(work / 'plan.json', dict(command=command, frozen=frozen, expected_tools=TOOLS,
                tool_key=KEY, baseline_tool_key=PARENT, experiment='private aggregate relocation',
                source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()))
        require(time.time() - admission['checked_at'] < 60, 'space admission expired')
        with (work / 'command.log').open('x') as log:
            child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            status.update(status='running', child_pid=child.pid, child_started_at=time.time(), command=command,
                child_identity=subprocess.check_output(['ps', '-p', str(child.pid), '-o', 'pid,ppid,lstart,tty,command'], text=True))
            write(work / 'status.json', status)
            code = child.wait()
        status.update(child_returncode=code, child_finished_at=time.time())
        write(work / 'status.json', status)
        require(code == 0, 'workflow failed; preserve original evidence')
        with (ROOT / '.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(all(sha(ROOT / p) == digest for p, digest in frozen.items()), 'frozen experiment changed')
            path = ROOT / 'results' / run / 'summary.json'
            report = read(path)
            result = assess(report)
            result.update(run_id=run, expected_tools=TOOLS, experiment='private aggregate relocation',
                evidence={str(path.relative_to(ROOT)): sha(path), **frozen})
            write(path.with_name('relocation-assessment.json'), result)
            path.with_name('relocation-assessment.md').write_text(
                f"# {args.case}: private aggregate frame relocation\n\n"
                f"Predeclared gate **{'passes' if result['passed'] else 'fails'}**. Candidate/control paired wall ratio "
                f"{result['wall_ratio_candidate_over_baseline']:.6f}; CPU ratio {result['cpu_ratio_candidate_over_baseline']:.6f}. "
                f"Medians: control {report['median_seconds']['baseline']:.3f}s, candidate {report['median_seconds']['candidate']:.3f}s, native {report['median_seconds']['native']:.3f}s.\n\n"
                '63 primary commands, 21 Cargo-check controls, 15 edited pairs and 42 artifact hashes verified. '
                'The same VM, wrapper, MIR policy and runtime options are retained; only the exporter changes.\n\n' + result['limitation'] + '\n')
        status.update(status='finished', finished_at=time.time(), passed=result['passed'])
        write(work / 'status.json', status)
        print(json.dumps({k:result[k] for k in ['run_id', 'passed', 'wall_ratio_candidate_over_baseline', 'cpu_ratio_candidate_over_baseline', 'median_seconds', 'stages']}))
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__': main()
