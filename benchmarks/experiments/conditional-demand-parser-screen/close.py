"""Close a complete matched parser history, including any failed timing gate."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(Path(__file__).parent))
from benchmark import ratios,schedule,screen_states,validate_demand_outcome,custom_command
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from probe import fingerprint,native_inventory
from states import source_states,native_outcomes
from suite_reports import read_report,validate_report

def main():
    profile='incremental';name=sys.argv[1]
    import re
    assert re.fullmatch(r'conditional-demand-parser-screen-incremental-\d{2}',name)
    raw=ROOT/'.work'/name;out=ROOT/'results'/name;outer=ROOT/'.work/experiments'/name
    s=json.loads((out/'summary.json').read_text());t=json.loads((outer/'status.json').read_text());plan=json.loads((raw/'plan.json').read_text());rows=json.loads((raw/'records.json').read_text())
    assert s['status']=='passed' and s['commands']==len(rows)==40 and s['original_tests']==114
    assert s['source_restored'] and s['candidate_control_artifacts_match'] and s['exact_native_test_outcomes']
    assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
    assert sha(outer/'command.log')==t['log_sha256'] and sha(outer/'plan.json')==t['plan_sha256']
    for key in ['plan','records','space']:assert sha(raw/(key+'.json'))==s[key+'_sha256']
    assert ratios(rows)==s['measurement'];bindings={};evidence={}
    spaces=json.loads((raw/'space.json').read_text());assert len(spaces)==80
    assert [(r['index'],r['phase']) for r in spaces]==[(i,p) for i in range(40) for p in ['before','after']]
    assert all(r['free_bytes']>=8*1024**3 for r in spaces if r['phase']=='before')
    for path,h in plan['frozen'].items():
        assert fingerprint(ROOT/path)==h,path
        if path.startswith(('.work/','results/')):bindings[path]=dict(kind='retained',fingerprint=h)
        else:
            assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_commit']+':'+path])).hexdigest()==h['sha256']
            bindings[path]=dict(kind='git',revision=plan['source_commit'],fingerprint=h)
    source=ROOT/'.work/sources/pgrust';changed=source/'crates/backend/parser/gram_core/src/parse.rs'
    assert sha(changed)==plan['original_source_sha256'] and schedule(screen_states(changed.read_bytes()))==plan['schedule']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
    names=native_inventory((ROOT/'.work/pgrust-parser-support-01/native.stdout').read_text());assert len(names)==114
    for row,planned in zip(rows,plan['schedule']):
        assert {k:row[k] for k in planned}==planned
        for stream in ['stdout','stderr']:
            p=raw/f"{row['index']}.{stream}";assert sha(p)==row[stream+'_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
        success=row['state']!=-1
        if row['mode']=='native':assert row['outcomes']==[list(x) for x in native_outcomes((raw/f"{row['index']}.stdout").read_text(),names,success)]
        else:
            suite,digest=read_report(raw/f"{row['index']}-suite.json",row['suite_sha256'])
            assert row['outcomes']==[list(x) for x in validate_report(suite,names,'prepared',success)]
            assert ('--jit-scalar-calls' in row['command'])==(row['mode']!='anchor')
            assert ('--jit-demand-regions-if-large' in row['command'])==(row['mode']=='candidate')
            assert '--jit-demand-regions' not in row['command']
            for test in suite['tests']:validate_demand_outcome(test,row['mode'])
            evidence[str((raw/f"{row['index']}-suite.json").relative_to(ROOT))]=digest
        for kind in ['artifact','entry_catalog','executable']:
            if kind in row:
                item=row[kind];assert sha(ROOT/item['path'])==item['sha256'];evidence[item['path']]=item['sha256']
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
        acquire_lock(lock,45);main()
