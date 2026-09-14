"""Join exact entry-guard candidates to closed adopted samples."""
import collections,importlib.util,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
spec=importlib.util.spec_from_file_location('closed_call_join',ROOT/'benchmarks/experiments/native-call-cost-census/analyze.py')
join=importlib.util.module_from_spec(spec);spec.loader.exec_module(join)
NAME='scalar-entry-dependency-coverage-01'
def read(p):
    assert p.stat().st_size<=256*1024**2
    return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),ROOT/'benchmarks/experiments/native-call-cost-census/analyze.py']
        paths += [ROOT/'scripts'/n for n in ['compare_saved_runtime.py','workflow_io.py','summarize_owned_sample.py']]
        for name in ['current-call-shapes-01','scalar-protocol-census-03']:
            folder=ROOT/'results'/name;closed=read(folder/'closure.json')
            assert closed['status']=='closed' and closed['all_hashes_verified']
            assert sha(folder/'summary.json')==closed['summary_sha256']
            binding=ROOT/closed['bindings'];assert sha(binding)==closed['bindings_sha256']
            paths += [folder/'summary.json',folder/'closure.json',binding]
            for p,h in read(binding)['artifacts'].items():assert sha(ROOT/p)==h;paths.append(ROOT/p)
        typed_path=ROOT/'.work/current-call-shapes-01/census.json';typed=read(typed_path)
        entry_folder=ROOT/'results/scalar-entry-dependency-census-02'
        entry_closed=read(entry_folder/'closure.json');entry_summary=read(entry_folder/'summary.json')
        assert entry_closed['status']=='closed' and entry_closed['logs_verified']
        assert sha(entry_folder/'summary.json')==entry_closed['summary_sha256']
        entry_binding=ROOT/entry_closed['source_bindings'];assert sha(entry_binding)==entry_closed['source_bindings_sha256']
        paths += [entry_folder/'summary.json',entry_folder/'closure.json',entry_binding]
        for p,b in read(entry_binding).items():
            if b['kind']=='retained': assert sha(ROOT/p)==b['sha256'];paths.append(ROOT/p)
        entry_path=ROOT/entry_summary['raw']/'census.json';entry=read(entry_path)
        input_path=entry_path.with_name('inputs.json');inputs=read(input_path)
        assert sha(entry_path)==entry_summary['census_sha256'] and sha(input_path)==entry_summary['inputs_sha256']
        assert entry['status']==typed['status']=='passed';assert len(entry['cases'])==len(inputs)==3
        assert typed['functions']==len(typed['rows'])
        shapes={f['function']:f for f in typed['rows']};assert sorted(shapes)==list(range(typed['functions']))
        policies={};evidence_rows={}
        for label,index in [('block',0),('exhaustive',1)]:
            c,=[c for c in entry['cases'] if c['index']==index];i,=[i for i in inputs if i['index']==index]
            assert i['artifact_sha256']==typed['artifact_sha256']
            assert all(shapes[f['function']]['name']==f['name'] for f in c['functions'])
            ids={f['function'] for f in c['functions'] if f['eligible']}
            assert len(ids)==len([f for f in c['functions'] if f['eligible']])
            policies[label]=ids;evidence_rows[label]={f['function']:f for f in c['functions'] if f['eligible']}
        paths += [entry_path,input_path]
        callees=collections.defaultdict(set);calls={}
        for c in typed['calls']:
            key=(c['caller'],c['pc']);assert key not in calls and c['callee'] in shapes
            calls[key]=c;callees[c['caller']].add(c['callee'])
        prior_path=ROOT/'results/scalar-protocol-census-03/attribution.json';prior=read(prior_path)
        paths += [typed_path,prior_path]
        captures=[]
        for label in ['block','exhaustive']:
            folder=ROOT/'.work'/('scratch-scalar-runtime-sample-'+label+'-01')/'0'
            mapping_path=folder/'jit-code/operations.json';sample_path=folder/'sample.txt'
            fine_path=ROOT/'.work/scalar-protocol-census-03'/(label+'.json')
            mapping,fine=read(mapping_path),read(fine_path)
            assert mapping['schema_version']==fine['schema_version']==2
            assert mapping['complete'] and mapping['reconstructed_bytes_match'] and not mapping['profiled']
            assert fine['exact_full_function_reconstruction'] and fine['exact_transition_reconstruction'] and fine['complete_partition']
            assert mapping['code_sha256']==fine['code_sha256']==sha(folder/'jit-code/code.bin')
            old,=[c for c in prior['cases'] if c['case']==label]
            for p,h in old['evidence'].items():assert sha(ROOT/p)==h;paths.append(ROOT/p)
            paths += [mapping_path,sample_path,fine_path,folder/'jit-code/code.bin']
            captures.append((label,mapping,fine,sample_path,old))
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,candidates={k:sorted(v) for k,v in policies.items()},guest_commands=0,performance_measurement=False))
        cases=[]
        for label,mapping,fine,sample_path,old in captures:
            require_space(ROOT,8)
            samples=[s for root in parse_tree(sample_path.read_text()) for s in self_samples(root)]
            a,b,parts,generated=join.attribute(calls,mapping,fine,samples)
            assert generated==old['generated_samples'] and dict(parts)==old['fine_samples']
            spans=[dict(s,function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
            starts=[s['offset'] for s in spans];assert starts==sorted(set(starts));bodies=collections.Counter()
            for count,frame,_ in samples:
                if '<unknown binary>' not in frame:continue
                owners=[join.locate(spans,starts,int(addr,16)-mapping['arena_base']) for addr in re.findall(r'0x([0-9a-f]+)',frame)]
                assert owners;identities={(s['function'],s['kind']) for s in owners};assert len(identities)==1
                fid,kind=next(iter(identities))
                if kind!='transition':bodies[fid]+=count
            reports={}
            for policy,ids in [('entry_dependencies',policies[label])]:
                targets=[];by_part=collections.Counter()
                for fid in ids:
                    by_part.update({'Call/'+k:v for k,v in a[fid].items()});by_part.update({'Return/'+k:v for k,v in b[fid].items()})
                    transition=sum(a[fid].values())+sum(b[fid].values());body=bodies[fid]
                    if transition+body:
                        f=shapes[fid];targets.append(dict(function=fid,name=f['name'],frame_size=f['frame_size'],
                            operations=f['operations'],arguments=f['arguments'],result=f['result'],callees=sorted(callees[fid]),
                            transition_samples=transition,body_samples=body,call_parts=dict(a[fid]),return_parts=dict(b[fid]),entry_plan=evidence_rows[label][fid]['entry_plan']))
                targets.sort(key=lambda f:-f['transition_samples']-f['body_samples'])
                reports[policy]=dict(candidate_functions=len(ids),transition_samples=sum(by_part.values()),
                    body_samples=sum(bodies[i] for i in ids),by_part=dict(by_part),sampled_targets=targets)
            cases.append(dict(case=label,generated_samples=generated,policies=reports))
            print(label,{k:(v['transition_samples'],v['body_samples']) for k,v in reports.items()},flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=1,cases=cases,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),guest_commands=0,executable_code_publications=0,performance_measurement=False,
            scope='Static entry-guard candidates from closed archived store-log bodies joined by exact artifact identity to partial perturbed adopted-VM samples. Whole body and transition coverage, not removable time. No new guest execution, direct-effect model, native admission or performance proof.'))
if __name__=='__main__':main()
