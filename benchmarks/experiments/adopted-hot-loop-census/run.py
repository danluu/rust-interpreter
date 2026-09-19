"""Offline loop coverage in two closed adopted-runtime captures; no new guest."""
from collections import Counter
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from graph import analyze, cycle_at, range_cycle

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
from summarize_owned_sample import parse_tree, self_samples
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scratch-memory-values'))
from native_observation import logical_counts, validate
sys.path.insert(0,str(ROOT/'benchmarks/experiments/operation-map'))
from attribute import assign

RUN='adopted-hot-loop-census-01'
VM='6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf'
KEY='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
CONTROLS=16
CAPTURE='adopted-current-runtime-sampling-02'
PROFILES='compact-switch-current-host-01'

def read(path):
    assert path.stat().st_size <= 256*1024**2,path
    return json.loads(path.read_text())

def relative(path):return str(path.relative_to(ROOT))

def inputs():
    frozen={}
    def bind(path,expected=None):
        digest=sha(path)
        if expected is not None:assert digest==expected,path
        key=relative(path)
        assert key not in frozen or frozen[key]==digest
        frozen[key]=digest
        return read(path) if path.suffix=='.json' else digest
    closed={}
    for run in [CAPTURE,PROFILES]:
        folder=ROOT/'results'/run
        closure=bind(folder/'closure.json')
        assert closure['status']=='closed' and closure['all_hashes_verified']
        summary=bind(folder/'summary.json',closure['summary_sha256'])
        terminal=bind(folder/'terminal.json',closure['terminal_sha256'])
        assert summary['status']=='passed' and terminal['status']=='finished' and terminal['returncode']==0
        evidence=bind(ROOT/closure['evidence'],closure['evidence_sha256'])
        closed[run]=(summary,evidence)
    sample_summary,sample_evidence=closed[CAPTURE]
    profile_summary,profile_evidence=closed[PROFILES]
    assert sample_summary['vm_sha256']==VM and sample_summary['tool_key']==KEY
    assert profile_summary['adopted_tool_key']==KEY and profile_summary['exact_current_per_pc_counts']
    for index,label in enumerate(['block','exhaustive']):
        sample='adopted-current-sample-'+label+'-02'
        row=sample_summary['cases'][index]
        assert row['case']==label and row['run_id']==sample
        report_path=ROOT/row['report']
        assert sample_evidence[relative(report_path)]==row['report_sha256']
        report=bind(report_path,row['report_sha256'])
        assert report['vm_sha256']==VM and report['status']=='passed' and report['unassigned_generated_samples']==0
        # Reuse exact data the closed attribution consumed; helper sources are
        # bound separately to this revision, not assumed identical to old helpers.
        for p,h in report['evidence'].items():
            if p.startswith(('.work/','results/')):
                assert sample_evidence[p]==h
                bind(ROOT/p,h)
        profile=ROOT/'.work'/PROFILES/'adopted'/f'{index}-profile.json'
        expected=profile_summary['comparisons'][index]['adopted']['profile_sha256']
        assert profile_evidence[relative(profile)]==expected
        bind(profile,expected)
    paths=list(HERE.glob('*.py'))+list(HERE.glob('*.md'))
    paths += [ROOT/'scripts'/x for x in ['workflow_io.py','compare_saved_runtime.py','summarize_owned_sample.py','supervise_experiment.py']]
    paths += [ROOT/'benchmarks/experiments/operation-map'/x for x in ['maps.py','attribute.py']]
    paths += [ROOT/'benchmarks/experiments/scratch-memory-values/native_observation.py', ROOT/'crates/bytecode/src/lib.rs']
    for path in paths:bind(path)
    return frozen


