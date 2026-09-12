#!/usr/bin/env python3
"""Bound a saved-program JIT attribution run to previously qualified inputs."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import compare_saved_runtime as compare
from interpreter import installed_tools
from workflow_io import write_json as write

CONTROL = '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'jit-merged-token-\d{2}', args.run_id)
    build_path = ROOT / 'results/fixed-frame-clear-combined-build-01/summary.json'
    token_path = ROOT / 'results/fixed-frame-clear-entropy-token-01/summary.json'
    entropy_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
    manifest_path = ROOT / '.work/fixed-frame-clear-combined-runtime-inputs-02/manifest.json'
    build, token = [json.loads(p.read_text()) for p in [build_path, token_path]]
    assert build['status'] == token['status'] == 'passed'
    assert build['tests']['baseline-test-release'] == dict(passed=297, failed=0, ignored=1)
    assert build['commits']['baseline'] == 'ae0a49e'
    subprocess.run(['git', 'diff', '--exit-code', 'ae0a49e', 'HEAD', '--', 'crates/bytecode'], cwd=ROOT, check=True)
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--', 'crates/bytecode'], cwd=ROOT)
    baseline, _ = installed_tools(CONTROL)
    candidate, key = installed_tools(build['installed_tools']['baseline']['tool_key'])
    assert compare.sha(candidate / 'rust-interp-vm') == build['vm_sha256']['baseline']
    assert compare.sha(baseline / 'rust-interp-vm') == '21d1e163a603aaf9d6f3238fd1057293c73afc41d17b5f73779b2d3188169ca9'
    case = next(c for c in json.loads(manifest_path.read_text()) if c['name'] == 'token-phrase')
    assert case['artifact_sha256'] == token['artifact_sha256']
    case['entropy_tapes'] = [dict(path=str(ROOT / token['raw'] / (str(s['stream']) + '.tape')),
        sha256=s['tape_sha256'], calls=s['values']['entropy_calls'], bytes=s['values']['entropy_bytes'])
        for s in token['streams']]
    paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), build_path, token_path, entropy_path,
             manifest_path, ROOT / 'scripts/compare_saved_runtime.py', ROOT / 'scripts/interpreter.py']
    paths += sorted((ROOT / 'crates/bytecode').rglob('*.rs'))
    frozen = {str(p.relative_to(ROOT)): compare.sha(p) for p in paths}
    work = ROOT / '.work' / (args.run_id + '-inputs')
    work.mkdir(exist_ok=False)
    write(work / 'manifest.json', [case])
    write(work / 'provenance.json', dict(frozen=frozen, candidate_key=key, baseline_key=CONTROL,
        source_equivalent_to='ae0a49e', source_scope='crates/bytecode Rust sources; installed qualified VM',
        minimum_free_bytes=8 * 1024**3, whole_command_measurement=False))
    original_acquire = compare.acquire_lock
    def acquire(lock, wait):
        original_acquire(lock, wait)
        assert shutil.disk_usage(ROOT).free >= 8 * 1024**3, 'disk floor; no guest execution started'
    compare.acquire_lock = acquire
    old_argv = sys.argv
    sys.argv = [str(ROOT / 'scripts/compare_saved_runtime.py'), '--baseline', str(baseline / 'rust-interp-vm'),
        '--candidate', str(candidate / 'rust-interp-vm'), '--manifest', str(work / 'manifest.json'),
        '--output', str(ROOT / '.work' / args.run_id), '--lock', str(ROOT / '.work/benchmark.lock'),
        '--lock-wait-seconds', '45', '--repetitions', '6', '--engines', 'jit',
        '--entropy-qualification', str(entropy_path)]
    try:
        compare.main()
    finally:
        compare.acquire_lock = original_acquire
        sys.argv = old_argv
    assert all(compare.sha(ROOT / p) == h for p, h in frozen.items())
    raw = ROOT / '.work' / args.run_id
    summary = json.loads((raw / 'summary.json').read_text())
    assert summary['status'] == 'passed' and summary['commands'] == 14
    for line in (raw / 'commands.jsonl').read_text().splitlines():
        row = json.loads(line)
        expected = token['streams'][row['entropy']['stream']]['values']
        assert all(row['statistics'].get(k) == v for k, v in expected.items())
    summary.update(raw=str(raw.relative_to(ROOT)), baseline_key=CONTROL, candidate_key=key,
        source_equivalent_to='ae0a49e', qualified_entropy_counters_unchanged=True,
        whole_command_measurement=False, adoption_gate=False,
        provenance_sha256=compare.sha(work / 'provenance.json'))
    result = ROOT / 'results' / args.run_id
    result.mkdir(exist_ok=False)
    write(result / 'summary.json', summary)


if __name__ == '__main__':
    main()
