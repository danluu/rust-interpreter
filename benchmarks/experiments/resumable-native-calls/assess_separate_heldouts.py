#!/usr/bin/env python3
"""Verify all seven predeclared held-out histories completed in separate corpora."""
import argparse
import fcntl
import json
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/bounded-native-calls'))
import evaluate_gates as gates

KEY = '0e94d6d82b4b734e281e5b8c95a55866e5c7b0a8be53be2dafadd410708467ee'
SOURCE = 'aa2f6ea213ee04408b9f47b9be1a0fd129ed850d'
ORDER = ['nushell-type-relations', 'ruff', 'nushell', 'forward-anchored-tls',
         'pgrust-sha1-inline8', 'pgrust', 'rg-aot']
OPTIONS = dict(candidate_tool_key=KEY, baseline_tool_key=gates.BASELINE,
    candidate_jit_native_call_stubs=False, candidate_jit_resumable_calls=True,
    candidate_jit_persistent_registers=True, candidate_jit_native_calls=False,
    baseline_jit_resumable_calls=False, baseline_jit_persistent_registers=False,
    cycles=3, jobs=4, native_jobs=18, baseline_jobs=None, candidate_jobs=None,
    native_profile='o0-incremental', native_test_threads='default', native_rustflag=[],
    lock_wait_seconds=600, minimum_free_gib=8)


def validate_plan(plan):
    gates.require(plan['schema_version'] == 1 and plan['owner'] == str(ROOT) and
        plan['run_id'] == 'resumable-copy-heldout-01' and plan['source_commit'] == SOURCE and
        plan['options'] == OPTIONS, 'separate held-out plan identity or controls differ')
    expected = [dict(label=label, run_id=plan['run_id'] + f'-case-{i:02}') for i, label in enumerate(ORDER, 1)]
    gates.require(plan['cases'] == expected and set(ORDER) == gates.HELD_OUT,
                  'all seven cases, fixed order and independent identities are required')
    return expected


def combine(plan, components):
    """Combine already verified cases; never turn a partial set into a complete one."""
    cases = validate_plan(plan)
    gates.require(len(components) == len(cases), 'incomplete held-out component set')
    counts = dict(primary_commands=0, check_commands=0, edited_pairs=0, artifacts=0)
    rows = []
    for case, (checked, evaluated) in zip(cases, components):
        gates.require(evaluated['held_out_case'] == case['label'] and
            evaluated['held_out_workflows_run'] is False and evaluated['retained'] is False and
            evaluated['source_commit'] == SOURCE and evaluated['tool_key'] == KEY and
            evaluated['baseline_tool_key'] == gates.BASELINE and len(evaluated['evaluated']) == 1 and
            evaluated['evaluated'][0]['workload'] == case['label'], 'component identity or scope differs')
        gates.require(checked['counts'] == dict(primary_commands=63, check_commands=21, edited_pairs=15, artifacts=42),
                      'incomplete component command counts')
        row = evaluated['evaluated'][0]
        gates.require(row['target_max_ratio'] == 1.05 and row['passed'] == (row['median_paired_ratio'] <= 1.05),
                      'component wall gate changed')
        for key in counts:
            counts[key] += checked['counts'][key]
        rows.append(dict(**case, evaluation=row))
    gates.require(counts == dict(primary_commands=441, check_commands=147, edited_pairs=105, artifacts=294),
                  'incomplete seven-case totals')
    return dict(status='all seven separately completed histories verified', source_commit=SOURCE, tool_key=KEY,
        baseline_tool_key=gates.BASELINE, counts=counts, workflows=rows, retained=False,
        held_out_workflows_run=True, held_out_wall_checks_passed=all(r['evaluation']['passed'] for r in rows),
        wall_regressions_above_5_percent=[r['label'] for r in rows if not r['evaluation']['passed']],
        cpu_regressions_above_5_percent=[r['label'] for r in rows if r['evaluation']['median_paired_cpu_ratio'] > 1.05],
        note='Every original case, edit, repetition and control is required. Histories remain independent; completed caches may be archived between cases. Five percent is an engineering gate, not a confidence interval. No retention or full-project compatibility claim follows automatically.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan_path = args.plan.resolve()
        gates.require(plan_path.is_relative_to(ROOT / 'benchmarks') and gates.sha(plan_path) == args.plan_sha256,
                      'reviewed held-out plan path or hash differs')
        plan = gates.read(plan_path)
        cases = validate_plan(plan)
        bound = {**plan['frozen'], **plan['evaluation_sources'], **plan['prerequisites']}
        gates.require(all(gates.sha(ROOT / path) == digest for path, digest in bound.items()),
                      'frozen benchmark/evaluation/prerequisite input changed')
        components, evidence = [], {str(plan_path.relative_to(ROOT)): args.plan_sha256, **bound}
        for case in cases:
            folder = ROOT / 'results' / case['run_id']
            corpus = gates.read(folder / 'summary.json')
            gates.require(corpus['plan']['options'] == dict(plan['options'], run_id=case['run_id'], only=[case['label']]) and
                          corpus['plan']['frozen'] == plan['frozen'], 'component benchmark controls or sources changed')
            arguments = SimpleNamespace(run_id=case['run_id'], source_commit=SOURCE, held_out=False,
                                        held_out_case=case['label'], copy_transitions=False)
            checked, evaluated = gates.evaluate(arguments)
            gates.require(checked == gates.read(folder / 'final-verification.json') and
                          evaluated == gates.read(folder / 'gate-evaluation.json'), 'component verification changed')
            components.append((checked, evaluated))
            for name in ['summary.json', 'final-verification.json', 'gate-evaluation.json']:
                path = folder / name
                evidence[str(path.relative_to(ROOT))] = gates.sha(path)
        result = combine(plan, components)
        gates.require(all(gates.sha(ROOT / path) == digest for path, digest in evidence.items()),
                      'held-out evidence changed during verification')
        result['evidence'] = evidence
        out = ROOT / 'results' / plan['run_id']
        out.mkdir(exist_ok=False)
        (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        lines = ['All seven predeclared held-out cases completed and verify: 588 commands, 105 edited pairs and 294 artifacts.', '',
                 '| Workflow | Paired wall change | Paired CPU change | Wall gate |', '| --- | ---: | ---: | --- |']
        for row in result['workflows']:
            v = row['evaluation']
            lines.append(f"| {row['label']} | {(v['median_paired_ratio']-1)*100:+.2f}% | {(v['median_paired_cpu_ratio']-1)*100:+.2f}% | {'pass' if v['passed'] else 'fail'} |")
        lines += ['', result['note'], '', 'See [complete evidence](summary.json).', '']
        (out / 'assessment.md').write_text('\n'.join(lines))
        print(json.dumps(dict(counts=result['counts'], wall_regressions=result['wall_regressions_above_5_percent'])))


if __name__ == '__main__':
    main()
