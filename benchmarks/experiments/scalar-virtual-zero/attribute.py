"""Join newly admitted confined leaves to current saved Call/Return self PCs."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from summarize_owned_sample import parse_tree,self_samples
from workflow_io import write_json as write
spec=importlib.util.spec_from_file_location('saved_protocol_lookup',ROOT/'benchmarks/experiments/scalar-protocol-census/attribute.py')
protocol=importlib.util.module_from_spec(spec);spec.loader.exec_module(protocol)
locate=protocol.locate


def read(path):
    assert path.stat().st_size<=256*1024**2
    return json.loads(path.read_text())


def main():
    name=sys.argv[1];assert re.fullmatch(r'scalar-virtual-zero-census-\d{2}',name)
    raw=ROOT/'.work'/name;census_path=raw/'census.json';census=read(census_path)
    assert census['status']=='passed' and not census['production_policy_changed']
    assert census['original_project_guest_commands']==census['executable_code_publications']==0
    candidates={r['function']:r for r in census['rows'] if r['candidate']}
    assert len(candidates)==census['candidates']
    for row in candidates.values():
        assert row['strict_decline']['reason']=='local_read_before_write'
        assert row['relaxed_eligible'] and row['scalar']['eligible']
        assert len(row['native'])==2 and all(n['eligible'] for n in row['native'])
    calls={(c['caller'],c['pc']):c['callee'] for c in census['calls']}
    assert len(calls)==len(census['calls']) and all(c in candidates for c in calls.values())
    prior_path=ROOT/'results/scalar-protocol-census-03/attribution.json';prior=read(prior_path)
    assert prior['status']=='passed';evidence={str(p.relative_to(ROOT)):sha(p) for p in [census_path,prior_path]}
    cases=[]
    for label in ['block','exhaustive']:
        folder=ROOT/'.work'/('scratch-scalar-runtime-sample-'+label+'-01')/'0'
        map_path=folder/'jit-code/operations.json';sample_path=folder/'sample.txt'
        fine_path=ROOT/'.work/scalar-protocol-census-03'/(label+'.json')
        mapping,fine=read(map_path),read(fine_path)
        assert mapping['schema_version']==fine['schema_version']==2
        assert mapping['complete'] and mapping['reconstructed_bytes_match'] and not mapping['profiled']
        assert fine['exact_full_function_reconstruction'] and fine['exact_transition_reconstruction'] and fine['complete_partition']
        assert mapping['code_sha256']==fine['code_sha256']==sha(folder/'jit-code/code.bin')
        case,=[c for c in prior['cases'] if c['case']==label]
        assert all(sha(ROOT/p)==h for p,h in case['evidence'].items())
        previous_scalar={f['function'] for f in mapping['functions'] if f['spans'][0]['kind']=='scalar_leaf'}
        assert previous_scalar.isdisjoint(candidates)
        for f in mapping['functions']:
            if f['function'] in candidates:assert candidates[f['function']]['name']==f['name']
        coarse=[dict(s,function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
        starts=[s['offset'] for s in coarse];assert starts==sorted(set(starts))
        spans=fine['spans'];fine_starts=[s['offset'] for s in spans];assert fine_starts==sorted(set(fine_starts))
        all_parts,parts,targets=Counter(),Counter(),Counter();whole=ambiguous=generated=0
        for root in parse_tree(sample_path.read_text()):
            for count,frame,_ in self_samples(root):
                if '<unknown binary>' not in frame:continue
                assert '...' not in frame
                offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)];assert offsets
                owners=[locate(coarse,starts,o) for o in offsets]
                identities={(s['function'],s['pc'],s['kind']) for s in owners};assert len(identities)==1
                fid,pc,kind=next(iter(identities));generated+=count
                if kind!='transition':continue
                fine_rows=[locate(spans,fine_starts,o) for o in offsets]
                assert all((s['function'],s['pc'])==(fid,pc) for s in fine_rows)
                detail={(s['operation'],s['kind'],s['argument']) for s in fine_rows}
                assert len({s['operation'] for s in fine_rows})==1
                operation=fine_rows[0]['operation']
                target=calls.get((fid,pc)) if operation=='Call' else (fid if fid in candidates else None)
                if target is not None:whole+=count;targets[target]+=count
                if len(detail)!=1:
                    if target is not None:ambiguous+=count
                    continue
                op,part,_=next(iter(detail));key=op+'/'+part;all_parts[key]+=count
                if target is not None:parts[key]+=count
        assert generated==case['generated_samples'] and dict(all_parts)==case['fine_samples']
        assert sum(parts.values())+ambiguous==whole
        cases.append(dict(case=label,generated_samples=generated,candidate_transition_samples=whole,
            ambiguous_candidate_samples=ambiguous,candidate_frame_clear_samples=parts.get('Call/call_frame_clear',0),
            by_part=dict(parts.most_common()),sampled_targets=[dict(function=i,name=candidates[i]['name'],samples=n)
                for i,n in targets.most_common()],previous_scalar_bodies=len(previous_scalar)))
        for path in [map_path,sample_path,fine_path,folder/'jit-code/code.bin']:
            evidence[str(path.relative_to(ROOT))]=sha(path)
    out=ROOT/'results'/name;out.mkdir(exist_ok=True)
    write(out/'attribution.json',dict(status='passed',cases=cases,candidate_functions=len(candidates),
        candidate_callsites=len(calls),strict_reasons=census['strict_reasons'],
        strict_work_used=census['strict_work_used'],relaxed_work_used=census['relaxed_work_used'],
        evidence=evidence,guest_commands=0,performance_measurement=False,
        limitation='Structural admission census and partial perturbed same-process PCs. No runtime preparation order, arena capacity, bridge overhead or latency benefit is established. Virtual-zero policy is diagnostic only.'))
    print(json.dumps(dict(candidates=len(candidates),callsites=len(calls),cases=cases)),flush=True)


if __name__=='__main__':main()
