#!/usr/bin/env python3
"""Attribute generated self-PC samples to verified operations and explicit overhead."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import sha
from summarize_owned_sample import parse_tree, self_samples
sys.path.insert(0,str(Path(__file__).parent.parent/'operation-map'))
from maps import validate
from attribute import detail, assign


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['block', 'exhaustive'], required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch('adopted-runtime-sample-' + args.case + r'-\d{2}', args.run_id)
    index = ['block', 'exhaustive'].index(args.case)
    folder = ROOT / '.work' / args.run_id / '0'
    result = ROOT / 'results' / args.run_id
    summary_path = result / 'summary.json'; summary = json.loads(summary_path.read_text())
    proof_path = ROOT / 'results/guarded-local-facts-main-final-audit-01/summary.json'; proof = json.loads(proof_path.read_text())
    assert proof['status']=='passed' and proof['all_frozen_inputs_verified']
    assert summary['tool_key'] == proof['tool_key'] and summary['vm_sha256'] == proof['binaries']['rust-interp-vm']
    assert len(summary['samples']) == 1 and summary['options']['jit_operation_map']
    reference_path = ROOT / 'results/guarded-local-facts-profile-01/summary.json'
    reference = json.loads(reference_path.read_text()); assert reference['status'] == 'passed'
    profile_path = ROOT / reference['raw'] / f'{index}-profile.json'
    assert sha(profile_path) == reference['comparisons'][index]['profile_sha256']
    assert summary['artifact_sha256'] == 'caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9'
    profile = json.loads(profile_path.read_text())
    record = json.loads((folder / 'record.json').read_text())
    assert record['identity']['status'] == 'finished' and record['identity']['returncode'] == 0
    assert all(sha(folder / p) == h for p, h in record['files'].items())
    for flag in ['--jit-operation-map', '--jit-resumable-calls', '--jit-persistent-registers']:
        assert flag in record['identity']['command']
    assert '--profile' not in record['identity']['command']
    native_path = folder / 'jit-code/map.json'; operation_path = folder / 'jit-code/operations.json'
    code_path = folder / 'jit-code/code.bin'
    native, operations = [json.loads(p.read_text()) for p in [native_path, operation_path]]
    assert not native['profiled'] and native['pid'] == summary['samples'][0]['pid']
    assert native['code_bytes'] == record['statistics']['jit_bytes']
    base = native['arena_base']
    assert any(lo == base and base + native['code_bytes'] <= hi
               for lo, hi in summary['samples'][0]['generated_address_ranges'])
    checked = validate(operations, native, code_path.read_bytes(), profile, record['identity']['pid'])
    frames = [frame for root in parse_tree((folder / 'sample.txt').read_text()) for frame in self_samples(root)]
    labels, sites, unresolved = assign(checked, base, frames)
    unknown = summary['disjoint_counts'].get('generated_code', 0) + summary['disjoint_counts'].get('unresolved_unknown_binary', 0)
    assert sum(labels.values()) + sum(r['count'] for r in unresolved) == unknown
    detailed, static, region_samples = Counter(), Counter(), Counter()
    for row in checked['rows']: static[detail(row, profile)] += (row['end'] - row['offset']) // 4
    for (fid, region, pc, kind, label), count in sites.items():
        detailed[detail(dict(function=fid, pc=pc, label=label), profile)] += count
        region_samples[fid, region] += count
    top = []
    for (fid, region, pc, kind, label), count in sites.most_common(30):
        top.append(dict(function=fid, name=profile['functions'][fid]['name'], region_pc=region, pc=pc,
            kind=kind, label=label, samples=count,
            operation=profile['functions'][fid]['operations'][pc] if pc is not None else None))
    hot = []
    regions = {(r['function'], r['pc']): r for r in native['ranges']}
    rows_by_region = {}
    for row in checked['rows']: rows_by_region.setdefault((row['function'], row['region_pc']), []).append(row)
    for key, samples in region_samples.most_common(10):
        row = regions[key]; words = Counter()
        for span in rows_by_region[key]: words[detail(span, profile)] += (span['end'] - span['offset']) // 4
        hot.append(dict(function=row['function'], name=row['name'], pc=row['pc'], pc_end=row['pc_end'],
            samples=samples, emitted_words=(row['end'] - row['offset']) // 4, static_words=dict(words)))
    attributed = sum(labels.values()); assert attributed > 0
    paths = [summary_path, proof_path, reference_path, profile_path, folder / 'record.json',
             folder / 'sample.txt', native_path, operation_path, code_path, Path(__file__), Path(__file__).parent.parent/'operation-map/maps.py',Path(__file__).parent.parent/'operation-map/attribute.py']
    report = dict(status='passed', case=args.case, tool_key=proof['tool_key'], vm_sha256=proof['binaries']['rust-interp-vm'],
        captured_thread_samples=summary['total_samples'], attributed_generated_samples=attributed,
        unassigned_generated_samples=sum(r['count'] for r in unresolved), unresolved=unresolved,
        by_label=dict(labels.most_common()), by_detail=dict(detailed.most_common()),
        percent_of_attributed_generated={k: 100 * n / attributed for k, n in labels.items()},
        static_words=dict(static), top_sites=top, hot_regions=hot,
        known_post_execution_samples=summary['disjoint_counts'].get('post_execution_diagnostic', 0),
        performance_measurement=False, evidence={str(p.relative_to(ROOT)): sha(p) for p in paths},
        limitation='One partial perturbed window under normal entropy. Generated self-PCs only; host samples may include post-execution reconstruction/I/O. Static words include unexecuted tails and are not retired instructions. Whole Call/Return transitions include their protocol. No end-to-end speedup claim.')
    with (result / 'operation-attribution.json').open('x') as output:
        json.dump(report, output, indent=2); output.write('\n')
    print(json.dumps(dict(case=args.case, samples=attributed, unassigned=report['unassigned_generated_samples'],
                         labels=report['by_label'])))


if __name__ == '__main__': main()