def case(index,label):
    require_space(ROOT,8)
    folder=ROOT/'.work'/('adopted-current-sample-'+label+'-02')/'0'
    report=read(ROOT/'results'/('adopted-current-sample-'+label+'-02')/'operation-attribution.json')
    profile=read(ROOT/'.work'/PROFILES/'adopted'/f'{index}-profile.json')
    old_profile_path=next(p for p in report['evidence'] if p.endswith('-profile.json'))
    old_profile=read(ROOT/old_profile_path)
    assert len(profile['functions'])==len(old_profile['functions'])==5468
    for a,b in zip(profile['functions'],old_profile['functions']):
        for key in ['name','operations','frame_size','registers']:assert a[key]==b[key]
    del old_profile
    native=read(folder/'jit-code/map.json');operations=read(folder/'jit-code/operations.json')
    record=read(folder/'record.json')
    assert record['identity']['status']=='finished' and record['identity']['returncode']==0
    assert not native['profiled']
    checked=validate(operations,native,(folder/'jit-code/code.bin').read_bytes(),profile,record['identity']['pid'])
    frames=[item for tree in parse_tree((folder/'sample.txt').read_text()) for item in self_samples(tree)]
    labels,sites,unresolved=assign(checked,native['arena_base'],frames)
    assert not unresolved and dict(labels)==report['by_label']
    assert sum(labels.values())==report['attributed_generated_samples']
    del checked,operations,frames
    logical,totals=logical_counts(profile)
    assert sum(len(f['operations']) for f in profile['functions'])<=2_000_000
    graphs=[];cycles=[];static=Counter();lookup={}
    for fid,f in enumerate(profile['functions']):
        graph=analyze(f['operations']);graphs.append(graph)
        static['functions']+=1;static['operations']+=len(f['operations']);static['blocks']+=graph['blocks']
        static['unreachable_operations']+=graph['unreachable_operations']
        for cycle in graph['cycles']:
            row=dict(cycle,function=fid,name=f['name'],frame_size=f['frame_size'],registers=f['registers'],
                direct_samples=0,region_overhead_samples=0,direct_labels={},overhead_labels={},
                logical_operations=sum(sum(logical[fid][lo:hi]) for lo,hi in cycle['ranges']))
            lookup[fid,row['index']]=row;cycles.append(row)
            prefix='reachable' if row['reachable'] else 'unreachable'
            static[prefix+'_cyclic_components']+=1;static[prefix+'_cyclic_operations']+=row['operations']
    regions={(r['function'],r['pc']):r for r in native['ranges']}
    partitions=Counter();direct_labels=Counter();overhead_labels=Counter();site_rows=[]
    for (fid,region,pc,kind,label_name),count in sorted(sites.items(),key=lambda item:str(item[0])):
        graph=graphs[fid]
        if pc is not None:
            selected=cycle_at(graph,pc)
            bucket='direct_cycle' if selected>=0 else 'direct_acyclic'
        elif kind=='scalar_leaf':
            selected=None;bucket='scalar_whole_body'
        else:
            span=regions[fid,region]
            selected=range_cycle(graph,span['pc'],span['pc_end'])
            bucket='overhead_mixed_region' if selected is None else ('overhead_cycle' if selected>=0 else 'overhead_acyclic')
        if selected is not None and selected>=0:
            row=lookup[fid,selected]
            assert row['reachable'],'sample attributed to unreachable CFG component'
            direct=pc is not None
            key='direct_samples' if direct else 'region_overhead_samples';row[key]+=count
            field='direct_labels' if direct else 'overhead_labels'
            row[field][label_name]=row[field].get(label_name,0)+count
            (direct_labels if direct else overhead_labels)[label_name]+=count
        partitions[bucket]+=count
        site_rows.append(dict(function=fid,region_pc=region,pc=pc,kind=kind,label=label_name,
            samples=count,bucket=bucket,component=selected if selected is not None and selected>=0 else None))
    total=sum(labels.values());assert sum(partitions.values())==total
    active=[r for r in cycles if r['reachable']]
    buckets={}
    for title,predicate in [
        ('all_cycles',lambda r:True),
        ('single_entry',lambda r:len(r['entries'])==1),
        ('multiple_entry',lambda r:len(r['entries'])>1),
        ('call_free',lambda r:r['calls']==0),
        ('single_entry_call_free',lambda r:len(r['entries'])==1 and r['calls']==0),
        ('single_entry_call_free_at_most_512_ops',lambda r:len(r['entries'])==1 and r['calls']==0 and r['operations']<=512),
        ('single_entry_call_free_at_most_128_ops',lambda r:len(r['entries'])==1 and r['calls']==0 and r['operations']<=128),
        ('with_calls',lambda r:r['calls']>0)]:
        rows=[r for r in active if predicate(r)]
        buckets[title]=dict(components=len(rows),static_operations=sum(r['operations'] for r in rows),
            direct_samples=sum(r['direct_samples'] for r in rows),
            region_overhead_samples=sum(r['region_overhead_samples'] for r in rows),
            logical_operations=sum(r['logical_operations'] for r in rows))
    ranked=sorted(active,key=lambda r:(-r['direct_samples'],-r['region_overhead_samples'],r['function'],r['index']))
    summary=dict(case=label,generated_samples=total,partitions=dict(partitions),static=dict(static),
        coverage=buckets,cyclic_direct_labels=dict(direct_labels),cyclic_overhead_labels=dict(overhead_labels),
        whole_test_fixed_entropy_logical=totals,top_components=ranked[:12],
        unassigned_generated_samples=0)
    details=dict(case=label,components=cycles,sites=site_rows)
    return summary,details


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen=inputs()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,controls=CONTROLS,
            guest_commands=0,host_builds=0,production_changes=0,performance_measurement=False))
        child,out,err=capture([sys.executable,'-m','unittest','test_graph','-v'],cwd=HERE,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=raw/'active.json',receipt=dict(stage='graph controls'))
        (raw/'controls.stdout').write_text(out);(raw/'controls.stderr').write_text(err)
        write(raw/'records.json',[dict(label='controls',pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/'controls.stdout'),stderr_sha256=sha(raw/'controls.stderr'))])
        assert child.returncode==0 and f'Ran {CONTROLS} tests' in err and err.rstrip().endswith('OK'),err
        cases=[];detail_hashes={}
        for index,label in enumerate(['block','exhaustive']):
            summary,detail=case(index,label)
            write(raw/(label+'-details.json'),detail)
            detail_hashes[label]=sha(raw/(label+'-details.json'));cases.append(summary)
            print(json.dumps(dict(case=label,generated=summary['generated_samples'],partitions=summary['partitions'],coverage=summary['coverage'])),flush=True)
            del detail;gc.collect()
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=relative(raw),
            tool_key=KEY,vm_sha256=VM,controls=CONTROLS,plan_sha256=sha(raw/'plan.json'),
            records_sha256=sha(raw/'records.json'),details_sha256=detail_hashes,cases=cases,
            guest_commands=0,host_builds=0,production_changes=0,executable_code_publications=0,
            performance_measurement=False,
            limitation='Normal-return intraprocedural CFG overapproximates possible paths. No alias, bounds, SSA, reducibility, or optimization-safety proof. Partial perturbed normal-entropy native self-PC windows are separate from fixed-entropy whole-test logical counts. Region-associated overhead is separate from direct operation samples. Callee work is not attributed to caller loops. No elapsed-time or speedup inference.'))


