"""Measure full-width interpreted operands without running original guests."""
import json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='selective-narrow-repair-census-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated);assert shutil.disk_usage(ROOT).free>=needed
        frozen={}
        def bind(p,digest=None):
            h=sha(p)
            if digest is not None:assert h==digest,p
            frozen[str(p.relative_to(ROOT))]=h
            return read(p) if p.suffix=='.json' else h
        prior=ROOT/'results/narrow-register-storage-census-01'
        closed=bind(prior/'closure.json');old=bind(prior/'summary.json',closed['summary_sha256'])
        assert closed['status']=='closed' and closed['all_hashes_verified'] and old['controls']==dict(debug=7,release=7,traffic=6)
        old_plan=bind(ROOT/old['raw']/'plan.json',old['plan_sha256'])
        profile_folder=ROOT/'results/implicit-zero-storage-profile-01'
        pc=bind(profile_folder/'closure.json');profiles=bind(profile_folder/'summary.json',pc['summary_sha256'])
        assert pc['status']=='closed' and pc['all_hashes_verified'] and profiles['exact_per_pc_counts']
        assert profiles['tool_key']=='3e53b127220f71115eec7b18e2ed452577471ab48cfd5d4c669c0ae3a295f32a'
        paths=[]
        for i in range(2):
            a,=[r for r in profiles['comparisons'] if r['index']==i and r['mode']=='control']
            b,=[r for r in profiles['comparisons'] if r['index']==i and r['mode']=='candidate']
            ap=bind(ROOT/a['profile_path'],a['profile_sha256']);bp=bind(ROOT/b['profile_path'],b['profile_sha256'])
            assert old_plan['frozen'][a['profile_path']]==a['profile_sha256']
            assert len(ap['functions'])==len(bp['functions'])
            for af,bf in zip(ap['functions'],bp['functions']):
                for field in ['name','frame_size','registers','operations','interpreted']:
                    assert af[field]==bf[field],(i,field)
            paths.append(str(ROOT/b['profile_path']))
        artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        bind(artifact,old_plan['artifact_sha256']);assert artifact.stem==sha(artifact)
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md']:bind(p)
        for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True,cwd=ROOT).splitlines():bind(ROOT/p)
        for name in ['workflow_io.py','compare_saved_runtime.py']:bind(ROOT/'scripts'/name)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.argv],expected_commands=7,target=str(target.relative_to(ROOT)),
            allocated_target_bytes=allocated,required_free_bytes=needed,minimum_child_gib=8,
            original_project_guest_commands=0,synthetic_interpreter_fixtures=True,
            production_runtime_changes=0,executable_code_publications=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','SELECTIVE_REPAIR_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        cargo=['cargo','+nightly-2026-09-08','test','--locked','--offline','--jobs','2',
            '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode','--lib']
        commands=[]
        for profile,extra in [('debug',[]),('release',['--release'])]:
            for label,test,count in [('width','jit::register_widths::tests::',4),
                ('cost','jit::code_spans::narrow_storage::narrow_storage_work_',3),
                ('roles','jit::code_spans::selective_repair::selective_repair_',4)]:
                commands.append((label+'-'+profile,[*cargo,*extra,test],{},count))
        commands.append(('typed',[*cargo,'--release','jit::code_spans::selective_repair::observe_selective_repair','--','--ignored','--exact'],
            dict(SELECTIVE_REPAIR_ARTIFACT=str(artifact),SELECTIVE_REPAIR_PROFILES=json.dumps(paths),
                SELECTIVE_REPAIR_OUTPUT=str(raw/'typed.json')),1))
        records=[]
        for label,command,extra,count in commands:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=env|extra,
                receipt_path=raw/'active.json',receipt=dict(stage=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                seconds=time.time()-start,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            assert f'test result: ok. {count} passed; 0 failed; 0 ignored;' in out
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',flush=True)
        typed=read(raw/'typed.json');assert typed['status']=='passed' and typed['artifact_sha256']==sha(artifact) and len(typed['cases'])==2
        cases=[]
        for i,c in enumerate(typed['cases']):
            assert c['path']==paths[i] and c['sha256']==sha(Path(paths[i]))
            totals=c['totals'];before=old['cases'][i]['conservative_interpreter_work']
            assert totals['interpreted_instructions']==before['interpreted_instructions']
            assert totals['all_narrow_read_operands']==before['narrow_read_operands']
            assert sum(r[0] for r in c['by_kind'].values())==totals['interpreted_instructions']
            assert sum(r[1] for r in c['by_kind'].values())==totals['all_narrow_read_operands']
            assert sum(r[2] for r in c['by_kind'].values())==totals['full_narrow_read_operands']
            assert sum(r[3] for r in c['by_kind'].values())==totals['unique_full_narrow_reads']
            cases.append(dict(case=['block','exhaustive'][i],totals=totals,by_kind=c['by_kind']))
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,commands=len(records),
            controls=dict(debug=11,release=11),cases=cases,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            outputs={str((raw/'typed.json').relative_to(ROOT)):sha(raw/'typed.json')},
            setup_seconds=sum(r['seconds'] for r in records),original_project_guest_commands=0,
            synthetic_interpreter_fixtures=True,production_runtime_changes=0,
            executable_code_publications=0,performance_measurement=False))
if __name__=='__main__':main()
