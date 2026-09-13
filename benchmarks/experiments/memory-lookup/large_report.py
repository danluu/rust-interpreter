#!/usr/bin/env python3
"""Recompute complete-command results; keep private workload names local."""
import argparse
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import write_json
from large_compare import assessment, CUSTOM, MODES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert Path(args.run_id).name == args.run_id and args.run_id.startswith('memory-lookup-edit-')
    out = ROOT/'results'/args.run_id
    summary = json.loads((out/'summary.json').read_text())
    assert summary['status'] == 'passed' and summary['commands'] == 132
    raw = ROOT/summary['raw']
    for name, digest in summary['evidence'].items():
        assert sha(raw/(name+'.json')) == digest
    rows = json.loads((raw/'records.json').read_text())
    recalculated = assessment(rows, summary['case'])
    assert all(summary[k] == v for k,v in recalculated.items())
    for row in rows:
        cpu = row['cpu']
        assert math.isclose(cpu['total_seconds'],cpu['user_seconds']+cpu['system_seconds'],abs_tol=1e-9)
        for kind in ['cargo_timing','artifact','entry_catalog']:
            if kind in row:
                assert sha(ROOT/row[kind]['path']) == row[kind]['sha256']
    median = statistics.median
    stages = {}
    for mode in MODES:
        selected = [r for r in rows if r['mode'] == mode and r['state'] > 0]
        assert len(selected) == 15
        stage = dict(command_seconds=median(r['seconds'] for r in selected),
                     cpu_seconds=median(r['cpu']['total_seconds'] for r in selected))
        if mode in CUSTOM:
            stage['launch'] = {k:median(r['launch'][k] for r in selected) for k in
                ['std_mir_seconds','cargo_seconds','build_to_ready_seconds','execution_seconds']}
            stage['exporter'] = {k:median(r['exporter_stages'][k] for r in selected)
                                 for k in ['frontend','lowering']}
            stage['lookup_outcomes'] = sorted({r['launch']['toolchain_lookup']['outcome'] for r in selected})
        elif mode != 'check':
            stage['reported_suite_seconds'] = median(r['native_reported_suite_seconds'] for r in selected)
            stage['build_and_residual_seconds'] = median(r['build_and_residual_seconds'] for r in selected)
        stages[mode] = stage
    result = dict(summary_sha256=sha(out/'summary.json'), stages=stages,
        initial_observations={r['mode']:r['seconds'] for r in rows if r['cycle']==0 and r['state']==0},
        source_sha256=sha(Path(__file__)), private_details_redacted=summary['private'],
        scope='All fifteen edited pairs, original assertions, wrong edits and restoration are retained. '
        'Stages are nested; separate medians need not add. A/A envelopes are descriptive, not confidence intervals. '
        'Initial empty-target observations are excluded and do not establish a repeatable cold-build gain.')
    assert not (out/'assessment.json').exists() and not (out/'assessment.md').exists()
    write_json(out/'assessment.json', result)
    lines = [f"# Memory and lookup composition: {summary['case']}", '',
        f"All132 commands have their expected outcomes, with{summary['test_count']} original tests, fifteen edited pairs "
        'and fifteen A/A pairs. Custom bytecode and catalogs match for every state.', '',
        f"The prospective gate **{'passes' if summary['gate_passed'] else 'does not pass'}**. "
        f"Paired wall change {(summary['paired_wall_ratio']-1)*100:+.2f}%; CPU {(summary['paired_cpu_ratio']-1)*100:+.2f}%. "
        f"A/A envelopes: {summary['aa_envelope']['wall']*100:.2f}% wall, {summary['aa_envelope']['cpu']*100:.2f}% CPU.", '',
        f"Candidate/ordinary-native wall ratio {summary['paired_native_wall_ratio']:.3f}; "
        f"candidate/line-tables native {summary['paired_native_lines_wall_ratio']:.3f}. "
        'All modes use two Cargo workers; native retains default libtest concurrency.', '',
        '| Custom mode | Command | CPU | Std-MIR lookup | Cargo | Frontend | Lowering | VM |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for mode in CUSTOM:
        r = stages[mode]
        values = [r['command_seconds'],r['cpu_seconds'],r['launch']['std_mir_seconds'],
            r['launch']['cargo_seconds'],r['exporter']['frontend'],r['exporter']['lowering'],r['launch']['execution_seconds']]
        lines.append('| '+mode+' | '+' | '.join(f'{v:.3f}s' for v in values)+' |')
    lines += ['', result['scope'], '', 'Every edited candidate lookup is a validated cache hit. '
        'The candidate combines the qualified memory VM and cached identity lookup; the wide control uses fresh lookup. '
        'Exporter/wrapper bytes, strict checking and guest options match. These are composition results, not isolated component effects.', '',
        'All declared project guards are required before adoption. Private names and command details remain local.'
        if summary['private'] else 'All declared project guards are required before adoption.']
    (out/'assessment.md').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    main()
