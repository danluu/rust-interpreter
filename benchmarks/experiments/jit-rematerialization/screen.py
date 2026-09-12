#!/usr/bin/env python3
"""One fixed six-pair runtime rejection screen, before edited-command timing."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import compare_saved_runtime as compare
from interpreter import installed_tools
from workflow_io import write_json as write
from build import CONTROL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'jit-remat-screen-\d{2}', args.run_id)
    build_path = args.build.resolve()
    build = json.loads(build_path.read_text())
    assert build['status'] == 'passed'
    assert build['tests']['test-debug'] == build['tests']['test-release']
    assert build['tests']['test-debug'] == dict(passed=315, ignored=1)
    assert build['composition']['exporter_and_wrapper_key'] == CONTROL
    baseline, _ = installed_tools(CONTROL)
    candidate, key = installed_tools(build['tool_key'])
    manifest = ROOT / '.work/jit-merged-token-01-inputs/manifest.json'
    qualification = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
    original = ROOT / 'results/fixed-frame-clear-entropy-token-01/summary.json'
    expected = json.loads(original.read_text())
    cases = json.loads(manifest.read_text())
    assert len(cases) == 1 and cases[0]['artifact_sha256'] == expected['artifact_sha256']
    paths = [Path(__file__).resolve(), Path(__file__).with_name('PLAN.md').resolve(), build_path,
             manifest, qualification, original, ROOT / 'scripts/compare_saved_runtime.py']
    frozen = {str(p.relative_to(ROOT)): compare.sha(p) for p in paths}
    original_acquire = compare.acquire_lock
    def acquire(lock, seconds):
        original_acquire(lock, seconds)
        assert shutil.disk_usage(ROOT).free >= 8 * 1024**3, 'disk floor; no execution started'
    old_argv = sys.argv
    compare.acquire_lock = acquire
    sys.argv = [str(ROOT / 'scripts/compare_saved_runtime.py'), '--baseline', str(baseline / 'rust-interp-vm'),
        '--candidate', str(candidate / 'rust-interp-vm'), '--manifest', str(manifest),
        '--output', str(ROOT / '.work' / args.run_id), '--lock', str(ROOT / '.work/benchmark.lock'),
        '--lock-wait-seconds', '45', '--repetitions', '6', '--engines', 'jit',
        '--entropy-qualification', str(qualification)]
    try:
        compare.main()
    finally:
        compare.acquire_lock = original_acquire
        sys.argv = old_argv
    assert all(compare.sha(ROOT / p) == h for p, h in frozen.items())
    work = ROOT / '.work' / args.run_id
    summary = json.loads((work / 'summary.json').read_text())
    assert summary['status'] == 'passed' and summary['commands'] == 14
    stages = []
    for line in (work / 'commands.jsonl').read_text().splitlines():
        row = json.loads(line)
        counts = expected['streams'][row['entropy']['stream']]['values']
        assert all(row['statistics'].get(k) == v for k, v in counts.items())
        assert row['statistics']['jit_declined_functions'] == 0, 'code growth caused JIT declines'
        stages.append(dict(mode=row['mode'], repetition=row['repetition'],
            statistics=row['statistics']))
    row = summary['rows'][0]
    wall = row['seconds']['median_paired_percent']
    cpu = row['cpu_seconds']['median_paired_percent']
    passed = wall <= -10 and cpu <= 0
    summary.update(frozen=frozen, baseline_key=CONTROL, candidate_key=key,
        raw=str(work.relative_to(ROOT)), runtime_screen_passed=passed,
        runtime_wall_percent_gate=-10, cpu_percent_gate=0,
        decision='Proceed to fresh five-edit end-to-end screen' if passed else 'Park this candidate; no retiming',
        qualified_entropy_counters_unchanged=True, jit_declines=0, whole_command_measurement=False)
    write(work / 'statistics.json', stages)
    result = ROOT / 'results' / args.run_id
    result.mkdir(exist_ok=False)
    write(result / 'summary.json', summary)
    print(summary['decision'], flush=True)


if __name__ == '__main__':
    main()
