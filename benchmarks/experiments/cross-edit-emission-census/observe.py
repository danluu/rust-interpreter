"""Read all saved parser edits after model qualification; never execute a guest."""
import json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='cross-edit-emission-census-01'
def read(p):return json.loads(p.read_text())

with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45)
    target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
    allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
    needed=max(14*1024**3,8*1024**3+2*allocated)
    assert shutil.disk_usage(ROOT).free>=needed
    frozen={}
    def bind(path,digest=None):
        actual=sha(path)
        if digest is not None:assert actual==digest,path
        frozen[str(path.relative_to(ROOT))]=actual
        return read(path) if path.suffix=='.json' else actual
    model=ROOT/'results/cross-edit-emission-model-01'
    closed=bind(model/'closure.json');assert closed['status']=='closed' and closed['all_hashes_verified']
    qualified=bind(model/'summary.json',closed['summary_sha256'])
    assert qualified['status']=='passed' and qualified['tests_per_profile']==7
    bind(model/'terminal.json',closed['terminal_sha256'])
    model_plan=bind(ROOT/qualified['raw']/'plan.json',qualified['plan_sha256'])
    for p,h in model_plan['frozen'].items():
        if p.startswith('crates/') or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/p,h)
    folder=ROOT/'results/emitter-register-workspace-parser-screen-incremental-01'
    closed=bind(folder/'closure.json');assert closed['status']=='closed' and closed['all_hashes_verified']
    history=bind(folder/'summary.json',closed['summary_sha256'])
    bind(folder/'terminal.json',closed['terminal_sha256'])
    assert history['commands']==32 and history['source_restored'] and history['candidate_control_artifacts_match']
    original=ROOT/history['raw'];bind(original/'plan.json',history['plan_sha256'])
    records=bind(original/'records.json',history['records_sha256'])
    rows=[r for r in records if r['mode']=='baseline']
    assert [(r['cycle'],r['state']) for r in rows]==[(0,s) for s in [0,-1,1,2,3,4,5]]+[(1,0)]
    inputs=[];previous=None
    for row in rows:
        assert row['launch']['tool_key']==history['tool_keys']['baseline']
        assert row['launch']['borrowck_cache']=='off'
        assert row['returncode']==(1 if row['state']==-1 else 0)
        assert row['previous_source_sha256']==previous and row['source_sha256']!=previous
        previous=row['source_sha256']
        for key in ['artifact','entry_catalog']:
            item=row[key];bind(ROOT/item['path'],item['sha256'])
        item=row['artifact']
        inputs.append(dict(path=str(ROOT/item['path']),sha256=item['sha256'],state=row['state']))
    assert inputs[0]['sha256']==inputs[-1]['sha256']
    for path in Path(__file__).parent.iterdir():
        if path.suffix in ['.py','.md']:bind(path)
    for name in ['compare_saved_runtime.py','workflow_io.py']:bind(ROOT/'scripts'/name)
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'inputs.json',inputs)
    write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
        controller_command=[sys.executable,*sys.orig_argv[1:]],inputs_sha256=sha(raw/'inputs.json'),
        required_free_bytes=needed,allocated_target_bytes=allocated,artifact_states=8,comparisons=7,
        original_project_guest_commands=0,executable_code_publications=0,cache_admission=False))
    env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
        and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
    assert not any(k.startswith('DYLD_') for k in env)
    env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
        CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',
        RUST_INTERP_CROSS_EDIT_INPUTS=str(raw/'inputs.json'),RUST_INTERP_CROSS_EDIT_OUTPUT=str(raw/'report.json'))
    command=['cargo','+nightly-2026-09-08','test','--release','--locked','--offline','--jobs','2',
        '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode',
        '--lib','cross_edit_census::cross_edit_observe_saved_artifact_sequence','--','--ignored','--exact']
    require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
    started=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label='observe'))
    (raw/'observe.stdout').write_text(out);(raw/'observe.stderr').write_text(err)
    write(raw/'records.json',[dict(label='observe',command=command,pid=child.pid,returncode=child.returncode,
        seconds=time.time()-started,stdout_sha256=sha(raw/'observe.stdout'),stderr_sha256=sha(raw/'observe.stderr'))])
    assert child.returncode==0 and 'test result: ok. 1 passed; 0 failed; 0 ignored;' in out,(out+err)[-5000:]
    report=read(raw/'report.json');assert report['guest_commands']==report['executable_code_publications']==0
    assert report['cache_admission'] is False and len(report['comparisons'])==7
    summaries=[]
    fields=['same_function_at_same_id','same_function_and_direct_callees','same_closed_direct_call_graph','global_context_and_graph_equal']
    for index,row in enumerate(report['comparisons']):
        assert row['previous_artifact_sha256']==inputs[index]['sha256'] and row['artifact_sha256']==inputs[index+1]['sha256']
        assert row['previous_state']==inputs[index]['state'] and row['state']==inputs[index+1]['state']
        functions=row['functions'];assert len(functions)==row['current_functions']
        assert [f['function'] for f in functions]==list(range(len(functions)))
        assert sum(f['operations'] for f in functions)==row['current_operations']
        for f in functions:
            assert all(type(f[k]) is bool for k in fields)
            assert f[fields[2]]<=f[fields[1]]<=f[fields[0]]
            assert f[fields[3]]==(f[fields[2]] and row['global_context_equal'])
        for key in fields:
            assert row[key]==dict(functions=sum(f[key] for f in functions),operations=sum(f['operations'] for f in functions if f[key]))
        summaries.append({k:v for k,v in row.items() if k!='functions'})
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
    outputs={str((raw/n).relative_to(ROOT)):sha(raw/n) for n in ['report.json','inputs.json']}
    write(output/'summary.json',dict(status='passed',source_revision=revision,commands=1,comparisons=summaries,
        artifact_states=8,original_project_guest_commands=0,executable_code_publications=0,cache_admission=False,
        performance_measurement=False,raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),
        records_sha256=sha(raw/'records.json'),outputs=outputs))
    for row in summaries:print(json.dumps(row,sort_keys=True),flush=True)
