"""Read-only copy-equality scope joined to independently closed PC samples."""
from collections import Counter
import gc,hashlib,json,os,subprocess,sys
from pathlib import Path
from model import Region
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scratch-memory-values'))
from native_observation import logical_counts
RUN='local-copy-equality-01';LOOPS='adopted-hot-loop-census-02';CONTROLS=14
def read(p):
    assert p.stat().st_size<=256*1024**2
    return json.loads(p.read_text())
def rel(p):return str(p.relative_to(ROOT))
def inputs():
    frozen={}
    def bind(p,expected=None):
        h=sha(p)
        if expected is not None:assert h==expected,p
        frozen[rel(p)]=h
        return read(p) if p.suffix=='.json' else h
    out=ROOT/'results'/LOOPS;c=bind(out/'closure.json')
    assert c['status']=='closed' and c['all_hashes_verified'] and c['all_derivations_recomputed']
    s=bind(out/'summary.json',c['summary_sha256'])
    t=bind(out/'terminal.json',c['terminal_sha256'])
    assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0
    bindings=bind(ROOT/c['bindings'],c['bindings_sha256'])
    for p,row in bindings.items():bind(ROOT/p,row['sha256'])
    for label,h in s['details_sha256'].items():bind(ROOT/s['raw']/(label+'-details.json'),h)
    for p in HERE.iterdir():
        if p.suffix in ['.py','.md']:bind(p)
    for name in ['workflow_io.py','compare_saved_runtime.py','supervise_experiment.py']:bind(ROOT/'scripts'/name)
    bind(ROOT/'benchmarks/experiments/scratch-memory-values/native_observation.py')
    return frozen

def case(index,label):
    require_space(ROOT,8)
    details=read(ROOT/'.work'/LOOPS/(label+'-details.json'))
    profile=read(ROOT/'.work/compact-switch-current-host-01/adopted'/f'{index}-profile.json')
    native=read(ROOT/'.work'/('adopted-current-sample-'+label+'-02')/'0/jit-code/map.json')
    assert native['profiled'] is False
    logical,totals=logical_counts(profile)
    samples=Counter();cyclic_samples=Counter();by_label=Counter()
    for row in details['sites']:
        by_label[row['label']]+=row['samples']
        if row['pc'] is not None and row['label']=='operation:Copy':
            samples[row['function'],row['pc']]+=row['samples']
            if row['bucket']=='direct_cycle':cyclic_samples[row['function'],row['pc']]+=row['samples']
    assert sum(samples.values())==by_label['operation:Copy']
    rows=[];counts=Counter();functions=Counter();seen=set()
    for native_region in native['ranges']:
        if native_region['kind']=='scalar_leaf':continue
        fid=native_region['function'];f=profile['functions'][fid]
        start,end=native_region['pc'],native_region['pc_end']
        assert 0<=start<end<=len(f['operations']) and end-start<=1024
        model=Region(f['frame_size']);counts['regions']+=1
        for pc in range(start,end):
            assert (fid,pc) not in seen;seen.add((fid,pc))
            op=f['operations'][pc];counts['operations']+=1
            if op.startswith('Copy {'):
                counts['copy_operations']+=1;counts['copy_logical_executions']+=logical[fid][pc]
            match=model.step(op)
            if match:
                n=samples[fid,pc];cyclic=cyclic_samples[fid,pc]
                row=dict(function=fid,name=f['name'],pc=pc,region_start=start,region_end=end,
                    **match,samples=n,cyclic_samples=cyclic,logical_executions=logical[fid][pc])
                rows.append(row);counts['modeled_redundant_copies']+=1
                counts['modeled_redundant_copy_samples']+=n;counts['modeled_cyclic_copy_samples']+=cyclic
                counts['modeled_redundant_copy_logical']+=logical[fid][pc]
                counts[match['reason']+'_samples']+=n
                functions[fid]+=n
        counts['unmodeled_effect_barriers']+=model.barriers
    assert all((fid,pc) in seen for fid,pc in samples)
    total=sum(by_label.values());redundant=counts['modeled_redundant_copy_samples']
    assert redundant<=sum(samples.values())<=total
    summary=dict(case=label,generated_samples=total,copy_samples=sum(samples.values()),counts=dict(counts),
        modeled_copy_sample_percent=100*redundant/total,
        whole_test_fixed_entropy_logical=totals,
        top_functions=[dict(function=fid,name=profile['functions'][fid]['name'],samples=n) for fid,n in functions.most_common(12)],
        top_sites=sorted(rows,key=lambda r:(-r['samples'],-r['logical_executions'],r['function'],r['pc']))[:20])
    return summary,rows

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen=inputs();revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(source_revision=revision,owner=str(ROOT),frozen=frozen,controls=CONTROLS,
            guest_commands=0,host_builds=0,production_changes=0,performance_measurement=False))
        require_space(ROOT,8)
        child,stdout,stderr=capture([sys.executable,'-m','unittest','test_model','-v'],cwd=HERE,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=raw/'active.json',receipt=dict(stage='model controls'))
        (raw/'controls.stdout').write_text(stdout);(raw/'controls.stderr').write_text(stderr)
        write(raw/'records.json',[dict(pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/'controls.stdout'),stderr_sha256=sha(raw/'controls.stderr'))])
        assert child.returncode==0 and f'Ran {CONTROLS} tests' in stderr and stderr.rstrip().endswith('OK'),stderr
        cases=[];detail_hashes={}
        for index,label in enumerate(['block','exhaustive']):
            s,rows=case(index,label);cases.append(s)
            write(raw/(label+'-details.json'),rows);detail_hashes[label]=sha(raw/(label+'-details.json'))
            print(json.dumps({k:v for k,v in s.items() if k not in ['top_sites','top_functions']}),flush=True)
            del rows;gc.collect()
        assert frozen==inputs()
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',raw=rel(raw),source_revision=revision,controls=CONTROLS,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),details_sha256=detail_hashes,
            cases=cases,guest_commands=0,host_builds=0,production_changes=0,performance_measurement=False,
            limitation='Diagnostic rendered-operation model, not an emitter proof or native instruction saving. Native partial normal-entropy self-PC samples and fixed-entropy whole-test logical executions remain separate. No speedup or adoption inference. Typed exact-emitter qualification required before runtime changes.'))

