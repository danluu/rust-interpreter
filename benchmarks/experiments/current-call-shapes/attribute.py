"""Use typed calls from the pinned artifact; rendered snippets are descriptive only."""
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
spec=importlib.util.spec_from_file_location('closed_call_cost_join',ROOT/'benchmarks/experiments/native-call-cost-census/analyze.py')
join=importlib.util.module_from_spec(spec);spec.loader.exec_module(join)

def read(p):
    assert p.stat().st_size<=256*1024**2
    return json.loads(p.read_text())

def main():
    name=sys.argv[1];assert re.fullmatch(r'current-call-shapes-\d{2}',name)
    raw=ROOT/'.work'/name;census_path=raw/'census.json';census=read(census_path)
    assert census['status']=='passed' and not census['production_policy_changed']
    assert census['original_project_guest_commands']==census['executable_code_publications']==0
    assert census['memory_work_remaining']>0, 'incomplete memory-plan census'
    rows={r['function']:r for r in census['rows']}
    assert len(rows)==census['functions'] and sorted(rows)==list(range(len(rows)))
    calls={}
    for c in census['calls']:
        key=(c['caller'],c['pc']);assert key not in calls
        assert c['callee'] in rows and 0<=c['pc']<rows[c['caller']]['operations']
        assert len(c['args'])==len(rows[c['callee']]['arguments'])
        calls[key]=c
    prior_path=ROOT/'results/scalar-protocol-census-03/attribution.json';prior=read(prior_path)
    assert prior['status']=='passed'
    artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts'/('caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc')
    assert census['artifact_sha256']==artifact.stem==sha(artifact)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [census_path,prior_path,artifact]}
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
        scalar={f['function'] for f in mapping['functions'] if f['spans'][0]['kind']=='scalar_leaf'}
        for f in mapping['functions']:
            assert f['name']==rows[f['function']]['name']
        for s in fine['spans']:
            if s['operation']=='Call':assert (s['function'],s['pc']) in calls
        samples=[sample for root in parse_tree(sample_path.read_text()) for sample in self_samples(root)]
        a,b,parts,generated=join.attribute(calls,mapping,fine,samples)
        assert generated==case['generated_samples'] and dict(parts)==case['fine_samples']
        targets=[];clear_reasons=Counter();transition_reasons=Counter()
        for fid in sorted(set(a)|set(b)):
            r=rows[fid]
            target=dict(r,captured_scalar_body=fid in scalar,call_parts=dict(a[fid]),return_parts=dict(b[fid]),
                call_samples=sum(a[fid].values()),return_samples=sum(b[fid].values()))
            targets.append(target)
            clear_reasons[r['memory_reason']]+=a[fid].get('call_frame_clear',0)
            if fid not in scalar:
                transition_reasons[r['memory_reason']]+=target['call_samples']+target['return_samples']
        targets.sort(key=lambda r:(-r['call_parts'].get('call_frame_clear',0),-r['call_samples']-r['return_samples'],r['function']))
        assert sum(t['call_samples']+t['return_samples'] for t in targets)==sum(parts.values())==case['transition_samples']
        report=raw/(label+'.json')
        write(report,dict(status='passed',case=label,targets=targets,generated_samples=generated,
            fine_samples=dict(parts),memory_work_used=census['memory_work_used']))
        cases.append(dict(case=label,generated_samples=generated,transition_samples=sum(parts.values()),sampled_targets=len(targets),
            ordinary_clear_by_memory_reason=dict(clear_reasons.most_common()),
            non_scalar_target_transition_by_memory_reason=dict(transition_reasons.most_common()),
            report=str(report.relative_to(ROOT)),report_sha256=sha(report),top_callees=[{k:r[k] for k in
                ['function','name','frame_size','arguments','result','memory_reason','scalar','captured_scalar_body','call_samples','return_samples','call_parts','return_parts']}
                for r in targets[:15]]))
        for p in [map_path,sample_path,fine_path,folder/'jit-code/code.bin',report]:evidence[str(p.relative_to(ROOT))]=sha(p)
    out=ROOT/'results'/name;out.mkdir(exist_ok=True)
    write(out/'attribution.json',dict(status='passed',cases=cases,evidence=evidence,functions=len(rows),callsites=len(calls),
        memory_work_used=census['memory_work_used'],original_project_guest_commands=0,performance_measurement=False,
        limitation='Partial perturbed current same-process samples. Structural proofs do not model runtime preparation or arena admission. No latency benefit is established.'))
    print(json.dumps([dict(case=c['case'],clear=c['ordinary_clear_by_memory_reason'],transitions=c['non_scalar_target_transition_by_memory_reason']) for c in cases]),flush=True)

if __name__=='__main__':main()
