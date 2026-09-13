#!/usr/bin/env python3
"""Report completed comparisons with their native controls and nested stages."""
import argparse
import json
from pathlib import Path
import statistics

from workflows import ROOT, CUSTOM, MODES, assessment, read_report, sha, write


def suite_stages(rows, raw):
    """Overlapping worker durations are work measurements, not command stages."""
    selected = [r for r in rows if r['state'] > 0 and r['mode'] in CUSTOM]
    if not selected or 'suite_sha256' not in selected[0]:
        return None
    med = statistics.median
    reports = {}
    for row in selected:
        path = raw / f"{row['cycle']}-{row['state']}-{row['mode']}-suite.json"
        suite, _ = read_report(path, row['suite_sha256'])
        assert suite['status'] == 'passed' and all(t['status'] == 'passed' for t in suite['tests'])
        reports[row['cycle'], row['state'], row['mode']] = suite
    totals = {}
    for mode in CUSTOM:
        suites = [s for (*_, m), s in reports.items() if m == mode]
        assert len(suites) == 15
        totals[mode] = {
            'constructor_work_seconds': med(s['preparation_ns'] / 1e9 for s in suites),
            'jit_compile_work_seconds': med(sum(t['jit_compile_ns'] for t in s['tests']) / 1e9 for s in suites),
            'test_work_seconds': med(sum(t['seconds'] for t in s['tests']) for s in suites),
        }
    names = [t['name'] for t in reports[0, 1, 'baseline']['tests']]
    by_test = []
    for name in names:
        values = {mode: [] for mode in CUSTOM}
        for cycle in range(3):
            for state in range(1, 6):
                for mode in CUSTOM:
                    test, = [t for t in reports[cycle, state, mode]['tests'] if t['name'] == name]
                    values[mode].append(test)
        by_test.append(dict(name=name,
            median_seconds={m: med(t['seconds'] for t in tests) for m, tests in values.items()},
            paired_wall_ratio=med(c['seconds'] / b['seconds'] for b, c in zip(values['baseline'], values['candidate'])),
            logical_bytecode_instructions={m: med(t['instructions'] for t in tests) for m, tests in values.items()}))
    by_test.sort(key=lambda t: t['median_seconds']['baseline'], reverse=True)
    return dict(totals=totals, tests=by_test,
        scope='Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    out = ROOT / 'results' / args.run_id
    summary = json.loads((out / 'summary.json').read_text())
    assert summary['status'] == 'passed' and summary['commands'] == 154
    raw = ROOT / summary['raw']
    for name in ['plan', 'records', 'transitions', 'space']:
        assert sha(raw / (name + '.json')) == summary[name + '_sha256']
    rows = json.loads((raw / 'records.json').read_text())
    recomputed = assessment(rows, summary['case'])
    assert all(summary[k] == v for k, v in recomputed.items())
    plan = json.loads((raw / 'plan.json').read_text())
    edited = {m: [r for r in rows if r['state'] > 0 and r['mode'] == m] for m in MODES}
    med = statistics.median
    stages = {}
    for mode in CUSTOM:
        selected = edited[mode]
        stages[mode] = {
            'complete_seconds': med(r['seconds'] for r in selected),
            'complete_cpu_seconds': med(r['cpu']['total_seconds'] for r in selected),
            'launch': {key: med(r['launch'][key] for r in selected) for key in
                       ['cargo_seconds', 'build_to_ready_seconds', 'execution_seconds',
                        'artifact_bytes', 'artifact_hash_seconds']},
            'exporter': {key: med(r['exporter_stages'][key] for r in selected) for key in
                         ['frontend', 'lowering', 'inline', 'cfg']},
        }
    cache_rows = [r['function_cache'] for r in edited['candidate']]
    cache_modes = sorted({r['mode'] for r in cache_rows})
    cache = {'modes': cache_modes}
    if cache_modes == ['reuse']:
        keys = ['skipped_functions', 'lowered_functions', 'load_seconds',
                'previous_binding_seconds', 'previous_template_decoding_seconds',
                'current_template_encoding_seconds', 'file_encoding_seconds',
                'file_write_seconds', 'green_check_seconds']
        cache['medians'] = {k: med(r[k] for r in cache_rows) for k in keys}
    initial = {r['mode']: r['seconds'] for r in rows if r['cycle'] == 0 and r['state'] == 0}
    assert set(initial) == set(MODES)
    native = {m: {
        'complete_seconds': med(r['seconds'] for r in edited[m]),
        'complete_cpu_seconds': med(r['cpu']['total_seconds'] for r in edited[m]),
        'reported_suite_seconds': med(r['native_reported_suite_seconds'] for r in edited[m]),
        'build_and_residual_seconds': med(r['native_build_and_residual_seconds'] for r in edited[m]),
    } for m in ['native', 'native_lines']}
    result = dict(summary_sha256=sha(out / 'summary.json'), stages=stages, cache=cache,
                  native=native, initial_complete_seconds=initial,
                  stage_scope='Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.')
    result['suite_work'] = suite_stages(rows, raw)
    assert not (out / 'stage-assessment.json').exists()
    write(out / 'stage-assessment.json', result)
    lines = [f"# Combined engine: {summary['case']}", '',
        f"All154 commands passed their expected outcomes: {summary['test_count']} original tests, "
        'fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.', '',
        f"Predeclared performance gate **{'passes' if summary['gate_passed'] else 'does not pass'}**. "
        f"Versus integrated baseline: paired complete-command wall change {(summary['paired_wall_ratio']-1)*100:+.2f}%; "
        f"CPU {(summary['paired_cpu_ratio']-1)*100:+.2f}%. "
        f"Descriptive A/A envelopes: {summary['aa_envelope']['wall']*100:.2f}% wall, "
        f"{summary['aa_envelope']['cpu']*100:.2f}% CPU. These are not confidence intervals.", '',
        f"Versus fixed selected-suite anchor: wall {(summary['paired_anchor_wall_ratio']-1)*100:+.2f}%; "
        f"CPU {(summary['paired_anchor_cpu_ratio']-1)*100:+.2f}%.", '',
        f"Candidate/ordinary native paired wall ratio {summary['paired_native_wall_ratio']:.3f}; "
        f"candidate/line-tables native {summary['paired_native_lines_wall_ratio']:.3f}. "
        'Native uses default libtest concurrency; every mode uses two Cargo workers.', '',
        '| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for mode, row in stages.items():
        values = [row['complete_seconds'], row['complete_cpu_seconds'], row['launch']['cargo_seconds'],
                  row['exporter']['frontend'], row['exporter']['lowering'], row['launch']['execution_seconds']]
        lines.append('| ' + mode + ' | ' + ' | '.join(f'{v:.3f}s' for v in values) + ' |')
    lines += ['', result['stage_scope'], '', 'Cache mode: ' + ', '.join(cache_modes) + '.']
    if 'medians' in cache:
        values = cache['medians']
        lines += [f"Median reused/lowered functions: {values['skipped_functions']:g}/{values['lowered_functions']:g}. "
                  f"Binding {values['previous_binding_seconds']:.3f}s, template decoding "
                  f"{values['previous_template_decoding_seconds']:.3f}s, cache load {values['load_seconds']:.3f}s. "
                  'These costs are nested within export; they are not additional whole-command time.']
    lines += ['', 'The initial fresh-cache commands are single observations, excluded from edited-pair medians. '
              'Their times and both native stage splits are retained in `stage-assessment.json`.', '',
              'Tool keys: ' + ', '.join(f'{m} `{key}`' for m, key in plan['tools'].items()) + '.', '',
              'Broader adoption still requires the other predeclared comparisons and held-outs.']
    if summary['case'] == 'anchor':
        lines += ['', 'Both custom routes use the original ordinary three-test batch, stopping at the '
                  'first assertion. Separate outcomes after that failure are unavailable. This result '
                  'does not measure prepared execution or parallel test scheduling.']
    if result['suite_work'] is not None:
        suites = result['suite_work']
        lines += ['', 'Largest selected test durations:', '',
                  '| Test | Baseline median | Candidate median | Paired ratio |',
                  '| --- | ---: | ---: | ---: |']
        for row in suites['tests'][:5]:
            lines.append(f"| {row['name']} | {row['median_seconds']['baseline']:.3f}s | "
                         f"{row['median_seconds']['candidate']:.3f}s | {row['paired_wall_ratio']:.3f} |")
        lines += ['', suites['scope']]
    path = out / 'stage-assessment.md'
    assert not path.exists()
    path.write_text('\n'.join(lines) + '\n')
    print(json.dumps({k: summary[k] for k in ['case', 'gate_passed', 'paired_wall_ratio', 'paired_cpu_ratio']}))


if __name__ == '__main__':
    main()
