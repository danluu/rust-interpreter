"""Census saved typed inputs; compile only the offline diagnostic and its controls."""
import hashlib,json,os,shutil,statistics,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from analyze import compare
RUN='native-reuse-inputs-02'
SOURCE='fca687ebac0ea9374a1426addd01169fe707f608'
TEST='crates/bytecode/tests/native_reuse_inputs.rs'
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
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
            h=sha(path)
            if expected is not None:assert h==expected,path
            key=str(path.relative_to(ROOT));assert key not in frozen or frozen[key]==h
            frozen[key]=h
            return read(path) if path.suffix=='.json' else h
        cost_path=ROOT/'results/jit-preparation-costs-02/summary.json'
        closed=bind(cost_path.with_name('closure.json'));cost=bind(cost_path,closed['summary_sha256'])
        assert closed['status']=='closed' and closed['all_hashes_verified']
        assert cost['status']=='passed' and cost['controls']==7 and cost['retained_edited_receipts']==95
        assert cost['adopted_tool_key']==BASELINE
        bind(ROOT/closed['evidence'],closed['evidence_sha256'])
        changed=subprocess.check_output(['git','diff','--name-only',SOURCE,'--','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()
        assert changed==[TEST],changed
        histories=[];unique={};input_bytes=0
        for case in cost['cases']:
            path=ROOT/case['history'];summary=bind(path,case['history_sha256'])
            assert summary['status']=='passed' and summary['source_restored'] and summary['tool_keys']['baseline']==BASELINE
            raw=ROOT/summary['raw'];rh=summary.get('evidence') or {k:summary[k+'_sha256'] for k in ['plan','records']}
            bind(raw/'plan.json',rh['plan']);rows=bind(raw/'records.json',rh['records'])
            assert len(rows)==summary['commands']
            selected=[r for r in rows if r['mode']=='baseline'];cycles=1 if case['case']=='token-recent' else 3
            expected=[(c,s) for c in range(cycles) for s in [0,-1,1,2,3,4,5]]+[(cycles,0)]
            assert [(r['cycle'],r['state']) for r in selected]==expected
            steps=[]
            for row in selected:
                assert (row['returncode']==0)==(row['state']!=-1)
                assert row['launch']['tool_key']==BASELINE and row['launch']['isolated_batch']=='prepared'
                artifact=row['artifact'];payload=ROOT/artifact['path'];h=artifact['sha256']
                assert payload.is_relative_to(ROOT/'.work') and payload.stat().st_size<=128*1024**2
                if str(payload.relative_to(ROOT)) not in frozen:bind(payload,h)
                else:assert frozen[str(payload.relative_to(ROOT))]==h
                if h not in unique:
                    unique[h]=str(payload);input_bytes+=payload.stat().st_size
                steps.append(dict(cycle=row['cycle'],state=row['state'],source_sha256=row['source_sha256'],artifact_sha256=h))
            histories.append(dict(case=case['case'],history=case['history'],history_sha256=case['history_sha256'],steps=steps))
        assert 0<len(unique)<=128 and input_bytes<=4*1024**3
        for name in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines():bind(ROOT/name)
        for path in Path(__file__).parent.iterdir():
            if path.suffix in ['.py','.md']:bind(path)
        for name in ['compare_saved_runtime.py','workflow_io.py']:bind(ROOT/'scripts'/name)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'artifacts.json',dict(artifacts=[dict(sha256=h,path=p) for h,p in sorted(unique.items())]))
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,histories=histories,
            controller_command=[sys.executable,*sys.orig_argv[1:]],artifacts_sha256=sha(raw/'artifacts.json'),
            unique_artifacts=len(unique),total_artifact_bytes=input_bytes,expected_commands=4,
            required_free_bytes=needed,allocated_target_bytes=allocated,minimum_child_gib=8,
            rust_controls_per_profile=7,python_controls=4,guest_commands=0,original_project_build_commands=0,
            host_cargo_commands=3,executable_code_publications=0,production_runtime_changes=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','NATIVE_REUSE_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        cargo=['cargo','+nightly-2026-09-08','test','--locked','--offline','--jobs','2',
            '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode','--test','native_reuse_inputs']
        commands=[('python',[sys.executable,'-m','unittest','test_analyze','-v'],{},Path(__file__).parent),
            ('debug',cargo,{},ROOT),('release',[*cargo,'--release'],{},ROOT),
            ('typed',[*cargo,'--release','observe_saved_native_reuse_inputs','--','--ignored','--exact'],
                dict(NATIVE_REUSE_MANIFEST=str(raw/'artifacts.json'),NATIVE_REUSE_OUTPUT=str(raw/'typed')),ROOT)]
        records=[]
        for label,command,extra,cwd in commands:
            require_space(ROOT,8)
            if label!='python':assert shutil.disk_usage(ROOT).free>=needed
            started=time.time()
            child,out,err=capture(command,cwd=cwd,env=env|extra,receipt_path=raw/'active.json',receipt=dict(stage=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,extra_env=extra,pid=child.pid,returncode=child.returncode,
                seconds=time.time()-started,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
            if label=='python':assert 'Ran 4 tests' in err and err.rstrip().endswith('OK')
            else:
                count=1 if label=='typed' else 7;ignored=0 if label=='typed' else 1
                assert f'test result: ok. {count} passed; 0 failed; {ignored} ignored;' in out,out[-3000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,'passed',flush=True)
        typed=read(raw/'typed/summary.json');assert typed['status']=='passed'
        assert typed['new_guest_commands']==typed['executable_code_publications']==typed['production_runtime_changes']==0
        reports={r['artifact_sha256']:r for r in typed['reports']};assert set(reports)==set(unique)
        outputs={str((raw/'typed/summary.json').relative_to(ROOT)):sha(raw/'typed/summary.json')}
        for row in reports.values():
            path=Path(row['path']);assert path.parent==raw/'typed' and sha(path)==row['sha256']
            outputs[str(path.relative_to(ROOT))]=row['sha256']
        cases=[]
        for history in histories:
            before=None;transitions=[]
            for step in history['steps']:
                now=read(Path(reports[step['artifact_sha256']]['path']))
                if before is not None:transitions.append(dict(cycle=step['cycle'],state=step['state'],**compare(before,now)))
                before=now
            edited=[r for r in transitions if r['state'] in range(1,6)]
            cases.append(dict(case=history['case'],history=history['history'],transitions=transitions,
                valid_edit_transitions=len(edited),namespace_invalidating_valid_edits=sum(not r['namespace_same'] for r in edited),
                median_same_body_fraction=statistics.median(r['same_body_at_same_id']/r['functions'] for r in edited),
                median_same_necessary_input_fraction=statistics.median(r['same_necessary_inputs']/r['functions'] for r in edited),
                median_same_necessary_input_operation_fraction=statistics.median(r['same_necessary_input_operations']/r['operations'] for r in edited)))
        assert sum(c['valid_edit_transitions'] for c in cases)==95
        assert sum(len(c['transitions']) for c in cases)==133
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,cases=cases,unique_artifacts=len(unique),
            typed_functions=typed['total_functions'],total_artifact_bytes=input_bytes,typed_output_bytes=typed['output_bytes'],
            rust_controls_per_profile=7,python_controls=4,commands=4,guest_commands=0,original_project_build_commands=0,
            executable_code_publications=0,production_runtime_changes=0,private_details_redacted=True,performance_measurement=False,
            scope='Unweighted necessary-input identity across exported functions; not executed/native cache hits, hot coverage, or performance.',
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            artifacts_sha256=sha(raw/'artifacts.json'),outputs=outputs))
        print('PASS133 chronological transitions including95valid edits; zero guest execution',flush=True)


def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
        plan=read(raw/'plan.json');terminal=read(outer/'status.json');records=read(raw/'records.json')
        assert terminal['status']=='finished' and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
        assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert sha(raw/'artifacts.json')==plan['artifacts_sha256']
        bindings={};evidence={}
        for p,h in plan['frozen'].items():
            assert sha(ROOT/p)==h
            if p.startswith(('.work/','results/')):evidence[p]=h
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h;bindings[p]=dict(revision=plan['source_revision'],sha256=h)
        for r in records:
            for stream in ['stdout','stderr']:
                path=raw/(r['label']+'.'+stream);assert sha(path)==r[stream+'_sha256'];evidence[str(path.relative_to(ROOT))]=sha(path)
        out.mkdir(exist_ok=True);assert not (out/'closure.json').exists()
        if terminal['returncode']==0:
            summary=read(out/'summary.json');assert summary['status']=='passed' and len(records)==4
            assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
            for p,h in summary['outputs'].items():assert sha(ROOT/p)==h;evidence[p]=h
        else:
            assert not (out/'summary.json').exists()
            write(out/'summary.json',dict(status='failed',source_revision=plan['source_revision'],commands=len(records),
                returncodes=[r['returncode'] for r in records],raw=str(raw.relative_to(ROOT)),
                plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),guest_commands=0,performance_measurement=False))
            if (raw/'typed').exists():
                for p in (raw/'typed').glob('*.json'):evidence[str(p.relative_to(ROOT))]=sha(p)
        for p in [raw/'plan.json',raw/'records.json',raw/'artifacts.json',outer/'status.json',outer/'plan.json',outer/'command.log']:
            evidence[str(p.relative_to(ROOT))]=sha(p)
        write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,source_files=len(bindings),frozen_inputs=len(plan['frozen']),
            evidence_files=len(evidence),summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
            guest_commands=0,performance_measurement=False))
        print('Closed',RUN,'terminal',terminal['returncode'],flush=True)


if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:
        assert len(sys.argv)==1
        main()
