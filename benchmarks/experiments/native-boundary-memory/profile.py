"""Replay original real tests with bound entropy and verify complete per-PC profiles."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/operation-map'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
from maps import validate as validate_operation_map

HELPER=ROOT/'benchmarks/experiments/guarded-ranges/profile.py'
spec=importlib.util.spec_from_file_location('guarded_profile_helpers',HELPER)
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--qualification',type=Path,required=True)
    args=parser.parse_args()
    assert re.fullmatch(r'native-boundary-memory-profile-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        build_path=args.build.resolve(strict=True); qualification_path=args.qualification.resolve(strict=True)
        build=json.loads(build_path.read_text());qualification=json.loads(qualification_path.read_text())
        assert build['status']==qualification['status']=='passed'
        assert build['tests']=={'test-debug':519,'test-release':519}
        assert build['tool_key']==qualification['tool_key'] and qualification['commands']==119
        assert qualification['source_restored'] and qualification['automatic_cache_qualified']
        tools,key=installed_tools(build['tool_key']);vm=tools/'rust-interp-vm'
        assert all(sha(tools/name)==h for name,h in build['binaries'].items())
        baseline_path=ROOT/'results/guarded-local-facts-profile-01/summary.json'
        baseline=json.loads(baseline_path.read_text());old=ROOT/baseline['raw']
        assert baseline['status']=='passed' and baseline['exact_per_pc_counts'] and baseline['exact_operation_map_reconstruction']
        assert sha(old/'records.json')==baseline['records_sha256']
        reference_path=ROOT/'results/current-runtime-boundaries-02/summary.json'
        reference=json.loads(reference_path.read_text());raw=ROOT/reference['raw']
        assert reference['status']=='passed' and reference['exact_logical_counts_memory_and_entropy']
        assert sha(raw/'records.json')==reference['records_sha256']
        reference_rows=json.loads((raw/'records.json').read_text())
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json'
        entropy=json.loads(entropy_path.read_text());assert entropy['status']=='passed'
        library=ROOT/entropy['library'];assert sha(library)==entropy['library_sha256']
        paths=[Path(__file__),Path(__file__).with_name('QUALIFICATION.md'),build_path,qualification_path,
               baseline_path,old/'records.json',reference_path,raw/'records.json',entropy_path,library,HELPER,
               ROOT/'benchmarks/experiments/operation-map/maps.py']
        paths += [tools/name for name in build['binaries']]
        cases=[]
        for item in reference['profiles']:
            index=item['index'];previous,=[c for c in baseline['comparisons'] if c['index']==index]
            source=old/f'{index}-profile.json';assert sha(source)==previous['profile_sha256']
            original,=[r for r in reference_rows if r['index']==index and r['mode']=='profile']
            tape=raw/f'{index}.tape';assert sha(tape)==original['tape_sha256']
            assert previous['name']==item['name']
            for name in ['artifact','catalog']:
                p=ROOT/item[name];assert sha(p)==item[name+'_sha256'];paths.append(p)
            paths += [source,tape]
            cases.append((item,previous,original))
        assert len(cases)==3
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,expected_commands=3,tool_key=key,
            minimum_child_gib=8,initial_gib=12,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE='replay',RUST_INTERP_VM_STATS='1')
        rows,comparisons=[],[]
        for item,previous,original in cases:
            require_space(ROOT,8);index=item['index'];profile_path=work/f'{index}-profile.json';dump_path=work/f'{index}-code'
            command=[str(vm),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                '--jit-code-dump',str(dump_path),'--jit-operation-map','--profile',str(profile_path),
                '--profile-test',item['name'],'--suite-catalog',str(ROOT/item['catalog']),
                '--instruction-limit',str(item['limits']['instructions']),'--allocation-limit',str(item['limits']['allocations']),
                str(ROOT/item['artifact'])]
            child,out,err=capture(command,cwd=ROOT,env=dict(env,RUST_INTERP_ENTROPY_TAPE=str(raw/f'{index}.tape')),
                                  receipt_path=work/'active.json',receipt=dict(index=index))
            rows.append(dict(index=index,command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err))
            write(work/'records.json',rows)
            assert child.returncode==0 and out=='0\n',err
            selection,=[json.loads(line.split(': ',1)[1]) for line in err.splitlines() if line.startswith('rust-interp-profile-selection: ')]
            assert selection['name']==item['name'] and selection['artifact_sha256']==item['artifact_sha256']
            assert selection['catalog_sha256']==item['catalog_sha256']
            stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
            for name in ['instructions','peak_guest_memory','entropy_calls','entropy_bytes','jit_entries','jit_instructions']:
                assert stats[name]==previous['statistics'][name],(index,name,stats[name],previous['statistics'][name])
            assert stats['jit_declined_functions']==0
            profile=json.loads(profile_path.read_text()); prior=json.loads((old/f'{index}-profile.json').read_text())
            assert helpers.exact_profile_counts(profile,prior)
            code=(dump_path/'code.bin').read_bytes();mapping=json.loads((dump_path/'operations.json').read_text())
            dump=json.loads((dump_path/'map.json').read_text())
            validate_operation_map(mapping,dump,code,profile,child.pid)
            assert mapping['reconstructed_bytes_match']
            guards=helpers.verify_range_checks(mapping,code,require_active=index!=2)
            comparison=dict(index=index,name=item['name'],statistics=stats,range_checks=guards,
                profile_sha256=sha(profile_path),operation_map_sha256=sha(dump_path/'operations.json'),
                code_map_sha256=sha(dump_path/'map.json'),code_sha256=sha(dump_path/'code.bin'),
                exact_logical_counts_memory_and_entropy=True,exact_per_pc_counts=True,
                exact_operation_map_reconstruction=True,baseline_native_bytes=previous['statistics']['jit_bytes'],current_native_bytes=len(code))
            comparisons.append(comparison);write(work/'comparisons.json',comparisons)
            print(index,item['name'],'PASS',len(code),'native bytes',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=3,tool_key=key,vm_sha256=sha(vm),comparisons=comparisons,
            exact_logical_counts_memory_and_entropy=True,exact_per_pc_counts=True,exact_operation_map_reconstruction=True,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            performance_measurement=False))


if __name__=='__main__':main()
