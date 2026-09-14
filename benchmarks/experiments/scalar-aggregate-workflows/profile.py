"""Run three candidate profiles against exact retained adopted-VM evidence."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
from native_observation import validate,exact_logical_counts
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True);parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--qualification',type=Path,required=True);args=parser.parse_args()
    assert re.fullmatch(r'scalar-aggregate-profile-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        build_path=args.build.resolve(strict=True);qualification_path=args.qualification.resolve(strict=True)
        build=read(build_path);qualified=read(qualification_path)
        assert build['status']==qualified['status']=='passed' and build['composition']['kind']=='scalar-aggregate-calls'
        assert build['tests']=={'test-debug':637,'test-release':637} and qualified['commands']==121
        assert qualified['scalar_enabled_strict_cargo'] and qualified['scalar_partial_artifact_rejections']==1 and qualified['actual_demand_artifact']
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
        # Reuse exact unchanged observation/launcher controls; these are not new tests.
        for n in ['native_observation.py','test_native_observation.py']:
            expected=old_plan['frozen']['benchmarks/experiments/scratch-memory-values/'+n]
            assert sha(Path(__file__).with_name(n))==expected
        assert sha(ROOT/'tests/test_isolated_launcher.py')==old_plan['frozen']['tests/test_isolated_launcher.py']
        assert sha(old/'controls.json')==baseline['controls_sha256'] and sha(old/'launcher.json')==baseline['launcher_sha256']
        assert read(old/'controls.json')['returncode']==read(old/'launcher.json')['returncode']==0
        assert baseline['python_controls']==3 and baseline['launcher_controls']==7
        reference_path=ROOT/'results/current-runtime-boundaries-02/summary.json';reference=read(reference_path)
        assert reference['status']=='passed' and reference['exact_logical_counts_memory_and_entropy']
        raw=ROOT/reference['raw'];assert sha(raw/'records.json')==reference['records_sha256'];original_records=read(raw/'records.json')
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json';entropy=read(entropy_path)
        assert entropy['status']=='passed';library=ROOT/entropy['library'];assert sha(library)==entropy['library_sha256']
        paths += [reference_path,raw/'records.json',entropy_path,library,old/'controls.json',old/'launcher.json']
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [ROOT/'tests/test_isolated_launcher.py']+[ROOT/'scripts'/n for n in ['workflow_io.py','interpreter.py','compare_saved_runtime.py']]
        paths += [tools/n for n in build['binaries']]+[control/n for n in matched['binaries']]
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
            frozen=frozen,expected_guest_commands=3,reused_control_profiles=3,python_controls_reused=3,launcher_controls_reused=7,
            tool_key=key,matched_control_key=BASELINE,minimum_child_gib=8,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE='replay',RUST_INTERP_VM_STATS='1')
        records=[];comparisons=[]
        for item,prior in cases:
            require_space(ROOT,8);index=item['index'];previous=read(ROOT/prior['profile_path'])
            profile_path=work/f'candidate-{index}-profile.json';dump_path=work/f'candidate-{index}-code'
            command=list(map(str,[tools/'rust-interp-vm','--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--jit-scalar-calls',
                '--jit-code-dump',dump_path,'--jit-operation-map','--profile',profile_path,'--profile-test',item['name'],
                '--suite-catalog',ROOT/item['catalog'],'--instruction-limit',item['limits']['instructions'],
                '--allocation-limit',item['limits']['allocations'],ROOT/item['artifact']]))
            child,out,err=capture(command,cwd=ROOT,env=dict(env,RUST_INTERP_ENTROPY_TAPE=str(raw/f'{index}.tape')),
                receipt_path=work/'active.json',receipt=dict(index=index,mode='candidate'))
            records.append(dict(index=index,mode='candidate',command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err))
            write(work/'records.json',records);assert child.returncode==0 and out=='0\n',err
            selection,=[json.loads(line.split(': ',1)[1]) for line in err.splitlines() if line.startswith('rust-interp-profile-selection: ')]
            for n in ['name','artifact_sha256','catalog_sha256']:assert selection[n]==item[n]
            stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
            for n in ['instructions','peak_guest_memory','entropy_calls','entropy_bytes']:assert stats[n]==prior['statistics'][n],(index,n)
            profile=read(profile_path);totals=exact_logical_counts(profile,previous)
            assert totals['total']==stats['instructions'] and totals['native']==stats['jit_instructions']
            code=(dump_path/'code.bin').read_bytes();mapping=read(dump_path/'operations.json');dump=read(dump_path/'map.json')
            observed=validate(mapping,dump,code,profile,child.pid)
            scalar_calls=sum(sum(h for op,h in zip(f['operations'],f.get('jit_scalar_hits',[])) if op=='Return') for f in profile['functions'])
            scalar_functions=sum(any(f.get('jit_scalar_hits',[])) for f in profile['functions'])
            bodies=[f for f in mapping['functions'] if len(f['spans'])==1 and f['spans'][0]['kind']=='scalar_leaf']
            comparisons.append(dict(prior,mode='control',reused=True,tool_key=BASELINE))
            comparisons.append(dict(index=index,mode='candidate',reused=False,name=item['name'],statistics=stats,logical_counts=totals,
                scalar_calls=scalar_calls,scalar_functions_executed=scalar_functions,scalar_bodies=len(bodies),
                scalar_code_bytes=sum(f['end']-f['offset'] for f in bodies),current_native_bytes=len(code),
                profile_path=str(profile_path.relative_to(ROOT)),profile_sha256=sha(profile_path),
                code_path=str((dump_path/'code.bin').relative_to(ROOT)),code_sha256=sha(dump_path/'code.bin'),
                operations_path=str((dump_path/'operations.json').relative_to(ROOT)),operations_sha256=sha(dump_path/'operations.json'),
                map_sha256=sha(dump_path/'map.json'),mapped_spans=observed['spans']))
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(index,'original assertions/counts/peak/entropy/map PASS;',scalar_calls,'scalar Calls',flush=True)
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',tool_key=key,matched_control_key=BASELINE,commands=3,reused_control_profiles=3,
            python_controls_reused=3,launcher_controls_reused=7,comparisons=comparisons,control_vm_matches_adopted=True,
            exact_logical_counts_memory_and_entropy=True,exact_per_pc_counts=True,exact_operation_map_reconstruction=True,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),performance_measurement=False))
if __name__=='__main__':main()
