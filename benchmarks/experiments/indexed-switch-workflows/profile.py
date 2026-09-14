"""Run three candidate profiles against exact retained adopted-VM evidence."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import shutil
from types import SimpleNamespace
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
from native_observation import validate,exact_logical_counts
from relocation import compare as compare_code
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True);parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--qualification',type=Path,required=True);args=parser.parse_args()
    assert re.fullmatch(r'indexed-switches-profile-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        build_path=args.build.resolve(strict=True);qualification_path=args.qualification.resolve(strict=True)
        build=read(build_path);qualified=read(qualification_path)
        assert build['status']==qualified['status']=='passed' and build['composition']['kind']=='indexed-switches'
        assert build['tests']['test-debug']==build['tests']['test-release']>=612 and qualified['commands']==122
        assert qualified['scalar_enabled_strict_cargo'] and qualified['scalar_partial_artifact_rejections']==1 and qualified['actual_demand_artifact']
        assert qualified['indexed_switches_enabled_strict_cargo'] and qualified['indexed_partial_artifact_rejections']==1
        assert qualified['tool_key']==build['tool_key'] and qualified['source_restored'] and qualified['automatic_cache_qualified']
        tools,key=installed_tools(build['tool_key']);matched=build['matched_control'];control,_=installed_tools(BASELINE)
        assert matched['tool_key']==BASELINE
        assert all(sha(tools/n)==h for n,h in build['binaries'].items()) and all(sha(control/n)==h for n,h in matched['binaries'].items())
        for n in ['rust-interp-mir-export','rust-interp-rustc-wrapper']:assert build['binaries'][n]==matched['binaries'][n]
        old_summary_path=ROOT/'results/scratch-memory-values-profile-01/summary.json';baseline=read(old_summary_path)
        old=ROOT/baseline['raw'];old_closure_path=old_summary_path.with_name('closure.json');closure=read(old_closure_path)
        assert closure['status']=='closed' and closure['all_hashes_verified'] and sha(old_summary_path)==closure['summary_sha256']
        assert baseline['status']=='passed' and baseline['tool_key']==BASELINE and baseline['exact_per_pc_counts'] and baseline['exact_operation_map_reconstruction']
        binding=ROOT/closure['bindings'];assert sha(binding)==closure['bindings_sha256'];bindings=read(binding)
        paths=[build_path,qualification_path,old_summary_path,old_closure_path,binding,old/'plan.json',old/'records.json']
        assert sha(old/'plan.json')==baseline['plan_sha256'] and sha(old/'records.json')==baseline['records_sha256']
        old_plan=read(old/'plan.json')
        for name,digest in matched['binaries'].items():
            assert old_plan['frozen'][str((control/name).relative_to(ROOT))]==digest
        old_records=read(old/'records.json')
        assert all('--jit-scalar-calls' in r['command'] for r in old_records if r['mode']=='candidate')
        for p,h in bindings['artifacts'].items():assert sha(ROOT/p)==h;paths.append(ROOT/p)
        # The schema-2 observer is qualified below; old schema-2 controls remain
        # bound historical evidence and are not relabeled as new controls.
        assert sha(old/'controls.json')==baseline['controls_sha256'] and sha(old/'launcher.json')==baseline['launcher_sha256']
        assert read(old/'controls.json')['returncode']==read(old/'launcher.json')['returncode']==0
        reference_path=ROOT/'results/current-runtime-boundaries-02/summary.json';reference=read(reference_path)
        assert reference['status']=='passed' and reference['exact_logical_counts_memory_and_entropy']
        raw=ROOT/reference['raw'];assert sha(raw/'records.json')==reference['records_sha256'];original_records=read(raw/'records.json')
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json';entropy=read(entropy_path)
        assert entropy['status']=='passed';library=ROOT/entropy['library'];assert sha(library)==entropy['library_sha256']
        paths += [reference_path,raw/'records.json',entropy_path,library,old/'controls.json',old/'launcher.json']
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [ROOT/'tests/test_isolated_launcher.py']+[ROOT/'scripts'/n for n in ['workflow_io.py','interpreter.py','compare_saved_runtime.py']]
        paths += [tools/n for n in build['binaries']]+[control/n for n in matched['binaries']]
        failed=ROOT/'results/indexed-switches-profile-01'
        failed_closed=read(failed/'closure.json');failed_summary=read(failed/'summary.json')
        assert failed_closed['status']=='closed' and failed_summary['status']=='failed'
        assert sha(failed/'summary.json')==failed_closed['summary_sha256']
        failed_raw=ROOT/failed_summary['raw'];failed_plan=read(failed_raw/'plan.json')
        assert sha(failed_raw/'plan.json')==failed_summary['plan_sha256']
        assert failed_plan['tool_key']==key and failed_plan['matched_control_key']==BASELINE
        assert sha(failed_raw/'records.json')==failed_summary['records_sha256']
        reuse_record,=read(failed_raw/'records.json');assert reuse_record['index']==0 and reuse_record['returncode']==0
        assert reuse_record['command'][0]==str(tools/'rust-interp-vm') and '--indexed-switches' in reuse_record['command']
        binding=ROOT/failed_closed['bindings'];assert sha(binding)==failed_closed['bindings_sha256']
        for path,digest in read(binding)['artifacts'].items():assert sha(ROOT/path)==digest;paths.append(ROOT/path)
        paths += [failed/'summary.json',failed/'closure.json',failed/'terminal.json',failed_raw/'plan.json',binding]
        paths += [ROOT/'crates/bytecode/src/jit.rs',ROOT/'crates/bytecode/src/jit/scalar_calls.rs']
        cases=[]
        for item in reference['profiles']:
            index=item['index'];prior,=[r for r in baseline['comparisons'] if r['index']==index and r['mode']=='candidate']
            assert item['name']==prior['name']
            record,=[r for r in original_records if r['index']==index and r['mode']=='profile']
            tape=raw/f'{index}.tape';assert sha(tape)==record['tape_sha256'];paths.append(tape)
            assert old_plan['frozen'][str(tape.relative_to(ROOT))]==sha(tape)
            for n in ['artifact','catalog']:
                p=ROOT/item[n];assert sha(p)==item[n+'_sha256']==old_plan['frozen'][str(p.relative_to(ROOT))];paths.append(p)
            for n in ['profile','code','operations']:assert sha(ROOT/prior[n+'_path'])==prior[n+'_sha256']
            cases.append((item,prior))
        assert len(cases)==3
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,expected_guest_commands=2,reused_candidate_commands=1,reused_control_profiles=3,python_controls=7,launcher_controls_from_candidate_build=True,
            tool_key=key,matched_control_key=BASELINE,minimum_child_gib=8,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE='replay',RUST_INTERP_VM_STATS='1')
        check_env=dict(env)
        for name in ['DYLD_INSERT_LIBRARIES','RUST_INTERP_ENTROPY_MODE','RUST_INTERP_VM_STATS']:check_env.pop(name,None)
        check_env['PYTHONDONTWRITEBYTECODE']='1'
        child,out,err=capture([sys.executable,'-m','unittest','test_native_observation','test_relocation','-v'],cwd=Path(__file__).parent,
            env=check_env,receipt_path=work/'active.json',receipt=dict(mode='schema-2-observer-controls'))
        write(work/'controls.json',dict(returncode=child.returncode,pid=child.pid,stdout=out,stderr=err))
        assert child.returncode==0 and 'Ran 7 tests' in err and err.rstrip().endswith('OK'),err
        records=[];comparisons=[]
        for item,prior in cases:
            require_space(ROOT,8);index=item['index'];previous=read(ROOT/prior['profile_path'])
            profile_path=work/f'candidate-{index}-profile.json';dump_path=work/f'candidate-{index}-code'
            command=list(map(str,[tools/'rust-interp-vm','--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--jit-scalar-calls','--indexed-switches',
                '--jit-code-dump',dump_path,'--jit-operation-map','--profile',profile_path,'--profile-test',item['name'],
                '--suite-catalog',ROOT/item['catalog'],'--instruction-limit',item['limits']['instructions'],
                '--allocation-limit',item['limits']['allocations'],ROOT/item['artifact']]))
            if index==0:
                assert str(ROOT/item['artifact'])==reuse_record['command'][-1]
                assert reuse_record['command'][reuse_record['command'].index('--profile-test')+1]==item['name']
                assert failed_plan['frozen'][str((raw/'0.tape').relative_to(ROOT))]==sha(raw/'0.tape')
                shutil.copy2(failed_raw/'candidate-0-profile.json',profile_path)
                shutil.copytree(failed_raw/'candidate-0-code',dump_path)
                child=SimpleNamespace(pid=reuse_record['pid'],returncode=0)
                out,err=reuse_record['stdout'],reuse_record['stderr'];command=reuse_record['command']
            else:
                child,out,err=capture(command,cwd=ROOT,env=dict(env,RUST_INTERP_ENTROPY_TAPE=str(raw/f'{index}.tape')),
                    receipt_path=work/'active.json',receipt=dict(index=index,mode='candidate'))
            records.append(dict(index=index,mode='candidate',reused_from=str(failed_raw.relative_to(ROOT)) if index==0 else None,command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err))
            write(work/'records.json',records);assert child.returncode==0 and out=='0\n',err
            selection,=[json.loads(line.split(': ',1)[1]) for line in err.splitlines() if line.startswith('rust-interp-profile-selection: ')]
            for n in ['name','artifact_sha256','catalog_sha256']:assert selection[n]==item[n]
            stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
            for n in ['instructions','peak_guest_memory','entropy_calls','entropy_bytes']:assert stats[n]==prior['statistics'][n],(index,n)
            assert not any(n.startswith('jit_demand_') for n in stats), 'small program unexpectedly selected demand'
            profile=read(profile_path)
            assert max(len(f['operations']) for f in profile['functions']) <= 65536
            totals=exact_logical_counts(profile,previous)
            for n in ['native','interpreted','scalar','total']:assert totals[n]==prior['logical_counts'][n],(index,n)
            assert stats['jit_bytes']==prior['statistics']['jit_bytes']
            assert totals['total']==stats['instructions'] and totals['native']==stats['jit_instructions']
            code=(dump_path/'code.bin').read_bytes();mapping=read(dump_path/'operations.json');dump=read(dump_path/'map.json')
            observed=validate(mapping,dump,code,profile,child.pid)
            native_equality=compare_code((ROOT/prior['code_path']).read_bytes(),read((ROOT/prior['code_path']).with_name('map.json')),
                read(ROOT/prior['operations_path']),previous,code,dump,mapping,profile)
            scalar_calls=sum(sum(h for op,h in zip(f['operations'],f.get('jit_scalar_hits',[])) if op=='Return') for f in profile['functions'])
            scalar_functions=sum(any(f.get('jit_scalar_hits',[])) for f in profile['functions'])
            bodies=[f for f in mapping['functions'] if len(f['spans'])==1 and f['spans'][0]['kind']=='scalar_leaf']
            comparisons.append(dict(prior,mode='control',reused=True,tool_key=BASELINE))
            comparisons.append(dict(index=index,mode='candidate',reused=index==0,native_equality=native_equality,name=item['name'],statistics=stats,logical_counts=totals,
                scalar_calls=scalar_calls,scalar_functions_executed=scalar_functions,scalar_bodies=len(bodies),
                scalar_code_bytes=sum(f['end']-f['offset'] for f in bodies),current_native_bytes=len(code),
                profile_path=str(profile_path.relative_to(ROOT)),profile_sha256=sha(profile_path),
                code_path=str((dump_path/'code.bin').relative_to(ROOT)),code_sha256=sha(dump_path/'code.bin'),
                operations_path=str((dump_path/'operations.json').relative_to(ROOT)),operations_sha256=sha(dump_path/'operations.json'),
                map_sha256=sha(dump_path/'map.json'),mapped_spans=observed['spans']))
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(index,'original assertions/counts/peak/entropy/map PASS;',scalar_calls,'scalar Calls',flush=True)
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',tool_key=key,matched_control_key=BASELINE,commands=3,new_guest_commands=2,reused_candidate_commands=1,reused_control_profiles=3,
            python_controls=7,launcher_controls_from_candidate_build=True,comparisons=comparisons,control_vm_matches_adopted=True,
            exact_logical_counts_memory_and_entropy=True,exact_per_pc_counts=True,exact_operation_map_reconstruction=True,exact_native_bytes_after_bound_relocation=True,indexed_switches=True,operation_map_schema=2,controls_sha256=sha(work/'controls.json'),
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),performance_measurement=False))
if __name__=='__main__':main()