def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        out=ROOT/'results'/RUN;s=read(out/'summary.json');raw=ROOT/s['raw']
        assert s['status']=='passed' and s['controls']==CONTROLS
        for key in ['plan','records']:assert sha(raw/(key+'.json'))==s[key+'_sha256']
        plan=read(raw/'plan.json');assert plan['frozen']==inputs()
        bindings={}
        for p,h in plan['frozen'].items():
            if p.startswith(('.work/','results/')):bindings[p]=dict(kind='retained',sha256=h)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h
                bindings[p]=dict(kind='git',revision=plan['source_revision'],sha256=h)
        record,=read(raw/'records.json');assert record['returncode']==0
        for stream in ['stdout','stderr']:assert sha(raw/('controls.'+stream))==record[stream+'_sha256']
        stderr=(raw/'controls.stderr').read_text();assert f'Ran {CONTROLS} tests' in stderr and stderr.rstrip().endswith('OK')
        for index,label in enumerate(['block','exhaustive']):
            assert sha(raw/(label+'-details.json'))==s['details_sha256'][label]
            summary,rows=case(index,label)
            assert summary==s['cases'][index] and rows==read(raw/(label+'-details.json'))
            del rows;gc.collect()
        outer=ROOT/'.work/experiments'/RUN;t=read(outer/'status.json')
        assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
        assert Path(t['command'][0]).resolve()==Path(sys.executable).resolve()
        assert t['command'][1:]==[str(HERE/'analyze.py')]
        assert sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
        assert not (out/'closure.json').exists()
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes());write(raw/'bindings.json',bindings)
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,all_derivations_recomputed=True,
            source_revision=plan['source_revision'],frozen_inputs=len(bindings),bindings=rel(raw/'bindings.json'),
            bindings_sha256=sha(raw/'bindings.json'),summary_sha256=sha(out/'summary.json'),
            terminal_sha256=sha(out/'terminal.json'),guest_commands=0,performance_measurement=False))
        print('CLOSED',len(bindings),'bindings and both derivations',flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert not sys.argv[1:];main()
