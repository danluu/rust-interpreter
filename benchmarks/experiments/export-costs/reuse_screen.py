#!/usr/bin/env python3
"""Run the existing paired edit benchmark with a qualified reuse-only adapter."""
import argparse
import json
from pathlib import Path
import re
import shutil
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import sha
from interpreter import installed_tools
from workflow_io import write_json as write
from reuse_build import CONTROL
from reuse_profile import REFERENCES
from reuse_check import actual_cache
import bench_e2e_workflow as bench
from verify_repeated_workflow import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=REFERENCES, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--qualification', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch('export-reuse-screen-' + args.case + r'-\d{2}', args.run_id)
    build_path, qualification_path = args.build.resolve(), args.qualification.resolve()
    build, qualification = [json.loads(p.read_text()) for p in [build_path, qualification_path]]
    assert build['status'] == qualification['status'] == 'passed' and min(build['tests'].values()) >= 51
    assert qualification['tool_key'] == build['tool_key'] and qualification['commands'] == 8
    assert qualification['actual_skipped_lowering'] and qualification['all_artifact_hashes_identical']
    assert qualification['source_restored'] and qualification['wrong_edit_rejected']
    tool, key = installed_tools(build['tool_key'])
    retained, _ = installed_tools(CONTROL)
    reference_path = ROOT / 'results' / REFERENCES[args.case] / 'summary.json'
    reference = json.loads(reference_path.read_text())
    assert reference['project'] == qualification['project'] == 'fre'
    assert reference['workflow'] == qualification['workflow'] and reference['revision'] == qualification['revision']
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    paths = [Path(__file__), HERE / 'SCREEN.md', HERE / 'reuse_execute_launcher.py', HERE / 'reuse_check.py',
             HERE / 'reuse_profile.py', HERE / 'reuse_build.py', build_path, qualification_path, reference_path]
    paths += [ROOT / 'scripts' / n for n in ['bench_e2e_workflow.py', 'interpreter.py', 'workflow_io.py',
              'workflow_controls.py', 'workflow_measurements.py', 'workflow_cases.py', 'workflow_case_file.py',
              'workflow_jobs.py', 'verify_repeated_workflow.py', 'std_mir.py']]
    paths += [p / n for p in [tool, retained] for n in ['rust-interp-mir-export', 'rust-interp-vm', 'rust-interp-rustc-wrapper']]
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    required = 10 * 1024**3
    write(work / 'admission.json', dict(required_free_bytes=required, observed_free_bytes=shutil.disk_usage(ROOT).free))
    assert shutil.disk_usage(ROOT).free >= required, 'insufficient screen storage; source is unchanged'
    native = reference['native_control']
    command = [str(ROOT / 'scripts/bench_e2e_workflow.py'), '--run-id', args.run_id,
        '--project', 'fre', '--workflow', reference['workflow'], '--batch', '--cycles', '1',
        '--jobs', str(reference['build_jobs']), '--native-jobs', str(native['jobs']),
        '--native-profile', native['profile'], '--native-test-threads', native['test_threads'],
        '--baseline-tool-key', CONTROL, '--candidate-tool-key', key,
        '--comparison-engine', 'jit', '--expect-identical-bytecode', '--check-floor', '--std-mir',
        '--baseline-jit-resumable-calls', '--candidate-jit-resumable-calls',
        '--baseline-jit-persistent-registers', '--candidate-jit-persistent-registers',
        '--baseline-inline-leaves', '--inline-leaves', '--trap-unsupported-calls', '--run-try-callbacks',
        '--instruction-limit', str(reference['instruction_limit']), '--allocation-limit', str(reference['allocation_limit']),
        '--guest-mir-opt-level', str(reference['guest_mir_opt_level']), '--build-tool-opt-level', str(reference['build_tool_opt_level'])]
    command += ['--native-rustflag=' + value for value in native['rustflags']]
    if reference['guest_mir_inline_scale'] is not None:
        command += ['--guest-mir-inline-scale', str(reference['guest_mir_inline_scale'])]
    write(work / 'plan.json', dict(frozen=frozen, command=command, candidate_launcher=str(HERE / 'reuse_execute_launcher.py'),
        candidate_tool_key=key, baseline_tool_key=CONTROL, wall_ratio_limit=0.92, cpu_ratio_limit=1.02,
        cycles=1, edited_pairs=5, fresh_caches=True, actual_skipped_lowering=True,
        attribution='Combined cache, bulk-payload and SHA backend change; retained VM/wrapper.'))
    original_capture = bench.capture
    cache_reports = []
    def capture(command, **kwargs):
        receipt = kwargs['receipt']
        candidate = receipt.get('mode') == 'candidate'
        if candidate:
            assert Path(command[1]) == ROOT / 'scripts/interpreter.py'
            assert command[command.index('--tool-key') + 1] == key
            # Mutate this owned command list so the benchmark records exactly
            # what it executes, including the launcher inside its timed region.
            command[1] = str(HERE / 'reuse_execute_launcher.py')
        return original_capture(command, **kwargs)
    old_argv = sys.argv
    sys.argv = command
    bench.capture = capture
    try:
        bench.main()
    finally:
        bench.capture = original_capture
        sys.argv = old_argv
    assert all(sha(ROOT / p) == h for p, h in frozen.items())
    result_dir = ROOT / 'results' / args.run_id
    report = json.loads((result_dir / 'summary.json').read_text())
    # Extra cache diagnostics and file verification stay outside command time.
    rows = json.loads((ROOT / report['raw'] / 'records.json').read_text())
    for row in rows:
        if row['mode'] == 'candidate':
            assert len(row['calls']) == 1
            cached = actual_cache(row['calls'][0]['stderr'])
            assert cached['skipped_functions'] == 0 if row['phase'] == 'cold' else cached['skipped_functions'] > 0
            cache_reports.append(dict(cycle=row['cycle'], state=row['state'], **cached))
    write(work / 'cache-reports.json', cache_reports)
    verification = verify(report)
    assert len(cache_reports) == 7 and len(report['comparison']['pairs']) == 5
    ratios = [dict(state=p['state'], wall=p['candidate_seconds'] / p['baseline_seconds'],
                   cpu=p['candidate_cpu_seconds'] / p['baseline_cpu_seconds']) for p in report['comparison']['pairs']]
    wall = statistics.median(p['wall'] for p in ratios)
    cpu = statistics.median(p['cpu'] for p in ratios)
    decision = dict(status='passed' if wall <= 0.92 and cpu <= 1.02 else 'screen failed',
        wall_ratio=wall, cpu_ratio=cpu, wall_ratio_limit=0.92, cpu_ratio_limit=1.02, pairs=ratios,
        verification=verification, actual_cache_reports=cache_reports, plan_sha256=sha(work / 'plan.json'),
        measurement='One-cycle continuation screen, not confirmation; cold samples reported separately.',
        next='Run heldouts and fresh confirmation' if wall <= 0.92 and cpu <= 1.02 else 'Do not retime this candidate; use recorded costs to choose another implementation boundary')
    write(result_dir / 'verification.json', verification)
    write(result_dir / 'decision.json', decision)
    print(json.dumps(decision, indent=2), flush=True)


if __name__ == '__main__':
    main()
