"""Qualify the bounded pointer-slot diagnostic; never execute saved guest code."""
import hashlib, os, shutil, subprocess, sys, time
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
read=focus.read
RUN='frame-initialization-slots-build-01'
BASE='fca687ebac0ea9374a1426addd01169fe707f608'
BINARY='frame-initialization-slots-census'

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        def admission():
            allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
            needed=max(14*1024**3,8*1024**3+2*allocated);free=shutil.disk_usage(ROOT).free
            assert free>=needed,(free,needed)
            return dict(allocated_target_bytes=allocated,required_free_bytes=needed,free_bytes=free)
        initial=admission()
        assert not subprocess.check_output(['git','diff','--name-only',BASE,'--','crates/bytecode'],cwd=ROOT).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        directory=Path(__file__).parent
        paths=[ROOT/p for p in subprocess.check_output(['git','ls-files','crates/bytecode','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [p for p in directory.iterdir() if p.suffix in ['.rs','.py','.md','.toml','.lock']]
        previous=directory.parent/'frame-initialization-constants'
        paths += [previous/'proof.rs',previous/'proof_tests.rs',Path(focus.__file__)]
        paths += [ROOT/'scripts'/p for p in ['workflow_io.py','compare_saved_runtime.py','supervise_experiment.py']]
        # The legacy build predates closure.json. Revalidate its terminal, all
        # command logs and Git-bound inputs explicitly instead of inventing one.
        oldout=ROOT/'results/frame-initialization-constants-build-01'
        old=read(oldout/'summary.json');terminal=read(oldout/'terminal.json');oldraw=ROOT/old['raw']
        outer=ROOT/'.work/experiments/frame-initialization-constants-build-01'
        assert old['status']=='passed' and old['tests']==dict(debug=10,release=10)
        assert terminal['status']=='finished' and terminal['returncode']==0
        assert terminal['owner']==terminal['cwd']==str(ROOT)
        assert sha(outer/'status.json')==sha(oldout/'terminal.json')
        assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
        assert sha(oldraw/'plan.json')==old['plan_sha256'] and sha(oldraw/'records.json')==old['records_sha256']
        oldplan=read(oldraw/'plan.json');oldrows=read(oldraw/'records.json')
        assert len(oldrows)==4 and all(r['returncode']==0 for r in oldrows)
        historical={}
        for p,h in oldplan['frozen'].items():
            if p.startswith(('crates/','benchmarks/','scripts/','results/')):
                blob=subprocess.check_output(['git','show',oldplan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(blob).hexdigest()==h
                historical[p]=dict(revision=oldplan['source_revision'],sha256=h)
            else:
                assert sha(ROOT/p)==h;paths.append(ROOT/p)
        for row in oldrows:
            for stream in ['stdout','stderr']:
                p=oldraw/(row['label']+'.'+stream);assert sha(p)==row[stream+'_sha256'];paths.append(p)
        for name in ['proof.rs','proof_tests.rs']:
            p=previous/name;assert sha(p)==oldplan['frozen'][str(p.relative_to(ROOT))]
        paths += [oldout/'summary.json',oldout/'terminal.json',oldraw/'plan.json',oldraw/'records.json',
                  outer/'status.json',outer/'plan.json',outer/'command.log']
        artifacts=[(ROOT/p,h) for p,h in oldplan['frozen'].items() if p.endswith('.rbc')]
        assert len(artifacts)==1;artifact,digest=artifacts[0];assert sha(artifact)==digest
        oldtyped=oldraw/'typed.json';assert sha(oldtyped)==old['typed_sha256'];paths.append(oldtyped)
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'historical-bindings.json',historical)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target),admission=initial,
            expected_commands=4,tests_per_profile=18,mask_oracle_cases=6400,copy_oracle_cases=19584,
            adopted_runtime_source=BASE,artifact=str(artifact.relative_to(ROOT)),artifact_sha256=digest,
            historical_bindings_sha256=sha(raw/'historical-bindings.json'),original_project_guest_commands=0,
            native_fixture_execution=False,performance_measurement=False,production_runtime_changes=0))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[]
        def invoke(label,command,compiler=False,outputs=()):
            require_space(ROOT,8);current=admission() if compiler else dict(free_bytes=shutil.disk_usage(ROOT).free)
            command=list(map(str,command));start=time.time()
            child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            record=dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                admission=current,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')))
            records.append(record);write(raw/'records.json',records)
            assert child.returncode==0,(out+err)[-6000:]
            record['outputs']={str(p.relative_to(ROOT)):sha(p) for p in outputs};write(raw/'records.json',records)
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            return out
        common=['--locked','--offline','--jobs','2','--manifest-path',directory/'Cargo.toml','--target-dir',target,'--bin',BINARY]
        for label,extra in [('debug',[]),('release',['--release'])]:
            out=invoke(label,['cargo','+nightly-2026-09-08','test',*extra,*common,'proof::tests::'],compiler=True)
            assert 'test result: ok. 18 passed; 0 failed; 0 ignored;' in out
            assert 'path_byte_oracle_checks_both_sides_of_cfg_joins' in out
            assert 'byte_oracle_checks_every_claimed_copy_fact_and_partial_overlaps' in out
            print(label,'18 controls passed',flush=True)
        invoke('build',['cargo','+nightly-2026-09-08','build','--release',*common],compiler=True)
        binary=raw/BINARY;shutil.copy2(target/'release'/BINARY,binary)
        binary_sha=sha(binary);require_space(ROOT,12)
        invoke('analyze',[binary,artifact,raw/'typed.json'],outputs=[binary,raw/'typed.json'])
        assert sha(binary)==binary_sha
        typed=read(raw/'typed.json');rows=typed['functions'];before=read(oldtyped)['functions']
        assert typed['status']=='passed' and typed['guest_commands']==typed['runtime_changes']==0
        assert typed['caller_address_guards_required'] and len(rows)==old['functions']==5468
        assert [r['function'] for r in rows]==list(range(len(rows)))
        assert all((r['name'],r['frame_size'],r['frame_align'],r['calls'])==(b['name'],b['frame_size'],b['frame_align'],b['calls']) for r,b in zip(rows,before))
        assert all(r['previous_confined']==b['confined'] and r['previous_initialization']==b['cfg_with_callee_effects'] for r,b in zip(rows,before))
        assert sum(r['previous_confined']['eligible'] for r in rows)==old['confined_functions']==669
        assert sum(r['previous_initialization']['eligible'] for r in rows)==old['cfg_with_effects']==1150
        newkey='cfg_with_callee_effects';oldkey='previous_initialization'
        regressions=[dict(function=r['function'],decline=r[newkey]['decline']) for r in rows if r[oldkey]['eligible'] and not r[newkey]['eligible']]
        gains=[r['function'] for r in rows if not r[oldkey]['eligible'] and r[newkey]['eligible']]
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        outputs={str(p.relative_to(ROOT)):sha(p) for p in [binary,raw/'typed.json',raw/'historical-bindings.json']}
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=4,
            tests=dict(debug=18,release=18),mask_oracle_cases_per_profile=6400,copy_oracle_cases_per_profile=19584,
            functions=len(rows),previous_confined=669,previous_initialized=1150,
            confined_functions=sum(r['confined']['eligible'] for r in rows),
            cfg_without_effects=sum(r['cfg_without_callee_effects']['eligible'] for r in rows),
            cfg_with_effects=sum(r[newkey]['eligible'] for r in rows),newly_eligible_functions=gains,
            lost_eligible_functions=regressions,declines=Counter(r[newkey]['decline']['reason'] for r in rows if not r[newkey]['eligible']),
            global_work_remaining=typed['global_work_remaining'],previous_global_work_remaining=typed['previous_global_work_remaining'],
            binary_sha256=binary_sha,typed_sha256=sha(raw/'typed.json'),outputs=outputs,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            setup_seconds=sum(r['seconds'] for r in records[:3]),analysis_seconds=records[3]['seconds'],
            original_project_guest_commands=0,production_runtime_changes=0,performance_measurement=False,
            sample_coverage_measured=False,default_runtime_adoption=False))
        print('Typed diagnostic passed; newly eligible',len(gains),'lost',len(regressions),flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
