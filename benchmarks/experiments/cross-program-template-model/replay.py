"""Check modeled template reuse on all retained parser artifact transitions."""
import importlib.util,json,os,shutil,subprocess,sys,time
from pathlib import Path
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='cross-program-template-replay-01'
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
        model=closed('cross-program-template-model-02');assert model['status']=='passed' and model['tests_per_profile']==12
        anchor=closed('cross-edit-emission-anchors-02');assert anchor['status']=='passed'
        raw_anchor=ROOT/anchor['raw'];anchor_plan=bind(raw_anchor/'plan.json',anchor['plan_sha256'])
        bind(raw_anchor/'records.json',anchor['records_sha256'])
        for p,h in anchor['outputs'].items():bind(ROOT/p,h)
        artifacts=read(raw_anchor/'inputs.json');assert sha(raw_anchor/'inputs.json')==anchor_plan['inputs_sha256']
        assert [a['state'] for a in artifacts]==[0,-1,1,2,3,4,5,0]
        for a in artifacts:bind(Path(a['path']),a['sha256'])
        original=read(raw_anchor/'report.json')['original_functions']
        assert [f['function'] for f in original]==list(range(len(original)))
        weighted=closed('cross-edit-emission-weight-01');assert weighted['status']=='passed'
        prior=closed('preparation-phase-workloads-refined-01');assert prior['status']=='passed'
        raw_prior=ROOT/prior['raw'];prior_plan=bind(raw_prior/'plan.json',prior['plan_sha256'])
        records=bind(raw_prior/'records.json',prior['records_sha256'])
        record,=[r for r in records if r['label']=='pgrust-parser-original']
        assert record['returncode']==0 and sha(Path(record['command'][-1]))==artifacts[0]['sha256']
        path=raw_prior/'pgrust-parser-original.json';profile=bind(path,prior['outputs'][str(path.relative_to(ROOT))])
        validator=ROOT/'benchmarks/experiments/preparation-phase-workloads/refined.py'
        bind(validator,prior_plan['frozen'][str(validator.relative_to(ROOT))])
        spec=importlib.util.spec_from_file_location('retained_template_trace_validator',validator)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        assert module.validate_observations(profile)==prior['observations'][0]['workers']
        workers=[];phase_by_worker={}
        for worker in profile['preparation_observations']['workers']:
            selected=[]
            for f in worker['observation']['functions']:
                old=original[f['function']]
                assert old['name']==f['name'] and old['operations']==f['bytecode_operations']
                if f['ordinary_native_entries']>0:selected.append(old)
            selected.sort(key=lambda f:f['function']);assert len(selected)==len({f['function'] for f in selected})
            workers.append(dict(worker=worker['worker'],functions=selected))
            phase_by_worker[worker['worker']]={fid:m['nanos'] for fid,phase,m in worker['observation']['trace']['rows'] if phase=='ordinary_emission'}
        assert [w['worker'] for w in workers]==[0,1]
        for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines():bind(ROOT/p)
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md']:bind(p)
        for name in ['compare_saved_runtime.py','workflow_io.py','suite_reports.py','native_suite.py']:bind(ROOT/'scripts'/name)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'input.json',dict(artifacts=artifacts,workers=workers))
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
            '--lib','jit::cross_program_templates::replay::cross_program_template_replay_saved_parser_edits','--','--ignored','--exact']
        require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed;write(raw/'records.json',[])
        started=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label='replay'))
        (raw/'replay.stdout').write_text(out);(raw/'replay.stderr').write_text(err)
        write(raw/'records.json',[dict(label='replay',command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-started,
            stdout_sha256=sha(raw/'replay.stdout'),stderr_sha256=sha(raw/'replay.stderr'))])
        assert child.returncode==0 and 'test result: ok. 1 passed; 0 failed; 0 ignored;' in out,(out+err)[-6000:]
        report=read(raw/'report.json');assert report['schema_version']==1 and report['input_sha256']==sha(raw/'input.json')
        assert report['original_project_guest_commands']==report['executable_code_publications']==0
        assert report['production_cache_admission'] is False and len(report['workers'])==2
        summaries=[]
        for source,worker in zip(workers,report['workers']):
            assert worker['worker']==source['worker'] and worker['observed_functions']==len(source['functions'])
            assert worker['retained_charge']<=64*1024**2 and len(worker['comparisons'])==7
            selected={f['function'] for f in source['functions']};declined=[fid for fid,why in worker['declines']]
            assert len(declined)==len(set(declined)) and set(declined)<=selected
            assert worker['templates']+len(declined)==len(selected)
            rows=[]
            for ordinal,row in enumerate(worker['comparisons'],1):
                assert row['ordinal']==ordinal and row['state']==artifacts[ordinal]['state'] and row['artifact_sha256']==artifacts[ordinal]['sha256']
                outcomes=dict(row['outcomes']);assert len(outcomes)==len(row['outcomes'])==worker['templates']
                assert set(outcomes)==selected-set(declined) and set(outcomes.values())<={'key_miss','restore_miss','exact'}
                counts={s:sum(v==s for v in outcomes.values()) for s in ['key_miss','restore_miss','exact']};assert counts['exact']>0
                phases=phase_by_worker[worker['worker']]
                rows.append(dict(ordinal=ordinal,state=row['state'],artifact_sha256=row['artifact_sha256'],counts=counts,
                    exact_original_ordinary_emission_ns=sum(phases.get(fid,0) for fid,status in outcomes.items() if status=='exact'),
                    diagnostic_ns=row['diagnostic_ns'],exact_words=row['exact_words'],scalar_entries=row['scalar_entries']))
            summaries.append({**{k:v for k,v in worker.items() if k!='comparisons'},'comparisons':rows})
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
        focus.RUN=RUN
        # Extend the shared terminal/source closure with replay outputs, which
        # are bound by the summary and copied into its retained evidence table.
        focus.close()
    else:
        assert len(sys.argv)==1
        main()
