"""Replay original tests and reconcile logical counts across bridge partitions."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools

def expanded(function,field):
    size=len(function['operations']);hits=function[field];ends=function[field.replace('blocks','block_ends')]
    assert len(hits)==len(ends)==size
    assert all(type(n) is int and 0<=n<2**64 for n in hits+ends)
    delta=[0]*(size+1)
    for pc,n in enumerate(hits):
        if n:
            end=ends[pc];assert pc<end<=size
            delta[pc]+=n;delta[end]-=n
    total=0;out=[]
    for n in delta[:-1]:total+=n;out.append(total)
    return out

def reconcile(profile,baseline,stats):
    assert len(profile['functions'])==len(baseline['functions'])
    totals=dict(interpreted=0,ordinary=0,tree=0,tree_function_entries=0,native_calls=0,native_returns=0,tree_calls=0)
    moved=[]
    for fid,(f,old) in enumerate(zip(profile['functions'],baseline['functions'])):
        for key in ['name','operations','frame_size','registers']:assert f[key]==old[key],(fid,key)
        assert len(f['interpreted'])==len(old['interpreted'])==len(f['operations'])
        assert all(type(n) is int and 0<=n<2**64 for n in f['interpreted']+old['interpreted'])
        ordinary=expanded(f,'jit_blocks');tree=expanded(f,'jit_tree_blocks')
        old_ordinary=expanded(old,'jit_blocks');old_tree=expanded(old,'jit_tree_blocks')
        logical=[a+b+c for a,b,c in zip(f['interpreted'],ordinary,tree)]
        prior=[a+b+c for a,b,c in zip(old['interpreted'],old_ordinary,old_tree)]
        assert logical==prior,('logical per-PC mismatch',fid)
        totals['interpreted']+=sum(f['interpreted']);totals['ordinary']+=sum(ordinary);totals['tree']+=sum(tree)
        totals['tree_function_entries']+=f['jit_tree_blocks'][0] if tree else 0
        for pc,op in enumerate(f['operations']):
            if op.startswith(('Call {','CallIndirect {')):
                totals['native_calls']+=ordinary[pc]+tree[pc];totals['tree_calls']+=tree[pc]
            elif op=='Return':totals['native_returns']+=ordinary[pc]+tree[pc]
        if ordinary!=old_ordinary or tree!=old_tree or f['interpreted']!=old['interpreted']:
            moved.append(dict(function=fid,name=f['name'],ordinary_instructions=sum(ordinary),tree_instructions=sum(tree),
                interpreted_instructions=sum(f['interpreted']),previous_interpreted_instructions=sum(old['interpreted'])))
    assert totals['ordinary']+totals['tree']==stats['jit_instructions']
    assert totals['interpreted']+stats['jit_instructions']==stats['instructions']
    assert totals['tree']==stats['jit_tree_instructions']
    assert totals['tree_calls']==stats['jit_tree_calls']
    assert totals['tree_function_entries']==stats['jit_tree_calls']+stats['jit_tree_entries']
    assert totals['native_calls']==stats['jit_resumable_calls']
    assert totals['native_returns']==stats['jit_resumable_returns']
    return dict(totals=totals,changed_backend_functions=moved,exact_logical_per_pc_counts=True,exact_backend_accounting=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    parser.add_argument('--build',type=Path,required=True);parser.add_argument('--qualification',type=Path,required=True)
    parser.add_argument('--controls',type=Path,required=True);args=parser.parse_args()
    assert re.fullmatch(r'tree-bridge-profile-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        build_path=args.build.resolve(strict=True);qualification_path=args.qualification.resolve(strict=True)
        controls_path=args.controls.resolve(strict=True)
        build=json.loads(build_path.read_text());qualification=json.loads(qualification_path.read_text())
        controls=json.loads(controls_path.read_text())
        assert build['status']==qualification['status']==controls['status']=='passed'
        assert build['tests']=={'test-debug':556,'test-release':556}
        assert build['tool_key']==qualification['tool_key'] and qualification['commands']==119
        assert qualification['source_restored'] and qualification['automatic_cache_qualified'] and qualification['jit_tree_bridge']
        assert controls['profile_controls']==6 and controls['launcher_tests']==386 and controls['launcher_skipped']==16
        tools,key=installed_tools(build['tool_key']);vm=tools/'rust-interp-vm'
        assert all(sha(tools/name)==digest for name,digest in build['binaries'].items())
        baseline_path=ROOT/'results/guarded-local-facts-profile-01/summary.json';baseline=json.loads(baseline_path.read_text())
        assert baseline['status']=='passed' and baseline['vm_sha256']=='f0e5f2ea9bbe411c7309ae7283f8040b0549759344c5f81798c1e2eae9e99d9b'
        old=ROOT/baseline['raw'];assert sha(old/'records.json')==baseline['records_sha256']
        reference_path=ROOT/'results/current-runtime-boundaries-02/summary.json';reference=json.loads(reference_path.read_text())
        raw=ROOT/reference['raw'];assert reference['status']=='passed' and reference['exact_logical_counts_memory_and_entropy']
        assert sha(raw/'records.json')==reference['records_sha256'];reference_rows=json.loads((raw/'records.json').read_text())
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json';entropy=json.loads(entropy_path.read_text())
        assert entropy['status']=='passed';library=ROOT/entropy['library'];assert sha(library)==entropy['library_sha256']
        paths=[Path(__file__),Path(__file__).with_name('QUALIFICATION.md'),build_path,qualification_path,controls_path,
            baseline_path,old/'records.json',reference_path,raw/'records.json',entropy_path,library]
        paths += [tools/name for name in build['binaries']]+list((ROOT/'scripts').glob('*.py'))
        cases=[]
        for item in reference['profiles']:
            index=item['index'];previous,=[c for c in baseline['comparisons'] if c['index']==index]
            original,=[row for row in reference_rows if row['index']==index and row['mode']=='profile']
            source=old/f'{index}-profile.json';assert sha(source)==previous['profile_sha256']
            tape=raw/f'{index}.tape';assert sha(tape)==original['tape_sha256']
            assert previous['name']==item['name']
            for name in ['artifact','catalog']:
                path=ROOT/item[name];assert sha(path)==item[name+'_sha256'];paths.append(path)
            paths += [source,tape];cases.append((item,previous))
        assert len(cases)==3
        frozen={str(path.relative_to(ROOT)):sha(path) for path in paths}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,expected_commands=3,tool_key=key,
            initial_gib=12,minimum_child_gib=8,performance_measurement=False,operation_map_reconstruction=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE='replay',RUST_INTERP_VM_STATS='1')
        records=[];comparisons=[]
        for item,previous in cases:
            require_space(ROOT,8);assert all(sha(ROOT/path)==h for path,h in frozen.items())
            index=item['index'];output=work/f'{index}-profile.json';dump=work/f'{index}-code'
            command=[str(vm),'--engine','jit','--jit-resumable-calls','--jit-tree-bridge','--jit-persistent-registers',
                '--jit-code-dump',str(dump),'--profile',str(output),'--profile-test',item['name'],
                '--suite-catalog',str(ROOT/item['catalog']),'--instruction-limit',str(item['limits']['instructions']),
                '--allocation-limit',str(item['limits']['allocations']),str(ROOT/item['artifact'])]
            started=time.time()
            child,out,err=capture(command,cwd=ROOT,env=dict(env,RUST_INTERP_ENTROPY_TAPE=str(raw/f'{index}.tape')),
                receipt_path=work/'active.json',receipt=dict(index=index))
            records.append(dict(index=index,command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err,
                started_at=started,finished_at=time.time()));write(work/'records.json',records)
            assert child.returncode==0 and out=='0\n',err
            selection,=[json.loads(line.split(': ',1)[1]) for line in err.splitlines() if line.startswith('rust-interp-profile-selection: ')]
            for field in ['name','artifact_sha256','catalog_sha256']:assert selection[field]==item[field]
            stats={key:int(value) for key,value in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
            for field in ['instructions','peak_guest_memory','entropy_calls','entropy_bytes']:
                assert stats[field]==previous['statistics'][field],(index,field)
            assert stats['jit_bytes']<=16*1024**2 and stats['jit_tree_bytes']<=4*1024**2
            if index!=2:assert stats['jit_tree_entries']>0 and stats['jit_tree_instructions']>0
            assert output.stat().st_size<=256*1024**2
            profile=json.loads(output.read_text());prior=json.loads((old/f'{index}-profile.json').read_text())
            accounting=reconcile(profile,prior,stats);write(work/f'{index}-accounting.json',accounting)
            del profile,prior
            comparisons.append(dict(index=index,name=item['name'],statistics=stats,previous_statistics=previous['statistics'],
                profile_sha256=sha(output),code_sha256=sha(dump/'code.bin'),code_map_sha256=sha(dump/'map.json'),
                accounting_sha256=sha(work/f'{index}-accounting.json'),exact_logical_per_pc_counts=True,exact_backend_accounting=True,
                totals=accounting['totals'],changed_backend_functions=len(accounting['changed_backend_functions'])))
            write(work/'comparisons.json',comparisons)
            print(index,item['name'],'PASS',stats['jit_tree_entries'],'bridges;',stats['jit_bytes'],'native bytes',flush=True)
        assert all(sha(ROOT/path)==h for path,h in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=3,tool_key=key,vm_sha256=sha(vm),comparisons=comparisons,
            exact_logical_counts_memory_and_entropy=True,exact_logical_per_pc_counts=True,exact_backend_accounting=True,
            operation_map_reconstruction=False,raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),
            records_sha256=sha(work/'records.json'),performance_measurement=False))

if __name__=='__main__':main()
