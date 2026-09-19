"""Replay a populated, bounded staging history after focused qualification."""
import json,os,shutil,subprocess,sys,time
from pathlib import Path
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='cross-program-template-history-01'
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
        def closed(run):
            folder=ROOT/'results'/run;c=bind(folder/'closure.json')
            assert c['status']=='closed' and c['all_hashes_verified']
            bind(folder/'terminal.json',c['terminal_sha256'])
            return bind(folder/'summary.json',c['summary_sha256'])
        model=closed('cross-program-template-model-04');assert model['status']=='passed' and model['tests_per_profile']==14
        model_plan=bind(ROOT/model['raw']/'plan.json',model['plan_sha256'])
        for p,h in model_plan['frozen'].items():
            if p.startswith('crates/') or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/p,h)
        original=closed('cross-program-template-replay-01');assert original['status']=='passed'
        old=ROOT/original['raw'];bind(old/'plan.json',original['plan_sha256']);bind(old/'records.json',original['records_sha256'])
        source=old/'input.json';inputs=bind(source,original['outputs'][str(source.relative_to(ROOT))])
        assert [a['state'] for a in inputs['artifacts']]==[0,-1,1,2,3,4,5,0]
        assert [w['worker'] for w in inputs['workers']]==[0,1]
        for a in inputs['artifacts']:bind(Path(a['path']),a['sha256'])
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md']:bind(p)
        for name in ['compare_saved_runtime.py','workflow_io.py']:bind(ROOT/'scripts'/name)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);(raw/'input.json').write_bytes(source.read_bytes())
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,expected_commands=1,
            input_sha256=sha(raw/'input.json'),original_project_guest_commands=0,executable_code_publication=False,
            performance_measurement=False,diagnostic_intervals=True,production_runtime_changes=0))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',
            RUST_INTERP_TEMPLATE_REPLAY_INPUT=str(raw/'input.json'),RUST_INTERP_TEMPLATE_REPLAY_OUTPUT=str(raw/'report.json'))
        command=['cargo','+nightly-2026-09-08','test','--release','--locked','--offline','--jobs','2',
            '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode',
            '--lib','jit::cross_program_templates::replay::cross_program_template_replay_populated_parser_history','--','--ignored','--exact']
        require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed;write(raw/'records.json',[])
        start=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label='history'))
        (raw/'history.stdout').write_text(out);(raw/'history.stderr').write_text(err)
        write(raw/'records.json',[dict(label='history',command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
            stdout_sha256=sha(raw/'history.stdout'),stderr_sha256=sha(raw/'history.stderr'))])
        assert child.returncode==0 and 'test result: ok. 1 passed; 0 failed; 0 ignored;' in out,(out+err)[-6000:]
        report=read(raw/'report.json');assert report['schema_version']==1 and report['populated_history'] is True
        assert report['input_sha256']==sha(raw/'input.json') and len(report['workers'])==2
        assert report['original_project_guest_commands']==report['executable_code_publications']==0
        assert report['production_cache_admission'] is False;summaries=[]
        for source,worker in zip(inputs['workers'],report['workers']):
            assert worker['worker']==source['worker'] and worker['observed_functions']==len(source['functions'])
            selected={f['function'] for f in source['functions']};assert len(selected)==worker['observed_functions']
            assert len(worker['comparisons'])==8;rows=[];previous_entries=0
            for ordinal,row in enumerate(worker['comparisons']):
                assert row['ordinal']==ordinal and row['state']==inputs['artifacts'][ordinal]['state']
                assert row['artifact_sha256']==inputs['artifacts'][ordinal]['sha256']
                outcomes=dict(row['outcomes']);assert len(outcomes)==len(row['outcomes'])==len(selected) and set(outcomes)==selected
                assert set(outcomes.values())<={'key_miss','restore_miss','exact','unavailable'}
                counts={s:sum(v==s for v in outcomes.values()) for s in ['key_miss','restore_miss','exact','unavailable']}
                assert all(type(row[k]) is int and row[k]>=0 for k in ['inserted','capture_declines','emission_declines','evictions','history_entries','history_charge'])
                assert 512<=row['history_charge']<=64*1024**2 and row['history_entries']<=16_384
                assert row['inserted']+row['capture_declines']+row['emission_declines']==counts['key_miss']+counts['restore_miss']
                assert row['history_entries']<=previous_entries+row['inserted']-row['evictions'];previous_entries=row['history_entries']
                if ordinal==0:assert counts['exact']==counts['restore_miss']==0
                else:assert counts['exact']>0
                assert row['diagnostic_ns']['fresh_exact']<=row['diagnostic_ns']['fresh_all']
                rows.append({**{k:v for k,v in row.items() if k!='outcomes'},'counts':counts})
            summaries.append(dict(worker=worker['worker'],observed_functions=len(selected),comparisons=rows))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,commands=1,workers=summaries,
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            outputs={str(p.relative_to(ROOT)):sha(p) for p in [raw/'input.json',raw/'report.json']},
            original_project_guest_commands=0,executable_code_publications=0,production_cache_admission=False,
            performance_measurement=False,diagnostic_intervals=True,scope=report['scope'],scalar_admission=report['scalar_admission']))
        print(json.dumps(summaries,sort_keys=True),flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
