"""Count adopted allocator exits and their observed adjacent native overhead."""
from collections import Counter
import gc,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scratch-memory-values'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
from native_observation import logical_counts
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='allocator-exit-scope-01';LOOPS='adopted-hot-loop-census-02'
BASE='fca687ebac0ea9374a1426addd01169fe707f608'
KINDS={'Allocate','Deallocate','Reallocate','CAllocate','CDeallocate','CReallocate','CAlignedAllocate'}
read=focus.read

def inputs():
    frozen={}
    def bind(p,expected=None):
        digest=sha(p)
        if expected is not None:assert digest==expected,p
        frozen[str(p.relative_to(ROOT))]=digest
        return read(p) if p.suffix=='.json' else digest
    folder=ROOT/'results'/LOOPS;closure=bind(folder/'closure.json')
    assert closure['status']=='closed' and closure['all_hashes_verified'] and closure['all_derivations_recomputed']
    summary=bind(folder/'summary.json',closure['summary_sha256'])
    terminal=bind(folder/'terminal.json',closure['terminal_sha256'])
    assert summary['status']=='passed' and terminal['status']=='finished' and terminal['returncode']==0
    assert terminal['owner']==terminal['cwd']==str(ROOT)
    bindings=bind(ROOT/closure['bindings'],closure['bindings_sha256'])
    for p,row in bindings.items():bind(ROOT/p,row['sha256'])
    for label,h in summary['details_sha256'].items():bind(ROOT/summary['raw']/(label+'-details.json'),h)
    folder=ROOT/'results/compact-switch-current-host-01';closure=bind(folder/'closure.json')
    assert closure['status']=='closed' and closure['all_hashes_verified']
    control=bind(folder/'summary.json',closure['summary_sha256'])
    assert control['status']=='passed' and control['exact_current_per_pc_counts']
    for case in control['comparisons']:
        bind(ROOT/control['raw']/'adopted'/f"{case['index']}-profile.json",case['adopted']['profile_sha256'])
    folder=ROOT/'results/adopted-current-runtime-sampling-02';closure=bind(folder/'closure.json')
    assert closure['status']=='closed' and closure['all_hashes_verified']
    samples=bind(folder/'summary.json',closure['summary_sha256'])
    assert samples['status']=='passed' and samples['ordinary_entropy'] and not samples['performance_measurement']
    for c in samples['cases']:
        bind(ROOT/c['report'],c['report_sha256'])
    assert not subprocess.check_output(['git','diff','--name-only',BASE,'--','crates'],cwd=ROOT).strip()
    for p in subprocess.check_output(['git','ls-files','crates'],cwd=ROOT,text=True).splitlines():bind(ROOT/p)
    for p in [*HERE.glob('*.py'),*HERE.glob('*.md'),Path(focus.__file__),
              ROOT/'benchmarks/experiments/scratch-memory-values/native_observation.py']:
        bind(p)
    for name in ['workflow_io.py','compare_saved_runtime.py','supervise_experiment.py']:bind(ROOT/'scripts'/name)
    return frozen,control,samples

def derive(control,samples):
    result=[]
    for reference in control['comparisons']:
        require_space(ROOT,8);index=reference['index'];profile=read(ROOT/control['raw']/'adopted'/f'{index}-profile.json')
        logical,totals=logical_counts(profile)
        assert totals['total']==reference['adopted']['statistics']['instructions']
        assert totals['interpreted']==reference['adopted']['logical_counts']['interpreted']
        by_kind=Counter();sites=[];active=set()
        for fid,function in enumerate(profile['functions']):
            for pc,operation in enumerate(function['operations']):
                kind=operation.split(' ',1)[0]
                if kind not in KINDS:continue
                count=logical[fid][pc]
                assert count==function['interpreted'][pc],(fid,pc,kind)
                by_kind[kind]+=count
                if count:
                    active.add((fid,pc));next_pc=pc+1
                    following_native=next_pc<len(function['operations']) and function['jit_block_ends'][next_pc]>next_pc
                    sites.append(dict(function=fid,name=function['name'],pc=pc,kind=kind,logical_executions=count,following_native_entry=following_native))
        row=dict(index=index,name=reference['name'],whole_test_logical=totals,allocator_operations=dict(by_kind),
            allocator_executions=sum(by_kind.values()),active_allocator_sites=len(sites),
            executions_with_following_native_entry=sum(s['logical_executions'] for s in sites if s['following_native_entry']),
            sites=sorted(sites,key=lambda s:(-s['logical_executions'],s['function'],s['pc'])))
        assert row['allocator_executions']<=totals['interpreted']
        if index<2:
            label=['block','exhaustive'][index];sample,=[s for s in samples['cases'] if s['case']==label]
            details=read(ROOT/'.work'/LOOPS/(label+'-details.json'))
            native=read(ROOT/'.work'/('adopted-current-sample-'+label+'-02')/'0/jit-code/map.json')
            assert not native['profiled']
            regions={(r['function'],r['pc']):r for r in native['ranges'] if r['kind']!='scalar_leaf'}
            buckets=Counter();attributed=0;nearby=[]
            for site in details['sites']:
                count=site['samples'];attributed+=count
                key=(site['function'],site['region_pc']);region=regions.get(key)
                if region is None:continue
                category=None
                if site['label'] in ['entry','range_guard'] and (key[0],region['pc']-1) in active:
                    category='entry_after_allocator'
                elif site['label'] in ['flush','region_exit','successor_fallback'] and (key[0],region['pc_end']) in active:
                    category='exit_before_allocator'
                if category:
                    buckets[category]+=count;nearby.append(dict(site,scope_category=category))
            assert attributed==sample['attributed_generated_samples']
            row['partial_sample_window']=dict(generated_self_samples=attributed,allocator_adjacent_generated_samples=dict(buckets),
                native_boundary_self=sample['disjoint_counts'].get('native_boundary_self',0),
                other_host_self=sample['disjoint_counts'].get('other_host_self',0),
                heap_context_self=sample['disjoint_counts'].get('heap_inclusive',0),
                all_disjoint_counts=sample['disjoint_counts'],adjacent_sites=nearby,
                limitation='Sample windows are partial; allocator frequency is not latency. Broad host buckets are not allocation-specific; heap implementation cost is not removed by a bridge.')
        result.append(row);del profile,logical;gc.collect()
    return result

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12);frozen,control,samples=inputs()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=0,original_project_guest_commands=0,
            source_builds=0,performance_measurement=False,adopted_runtime_source=BASE))
        cases=derive(control,samples);write(raw/'cases.json',cases)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=0,
            cases=cases,outputs={str((raw/'cases.json').relative_to(ROOT)):sha(raw/'cases.json')},
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),original_project_guest_commands=0,
            source_builds=0,performance_measurement=False,default_runtime_adoption=False))
        for c in cases:
            window=c.get('partial_sample_window',{})
            print(c['index'],'allocator operations',c['allocator_executions'],'of',c['whole_test_logical']['interpreted'],
                  'interpreted; adjacent native samples',window.get('allocator_adjacent_generated_samples'),flush=True)

def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        terminal=read(ROOT/'.work/experiments'/RUN/'status.json')
        if terminal['returncode']==0:
            frozen,control,samples=inputs();summary=read(ROOT/'results'/RUN/'summary.json')
            assert derive(control,samples)==summary['cases']
    focus.RUN=RUN;focus.close()

if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()
