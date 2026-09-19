"""Refine saved input scope and bind the original published token code pools."""
import hashlib,json,os,statistics,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from scope import compare,native_pool,anchored_pool
RUN='native-reuse-scope-01'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen={}
        def bind(path,expected=None):
            h=sha(path)
            if expected is not None:assert h==expected,path
            key=str(path.relative_to(ROOT));assert key not in frozen or frozen[key]==h;frozen[key]=h
            return read(path) if path.suffix=='.json' else h
        prior=ROOT/'results/native-reuse-inputs-02'
        closure=bind(prior/'closure.json');assert closure['status']=='closed' and closure['all_hashes_verified']
        inputs=bind(prior/'summary.json',closure['summary_sha256']);assert inputs['status']=='passed'
        bind(ROOT/closure['evidence'],closure['evidence_sha256'])
        input_plan=bind(ROOT/inputs['raw']/'plan.json',inputs['plan_sha256'])
        for p,h in inputs['outputs'].items():bind(ROOT/p,h)
        typed=read(ROOT/inputs['raw']/'typed/summary.json')
        reports={r['artifact_sha256']:r for r in typed['reports']};assert len(reports)==54
        histories=input_plan['histories'];assert len(histories)==7
        native=ROOT/'results/adopted-current-runtime-sampling-02'
        closed=bind(native/'closure.json');assert closed['status']=='closed' and closed['all_hashes_verified']
        sample=bind(native/'summary.json',closed['summary_sha256']);assert sample['status']=='passed'
        bind(ROOT/closed['evidence'],closed['evidence_sha256'])
        pools=[]
        for case in sample['cases']:
            attribution=bind(ROOT/case['report'],case['report_sha256'])
            assert attribution['status']=='passed' and attribution['reconstructed_same_process_code']
            directory=ROOT/'.work'/case['run_id']/'0'
            summary_path=ROOT/'results'/case['run_id']/'summary.json'
            history=bind(summary_path,attribution['evidence'][str(summary_path.relative_to(ROOT))])
            assert history['tool_key']==sample['tool_key'] and history['vm_sha256']==sample['vm_sha256']
            original=history['artifact_sha256'];assert original in reports
            record_path=directory/'record.json';record=bind(record_path,attribution['evidence'][str(record_path.relative_to(ROOT))])
            mapping=directory/'jit-code/map.json';code=directory/'jit-code/code.bin'
            bind(mapping,record['files']['jit-code/map.json']);bind(code,record['files']['jit-code/code.bin'])
            assert code.stat().st_size==read(mapping)['code_bytes']
            pools.append(dict(case=case['case'],artifact_sha256=original,mapping=str(mapping.relative_to(ROOT))))
        for name in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines():bind(ROOT/name)
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md']:bind(p)
        bind(Path(__file__).parent.parent/'native-reuse-inputs/analyze.py')
        for name in ['compare_saved_runtime.py','workflow_io.py']:bind(ROOT/'scripts'/name)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,histories=histories,pools=pools,
            controller_command=[sys.executable,*sys.orig_argv[1:]],guest_commands=0,build_commands=0,performance_measurement=False))
        require_space(ROOT,8);env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
        child,out,err=capture([sys.executable,'-m','unittest','test_scope','-v'],cwd=Path(__file__).parent,
            env=env,receipt_path=raw/'active.json',receipt=dict(stage='controls'))
        (raw/'controls.stdout').write_text(out);(raw/'controls.stderr').write_text(err)
        write(raw/'controls.json',dict(pid=child.pid,returncode=child.returncode,stdout_sha256=sha(raw/'controls.stdout'),stderr_sha256=sha(raw/'controls.stderr')))
        assert child.returncode==0 and 'Ran 5 tests' in err and err.rstrip().endswith('OK'),out+err
        print('Five scope/map controls passed',flush=True)
        cases=[]
        for history in histories:
            before=None;rows=[]
            for step in history['steps']:
                now=read(Path(reports[step['artifact_sha256']]['path']))
                if before is not None:rows.append(dict(cycle=step['cycle'],state=step['state'],**compare(before,now)))
                before=now
            edits=[r for r in rows if r['state'] in range(1,6)]
            cases.append(dict(case=history['case'],transitions=rows,valid_edits=len(edits),
                median_same_body_and_callees_fraction=statistics.median(r['same_body_and_direct_callees']/r['functions'] for r in edits),
                median_stable_scope_fraction=statistics.median(r['same_body_callees_heap_count']/r['functions'] for r in edits),
                median_stable_scope_operation_fraction=statistics.median(r['stable_scope_operations']/r['operations'] for r in edits),
                heap_mode_changes=sum(not r['heap_mode_same'] for r in edits),function_count_changes=sum(not r['function_count_same'] for r in edits)))
        anchored=[]
        for pool in pools:
            original=read(Path(reports[pool['artifact_sha256']]['path']))
            weights,kinds=native_pool(read(ROOT/pool['mapping']),original)
            for history in histories:
                if history['steps'][0]['artifact_sha256']!=pool['artifact_sha256']:continue
                rows=[]
                for step in history['steps'][1:]:
                    now=read(Path(reports[step['artifact_sha256']]['path']))
                    rows.append(dict(cycle=step['cycle'],state=step['state'],**anchored_pool(original,now,weights)))
                edits=[r for r in rows if r['state'] in range(1,6)]
                anchored.append(dict(pool_case=pool['case'],history_case=history['case'],original_bytes_by_kind=kinds,
                    comparisons=rows,valid_edits=len(edits),
                    median_original_bytes_with_stable_scope_fraction=statistics.median(r['original_bytes_with_stable_scope']/r['original_compiled_bytes'] for r in edits)))
        assert len(anchored)==4 and sum(c['valid_edits'] for c in cases)==95 and sum(len(c['transitions']) for c in cases)==133
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,cases=cases,anchored_original_pools=anchored,
            controls=5,new_guest_commands=0,build_commands=0,production_runtime_changes=0,performance_measurement=False,
            scope='Stable local/direct bodies with equal numeric IDs, heap mode and function count; ignores other global/emitter/cache inputs. Original pool weights are not edited-execution coverage or cache hits.',
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),controls_sha256=sha(raw/'controls.json')))
        print('PASS:133 scoped transitions and two original token pools; no guest or build',flush=True)

