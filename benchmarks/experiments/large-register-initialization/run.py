"""Observe typed production initialization decisions without running guest code."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='large-register-initialization-01'
ARTIFACTS=[
('.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc','caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9'),
('.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc','caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9'),
('.work/call-capacity-credit-edit-folded-01/artifacts/2a869f1607f67f6878809b51705203f573fb0f38cb1a325f41c09597315b666c.rbc','2a869f1607f67f6878809b51705203f573fb0f38cb1a325f41c09597315b666c'),
('.work/guarded-local-facts-main-parser-01/artifact.rbc','a157f60c0356ae2498eaa94a1133e2257c8ee220bcfd3b24ca969525fe5f9a61')]
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        frozen={}
        def bind(p,h=None):
            p=Path(p);actual=sha(p)
            if h is not None:assert actual==h,str(p)
            frozen[str(p.relative_to(ROOT))]=actual
            return read(p) if p.suffix=='.json' else actual
        folder=ROOT/'results/large-register-calls-01'
        closed=bind(folder/'closure.json');assert closed['status']=='closed' and closed['all_hashes_verified']
        saved=bind(folder/'summary.json',closed['summary_sha256'])
        assert saved['status']=='passed' and saved['new_guest_commands']==0 and len(saved['profiles'])==4
        bind(ROOT/closed['bindings'],closed['bindings_sha256'])
        for p,h in saved['artifacts'].items():bind(ROOT/p,h)
        for p,h in ARTIFACTS:bind(ROOT/p,h)
        qualification=bind(ROOT/'results/scratch-scalar-main-qualification-01/summary.json')
        # The runtime source is bound to the adopted qualification's explicit revision.
        adopted=qualification['source_revision']
        for p in ['crates/bytecode/src/registers.rs','crates/bytecode/src/register_init.rs']:
            original=subprocess.check_output(['git','show',adopted+':'+p],cwd=ROOT)
            current=(ROOT/p).read_bytes()
            if p.endswith('register_init.rs'):current=current.replace(b'#[cfg(test)]\nmod census;\n\n',b'',1)
            assert current==original,p
        paths=subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()
        paths += [str(p.relative_to(ROOT)) for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += ['scripts/compare_saved_runtime.py','scripts/workflow_io.py']
        for p in paths:bind(ROOT/p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,adopted_revision=adopted,
            target=str(target.relative_to(ROOT)),required_free_bytes=needed,allocated_target_bytes=allocated,
            expected_commands=4,minimum_child_gib=8,guest_commands=0,production_changes=0,performance_measurement=False))
        records=[];write(work/'records.json',records)
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','INITIALIZATION_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',RUST_TEST_THREADS='2')
        command=['cargo','+nightly-2026-09-08','test','--release','--lib','-p','rust-interp-bytecode','--locked','--offline','--jobs','2',
            '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),
            'register_init::census::observe_saved_register_initialization','--','--ignored','--exact']
        cases=[]
        for i,((artifact,digest),saved_case) in enumerate(zip(ARTIFACTS,saved['profiles'])):
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed,'build admission no longer holds'
            label=str(i);extra=dict(INITIALIZATION_ARTIFACT=str(ROOT/artifact),
                INITIALIZATION_CALLS=str(ROOT/'.work/large-register-calls-01'/(label+'-calls.json')),
                INITIALIZATION_OUTPUT=str(work/(label+'.json')))
            start=time.time();child,stdout,stderr=capture(command,cwd=ROOT,env=env|extra,
                receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,payload in [('stdout',stdout),('stderr',stderr)]:(work/(label+'.'+stream)).write_text(payload)
            records.append(dict(label=label,command=command,extra_env=extra,pid=child.pid,returncode=child.returncode,
                seconds=time.time()-start,stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records)
            assert child.returncode==0,(stdout+stderr)[-5000:]
            assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in stdout
            detail=read(work/(label+'.json'));assert detail['status']=='passed' and detail['artifact_sha256']==digest
            assert detail['guest_commands']==detail['production_changes']==0
            assert detail['nominal_register_bytes']==saved_case['nominal_register_bytes']
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            selected=[r for r in detail['functions'] if r['needs_initial_zeroes']]
            cases.append(dict(case=label,name=saved_case['name'],functions=len(detail['functions']),
                needing_zeroes=len(selected),nominal_register_bytes=detail['nominal_register_bytes'],
                current_zeroing_direct_weight=detail['current_zeroing_direct_weight'],top=selected[:15],
                detail_sha256=sha(work/(label+'.json'))))
            print(label,'passed',len(selected),detail['current_zeroing_direct_weight'],flush=True)
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,commands=4,raw=str(work.relative_to(ROOT)),
            cases=cases,plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            setup_seconds=sum(r['seconds'] for r in records),guest_commands=0,production_changes=0,
            performance_measurement=False,scope=detail['scope']))
if __name__=='__main__':main()
