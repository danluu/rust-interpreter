"""Weight typed scratch-value opportunities with saved profiles, without execution."""
from collections import Counter
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import sha
from profile_vm_transitions import counts
from workflow_io import write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args(); assert re.fullmatch(r'scratch-local-values-census-\d{2}', args.run_id)
    work = ROOT / '.work' / args.run_id
    proof_path = ROOT / 'results/guarded-local-facts-profile-01/summary.json'
    proof = json.loads(proof_path.read_text())
    assert proof['status'] == 'passed' and proof['exact_per_pc_counts']
    assert proof['exact_operation_map_reconstruction']
    evidence = {str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__), proof_path,
        ROOT/'scripts/profile_vm_transitions.py',ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']}
    output = []
    for index, label in enumerate(['block', 'exhaustive']):
        report_path = work / (label + '.json'); report = json.loads(report_path.read_text())
        assert report['status'] == 'passed' and report['exact_full_function_reconstruction'] and report['observer_words_unchanged']
        assert report['guest_commands'] == report['executable_code_publications'] == 0
        folder = ROOT / '.work' / ('adopted-runtime-sample-' + label + '-01') / '0'
        map_path = folder / 'jit-code/operations.json'; mapping = json.loads(map_path.read_text())
        assert report['code_sha256'] == mapping['code_sha256'] == sha(folder / 'jit-code/code.bin')
        profile_path = ROOT / proof['raw'] / (str(index) + '-profile.json')
        comparison = proof['comparisons'][index]; assert sha(profile_path) == comparison['profile_sha256']
        profile = json.loads(profile_path.read_text()); accounting = counts(profile, comparison['statistics'])
        mapped = {f['function']:f for f in mapping['functions']}
        assert len(mapped) == len(report['functions'])
        by_origin, functions, sites = Counter(), [], []
        total_loads = already_forwarded = weighted = static = 0
        represented = set()
        for observed in report['functions']:
            fid = observed['function']; assert fid not in represented; represented.add(fid)
            f = profile['functions'][fid]; saved = mapped[fid]
            assert f['name'] == observed['name'] == saved['name']
            pcs = {s['pc']:s['region_pc'] for s in saved['spans'] if s['pc'] is not None}
            ends = {}
            for pc, region in pcs.items(): ends[region] = max(ends.get(region,0),pc+1)
            def hits(pc):
                region = pcs[pc]
                assert region <= pc < f['jit_block_ends'][region] == ends[region]
                return f['jit_blocks'][region]
            total_loads += sum(hits(pc) for pc in observed['loads8'])
            existing = {pc for pc, op, _ in observed['already_forwarded'] if op == 'Load'}
            already_forwarded += sum(hits(pc) for pc in existing if pc in observed['loads8'])
            value = 0
            for hit in observed['available_scratch_values']:
                pc = hit['pc']; assert pc in observed['loads8'] and pc not in existing
                n = hits(pc); value += n; by_origin[hit['origin']] += n
                sites.append(dict(function=fid,name=f['name'],**hit,region_weight=n))
            static += len(observed['available_scratch_values']); weighted += value
            if value: functions.append(dict(function=fid,name=f['name'],weighted_available_loads=value))
        omitted = []
        for fid, f in enumerate(profile['functions']):
            if fid in represented: continue
            native = sum(n*(f['jit_block_ends'][pc]-pc) for pc,n in enumerate(f['jit_blocks']) if n)
            if native: omitted.append(dict(function=fid,name=f['name'],native_instructions=native))
        assert weighted <= total_loads - already_forwarded
        output.append(dict(case=label,represented_functions=len(represented),static_available_loads=static,
            weighted_available_loads=weighted,weighted_native_load8_sites=total_loads,
            weighted_existing_forwarded_load8=already_forwarded,weighted_by_origin=dict(by_origin),
            native_instructions=accounting['native_instructions'],omitted_executed_functions=omitted,
            omitted_native_instructions=sum(f['native_instructions'] for f in omitted),
            top_functions=sorted(functions,key=lambda f:-f['weighted_available_loads'])[:20],
            top_sites=sorted(sites,key=lambda s:-s['region_weight'])[:30]))
        for p in [report_path,map_path,profile_path,folder/'jit-code/code.bin']: evidence[str(p.relative_to(ROOT))]=sha(p)
    result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=True)
    write(result/'attribution.json',dict(status='passed',cases=output,evidence=evidence,guest_commands=0,
        performance_measurement=False,limitation='Available x9 values, not executed optimizations or avoided machine loads. Frequency-weighted typed sites use an existing controlled-entropy profile; captured unprofiled function coverage may differ. Omitted executed functions are explicit.'))
    for case in output: print(json.dumps({k:v for k,v in case.items() if k not in ['top_functions','top_sites','omitted_executed_functions']}))


if __name__ == '__main__': main()
