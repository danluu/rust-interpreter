"""Reconstruct exact adopted machine words with reusable register workspace storage."""
import hashlib,json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='emitter-register-workspace-reconstruction-01'


def read(p):return json.loads(p.read_text())


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed
        frozen={}
        def bind(path,expected=None):
            digest=sha(path)
            if expected is not None:assert digest==expected,path
            frozen[str(path.relative_to(ROOT))]=digest
            return read(path) if path.suffix=='.json' else digest
        focused=ROOT/'results/emitter-register-workspace-integrated-02'
        fc=bind(focused/'closure.json');fs=bind(focused/'summary.json',fc['summary_sha256'])
        assert fc['status']=='closed' and fc['all_hashes_verified'] and fs['tests_per_profile']==7
        fp=bind(ROOT/fs['raw']/'plan.json',fs['plan_sha256'])
        for path,digest in fp['frozen'].items():
            if path.startswith('crates/') or path in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/path,digest)
        prior=ROOT/'results/adopted-current-runtime-sampling-02'
        closed=bind(prior/'closure.json');summary=bind(prior/'summary.json',closed['summary_sha256'])
        assert closed['status']=='closed' and closed['all_hashes_verified']
        for path,digest in bind(ROOT/closed['evidence'],closed['evidence_sha256']).items():bind(ROOT/path,digest)
        for path in Path(__file__).parent.iterdir():
            if path.suffix in ['.py','.md']:bind(path)
        for name in ['compare_saved_runtime.py','workflow_io.py']:bind(ROOT/'scripts'/name)
        artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        bind(artifact,artifact.stem)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            allocated_target_bytes=allocated,required_free_bytes=needed,minimum_child_gib=8,
            expected_commands=2,original_project_guest_commands=0,guest_commands=0,
            executable_code_publications=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','MEMORY_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        cargo=['cargo','+nightly-2026-09-08','test','--release','--locked','--offline','--jobs','2',
            '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode','--lib']
        commands=[]
        for case in summary['cases']:
            label=case['case'];folder=ROOT/'.work'/case['run_id']/'0/jit-code'
            commands.append((label,[*cargo,'jit::code_spans::memory_parts::observe_saved_small_memory_parts','--','--ignored','--exact'],
                dict(MEMORY_ARTIFACT=str(artifact),MEMORY_MAP=str(folder/'operations.json'),
                    MEMORY_CODE=str(folder/'code.bin'),MEMORY_OUTPUT=str(raw/(label+'.json'))),1))
        records=[];cases=[];outputs={};write(raw/'records.json',records);write(raw/'outputs.json',outputs)
        for label,command,extra,tests in commands:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            start=time.time()
            child,out,err=capture(command,cwd=ROOT,env=env|extra,receipt_path=raw/'active.json',receipt=dict(stage=label))
            for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,extra_env=extra,pid=child.pid,returncode=child.returncode,
                seconds=time.time()-start,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records)
            output_path=raw/(label+'.json')
            if output_path.exists():outputs[str(output_path.relative_to(ROOT))]=sha(output_path);write(raw/'outputs.json',outputs)
            assert child.returncode==0,(out+err)[-5000:]
            assert f'test result: ok. {tests} passed; 0 failed; 0 ignored;' in out
            report=read(output_path)
            assert report['status']=='passed' and report['guest_commands']==report['executable_code_publications']==0
            assert report['schema_version']==2 and report['scalar_bodies_reconstructed']>0 and report['scratch_copy_observed'] is False
            for key in ['exact_full_function_reconstruction','observer_words_unchanged','complete_small_memory_partition']:assert report[key]
            folder=ROOT/'.work'/next(c['run_id'] for c in summary['cases'] if c['case']==label)/'0/jit-code'
            assert report['code_sha256']==sha(folder/'code.bin') and report['code_bytes']==(folder/'code.bin').stat().st_size
            cases.append(dict(case=label,ordinary_functions=len(report['functions']),**{k:v for k,v in report.items() if k!='functions'}))
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,'exact adopted reconstruction passed',flush=True)
        destination=ROOT/'results'/RUN;destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,commands=len(records),reused_controls_per_profile=7,cases=cases,
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),outputs=outputs,
            guest_commands=0,executable_code_publications=0,setup_seconds=sum(r['seconds'] for r in records),performance_measurement=False))


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
            summary=read(out/'summary.json');assert summary['status']=='passed' and len(records)==2
            assert all(r['returncode']==0 for r in records)
            assert summary['plan_sha256']==sha(raw/'plan.json') and summary['records_sha256']==sha(raw/'records.json')
        else:
            assert not (out/'summary.json').exists()
            write(out/'summary.json',dict(status='reconstruction-failed',source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),
                commands=len(records),returncodes=[r['returncode'] for r in records],plan_sha256=sha(raw/'plan.json'),
                records_sha256=sha(raw/'records.json'),original_project_guest_commands=0,performance_measurement=False))
        for p in [raw/'plan.json',raw/'records.json',raw/'outputs.json',outer/'status.json',outer/'plan.json',outer/'command.log']:evidence[str(p.relative_to(ROOT))]=sha(p)
        write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,source_files=len(bindings),frozen_inputs=len(plan['frozen']),
            evidence_files=len(evidence),summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),original_project_guest_commands=0))
        print('Closed exact adopted reconstruction; terminal',terminal['returncode'],flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:
        assert len(sys.argv)==1
        main()
