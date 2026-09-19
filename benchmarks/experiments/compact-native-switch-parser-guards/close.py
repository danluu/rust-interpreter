"""Close a complete matched parser history, including any failed timing gate."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(Path(__file__).parent))
from benchmark import ratios,schedule,full_states,validate_outcome,custom_command,validate_options
from accounting import SESSION_MODES
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from probe import fingerprint,native_inventory
from states import source_states,native_outcomes
from suite_reports import read_report,validate_report,validate_runtime_limits,validate_shared_templates

def main():
    name=sys.argv[1];profile=name.rsplit('-',2)[-2]
    import re
    assert profile in ['incremental','repository'] and name=='compact-native-switch-parser-'+profile+'-01'
    raw=ROOT/'.work'/name;out=ROOT/'results'/name;outer=ROOT/'.work/experiments'/name
    s=json.loads((out/'summary.json').read_text());t=json.loads((outer/'status.json').read_text());plan=json.loads((raw/'plan.json').read_text());rows=json.loads((raw/'records.json').read_text());sessions=json.loads((raw/'sessions.json').read_text());strict=json.loads((raw/'strict.json').read_text())
    assert s['status']=='passed' and s['commands']==len(rows)==110 and s['original_tests']==114
    assert s['source_restored'] and s['candidate_control_artifacts_match'] and s['exact_native_test_outcomes']
    assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
    assert sha(outer/'command.log')==t['log_sha256'] and sha(outer/'plan.json')==t['plan_sha256']
    for key in ['plan','records','space','sessions','strict']:assert sha(raw/(key+'.json'))==s[key+'_sha256']
    assert t['command'][1:]==plan['controller_command'][1:]
    assert Path(t['command'][0]).resolve()==Path(plan['controller_command'][0]).resolve()
    assert plan['native_threads']==plan['cargo_jobs']==plan['prepared_workers']==2
    assert plan['profile']==s['profile']==profile
    assert plan['cargo_incremental']==('1' if profile=='incremental' else 'project defaults')
    assert plan['initial_minimum_gib']==24 and plan['new_cache_allowance_gib']==16 and plan['minimum_child_gib']==8
    assert ratios(rows,sessions)==s['measurement'];bindings={};evidence={}
    spaces=json.loads((raw/'space.json').read_text());assert len(spaces)==220
    assert [(r['index'],r['phase']) for r in spaces]==[(i,p) for i in range(110) for p in ['before','after']]
    assert all(r['free_bytes']>=8*1024**3 for r in spaces if r['phase']=='before')
    for path,h in plan['frozen'].items():
        assert fingerprint(ROOT/path)==h,path
        if path.startswith(('.work/','results/')):bindings[path]=dict(kind='retained',fingerprint=h)
        else:
            assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_commit']+':'+path])).hexdigest()==h['sha256']
            bindings[path]=dict(kind='git',revision=plan['source_commit'],fingerprint=h)
    source=ROOT/'.work/sources/pgrust';changed=source/'crates/backend/parser/gram_core/src/parse.rs'
    assert sha(changed)==plan['original_source_sha256'] and schedule(full_states(changed.read_bytes()))==plan['schedule']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    names=native_inventory((ROOT/'.work/pgrust-parser-support-01/native.stdout').read_text());assert len(names)==114
    endpoints={mode:ROOT/'.work/ts'/('compact-switch-parser-'+profile+'-01-'+mode)/'ready.json' for mode in SESSION_MODES}
    previous=dict.fromkeys(['native','baseline','duplicate',*SESSION_MODES])
    for row,planned in zip(rows,plan['schedule']):
        assert {k:row[k] for k in planned}==planned
        for stream in ['stdout','stderr']:
            p=raw/f"{row['index']}.{stream}";assert sha(p)==row[stream+'_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
        mode=row['mode'];success=row['state']!=-1
        assert row['previous_source_sha256']==previous[mode] and row['source_sha256']!=previous[mode]
        previous[mode]=row['source_sha256']
        expected=plan['native_template'] if mode=='native' else custom_command(plan['custom_template'],plan['tool_keys'][mode],mode,raw,row['index'],endpoints)
        assert row['command']==expected and row['returncode']==(0 if success else 101 if mode=='native' else 1)
        if row['mode']=='native':assert row['outcomes']==[list(x) for x in native_outcomes((raw/f"{row['index']}.stdout").read_text(),names,success)]
        else:
            launch,=[json.loads(line.split(': ',1)[1]) for line in (raw/f"{row['index']}.stderr").read_text().splitlines() if line.startswith('rust-interp-launch: ')]
            assert launch==row['launch'] and launch['tool_key']==plan['tool_keys'][mode] and validate_options(launch,row['command'],mode)
            suite,digest=read_report(raw/f"{row['index']}-suite.json",row['suite_sha256'])
            assert row['outcomes']==[list(x) for x in validate_report(suite,names,'prepared',success)]
            assert digest==launch['suite_report_sha256']
            assert suite['workers']==2
            if mode in SESSION_MODES:assert suite['jit_options']==dict(persistent_registers=True,scalar_calls=True,indirect_calls=True)
            assert '--jit-scalar-calls' in row['command']
            assert '--jit-shared-templates' not in row['command']
            assert '--jit-demand-regions' not in row['command']
            validate_runtime_limits(suite,100000000000,150000,required=True)
            validate_shared_templates(suite,False)
            for test in suite['tests']:validate_outcome(test,row['mode'])
            evidence[str((raw/f"{row['index']}-suite.json").relative_to(ROOT))]=digest
        for kind in ['artifact','entry_catalog','executable']:
            if kind in row:
                item=row[kind];assert sha(ROOT/item['path'])==item['sha256'];evidence[item['path']]=item['sha256']
    assert all(h==plan['original_source_sha256'] for h in previous.values())
    for offset in range(0,110,5):
        group=rows[offset:offset+5]
        assert len({tuple(map(tuple,r['outcomes'])) for r in group})==1
        for field in ['artifact','entry_catalog']:assert len({r[field]['sha256'] for r in group if r['mode']!='native'})==1
    assert [(r['label'],r['returncode'],r['next_session_request_id']) for r in strict]==[('type',101,1),('borrow',101,1)]
    for record in strict:
        for stream in ['stdout','stderr']:
            p=raw/('strict-'+record['label']+'.'+stream);assert sha(p)==record[stream+'_sha256']
        assert record['command']==custom_command(plan['custom_template'],plan['tool_keys']['candidate'],'candidate',raw,'strict-'+record['label'],endpoints,name+':strict')
        err=(raw/('strict-'+record['label']+'.stderr')).read_text()
        assert ('E0308' if record['label']=='type' else 'E0499') in err and 'rust-interp-launch: ' not in err
        assert '--jit-indirect-calls' in record['command']
        assert not (raw/('strict-'+record['label']+'-suite.json')).exists()
    for mode in SESSION_MODES:
        session=sessions[mode];assert session['returncode']==0 and session['requests_consumed']==22 and session['error'] is None
        assert json.loads((raw/mode/'terminal.json').read_text())==session
        for stream in ['stdout','stderr']:assert sha(raw/mode/stream)==session[stream+'_sha256']
        endpoint=Path(session['command'][session['command'].index('--serve-socket')+1]);assert endpoint==endpoints[mode].parent
        ready=json.loads((endpoint/'ready.json').read_text())
        assert ready['pid']==session['pid'] and ready['executable_sha256']==session['executable_sha256']
        assert ready['indirect_calls'] is True and ready['duration_order'] is True
        assert ready['shared_literal_keys'] is False and ready['buffered_template_keys'] is False
        assert ready['parameterized_literals'] is True
        evidence[str((endpoint/'ready.json').relative_to(ROOT))]=sha(endpoint/'ready.json')
    for row in rows:
        if row['mode'] in SESSION_MODES:
            receipt=row['launch']['template_session'];p=raw/f"{row['index']}-suite.json.session.json"
            assert sha(p)==receipt['receipt_sha256']
            public=json.loads(p.read_text())
            assert all(receipt[k]==v for k,v in public.items())
            assert '--jit-template-session' in row['command']
    for p in raw.rglob('*'):
        if p.is_file() and p.relative_to(raw).parts[0]!='native':
            assert not p.is_symlink();evidence[str(p.relative_to(ROOT))]=sha(p)
    assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',performance_gate_passed=s['measurement']['gate_passed'],source_revision=plan['source_commit'],
        verdict=s['measurement']['verdict'],adoption=False,frozen_inputs=len(bindings),evidence_files=len(evidence),all_hashes_verified=True,
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print('Closed',profile,len(bindings),'frozen inputs;',len(evidence),'evidence files')
if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8);main()
