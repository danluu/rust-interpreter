#!/usr/bin/env python3
"""Three predeclared real es8 edit histories; retain every cycle and outcome."""
import argparse
import json
import os
from pathlib import Path
import statistics
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from qualify_test_bodies import read, require, sha, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    run = parser.parse_args().run_id
    require(re.fullmatch(r'fixed-frame-clear-confirm-\d{2}', run), 'invalid confirmation run ID')
    work = ROOT / '.work' / run
    work.mkdir(exist_ok=False)
    pilot_path = ROOT / 'results/fre-integration-fixed-clear-edit-02/summary.json'
    pilot = read(pilot_path)
    require(pilot['status'] == 'passed' and pilot['pilot_target_met'], 'pilot did not pass')
    recipe = ROOT / 'benchmarks/experiments/test-targets/edit.py'
    tools = ROOT / '.work/fixed-frame-clear-01/installed-tools.json'
    paths = [Path(__file__), recipe, tools, pilot_path,
             ROOT / 'benchmarks/experiments/frame-initialization/FIXED-QUALIFICATION.md']
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    write(work / 'plan.json', dict(histories=3, offsets=[0, 1, 2], frozen=frozen,
        target_wall_ratio=.92, cpu_ratio_below=1, primary_pairs=15, pilot_excluded=True,
        cache_state='Warm caches from the completed pilot, then each preceding history; no cold claim.'))
    status = dict(status='starting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), completed=[])
    write(work / 'status.json', status)
    cycles, pairs = [], []
    try:
        for index in range(3):
            require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'confirmation recipe changed')
            child_run = 'fre-integration-' + run + '-cycle-' + str(index + 1).zfill(2)
            command = [sys.executable, str(recipe), '--case', 'es8', '--run-id', child_run,
                       '--comparison-tools', str(tools), '--initial-mode-offset', str(index), '--lock-wait-seconds', '45']
            with (work / (str(index) + '.log')).open('x') as log:
                child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                status.update(status='running', cycle=index, child_pid=child.pid, command=command, child_started_at=time.time(),
                    child_identity=subprocess.run(['ps', '-p', str(child.pid), '-o', 'pid,ppid,lstart,tty,command'],
                        capture_output=True, text=True).stdout)
                write(work / 'status.json', status)
                print('START', index, child.pid, flush=True)
                code = child.wait()
            status.update(child_returncode=code, child_finished_at=time.time())
            write(work / 'status.json', status)
            require(code == 0, 'history incomplete; retain the failed receipt')
            path = ROOT / 'results' / child_run / 'summary.json'
            report = read(path)
            require(report['status'] == 'passed' and report['commands'] == 32 and report['edited_pairs'] == 5,
                    'history command coverage differs')
            require(report['source_restored'] and report['paired_bytecode_identical']
                    and report['restoration_recompiled_all_modes'], 'history correctness or restoration differs')
            require(report['tool_key'] == pilot['tool_key'] and report['baseline_tool_key'] == pilot['baseline_tool_key'],
                    'comparison tools changed')
            records_path = ROOT / report['raw'] / 'records.json'
            require(sha(records_path) == report['records_sha256'], 'command records changed')
            for row in read(records_path):
                for stream in ['stdout', 'stderr']:
                    require(sha(ROOT / row[stream]) == row[stream + '_sha256'], 'command output changed')
                if 'snapshot' in row:
                    require(sha(ROOT / row['snapshot']) == row['launch']['artifact_sha256'], 'executed snapshot changed')
            cycles.append(dict(cycle=index, report=str(path.relative_to(ROOT)), report_sha256=sha(path),
                wall_ratio=report['paired_median_wall_ratio'], cpu_ratio=report['paired_median_cpu_ratio'],
                median_seconds=report['median_seconds']))
            pairs.extend(dict(cycle=index, **pair) for pair in report['pairs'])
            status['completed'].append(index)
            write(work / 'status.json', status)
            write(work / 'cycles.json', cycles)
            print('PASS protocol', index, cycles[-1]['wall_ratio'], flush=True)
        require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'confirmation input changed')
        wall = statistics.median(p['wall_ratio'] for p in pairs)
        cpu = statistics.median(p['cpu_ratio'] for p in pairs)
        summary = dict(status='passed', gate_passed=wall <= .92 and cpu < 1, wall_ratio=wall, cpu_ratio=cpu,
            target_wall_ratio=.92, commands=96, edited_pairs=15, artifacts=48, source_restored=True,
            paired_bytecode_identical=True, baseline_tool_key=pilot['baseline_tool_key'], tool_key=pilot['tool_key'],
            cycles=cycles, pairs=pairs, frozen=frozen, raw=str(work.relative_to(ROOT)),
            scope='Three complete warm production-edit histories. Pilot excluded; no cold-build or whole-suite claim.')
        out = ROOT / 'results' / run
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', summary)
        status.update(status='finished', returncode=0, gate_passed=summary['gate_passed'], finished_at=time.time())
        write(work / 'status.json', status)
        print(json.dumps({k: summary[k] for k in ['gate_passed', 'wall_ratio', 'cpu_ratio', 'commands', 'edited_pairs']}), flush=True)
    except Exception as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__':
    main()
