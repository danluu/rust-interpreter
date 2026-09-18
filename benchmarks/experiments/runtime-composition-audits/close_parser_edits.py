"""Close a complete matched parser history, including any failed timing gate."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/runtime-composition-parser-edits'))
from benchmark import ratios,schedule
from prerequisites import validate_runtime_options
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from probe import fingerprint,native_inventory
from states import source_states,native_outcomes
from suite_reports import read_report,validate_report

def main(profile):
    assert profile in ['incremental','repository']
    name='runtime-composition-parser-edits-'+profile+'-01';raw=ROOT/'.work'/name;out=ROOT/'results'/name;outer=ROOT/'.work/experiments'/name
    s=json.loads((out/'summary.json').read_text());t=json.loads((outer/'status.json').read_text());plan=json.loads((raw/'plan.json').read_text());rows=json.loads((raw/'records.json').read_text())
    assert s['status']=='passed' and s['commands']==len(rows)==88 and s['original_tests']==114
    assert s['source_restored'] and s['candidate_control_artifacts_match'] and s['exact_native_test_outcomes']
    assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
    assert sha(outer/'command.log')==t['log_sha256'] and sha(outer/'plan.json')==t['plan_sha256']
    for key in ['plan','records']:assert sha(raw/(key+'.json'))==s[key+'_sha256']
    assert ratios(rows)==s['measurement'];bindings={};evidence={}
    for path,h in plan['frozen'].items():
        assert fingerprint(ROOT/path)==h,path
        if path.startswith(('.work/','results/')):bindings[path]=dict(kind='retained',fingerprint=h)
        else:
            assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_commit']+':'+path])).hexdigest()==h['sha256']
            bindings[path]=dict(kind='git',revision=plan['source_commit'],fingerprint=h)
    source=ROOT/'.work/sources/pgrust';changed=source/'crates/backend/parser/gram_core/src/parse.rs'
    assert sha(changed)==plan['original_source_sha256'] and schedule(source_states(changed.read_bytes()))==plan['schedule']
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
            assert validate_runtime_options(row['launch'],row['command'],row['mode'])
            evidence[str((raw/f"{row['index']}-suite.json").relative_to(ROOT))]=digest
        for kind in ['artifact','entry_catalog','executable']:
            if kind in row:
                item=row[kind];assert sha(ROOT/item['path'])==item['sha256'];evidence[item['path']]=item['sha256']
    assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',performance_gate_passed=s['measurement']['gate_passed'],source_revision=plan['source_commit'],
        frozen_inputs=len(bindings),evidence_files=len(evidence),all_hashes_verified=True,
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print('Closed',profile,len(bindings),'frozen inputs;',len(evidence),'evidence files')
if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);main(sys.argv[1])
