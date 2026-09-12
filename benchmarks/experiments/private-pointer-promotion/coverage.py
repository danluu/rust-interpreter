#!/usr/bin/env python3
"""Check real exports and profile pointer-promotion coverage before any timing screen."""
import importlib.util,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from suite_reports import read_report,validate_report,validate_runtime_limits
from workflow_io import capture,require_space,write_json as write
spec=importlib.util.spec_from_file_location('profile_real',Path(__file__).parents[1]/'suite-profiling/real.py')
profile_real=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile_real)

CASES=[('pgrust','pgrust','filtered-workflow-pgrust-01'),('folded','fre','filtered-workflow-folded-01'),('token','fre','filtered-workflow-token-02')]

def main():
    run='private-pointer-promotion-coverage-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        build_path=ROOT/'results/private-pointer-promotion-build-01/summary.json'
        fixture_path=ROOT/'results/private-pointer-promotion-fixture-02/summary.json'
        profile_path=ROOT/'results/suite-profiling-real-01/summary.json'
        build=json.loads(build_path.read_text());fixture=json.loads(fixture_path.read_text());profiles=json.loads(profile_path.read_text())
        assert build['status']==fixture['status']==profiles['status']=='passed'
        tool,key=installed_tools(build['tool_key'])
        assert fixture['tools']['candidate']==key and fixture['vm_bytes_identical']
        baseline_build=ROOT/'results/suite-profiling-build-02/summary.json'
        assert build['binaries']['rust-interp-vm']==json.loads(baseline_build.read_text())['binaries']['rust-interp-vm']
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json'
        entropy=json.loads(entropy_path.read_text());library=(ROOT/entropy['library']).resolve(strict=True)
        assert entropy['status']=='passed' and sha(library)==entropy['library_sha256']
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        frozen_paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),Path(profile_real.__file__),build_path,fixture_path,profile_path,baseline_build,entropy_path,library]
        frozen_paths += [tool/n for n in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']]
        frozen_paths += [ROOT/'scripts'/n for n in ['interpreter.py','suite_reports.py','workflow_io.py','profile_vm_transitions.py','workflow_cases.py']]
        inputs=[]
        for case,project,reference in CASES:
            summary_path=ROOT/'results'/reference/'summary.json';summary=json.loads(summary_path.read_text())
            oldwork=ROOT/summary['raw'];plan_path=oldwork/'plan.json';oldplan=json.loads(plan_path.read_text())
            records_path=oldwork/'records.json';assert sha(records_path)==summary['records_sha256'] and sha(plan_path)==summary['plan_sha256']
            oldrows=json.loads(records_path.read_text());native=next(r for r in oldrows if r['mode']=='native' and r['state']==6)
            source=ROOT/'.work/sources'/project;owned=json.loads((source/'.rust-interp-owned.json').read_text())
            assert owned['owner']==str(ROOT) and owned['revision']==oldplan['revision']
            assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==oldplan['revision']
            assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
            assert sha(source/oldplan['case']['file'])==oldplan['original_source_sha256']==native['source_sha256']
            for p,h in oldplan['frozen'].items():
                if p.startswith(str(source.relative_to(ROOT))+'/'):assert sha(ROOT/p)==h
            frozen_paths += [summary_path,plan_path,records_path,source/'.rust-interp-owned.json']
            frozen_paths += [source/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0') if p]
            item=dict(case=case,source=str(source),package=oldplan['case']['package'],names=summary['tests'],filter=summary['filter'],
                limits=oldplan['runtime_limits'],flags=oldplan['guest_rustflags'],reference=reference,native_outcomes=native['outcomes'])
            inputs.append(item)
        selected=[p for p in profiles['profiles'] if p['index'] in [0,1,2]]
        for p in selected:
            oldprofile=ROOT/profiles['raw']/f"{p['index']}-profile.json";tape=ROOT/profiles['raw']/f"{p['index']}.tape"
            assert sha(oldprofile)==p['profile_sha256'];frozen_paths += [oldprofile,tape,ROOT/p['artifact'],ROOT/p['catalog']]
            assert sha(ROOT/p['artifact'])==p['artifact_sha256'] and sha(ROOT/p['catalog'])==p['catalog_sha256']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,inputs=inputs,tool_key=key,performance_measurement=False,
            scope='New checked exports against retained native assertions on exactly pinned original sources; candidate profiles replay previously qualified entropy. Different bytecode and logical counts are expected. No new native timing or cold-build comparison.'))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
        records=[];exports={};comparisons=[]
        def execute(label,command,cwd,child_env):
            require_space(ROOT,8)
            child,stdout,stderr=capture(command,cwd=cwd,env=child_env,receipt_path=work/'active.json',receipt=dict(label=label))
            row=dict(label=label,command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr)
            records.append(row);write(work/'records.json',records);assert child.returncode==0,stderr
            print(label,'PASS',flush=True);return row
        for item in inputs:
            case=item['case'];suite_path=work/(case+'-suite.json')
            command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(Path(item['source'])/'Cargo.toml'),
                '--package',item['package'],'--jobs','2','--tool-key',key,'--cache-namespace',run+':'+case,'--test-body','--std-mir',
                '--test-filter',item['filter'],'--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                '--isolated-batch','prepared','--suite-report',str(suite_path),'--instruction-limit',str(item['limits']['instructions']),
                '--trap-unsupported-calls','--run-try-callbacks']
            if case!='pgrust':command+=['--inline-leaves']
            if item['limits']['allocations'] is not None:command+=['--allocation-limit',str(item['limits']['allocations'])]
            child_env=dict(env)
            if item['flags']:
                child_env['RUSTFLAGS']=' '.join(item['flags'])
                for profile in ['DEV','TEST']:child_env['CARGO_PROFILE_'+profile+'_BUILD_OVERRIDE_OPT_LEVEL']='0'
            row=execute(case+'-export',command,Path(item['source']),child_env)
            suite,digest=read_report(suite_path);outcomes=validate_report(suite,item['names'],'prepared',True)
            assert list(map(list,outcomes))==item['native_outcomes']
            validate_runtime_limits(suite,item['limits']['instructions'],item['limits']['allocations'],required=True)
            launch=[json.loads(line.removeprefix('rust-interp-launch: ')) for line in row['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
            assert len(launch)==1;launch=launch[0]
            artifact=Path(launch['artifact_path']);catalog=Path(launch['entry_catalog_path'])
            assert sha(artifact)==launch['artifact_sha256'] and sha(catalog)==launch['entry_catalog_sha256']
            assert [e['name'] for e in json.loads(catalog.read_text())['entries']]==item['names']
            snapshot=work/(case+'.rbc');snapshot.write_bytes(artifact.read_bytes());Path(str(snapshot)+'.entries.json').write_bytes(catalog.read_bytes())
            counts=re.findall(r'pointer_slots=(\d+)',row['stderr']);assert len(counts)==1
            assert all(t['jit_declined_functions']==0 for t in suite['tests'])
            exports[case]=dict(artifact=str(snapshot.relative_to(ROOT)),artifact_sha256=sha(snapshot),catalog_sha256=sha(catalog),suite_sha256=digest,pointer_slots=int(counts[0]),tests=len(outcomes))
            row.update(exports[case]);write(work/'records.json',records)
        for p in selected:
            case=p['case'];artifact=ROOT/exports[case]['artifact'];catalog=Path(str(artifact)+'.entries.json')
            output=work/f"{p['index']}-profile.json";tape=ROOT/profiles['raw']/f"{p['index']}.tape"
            command=[str(tool/'rust-interp-vm'),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                '--instruction-limit',str(p['limits']['instructions']),'--allocation-limit',str(p['limits']['allocations']),
                '--profile',str(output),'--profile-test',p['name'],'--suite-catalog',str(catalog),str(artifact)]
            child_env=dict(env,DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_VM_STATS='1',RUST_INTERP_ENTROPY_MODE='replay',RUST_INTERP_ENTROPY_TAPE=str(tape))
            row=execute(case+'-profile-'+str(p['index']),command,ROOT,child_env)
            assert row['stdout']=='0\n'
            stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',row['stderr'])}
            assert stats['jit_declined_functions']==0
            assert all(stats[k]==p['statistics'][k] for k in ['entropy_calls','entropy_bytes'])
            assert output.stat().st_size<=256*1024**2
            current=json.loads(output.read_text());diagnostic=profile_real.distribution(current,stats)
            prior=json.loads((ROOT/profiles['raw']/f"{p['index']}-profile.json").read_text())
            old={f['name']:f for f in prior['functions']};new={f['name']:f for f in current['functions']}
            assert len(old)==len(prior['functions']) and len(new)==len(current['functions'])
            changed=[name for name in old.keys()&new.keys() if old[name]['operations']!=new[name]['operations']]
            hot_changed=[dict(name_prefix=f['name_prefix'],function=f['function'],native_operations=f['native_operations'])
                for f in p['distribution']['top_native_functions'] if prior['functions'][f['function']]['name'] in changed]
            comparison=dict(index=p['index'],case=case,name=p['name'],baseline_instructions=p['statistics']['instructions'],candidate_instructions=stats['instructions'],
                logical_reduction=1-stats['instructions']/p['statistics']['instructions'],baseline_functions=len(old),candidate_functions=len(new),
                common_functions=len(old.keys()&new.keys()),changed_common_function_bodies=len(changed),changed_baseline_hot_functions=hot_changed,
                statistics=stats,distribution=diagnostic,profile_sha256=sha(output),baseline_profile_sha256=p['profile_sha256'],tape_sha256=sha(tape))
            comparisons.append(comparison);row.update(statistics=stats,profile_sha256=sha(output));write(work/'records.json',records);write(work/'comparisons.json',comparisons)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=len(records),tool_key=key,exports=exports,profiles=comparisons,
            source_unchanged=True,retained_native_outcomes_match=True,entropy_replay_complete=True,vm_bytes_identical=True,performance_measurement=False,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))

if __name__=='__main__':main()
