#!/usr/bin/env python3
"""Report complete host-MIR histories and their recorded Cargo unit intervals."""
import argparse
import collections
import json
import math
from pathlib import Path
import statistics
import sys

SOURCE=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(SOURCE/'scripts'))
from cargo_timing_data import group_key, units_from_html
from compare_saved_runtime import sha
from workflow_io import write_json as write
from edit_compare import assessment, CUSTOM, MODES


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root',type=Path,required=True)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    root=args.workspace_root.resolve(strict=True)
    out=root/'results'/args.run_id
    summary=json.loads((out/'summary.json').read_text())
    assert summary['status']=='passed' and summary['commands']==132
    raw=root/summary['raw']
    for name,digest in summary['evidence'].items():assert sha(raw/(name+'.json'))==digest
    rows=json.loads((raw/'records.json').read_text())
    plan=json.loads((raw/'plan.json').read_text())
    recomputed=assessment(rows,summary['case'])
    assert all(summary[k]==value for k,value in recomputed.items())
    for row in rows:
        cpu=row['cpu'];assert math.isclose(cpu['total_seconds'],cpu['user_seconds']+cpu['system_seconds'],rel_tol=1e-12,abs_tol=1e-9)
        for kind in ['cargo_timing','artifact','entry_catalog']:
            if kind in row:assert sha(root/row[kind]['path'])==row[kind]['sha256']
    median=statistics.median
    edited={m:[r for r in rows if r['mode']==m and r['state']>0] for m in MODES}
    assert all(len(r)==15 for r in edited.values())
    stages={}
    for mode,selected in edited.items():
        stage=dict(complete_seconds=median(r['seconds'] for r in selected),
            complete_cpu_seconds=median(r['cpu']['total_seconds'] for r in selected))
        if mode in CUSTOM:
            stage['launch']={k:median(r['launch'][k] for r in selected)
                for k in ['cargo_seconds','build_to_ready_seconds','execution_seconds','artifact_bytes']}
            stage['exporter']={k:median(r['exporter_stages'][k] for r in selected) for k in ['frontend','lowering']}
        elif mode!='check':
            stage['reported_suite_seconds']=median(r['native_reported_suite_seconds'] for r in selected)
            stage['build_and_residual_seconds']=median(r['build_and_residual_seconds'] for r in selected)
        stages[mode]=stage
    # Keep Cargo's target text and feature identities separate. A timing label
    # alone does not establish host/guest routing or serial critical-path cost.
    grouped={}
    for row in rows:
        if row['state']<=0:continue
        units=units_from_html((root/row['cargo_timing']['path']).read_bytes())
        totals=collections.defaultdict(float)
        counts=collections.Counter()
        for unit in units:
            key=group_key(unit);totals[key]+=unit['duration'];counts[key]+=1
        grouped[row['cycle'],row['state'],row['mode']]={key:dict(seconds=value,units=counts[key]) for key,value in totals.items()}
    keys=set(key for values in grouped.values() for key in values)
    units=[]
    for key in sorted(keys):
        values={m:[grouped[c,s,m].get(key) for c in range(3) for s in range(1,6)] for m in MODES}
        pairs=[(a['seconds'],b['seconds']) for a,b in zip(values['baseline'],values['candidate']) if a and b and a['seconds']>0]
        units.append(dict(package=key[0],version=key[1],cargo_mode=key[2],target=key[3],features=list(key[4]),
            presence={m:sum(v is not None for v in items) for m,items in values.items()},
            median_reported_unit_seconds={m:median(v['seconds'] for v in items if v is not None) if any(items) else None
                for m,items in values.items()},
            paired_reported_unit_intervals=len(pairs),paired_ratio=median(b/a for a,b in pairs) if pairs else None))
    initial={r['mode']:r['seconds'] for r in rows if r['cycle']==0 and r['state']==0}
    assert set(initial)==set(MODES)
    result=dict(summary_sha256=sha(out/'summary.json'),stages=stages,initial_complete_seconds=initial,
        unit_groups=units,source_hashes={str(p.relative_to(root)):sha(p) for p in
            [Path(__file__),Path(__file__).with_name('edit_compare.py'),SOURCE/'scripts/cargo_timing_data.py']},
        scope='Complete-command ratios retain all15pairs. Stages are nested, and their separate medians need not add. '
            'Cargo unit intervals are rounded and may overlap; they are not CPU times or a measured critical path. '
            'Unit ratios use only reported matching intervals, with counts retained, and never change the complete-command gate.')
    assert not (out/'assessment.json').exists() and not (out/'assessment.md').exists()
    write(out/'assessment.json',result)
    lines=[f"# Host dependency MIR: {summary['case']}",'',
        f"All132 commands passed their expected outcomes, with {summary['test_count']} original tests, fifteen edited pairs, "
        'fifteen A/A pairs, wrong edits and compiled restoration. Candidate and baseline guest bytecode/catalogs match in every state.','',
        f"The predeclared gate **{'passes' if summary['gate_passed'] else 'does not pass'}**. "
        f"Paired wall changes {(summary['paired_wall_ratio']-1)*100:+.2f}%; CPU {(summary['paired_cpu_ratio']-1)*100:+.2f}%. "
        f"Observed A/A envelopes are {summary['aa_envelope']['wall']*100:.2f}% wall and {summary['aa_envelope']['cpu']*100:.2f}% CPU. "
        'These describe noise, not confidence intervals.','',
        f"Candidate/ordinary-native paired wall ratio is {summary['paired_native_wall_ratio']:.3f}; "
        f"candidate/line-tables native is {summary['paired_native_lines_wall_ratio']:.3f}. "
        'All modes use two Cargo workers; native keeps default libtest concurrency.','',
        '| Custom mode | Command | CPU | Cargo | Frontend | Lowering | VM stage |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for mode in CUSTOM:
        r=stages[mode];values=[r['complete_seconds'],r['complete_cpu_seconds'],r['launch']['cargo_seconds'],
            r['exporter']['frontend'],r['exporter']['lowering'],r['launch']['execution_seconds']]
        lines.append('| '+mode+' | '+' | '.join(f'{v:.3f}s' for v in values)+' |')
    lines+=['',result['scope'],'','Largest repeatedly reported unit groups, keeping Cargo target labels and features separate:','',
        '| Package and Cargo target label | Features | Baseline intervals | Candidate intervals | Paired ratio |',
        '| --- | --- | ---: | ---: | ---: |']
    comparable=[r for r in units if r['paired_reported_unit_intervals']==15]
    comparable.sort(key=lambda r:r['median_reported_unit_seconds']['baseline'],reverse=True)
    for r in comparable[:8]:
        label=r['target'] or '(blank label)'
        lines.append(f"| {r['package']} {label} | {', '.join(r['features']) or 'none'} | "
            f"{r['median_reported_unit_seconds']['baseline']:.3f}s | {r['median_reported_unit_seconds']['candidate']:.3f}s | {r['paired_ratio']:.3f} |")
    lines+=['','A blank target label is preserved as reported; this table alone does not identify a host unit or prove where a flag took effect. '
        'The separate real Cargo qualification verifies the wrapper routing.','',
        'Initial empty-target observations and both rounded native suite/residual splits are retained in assessment.json. '
        'They are excluded from edited medians and do not establish a repeatable cold-build gain.','',
        'VM and exporter bytes are identical between custom arms; the wrapper is the candidate change. '
        'Broad adoption still requires the other predeclared project guards.','',
        'Tools: '+', '.join(f'{m} `{key}`' for m,key in plan['tool_keys'].items())+'.']
    (out/'assessment.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
