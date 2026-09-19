"""Independently verify the complete public history, including a failed timing gate."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from benchmark import CASE_INPUTS,case_states,native_outcomes
from accounting import MODES,CUSTOM,SESSION_MODES,schedule,ratios
from commands import command,validate_options
from workflow_cases import WORKFLOWS,WORKFLOW_VARIANTS
from test_discovery import read_listing,read_selection
from suite_reports import read_report,validate_report,validate_runtime_limits
from screen import native_executable

def read(p):return json.loads(p.read_text())
def main():
    name=sys.argv[1];assert name in ['compact-native-switch-screen-'+case+'-01' for case in CASE_INPUTS]
    raw=ROOT/'.work'/name;out=ROOT/'results'/name;outer=ROOT/'.work/experiments'/name
    summary=read(out/'summary.json');plan=read(raw/'plan.json');records=read(raw/'records.json');terminal=read(outer/'status.json')
    assert summary['status']=='passed' and summary['commands']==len(records)==40
    assert summary['source_restored'] and summary['original_assertions_unchanged'] and summary['exact_native_test_outcomes'] and summary['candidate_control_artifacts_match']
    assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['command'][1:]==plan['controller_command'][1:]
    assert Path(terminal['command'][0]).resolve()==Path(plan['controller_command'][0]).resolve()
    assert sha(outer/'command.log')==terminal['log_sha256'] and sha(outer/'plan.json')==terminal['plan_sha256']
    for field in ['plan','records','strict','sessions','space']:assert sha(raw/(field+'.json'))==summary[field+'_sha256']
    case_name=plan['case_name'];assert name=='compact-native-switch-screen-'+case_name+'-01'
    project,variant,pattern,reference_name=CASE_INPUTS[case_name]
    case=WORKFLOWS[project] if variant is None else WORKFLOW_VARIANTS[project,variant]
    source=ROOT/'.work/sources'/project;changed=source/case['file'];original=changed.read_bytes()
    assert plan['case']==case and plan['source']==str(source.relative_to(ROOT)) and plan['project']==project and plan['pattern']==pattern
    assert plan['reference']==read(ROOT/'results'/reference_name/'summary.json')
    assert sha(changed)==plan['original_source_sha256'] and schedule(case_states(original,case))==plan['schedule']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    owner=read(source/'.rust-interp-owned.json');assert owner['owner']==str(ROOT) and owner['revision']==plan['revision']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==plan['revision']
    listing,_=read_listing(ROOT/'.work/test-discovery-real-01'/(project+'-tests.json'))
    names=[t['name'] for t in listing['tests'] if pattern in t['name'] and not t['ignored']]
    assert names==plan['names'] and len(names)==summary['original_tests']
    assert plan['native_threads']==plan['prepared_workers']==plan['cargo_jobs']==2
    assert plan['initial_minimum_gib']==(16 if project=='fre' else 12) and plan['minimum_child_gib']==8
    bindings={};evidence={}
    for path,h in plan['frozen'].items():
        assert sha(ROOT/path)==h,path
        if path.startswith(('.work/','results/')):bindings[path]=dict(kind='retained',sha256=h)
        else:
            data=subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==h,path
            bindings[path]=dict(kind='git',revision=plan['source_revision'],sha256=h)
    sessions=read(raw/'sessions.json');assert set(sessions)==set(SESSION_MODES)
    assert summary['measurement']==ratios(records,sessions,case_name)
    spaces=read(raw/'space.json');assert [(r['index'],r['phase']) for r in spaces]==[(i,phase) for i in range(40) for phase in ['before','after']]
    assert all(r['free_bytes']>=8*1024**3 for r in spaces if r['phase']=='before')
    endpoints={mode:ROOT/'.work/ts'/('compact-switch-primary-'+case_name+'-01-'+mode)/'ready.json' for mode in SESSION_MODES}
    builds={mode:dict(tool_key=key) for mode,key in plan['tool_keys'].items()}
    assert plan['tool_keys']==summary['tool_keys']
    previous=dict.fromkeys(MODES)
    for row,scheduled in zip(records,plan['schedule']):
        assert {k:row[k] for k in scheduled}==scheduled and row['index']==records.index(row)
        mode=row['mode'];success=row['state']!=-1
        assert row['previous_source_sha256']==previous[mode] and row['source_sha256']!=previous[mode];previous[mode]=row['source_sha256']
        assert row['command']==command(ROOT,source,case,plan['reference'],names,pattern,raw,row['index'],mode,builds,endpoints)
        assert row['returncode']==(0 if success else 1 if mode in CUSTOM else 101)
        for stream in ['stdout','stderr']:
            p=raw/(str(row['index'])+'.'+stream);assert sha(p)==row[stream+'_sha256']
        if mode in CUSTOM:
            launch,=[json.loads(line.split(': ',1)[1]) for line in (raw/(str(row['index'])+'.stderr')).read_text().splitlines() if line.startswith('rust-interp-launch: ')]
            assert launch==row['launch'] and validate_options(launch,row['command'],mode)
            suite,digest=read_report(raw/(str(row['index'])+'-suite.json'),row['suite_sha256'])
            assert digest==launch['suite_report_sha256'] and row['outcomes']==[list(x) for x in validate_report(suite,names,'prepared',success)]
            validate_runtime_limits(suite,plan['reference']['instruction_limit'],plan['reference']['allocation_limit'],required=True)
            assert suite['workers']==2 and launch['tool_key']==plan['tool_keys'][mode]
            assert row['artifact']['sha256']==launch['artifact_sha256'] and row['catalog']['sha256']==launch['entry_catalog_sha256']
            catalog=read(ROOT/row['catalog']['path']);assert [e['name'] for e in catalog['entries']]==names
            assert [e['function'] for e in catalog['entries']]==[t['function'] for t in suite['tests']]
            selection,h=read_selection(ROOT/row['selection']['path'],ROOT/row['artifact']['path'],pattern,False)
            assert h==launch['test_selection_sha256'] and selection['selected']==names
            if mode in SESSION_MODES:
                receipt=launch['template_session'];p=raw/(str(row['index'])+'-suite.json.session.json')
                assert sha(p)==receipt['receipt_sha256'] and all(receipt[k]==v for k,v in read(p).items())
                assert receipt['server_pid']==sessions[mode]['pid'] and receipt['server_executable_sha256']==sessions[mode]['executable_sha256']
                assert suite['selected']==suite['completed']==len(names) and suite['poisoned'] is False
                assert suite['jit_options']==dict(persistent_registers=True,scalar_calls=True,indirect_calls=True)
            else:assert suite['requested_workers']==2
        else:
            stdout=(raw/(str(row['index'])+'.stdout')).read_text()
            assert row['outcomes']==[list(x) for x in native_outcomes(stdout,names,success)]
            native_executable(stdout,source,raw/mode)
        for field in ['artifact','catalog','selection','executable']:
            if field in row:assert sha(ROOT/row[field]['path'])==row[field]['sha256']
    assert all(h==plan['original_source_sha256'] for h in previous.values())
    for offset in range(0,40,5):
        group=records[offset:offset+5];assert set(r['mode'] for r in group)==set(MODES)
        assert len({tuple(map(tuple,r['outcomes'])) for r in group })==1
        for field in ['artifact','catalog']:assert len({r[field]['sha256'] for r in group if r['mode'] in CUSTOM and r['mode']!='anchor'})==1
    strict=read(raw/'strict.json');assert [(r['label'],r['returncode'],r['next_session_request_id']) for r in strict]==[('type',101,1),('borrow',101,1)]
    for row in strict:
        label=row['label'];assert row['command']==command(ROOT,source,case,plan['reference'],names,pattern,raw,'strict-'+label,'candidate',builds,endpoints,name+':strict')
        for stream in ['stdout','stderr']:assert sha(raw/('strict-'+label+'.'+stream))==row[stream+'_sha256']
        err=(raw/('strict-'+label+'.stderr')).read_text();assert ('E0308' if label=='type' else 'E0499') in err and 'rust-interp-launch: ' not in err
        assert not (raw/('strict-'+label+'-suite.json')).exists()
    for mode,session in sessions.items():
        assert session['returncode']==0 and session['requests_consumed']==8 and session['error'] is None
        assert read(raw/mode/'terminal.json')==session
        assert session['cwd']==str(source) and Path(session['command'][session['command'].index('--serve-socket')+1])==endpoints[mode].parent
        for stream in ['stdout','stderr']:assert sha(raw/mode/stream)==session[stream+'_sha256']
        ready=read(raw/mode/'ready.json');assert ready['indirect_calls'] is True and ready['duration_order'] is True and ready['shared_literal_keys'] is False
        assert ready['executable_sha256']==session['executable_sha256'] and ready['pid']==session['pid']
        evidence[str(endpoints[mode].relative_to(ROOT))]=sha(endpoints[mode])
    for p in raw.rglob('*'):
        if p.is_file() and p.relative_to(raw).parts[0] not in ['native','native_lines','check']:
            assert not p.is_symlink();evidence[str(p.relative_to(ROOT))]=sha(p)
    for p in [outer/'status.json',outer/'plan.json',outer/'command.log']:evidence[str(p.relative_to(ROOT))]=sha(p)
    assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision=plan['source_revision'],all_hashes_verified=True,
        performance_gate_passed=summary['measurement']['gate_passed'],verdict=summary['measurement']['verdict'],adoption=False,
        frozen_inputs=len(bindings),evidence_files=len(evidence),bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),
        bindings_sha256=sha(raw/'closed-bindings.json'),evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),
        evidence_sha256=sha(raw/'closed-evidence.json'),summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print('Closed',case_name,'40 commands; verdict',summary['measurement']['verdict'],flush=True)
if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8);main()