def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        out=ROOT/'results'/RUN;s=read(out/'summary.json');raw=ROOT/s['raw']
        assert s['status']=='passed' and s['controls']==CONTROLS
        for key in ['plan','records']:assert sha(raw/(key+'.json'))==s[key+'_sha256']
        plan=read(raw/'plan.json');assert plan['frozen']==inputs()
        assert plan['source_revision']==s['source_revision']
        bindings={}
        for p,h in plan['frozen'].items():
            if p.startswith(('.work/','results/')):bindings[p]=dict(kind='retained',sha256=h)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h
                bindings[p]=dict(kind='git',revision=plan['source_revision'],sha256=h)
        records=read(raw/'records.json');assert len(records)==1
        record=records[0];assert record['returncode']==0
        for stream in ['stdout','stderr']:assert sha(raw/('controls.'+stream))==record[stream+'_sha256']
        stderr=(raw/'controls.stderr').read_text()
        assert f'Ran {CONTROLS} tests' in stderr and stderr.rstrip().endswith('OK')
        for index,label in enumerate(['block','exhaustive']):
            assert sha(raw/(label+'-details.json'))==s['details_sha256'][label]
            summary,details=case(index,label)
            assert summary==s['cases'][index] and details==read(raw/(label+'-details.json'))
            del details;gc.collect()
        outer=ROOT/'.work/experiments'/RUN;t=read(outer/'status.json')
        assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
        assert t['command']==[str(Path(sys.executable)),str(HERE/'run.py')]
        assert sha(outer/'command.log')==t['log_sha256'] and sha(outer/'plan.json')==t['plan_sha256']
        assert not (out/'closure.json').exists()
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(raw/'bindings.json',bindings)
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,all_derivations_recomputed=True,
            frozen_inputs=len(bindings),source_revision=plan['source_revision'],bindings=relative(raw/'bindings.json'),
            bindings_sha256=sha(raw/'bindings.json'),summary_sha256=sha(out/'summary.json'),
            terminal_sha256=sha(out/'terminal.json'),guest_commands=0,performance_measurement=False))
        print('CLOSED',len(bindings),'bindings; both full derivations recomputed',flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert not sys.argv[1:];main()
