"""Close complete parser compatibility with historical source and artifact bindings."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/pgrust-parser-probe'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
from probe import fingerprint
from suite_reports import read_report,validate_report

def main():
    run='runtime-composition-parser-01';revision=sys.argv[1]
    out=ROOT/'results'/run;raw=ROOT/'.work'/run;outer=ROOT/'.work/experiments'/run
    s=json.loads((out/'summary.json').read_text());t=json.loads((outer/'status.json').read_text());p=json.loads((raw/'plan.json').read_text())
    assert s['status']=='passed' and s['commands']==1 and s['custom_tests_passed']==s['native_tests_reused']==114
    assert s['source_unchanged'] and s['original_assertions_match']
    assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
    assert sha(outer/'command.log')==t['log_sha256'] and sha(outer/'plan.json')==t['plan_sha256']
    for key in ['plan','records']:assert sha(raw/(key+'.json'))==s[key+'_sha256']
    bindings={}
    for path,digest in p['frozen'].items():
        assert fingerprint(ROOT/path)==digest,path
        if path.startswith(('.work/','results/')):bindings[path]=dict(kind='retained',fingerprint=digest)
        else:
            assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+path])).hexdigest()==digest['sha256']
            bindings[path]=dict(kind='git',revision=revision,fingerprint=digest)
    record,=json.loads((raw/'records.json').read_text());assert record['returncode']==0 and all(flag in record['command'] for flag in ['--jit-scalar-calls','--jit-indirect-calls'])
    for stream in ['stdout','stderr']:assert sha(raw/stream)==record[stream+'_sha256']
    suite,_=read_report(raw/'suite.json',s['suite_sha256']);catalog=json.loads((ROOT/s['artifacts']['entry_catalog']['path']).read_text());names=[e['name'] for e in catalog['entries']]
    assert len(validate_report(suite,names,'prepared',True))==114
    assert not (out/'closure.json').exists();write(raw/'bindings.json',bindings);(out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision=revision,frozen_inputs=len(bindings),all_hashes_verified=True,
        bindings=str((raw/'bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'bindings.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),performance_measurement=False))
    print('Closed 114 parser tests and',len(bindings),'frozen inputs')
if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);main()
