#!/usr/bin/env python3
"""Describe a completed native calibration without creating an optimizer gate."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    args = parser.parse_args()
    path = args.result.resolve(strict=True)
    summary = json.loads(path.read_text())
    assert summary['status'] == 'passed' and summary['commands'] == 88 and summary['edited_pairs'] == 15
    assert summary['source_restored'] and summary['original_assertions_match'] and summary['test_source_unchanged']
    raw = ROOT/summary['raw']
    for name,digest in summary['evidence'].items():
        assert hashlib.sha256((raw/(name+'.json')).read_bytes()).hexdigest() == digest
    rows = json.loads((raw/'records.json').read_text())
    assert len(rows) == 88 and all((r['returncode']==0) == (r['state']!=-1 or r['mode']=='check') for r in rows)
    med = statistics.median
    modes = ['repository','duplicate','line_tables','check']
    stages = {}
    for mode in modes:
        selected = [r for r in rows if r['mode']==mode and r['state']>0]
        assert len(selected) == 15
        stages[mode] = dict(command_seconds=med(r['seconds'] for r in selected),
                            cpu_seconds=med(r['cpu']['total_seconds'] for r in selected))
        if mode != 'check':
            stages[mode].update(reported_suite_seconds=med(r['native_reported_suite_seconds'] for r in selected),
                build_and_residual_seconds=med(r['build_and_residual_seconds'] for r in selected))
    initial = {r['mode']:r['seconds'] for r in rows if r['cycle']==0 and r['state']==0}
    assert set(initial) == set(modes)
    result = dict(status='completed',summary_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        stages=stages,initial_empty_target_seconds=initial,
        paired_wall_ratio=summary['paired_wall_ratio'],paired_cpu_ratio=summary['paired_cpu_ratio'],
        aa_envelope=summary['aa_envelope'],noise_acceptable=summary['noise_acceptable'],
        optimization_gate=None,custom_relative_speed_claim=False,
        limitations=['Line tables reduce variable/type debugger information.',
            'Each initial empty-target build is one observation; filesystem/toolchain caches were not flushed.',
            'Libtest duration is rounded; build_and_residual is not pure compilation.',
            'Separate medians are not additive; A/A envelopes are descriptive, not confidence intervals.',
            'No custom-engine timing is part of this calibration.'])
    decision = ('A/A variation stays within the declared 4% wall and 3% CPU bounds.' if result['noise_acceptable']
                else 'A/A variation exceeds the declared noise bounds; keep the observed effect descriptive.')
    lines = [
        '# Nushell native debuginfo calibration', '',
        f"All88 commands preserve their expected outcomes on fourteen original tests, including wrong edits and compiled restoration. Across fifteen edited pairs, line-tables/repository wall ratio is{result['paired_wall_ratio']:.5f} and CPU ratio is{result['paired_cpu_ratio']:.5f}.", '',
        f"The observed A/A envelopes are{result['aa_envelope']['wall']:.2%} wall and{result['aa_envelope']['cpu']:.2%} CPU. {decision} This native control has no8% optimization gate.", '',
        '| Mode | Edited command median (s) | Child CPU median (s) | Reported suite median (s) | Build and residual median (s) |',
        '| --- | ---: | ---: | ---: | ---: |']
    for mode,values in stages.items():
        fields=[f"{values[k]:.3f}" if k in values else '—' for k in
            ['command_seconds','cpu_seconds','reported_suite_seconds','build_and_residual_seconds']]
        lines.append('| '+mode+' | '+' | '.join(fields)+' |')
    lines += ['', 'Repository and line-tables controls have identical unit graphs after removing only the debuginfo field. Optimization, incremental compilation, assertions, overflow checks and default libtest concurrency match; both use two Cargo workers. Line tables retain source locations but reduce debugger variable/type information.', '',
        'Each first command used an empty run-specific Cargo target. These single observations are separate from the warm edited pairs; they do not establish a repeatable cold-build gain.', '',
        'The suite timer is rounded and its residual includes startup and Cargo overhead. Separately computed medians need not add. This calibration contains no custom-engine commands; a later relative-speed claim needs a same-session custom comparison.', '',
        '[Raw-bound summary](summary.json). All observations are retained; no partial pairs or retries were selected.', '']
    with path.with_name('assessment.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    with path.with_name('assessment.md').open('x') as f:f.write('\n'.join(lines))
    print(json.dumps({k:result[k] for k in ['status','paired_wall_ratio','paired_cpu_ratio','aa_envelope','noise_acceptable']}))


if __name__ == '__main__':main()
