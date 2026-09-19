"""Join closed actual template misses to hash-bound consecutive bytecode differences."""
import json,subprocess,sys
from collections import Counter,defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='template-miss-causes-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12);frozen={}
        def bind(p,h=None):
            actual=sha(p)
            if h is not None:assert actual==h,p
            frozen[str(p.relative_to(ROOT))]=actual
            return read(p) if p.suffix=='.json' else actual
        def closed(name):
            p=ROOT/'results'/name;c=bind(p/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            s=bind(p/'summary.json',c['summary_sha256']);t=bind(p/'terminal.json',c['terminal_sha256'])
            assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0 and t['owner']==str(ROOT)
            return s
        trace=closed('template-miss-parser-01');assert trace['history_reconstructed'] and trace['test_invocations']==1824
        diff=closed('cross-edit-emission-differences-01')
        for s in [trace,diff]:
            bind(ROOT/s['raw']/'plan.json',s['plan_sha256']);bind(ROOT/s['raw']/'records.json',s['records_sha256'])
        changes=bind(ROOT/diff['raw']/'report.json',diff['outputs'][diff['raw']+'/report.json'])['comparisons']
        inputs=bind(ROOT/diff['raw']/'inputs.json',diff['outputs'][diff['raw']+'/inputs.json'])
        assert [a['state'] for a in inputs]==[0,-1,1,2,3,4,5,0]
        saved=closed('cross-program-template-suites-01');cases=bind(ROOT/saved['raw']/'input.json',saved['outputs'][saved['raw']+'/input.json'])['cases']
        assert [(a['state'],a['sha256']) for a in inputs]==[(a['state'],a['artifact_sha256']) for a in cases]
        for a in inputs:bind(Path(a['path']),a['sha256'])
        maps=[]
        for i,row in enumerate(changes):
            assert row['previous_artifact_sha256']==inputs[i]['sha256'] and row['artifact_sha256']==inputs[i+1]['sha256']
            assert all(row['global_fields_equal'][k] for k in ['entry','function_count','heap_mode','target','thread_locals','version'])
            byid={f['function']:f for f in row['changed_functions']};assert len(byid)==len(row['changed_functions']);maps.append(byid)
        histories=[{},{}];rows=[];counts=Counter();nanos=Counter();top=[]
        for ordinal,case in enumerate(cases):
            path=ROOT/trace['raw']/'cached'/f'{ordinal}.report.json';report=bind(path,trace['outputs'][str(path.relative_to(ROOT))])
            assert report['request_id']==ordinal+1 and report['selected']==report['completed']==114
            assert sorted((t['name'],t['status']) for t in report['tests'])==sorted(map(tuple,case['expected']))
            for w in report['worker_records']:
                hist=histories[w['worker']];events=w['templates']['trace'];assert w['templates']['trace_dropped']==0
                assert sum(e['emission_ns'] for e in events)==w['templates']['miss_emit_ns']
                local_count=Counter();local_ns=Counter()
                for e in events:
                    fid=e['function'];old=hist.get(fid);hist[fid]=(ordinal,e['key'])
                    if e['lookup']=='hit':continue
                    delta=[] if old is None else [m[fid] for m in maps[old[0]:ordinal] if fid in m]
                    if old is None:kind='first_worker_function'
                    elif not delta:kind='unchanged_body'
                    elif any(not d.get('same_name',False) for d in delta):kind='function_identity_moved'
                    elif all(d.get('only_immediate_values_changed',False) for d in delta):kind='immediate_values_only'
                    elif all(d.get('same_metadata',False) and d.get('same_operation_count',False)
                        and set(d.get('categories',{}))<={'immediate_value_only','direct_call_id_only'} for d in delta):kind='immediates_and_call_ids'
                    else:kind='other_body_changes'
                    if old is not None and old[1]==e['key']:kind='same_key_not_retained'
                    local_count[kind]+=1;local_ns[kind]+=e['emission_ns']
                    if case['state']>0:
                        counts[kind]+=1;nanos[kind]+=e['emission_ns']
                        top.append(dict(ordinal=ordinal,state=case['state'],worker=w['worker'],function=fid,category=kind,
                            emission_ns=e['emission_ns'],previous_ordinal=None if old is None else old[0],
                            source_difference_categories=[d.get('categories',{}) for d in delta],
                            current_name=delta[-1].get('name') if delta else None))
                rows.append(dict(ordinal=ordinal,state=case['state'],worker=w['worker'],counts=dict(local_count),emission_ns=dict(local_ns)))
        paths=[p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [Path(focus.__file__),ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']
        for p in paths:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=0,original_project_guest_commands=0,performance_measurement=False))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=0,
            valid_edit_counts=dict(counts),valid_edit_emission_ns=dict(nanos),all_states=rows,
            most_expensive_valid_misses=sorted(top,key=lambda r:r['emission_ns'],reverse=True)[:40],
            original_project_guest_commands=0,performance_measurement=False,
            scope='Observed bytecode differences between each worker/function attempt, not isolated causes. Diagnostic intervals overlap across workers; no predicted command savings or changed cache policy.'))
        print(json.dumps(dict(counts=counts,emission_ms={k:v/1e6 for k,v in nanos.items()})),flush=True)
if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