def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
        plan=read(raw/'plan.json');terminal=read(outer/'status.json');controls=read(raw/'controls.json')
        assert terminal['status']=='finished' and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
        bindings={};evidence={}
        for p,h in plan['frozen'].items():
            assert sha(ROOT/p)==h
            if p.startswith(('.work/','results/')):evidence[p]=h
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h;bindings[p]=dict(revision=plan['source_revision'],sha256=h)
        for stream in ['stdout','stderr']:assert sha(raw/('controls.'+stream))==controls[stream+'_sha256']
        out.mkdir(exist_ok=True);assert not (out/'closure.json').exists()
        if terminal['returncode']==0:
            summary=read(out/'summary.json');assert summary['status']=='passed' and controls['returncode']==0
            assert summary['plan_sha256']==sha(raw/'plan.json') and summary['controls_sha256']==sha(raw/'controls.json')
        else:
            assert not (out/'summary.json').exists()
            write(out/'summary.json',dict(status='observer-failed',source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),
                controls_returncode=controls['returncode'],plan_sha256=sha(raw/'plan.json'),new_guest_commands=0,build_commands=0,performance_measurement=False))
        for p in [raw/'plan.json',raw/'controls.json',raw/'controls.stdout',raw/'controls.stderr',outer/'status.json',outer/'plan.json',outer/'command.log']:
            evidence[str(p.relative_to(ROOT))]=sha(p)
        write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,source_files=len(bindings),frozen_inputs=len(plan['frozen']),
            evidence_files=len(evidence),summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),new_guest_commands=0))
        print('Closed scope observer; terminal',terminal['returncode'],flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:
        assert len(sys.argv)==1
        main()
