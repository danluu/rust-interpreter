"""Qualify original selected tests and exact profiles before any edited-source timing."""
import argparse
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
from maps import validate as validate_legacy
from native_observation import validate,logical_counts,exact_logical_counts

def read(p):return json.loads(p.read_text())
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True);parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--qualification',type=Path,required=True);args=parser.parse_args()
    assert re.fullmatch(r'scalar-local-registers-profile-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        build_path=args.build.resolve(strict=True);qualification_path=args.qualification.resolve(strict=True)
        build=read(build_path);qualified=read(qualification_path)
        assert build['status']==qualified['status']=='passed'
        assert build['tests']=={'test-debug':593,'test-release':593} and qualified['commands']==121
        assert qualified['scalar_enabled_strict_cargo'] and qualified['scalar_partial_artifact_rejections']==1 and qualified['actual_demand_artifact']
        assert qualified['tool_key']==build['tool_key'] and qualified['source_restored'] and qualified['automatic_cache_qualified']
        vm_dir,key=installed_tools(build['tool_key']);matched=build['matched_control'];control_dir,_=installed_tools(matched['tool_key'])
        assert all(sha(vm_dir/n)==h for n,h in build['binaries'].items())
        assert all(sha(control_dir/n)==h for n,h in matched['binaries'].items())
        for name in ['rust-interp-mir-export','rust-interp-rustc-wrapper']:assert build['binaries'][name]==matched['binaries'][name]
        baseline_path=ROOT/'results/guarded-local-facts-profile-01/summary.json';baseline=read(baseline_path);old=ROOT/baseline['raw']
        assert baseline['status']=='passed' and baseline['exact_per_pc_counts'] and baseline['exact_operation_map_reconstruction']
        assert sha(old/'records.json')==baseline['records_sha256']
        reference_path=ROOT/'results/current-runtime-boundaries-02/summary.json';reference=read(reference_path);raw=ROOT/reference['raw']
        assert reference['status']=='passed' and reference['exact_logical_counts_memory_and_entropy']
        assert sha(raw/'records.json')==reference['records_sha256'];original_records=read(raw/'records.json')
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json';entropy=read(entropy_path)
        assert entropy['status']=='passed';library=ROOT/entropy['library'];assert sha(library)==entropy['library_sha256']
        paths=[build_path,qualification_path,baseline_path,old/'records.json',reference_path,raw/'records.json',entropy_path,library]
        paths += [Path(__file__),Path(__file__).with_name('native_observation.py'),Path(__file__).with_name('test_native_observation.py'),
                  Path(__file__).with_name('NATIVE-CALL.md'),ROOT/'tests/test_isolated_launcher.py',ROOT/'benchmarks/experiments/operation-map/maps.py']
        paths += [ROOT/'scripts'/n for n in ['workflow_io.py','interpreter.py','compare_saved_runtime.py']]
        paths += [vm_dir/n for n in build['binaries']]+[control_dir/n for n in matched['binaries']]
        cases=[]
        for item in reference['profiles']:
            index=item['index'];prior,=[c for c in baseline['comparisons'] if c['index']==index]
            assert item['name']==prior['name']
            previous=old/f'{index}-profile.json';assert sha(previous)==prior['profile_sha256'];paths.append(previous)
            record,=[r for r in original_records if r['index']==index and r['mode']=='profile']
            tape=raw/f'{index}.tape';assert sha(tape)==record['tape_sha256'];paths.append(tape)
            for name in ['artifact','catalog']:
                p=ROOT/item[name];assert sha(p)==item[name+'_sha256'];paths.append(p)
            cases.append((item,prior))
        assert len(cases)==3
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,expected_guest_commands=6,python_controls=3,launcher_controls=7,tool_key=key,matched_control_key=matched['tool_key'],minimum_child_gib=8,
            performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        child,out,err=capture([sys.executable,'-m','unittest','discover','-s','tests','-p','test_isolated_launcher.py','-v'],cwd=ROOT,
            env=dict(env,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage='corrected launcher controls'))
        (work/'launcher.stdout').write_text(out);(work/'launcher.stderr').write_text(err)
        write(work/'launcher.json',dict(pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/'launcher.stdout'),stderr_sha256=sha(work/'launcher.stderr')))
        assert child.returncode==0 and 'Ran 7 tests' in err and err.rstrip().endswith('OK'),out+err
        child,out,err=capture([sys.executable,'-m','unittest','test_native_observation','-v'],cwd=Path(__file__).parent,
            env=dict(env,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage='observation controls'))
        (work/'controls.stdout').write_text(out);(work/'controls.stderr').write_text(err)
        write(work/'controls.json',dict(pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/'controls.stdout'),stderr_sha256=sha(work/'controls.stderr')))
        assert child.returncode==0 and 'Ran 3 tests' in err and err.rstrip().endswith('OK'),out+err
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE='replay',RUST_INTERP_VM_STATS='1')
        rows=[];comparisons=[]
        for item,prior in cases:
            index=item['index'];previous=read(old/f'{index}-profile.json')
            for mode in ['control','candidate']:
                require_space(ROOT,8);profile_path=work/f'{mode}-{index}-profile.json';dump_path=work/f'{mode}-{index}-code'
                active_vm=(control_dir if mode=='control' else vm_dir)/'rust-interp-vm'
                command=[active_vm,'--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                    *(['--jit-scalar-calls'] if mode=='candidate' else []),
                    '--jit-code-dump',dump_path,'--jit-operation-map','--profile',profile_path,'--profile-test',item['name'],
                    '--suite-catalog',ROOT/item['catalog'],'--instruction-limit',str(item['limits']['instructions']),
                    '--allocation-limit',str(item['limits']['allocations']),ROOT/item['artifact']]
                command=list(map(str,command))
                child,out,err=capture(command,cwd=ROOT,env=dict(env,RUST_INTERP_ENTROPY_TAPE=str(raw/f'{index}.tape')),
                    receipt_path=work/'active.json',receipt=dict(index=index,mode=mode))
                rows.append(dict(index=index,mode=mode,command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err))
                write(work/'records.json',rows);assert child.returncode==0 and out=='0\n',err
                selection,=[json.loads(line.split(': ',1)[1]) for line in err.splitlines() if line.startswith('rust-interp-profile-selection: ')]
                for k in ['name','artifact_sha256','catalog_sha256']:assert selection[k]==item[k]
                stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
                for name in ['instructions','peak_guest_memory','entropy_calls','entropy_bytes']:
                    assert stats[name]==prior['statistics'][name],(index,mode,name,stats[name],prior['statistics'][name])
                profile=read(profile_path);totals=exact_logical_counts(profile,previous)
                assert totals['total']==stats['instructions'] and totals['native']==stats['jit_instructions']
                code=(dump_path/'code.bin').read_bytes();mapping=read(dump_path/'operations.json');dump=read(dump_path/'map.json')
                observed=(validate if mode=='candidate' else validate_legacy)(mapping,dump,code,profile,child.pid)
                if mode=='control':
                    assert sha(dump_path/'code.bin')==prior['code_sha256'] and totals['scalar']==0
                elif index in [0,1]:assert totals['scalar']>0
                scalar_calls=sum(sum(h for op,h in zip(f['operations'],f.get('jit_scalar_hits',[])) if op=='Return') for f in profile['functions'])
                scalar_functions=sum(any(f.get('jit_scalar_hits',[])) for f in profile['functions'])
                bodies=[f for f in mapping['functions'] if len(f['spans'])==1 and f['spans'][0]['kind']=='scalar_leaf']
                if mode=='candidate':assert bool(bodies) or totals['scalar']==0
                comparison=dict(index=index,mode=mode,name=item['name'],statistics=stats,logical_counts=totals,scalar_calls=scalar_calls,
                    scalar_functions_executed=scalar_functions,scalar_bodies=len(bodies),scalar_code_bytes=sum(f['end']-f['offset'] for f in bodies),
                    current_native_bytes=len(code),profile_path=str(profile_path.relative_to(ROOT)),profile_sha256=sha(profile_path),
                    code_path=str((dump_path/'code.bin').relative_to(ROOT)),code_sha256=sha(dump_path/'code.bin'),
                    operations_path=str((dump_path/'operations.json').relative_to(ROOT)),operations_sha256=sha(dump_path/'operations.json'),
                    map_sha256=sha(dump_path/'map.json'),mapped_spans=observed['spans'])
                comparisons.append(comparison)
                print(index,mode,'original assertions/counts/peak/entropy/map PASS;',scalar_calls,'scalar Calls;',totals['scalar'],'scalar instructions',flush=True)
                assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',tool_key=key,matched_control_key=matched['tool_key'],commands=6,python_controls=3,launcher_controls=7,
            comparisons=comparisons,control_code_matches_adopted=True,exact_logical_counts_memory_and_entropy=True,exact_per_pc_counts=True,
            exact_operation_map_reconstruction=True,raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            controls_sha256=sha(work/'controls.json'),launcher_sha256=sha(work/'launcher.json'),performance_measurement=False))
if __name__=='__main__':main()
