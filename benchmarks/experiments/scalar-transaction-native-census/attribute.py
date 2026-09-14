"""Join complete native private-store plans to current same-process sample PCs."""
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
spec=importlib.util.spec_from_file_location('closed_call_join',ROOT/'benchmarks/experiments/native-call-cost-census/analyze.py')
join=importlib.util.module_from_spec(spec);spec.loader.exec_module(join)
def read(p):
    assert p.stat().st_size<=256*1024**2
    return json.loads(p.read_text())
def main():
    name=sys.argv[1];assert re.fullmatch(r'scalar-transaction-native-census-\d{2}',name)
    raw=ROOT/'.work'/name;census_path=raw/'census.json';census=read(census_path)
    assert census['status']=='passed' and not census['production_policy_changed'] and census['memory_work_remaining']>0
    typed_path=ROOT/'.work/current-call-shapes-01/census.json';typed=read(typed_path)
    assert typed['artifact_sha256']==census['artifact_sha256'] and typed['functions']==census['functions']
    candidates={r['function']:r for r in census['rows'] if r['candidate']}
    shapes={r['function']:r for r in typed['rows']}
    for r in candidates.values():
        assert r['scalar']['eligible'] and r['memory_eligible'] and r['external_writes']>0 and r['native_implemented']
        assert len(r['native'])==2 and all(n['eligible'] for n in r['native'])
        assert shapes[r['function']]['name']==r['name']
    calls={(r['caller'],r['pc']):r for r in typed['calls']};assert len(calls)==len(typed['calls'])
    prior_path=ROOT/'results/scalar-protocol-census-03/attribution.json';prior=read(prior_path)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [census_path,typed_path,prior_path]};cases=[]
    for label in ['block','exhaustive']:
        folder=ROOT/'.work'/('scratch-scalar-runtime-sample-'+label+'-01')/'0'
        map_path=folder/'jit-code/operations.json';sample_path=folder/'sample.txt';fine_path=ROOT/'.work/scalar-protocol-census-03'/(label+'.json')
        mapping,fine=read(map_path),read(fine_path)
        assert mapping['schema_version']==fine['schema_version']==2
        assert mapping['complete'] and mapping['reconstructed_bytes_match'] and not mapping['profiled']
        assert fine['exact_full_function_reconstruction'] and fine['exact_transition_reconstruction'] and fine['complete_partition']
        assert mapping['code_sha256']==fine['code_sha256']==sha(folder/'jit-code/code.bin')
        case,=[c for c in prior['cases'] if c['case']==label];assert all(sha(ROOT/p)==h for p,h in case['evidence'].items())
        scalar={f['function'] for f in mapping['functions'] if f['spans'][0]['kind']=='scalar_leaf'}
        assert scalar.isdisjoint(candidates)
        for f in mapping['functions']:assert shapes[f['function']]['name']==f['name']
        samples=[sample for root in parse_tree(sample_path.read_text()) for sample in self_samples(root)]
        a,b,parts,generated=join.attribute(calls,mapping,fine,samples)
        assert generated==case['generated_samples'] and dict(parts)==case['fine_samples']
        selected=Counter()
        for fid in candidates:
            selected.update({'Call/'+k:v for k,v in a[fid].items()});selected.update({'Return/'+k:v for k,v in b[fid].items()})
        coarse=[dict(s,function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
        starts=[s['offset'] for s in coarse];assert starts==sorted(set(starts))
        bodies=Counter();body_targets=Counter()
        for count,frame,_ in samples:
            if '<unknown binary>' not in frame:continue
            offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
            owners=[join.locate(coarse,starts,o) for o in offsets];assert owners
            identities={(s['function'],s['kind']) for s in owners};assert len(identities)==1
            fid,kind=next(iter(identities))
            if fid in candidates and kind!='transition':bodies[kind]+=count;body_targets[fid]+=count
        targets=[]
        for fid in candidates:
            transition=sum(a[fid].values())+sum(b[fid].values());body=body_targets[fid]
            if transition+body:
                targets.append(dict(function=fid,name=shapes[fid]['name'],frame_size=shapes[fid]['frame_size'],
                    operations=shapes[fid]['operations'],external_reads=candidates[fid]['external_reads'],external_writes=candidates[fid]['external_writes'],
                    transition_samples=transition,body_samples=body,call_parts=dict(a[fid]),return_parts=dict(b[fid])))
        targets.sort(key=lambda r:-r['transition_samples']-r['body_samples'])
        cases.append(dict(case=label,generated_samples=generated,candidate_transition_samples=sum(selected.values()),
            candidate_frame_clear_samples=selected.get('Call/call_frame_clear',0),candidate_body_samples=sum(bodies.values()),
            by_part=dict(selected.most_common()),body_kinds=dict(bodies.most_common()),sampled_targets=targets))
        for p in [map_path,sample_path,fine_path,folder/'jit-code/code.bin']:evidence[str(p.relative_to(ROOT))]=sha(p)
    out=ROOT/'results'/name;out.mkdir(exist_ok=True)
    write(out/'attribution.json',dict(status='passed',cases=cases,candidate_functions=len(candidates),
        candidate_callsites=sum(c['callee'] in candidates for c in calls.values()),memory_work_used=census['memory_work_used'],
        evidence=evidence,existing_scalar_bodies_verified=census['existing_scalar_bodies_verified'],captures=census['captures'],original_project_guest_commands=0,performance_measurement=False,
        limitation='Native emission only, with existing scalar bodies byte-verified. Actual runtime preparation, alias declines, arena admission and speedup remain unmeasured. Production store admission remains closed. Partial perturbed samples are coverage bounds.'))
    print(json.dumps(dict(candidates=len(candidates),cases=[{k:c[k] for k in ['case','candidate_transition_samples','candidate_body_samples']} for c in cases])),flush=True)
if __name__=='__main__':main()
