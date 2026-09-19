"""Qualify the bounded emitter workspace and compose its VM with the adopted compiler."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
RUN='emitter-register-workspace-build-01'
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'


def read(p):return json.loads(p.read_text())


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed
        integration_path=ROOT/'results/scratch-scalar-main-qualification-01/summary.json'
        integration=read(integration_path)
        assert integration['status']=='passed' and integration['tool_key']==BASELINE
        retained,key=installed_tools(BASELINE);assert key==BASELINE
        assert all(sha(retained/n)==h for n,h in integration['binaries'].items())
        paths=[integration_path]+[retained/n for n in [*integration['binaries'],'ready.json','source.json','capabilities.json']]
        for stage,number in [('integrated','02'),('reconstruction','01')]:
            folder=ROOT/'results'/f'emitter-register-workspace-{stage}-{number}'
            closed,summary=read(folder/'closure.json'),read(folder/'summary.json')
            assert closed['status']=='closed' and closed['all_hashes_verified']
            assert summary['status']=='passed' and sha(folder/'summary.json')==closed['summary_sha256']
            plan_path=ROOT/summary['raw']/'plan.json';assert sha(plan_path)==summary['plan_sha256']
            for p,h in read(plan_path)['frozen'].items():
                if p.startswith(('crates/','scripts/','tests/')) or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:assert sha(ROOT/p)==h
            paths += [folder/'closure.json',folder/'summary.json',folder/'terminal.json',plan_path]
        paths += [ROOT/p for p in subprocess.check_output(['git','ls-files','crates','scripts','tests','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            allocated_target_bytes=allocated,required_free_bytes=needed,minimum_child_gib=8,
            expected_commands=4,minimum_workspace_tests_per_profile=615,expected_ignored_per_profile=13,
            baseline_tool_key=BASELINE,original_project_guest_commands=0,native_guest_unit_tests=True,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common=['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target)]
        commands=[('test-debug',['cargo','+nightly-2026-09-08','test',*common,'--workspace']),
            ('test-release',['cargo','+nightly-2026-09-08','test','--release',*common,'--workspace']),
            ('python',[sys.executable,'-m','unittest','discover','-s','tests','-v']),
            ('vm',['cargo','+nightly-2026-09-08','build','--release',*common,'-p','rust-interp-bytecode','--bin','rust-interp-vm','--message-format=json'])]
        records=[];rust_counts={};python_counts=None;outputs={};write(raw/'records.json',records);write(raw/'outputs.json',outputs)
        for label,command in commands:
            require_space(ROOT,8)
            if command[0]=='cargo':assert shutil.disk_usage(ROOT).free>=needed
            start=time.time()
            child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(stage=label))
            for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                seconds=time.time()-start,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records)
            assert child.returncode==0,(out+err)[-6000:]
            if label.startswith('test-'):
                counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert counts and all(int(f)==0 for _,f,_ in counts)
                total=sum(int(p) for p,_,_ in counts);ignored=sum(int(i) for _,_,i in counts)
                assert total>=615 and ignored==13,(total,ignored)
                rust_counts[label]=total
                names=re.findall(r'^\s*fn (register_workspace_[a-z_]+)\(', (ROOT/'crates/bytecode/src/jit/register_workspace.rs').read_text(),re.M)
                assert len(names)==7,names
                for test in [*names,'native_scalar_2187_copy_cases_in_both_profile_modes']:
                    assert test+' ... ok' in out,test
            if label=='python':
                count,=re.findall(r'Ran (\d+) tests? in ',err)
                skipped,=re.findall(r'^OK(?: \(skipped=(\d+)\))?$',err,re.M)
                assert int(count)>=456 and int(skipped or 0)==22
                python_counts=dict(discovered=int(count),passed=int(count)-22,skipped=22)
            if label=='vm':
                messages=[json.loads(line) for line in out.splitlines() if line.strip()]
                artifacts=[m for m in messages if m.get('reason')=='compiler-artifact' and m.get('target',{}).get('name')=='rust-interp-vm' and m.get('executable')]
                assert len(artifacts)==1;binary=Path(artifacts[0]['executable']);assert binary.is_relative_to(target)
                retained_vm=raw/'rust-interp-vm';shutil.copy2(binary,retained_vm)
                outputs[str(retained_vm.relative_to(ROOT))]=sha(retained_vm);write(raw/'outputs.json',outputs)
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,'passed',flush=True)
        binaries=dict(integration['binaries']);binaries['rust-interp-vm']=sha(retained_vm)
        assert binaries['rust-interp-vm']!=integration['binaries']['rust-interp-vm']
        composition=dict(kind='bounded-emitter-register-workspace',schema_version=1,source_commit=revision,
            compiler_source_key=BASELINE,binaries=binaries,dense_register_limit=65536,dense_combined_payload_limit=4*1024*1024)
        key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication,45)
            installed=ROOT/'.work/interpreter-tools'/key;installed.mkdir(exist_ok=False)
            for name in binaries:shutil.copy2(retained_vm if name=='rust-interp-vm' else retained/name,installed/name)
            caps=read(retained/'capabilities.json');caps.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed/'capabilities.json',caps)
            write(installed/'source.json',dict(tool_key=key,composition=composition,files=frozen,source_commit=revision,
                key_algorithm='SHA256 of canonical composition JSON',source=str(ROOT)))
            assert all(sha(installed/n)==h for n,h in binaries.items())
            write(installed/'ready.json',binaries)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        outputs.update({str((installed/n).relative_to(ROOT)):sha(installed/n) for n in [*binaries,'ready.json','source.json','capabilities.json']});write(raw/'outputs.json',outputs)
        destination=ROOT/'results'/RUN;destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,tests=rust_counts,ignored_per_profile=13,
            python=python_counts,commands=len(records),tool_key=key,binaries=binaries,composition=composition,outputs=outputs,
            matched_control=dict(tool_key=BASELINE,binaries=integration['binaries'],integration=str(integration_path.relative_to(ROOT))),
            source_manifest=str((raw/'plan.json').relative_to(ROOT)),source_manifest_sha256=sha(raw/'plan.json'),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),raw=str(raw.relative_to(ROOT)),
            setup_seconds=sum(r['seconds'] for r in records),original_project_guest_commands=0,performance_measurement=False))


def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
        plan=read(raw/'plan.json');records=read(raw/'records.json');terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert Path(terminal['command'][0]).resolve()==Path(plan['controller_command'][0]).resolve()
        assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
        bindings={};evidence={}
        for p,h in plan['frozen'].items():
            assert sha(ROOT/p)==h
            if p.startswith(('.work/','results/')):evidence[p]=h
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h;bindings[p]=dict(revision=plan['source_revision'],sha256=h)
        for r in records:
            for stream in ['stdout','stderr']:
                p=raw/(r['label']+'.'+stream);assert sha(p)==r[stream+'_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
        for p,h in read(raw/'outputs.json').items():assert sha(ROOT/p)==h;evidence[p]=h
        out.mkdir(exist_ok=True);assert not (out/'closure.json').exists()
        if terminal['returncode']==0:
            summary=read(out/'summary.json');assert summary['status']=='passed' and len(records)==4
            assert all(r['returncode']==0 for r in records)
            assert summary['plan_sha256']==sha(raw/'plan.json') and summary['records_sha256']==sha(raw/'records.json')
        else:
            assert not (out/'summary.json').exists()
            write(out/'summary.json',dict(status='build-failed',source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),
                commands=len(records),returncodes=[r['returncode'] for r in records],plan_sha256=sha(raw/'plan.json'),
                records_sha256=sha(raw/'records.json'),original_project_guest_commands=0,performance_measurement=False))
        for p in [raw/'plan.json',raw/'records.json',raw/'outputs.json',outer/'status.json',outer/'plan.json',outer/'command.log']:evidence[str(p.relative_to(ROOT))]=sha(p)
        write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,source_files=len(bindings),frozen_inputs=len(plan['frozen']),
            evidence_files=len(evidence),summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),original_project_guest_commands=0))
        print('Closed emitter register workspace build; terminal',terminal['returncode'],flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:
        assert len(sys.argv)==1
        main()
