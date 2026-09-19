"""Qualify a typed upper-read census; no new guest or runtime publication."""
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='upper-word-read-census-02'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed
        frozen={}
        def bind(p,expected=None):
            digest=sha(p)
            if expected is not None:assert digest==expected,p
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p) if p.suffix=='.json' else digest
        prior=ROOT/'results/adopted-current-runtime-sampling-02'
        closed=bind(prior/'closure.json');summary=bind(prior/'summary.json',closed['summary_sha256'])
        assert closed['status']=='closed' and closed['all_hashes_verified'] and summary['status']=='passed'
        for p,h in bind(ROOT/closed['evidence'],closed['evidence_sha256']).items():bind(ROOT/p,h)
        first=ROOT/'results/upper-word-read-census-01'
        fc=bind(first/'closure.json');fs=bind(first/'summary.json',fc['summary_sha256'])
        assert fc['status']=='closed' and fc['all_hashes_verified'] and fs['controls']==dict(debug=6,release=6,traffic=6)
        for p,h in fs['outputs'].items():bind(ROOT/p,h)
        old=ROOT/'results/ordinary-memory-traffic-01'
        oc=bind(old/'closure.json');obs=bind(old/'summary.json',oc['summary_sha256'])
        assert oc['status']=='closed' and oc['all_hashes_verified'] and obs['controls']==8
        oldraw=ROOT/obs['raw'];oldplan=bind(oldraw/'plan.json',obs['plan_sha256'])
        bindings=bind(ROOT/oc['bindings'],oc['bindings_sha256'])
        object_path=oldraw/'traffic.o';bind(object_path,obs['object_sha256'])
        records=bind(oldraw/'records.json',obs['records_sha256'])
        for record in records:
            assert record['returncode']==0
            for stream in ['stdout','stderr']:bind(oldraw/(record['label']+'.'+stream),record[stream+'_sha256'])
        decoder_paths=['benchmarks/experiments/ordinary-memory-traffic/'+n for n in ['traffic.py','test_traffic.py','fixture.s']]
        decoder_paths+=['benchmarks/experiments/ordinary-register-census/'+n for n in
            ['linear.py','regions.py','test_memory.py','memory.py','cfg_memory.py','cfg.py']]
        decoder_paths+=['benchmarks/experiments/scalar-word-census/'+n for n in ['words.py','test_words.py']]
        for p in decoder_paths:
            bind(ROOT/p,oldplan['frozen'][p]);assert bindings[p]['sha256']==frozen[p]
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md']:bind(p)
        for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines():bind(ROOT/p)
        for name in ['compare_saved_runtime.py','workflow_io.py','summarize_owned_sample.py','vmmap_ranges.py']:bind(ROOT/'scripts'/name)
        artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        bind(artifact,artifact.stem)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.argv],artifact_sha256=sha(artifact),
            target=str(target.relative_to(ROOT)),allocated_target_bytes=allocated,required_free_bytes=needed,
            expected_commands=5,minimum_child_gib=8,guest_commands=0,production_runtime_changes=0,
            executable_code_publications=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','UPPER_READ_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        cargo=['cargo','+nightly-2026-09-08','test','--locked','--offline','--jobs','2',
            '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode','--lib']
        test='jit::code_spans::upper_reads::'
        commands=[('debug',[*cargo,test+'upper_read_'],{},ROOT,8),
            ('release',[*cargo,'--release',test+'upper_read_'],{},ROOT,8),
            ('typed',[*cargo,'--release',test+'observe_saved_upper_reads','--','--ignored','--exact'],
                dict(UPPER_READ_ARTIFACT=str(artifact),UPPER_READ_OUTPUT=str(raw/'typed.json')),ROOT,1),
            ('traffic',[sys.executable,'-m','unittest','test_traffic','-v'],dict(ORDINARY_TRAFFIC_OBJECT=str(object_path)),
                ROOT/'benchmarks/experiments/ordinary-memory-traffic',6),
            ('attribute',[sys.executable,str(Path(__file__).with_name('analyze.py'))],{},ROOT,0)]
        records=[]
        for label,command,extra,cwd,count in commands:
            require_space(ROOT,8)
            if command[0]=='cargo':assert shutil.disk_usage(ROOT).free>=needed
            else:require_space(ROOT,12)
            start=time.time();child,out,err=capture(command,cwd=cwd,env=env|extra,
                receipt_path=raw/'active.json',receipt=dict(stage=label))
            for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,cwd=str(cwd),extra_env=extra,pid=child.pid,
                returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if label=='traffic':assert 'Ran 6 tests' in err and err.rstrip().endswith('OK')
            elif count:assert f'test result: ok. {count} passed; 0 failed; 0 ignored;' in out
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,'passed',flush=True)
        attribution=read(raw/'attribution.json');assert attribution['status']=='passed' and len(attribution['cases'])==2
        outputs={str(p.relative_to(ROOT)):sha(p) for p in [raw/n for n in ['typed.json','attribution.json','details.json','block-sites.json','exhaustive-sites.json']]}
        dest=ROOT/'results'/RUN;dest.mkdir(exist_ok=False)
        write(dest/'summary.json',dict(status='passed',source_revision=revision,commands=len(records),
            controls=dict(debug=8,release=8,traffic=6),cases=attribution['cases'],
            typed_functions=attribution['typed_functions'],declined_functions=attribution['declined_functions'],
            eligible_registers=attribution['eligible_registers'],outputs=outputs,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            setup_seconds=sum(r['seconds'] for r in records),guest_commands=0,
            executable_code_publications=0,production_runtime_changes=0,performance_measurement=False))
if __name__=='__main__':main()
