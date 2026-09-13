"""Observe two original token tests; demand exact adopted code, counts and entropy."""
import argparse
from collections import Counter, defaultdict
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/operation-map'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from maps import validate as validate_operation_map
HELPER=ROOT/'benchmarks/experiments/guarded-ranges/profile.py'
spec=importlib.util.spec_from_file_location('exact_profiles',HELPER)
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)


def aggregate(report,profile):
    assert report['status']=='passed' and not report['overflow'] and len(report['rows'])<=report['max_keys']==4096
    grouped=defaultdict(list);keys=set()
    for row in report['rows']:
        caller,pc,target=row['caller'],row['pc'],row['target']
        key=tuple(row[k] for k in ['caller','pc','target','entry_ready','continuation_ready','local_arguments'])
        assert key not in keys;keys.add(key)
        assert type(row['count']) is int and row['count']>0
        assert all(type(row[k]) is bool for k in ['entry_ready','continuation_ready','local_arguments'])
        assert 0<=caller<len(profile['functions']) and 0<=target<len(profile['functions'])
        function=profile['functions'][caller]
        assert 0<=pc<len(function['operations']) and function['operations'][pc].startswith('CallIndirect ')
        assert function['name']==row['caller_name'] and profile['functions'][target]['name']==row['target_name']
        grouped[caller,pc].append(row)
    expected={(fid,pc):count for fid,f in enumerate(profile['functions'])
        for pc,count in enumerate(f['interpreted']) if count and f['operations'][pc].startswith('CallIndirect ')}
    assert set(grouped)==set(expected)
    sites=[]
    for (caller,pc),rows in grouped.items():
        targets=Counter()
        for r in rows:targets[r['target']]+=r['count']
        total=sum(targets.values());assert total==expected[caller,pc]
        site=dict(caller=caller,pc=pc,name=profile['functions'][caller]['name'],calls=total,
            target_count=len(targets),targets=[dict(target=t,name=profile['functions'][t]['name'],calls=n)
                for t,n in targets.most_common()],
            entry_ready=sum(r['count'] for r in rows if r['entry_ready']),
            continuation_ready=sum(r['count'] for r in rows if r['continuation_ready']),
            both_ready=sum(r['count'] for r in rows if r['entry_ready'] and r['continuation_ready']),
            local_arguments=sum(r['count'] for r in rows if r['local_arguments']))
        sites.append(site)
    sites.sort(key=lambda s:(-s['calls'],s['caller'],s['pc']))
    return dict(calls=sum(expected.values()),sites=len(sites),rows=len(report['rows']),
        coverage={str(n):sum(s['calls'] for s in sites if s['target_count']<=n) for n in [1,2,4]},
        **{k:sum(s[k] for s in sites) for k in ['entry_ready','continuation_ready','both_ready','local_arguments']},
        sites_by_calls=sites,ordered_target_history_collected=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);p.add_argument('--build',type=Path,required=True)
    args=p.parse_args();assert re.fullmatch(r'indirect-target-census-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        build_path=args.build.resolve(strict=True);build=json.loads(build_path.read_text())
        assert build['status']=='passed' and build['tests']=={'debug':417,'release':417} and build['observer_only']
        observer=ROOT/build['observer'];assert sha(observer)==build['observer_sha256']
        build_raw=ROOT/build['raw'];build_plan=json.loads((build_raw/'plan.json').read_text())
        assert sha(build_raw/'plan.json')==build['plan_sha256'] and sha(build_raw/'records.json')==build['records_sha256']
        assert build_plan['rust_inputs']==build['rust_inputs']
        assert all(sha(ROOT/k)==v for k,v in build_plan['frozen'].items())
        baseline_path=ROOT/'results/guarded-local-facts-profile-01/summary.json'
        baseline=json.loads(baseline_path.read_text());old=ROOT/baseline['raw']
        assert baseline['status']=='passed' and baseline['exact_per_pc_counts'] and baseline['exact_operation_map_reconstruction']
        assert sha(old/'records.json')==baseline['records_sha256']
        reference_path=ROOT/'results/current-runtime-boundaries-02/summary.json'
        reference=json.loads(reference_path.read_text());raw=ROOT/reference['raw']
        assert reference['status']=='passed' and reference['exact_logical_counts_memory_and_entropy']
        assert sha(raw/'records.json')==reference['records_sha256'];reference_rows=json.loads((raw/'records.json').read_text())
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json'
        entropy=json.loads(entropy_path.read_text());assert entropy['status']=='passed'
        library=ROOT/entropy['library'];assert sha(library)==entropy['library_sha256']
        paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),build_path,observer,build_raw/'plan.json',build_raw/'records.json',
            baseline_path,old/'records.json',reference_path,raw/'records.json',entropy_path,library,HELPER,
            ROOT/'benchmarks/experiments/operation-map/maps.py']
        paths += [ROOT/'scripts'/n for n in ['compare_saved_runtime.py','workflow_io.py','profile_vm_transitions.py']]
        cases=[]
        for item in reference['profiles']:
            index=item['index']
            if index not in [0,1]:continue
            previous,=[c for c in baseline['comparisons'] if c['index']==index]
            source=old/f'{index}-profile.json';assert sha(source)==previous['profile_sha256']
            original,=[r for r in reference_rows if r['index']==index and r['mode']=='profile']
            tape=raw/f'{index}.tape';assert sha(tape)==original['tape_sha256']
            assert previous['name']==item['name']
            for name in ['artifact','catalog']:
                path=ROOT/item[name];assert sha(path)==item[name+'_sha256'];paths.append(path)
            paths += [source,tape];cases.append((item,previous))
        assert [item['index'] for item,_ in cases]==[0,1]
        frozen=dict(build_plan['frozen']);frozen.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,expected_guest_commands=2,
            source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            observer_sha256=sha(observer),minimum_child_gib=8,initial_gib=12,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','INDIRECT_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE='replay')
        rows=[];comparisons=[]
        for item,previous in cases:
            require_space(ROOT,8);index=item['index'];profile_path=work/f'{index}-profile.json';dump_path=work/f'{index}-code';report_path=work/f'{index}-trace.json'
            assert sha(observer)==build['observer_sha256']
            command=[str(observer),'indirect_trace::observe_saved_indirect_targets','--exact','--ignored','--nocapture','--test-threads','1']
            child,out,err=capture(command,cwd=ROOT,env=dict(env,RUST_INTERP_ENTROPY_TAPE=str(raw/f'{index}.tape'),
                INDIRECT_ARTIFACT=str(ROOT/item['artifact']),INDIRECT_CATALOG=str(ROOT/item['catalog']),INDIRECT_TEST=item['name'],
                INDIRECT_INSTRUCTIONS=str(item['limits']['instructions']),INDIRECT_ALLOCATIONS=str(item['limits']['allocations']),
                INDIRECT_PROFILE=str(profile_path),INDIRECT_CODE=str(dump_path),INDIRECT_REPORT=str(report_path)),
                receipt_path=work/'active.json',receipt=dict(index=index))
            rows.append(dict(index=index,command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err));write(work/'records.json',rows)
            assert child.returncode==0 and 'test result: ok. 1 passed; 0 failed;' in out,(out+err)[-4000:]
            report=json.loads(report_path.read_text());assert report['pid']==child.pid and report['entry']==item['function'] and report['name']==item['name']
            assert report['guest_commands']==1 and not report['performance_measurement']
            for name in ['artifact','catalog']:assert report[name+'_sha256']==item[name+'_sha256']
            stats=report['statistics']
            for name in ['entropy_calls','entropy_bytes']:
                values=re.findall(r'\b'+name+r'=(\d+)\b',err);assert len(values)==1,(name,err);stats[name]=int(values[0])
            for name,value in stats.items():assert value==previous['statistics'][name],(index,name,value,previous['statistics'][name])
            assert profile_path.stat().st_size<=256*1024**2
            profile=json.loads(profile_path.read_text());prior=json.loads((old/f'{index}-profile.json').read_text())
            assert helpers.exact_profile_counts(profile,prior);del prior
            code=(dump_path/'code.bin').read_bytes();assert sha(dump_path/'code.bin')==previous['code_sha256']
            mapping=json.loads((dump_path/'operations.json').read_text());dump=json.loads((dump_path/'map.json').read_text())
            validate_operation_map(mapping,dump,code,profile,child.pid);assert mapping['reconstructed_bytes_match']
            attribution=aggregate(report,profile);assert attribution['calls']==[1025947,843776][index]
            comparison=dict(index=index,name=item['name'],statistics=stats,attribution=attribution,
                profile_sha256=sha(profile_path),trace_sha256=sha(report_path),operation_map_sha256=sha(dump_path/'operations.json'),
                code_map_sha256=sha(dump_path/'map.json'),code_sha256=sha(dump_path/'code.bin'),
                exact_adopted_code=True,exact_per_pc_counts=True,exact_counts_memory_entropy=True)
            comparisons.append(comparison);write(work/'comparisons.json',comparisons)
            print(index,'PASS',json.dumps({k:v for k,v in attribution.items() if k!='sites_by_calls'}),flush=True)
            del code,mapping,dump,profile,report
        assert all(sha(ROOT/k)==v for k,v in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',guest_commands=2,observer_sha256=sha(observer),comparisons=comparisons,
            exact_adopted_code=True,exact_per_pc_counts=True,exact_counts_memory_entropy=True,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),performance_measurement=False))


if __name__=='__main__':main()
