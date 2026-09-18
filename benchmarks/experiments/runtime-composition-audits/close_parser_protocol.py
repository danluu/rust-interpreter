"""Close the unchanged parser schedule and composed-runtime option controls."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

def read(p):return json.loads(p.read_text())
def main():
    revision=sys.argv[1];name='runtime-composition-parser-edits-protocol-01'
    raw=ROOT/'.work'/name;out=ROOT/'results'/name;outer=ROOT/'.work/experiments'/name
    summary=read(out/'summary.json');terminal=read(outer/'status.json')
    assert summary['status']=='passed' and summary['tests']==16 and summary['commands']==2 and summary['guest_commands']==0
    assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256']
    assert sha(raw/'inputs.json')==summary['inputs_sha256'] and sha(raw/'records.json')==summary['records_sha256']
    bindings={};artifacts={}
    for p,h in read(raw/'inputs.json').items():
        assert sha(ROOT/p)==h,p
        payload=subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT)
        assert hashlib.sha256(payload).hexdigest()==h,p
        bindings[p]=dict(kind='git',revision=revision,sha256=h)
    records=read(raw/'records.json');assert [(r['label'],r['tests']) for r in records]==[('matched',6),('original',10)]
    for r in records:
        assert r['returncode']==0
        for stream in ['stdout','stderr']:
            p=raw/(r['label']+'.'+stream);assert sha(p)==r[stream+'_sha256'];artifacts[str(p.relative_to(ROOT))]=sha(p)
        error=(raw/(r['label']+'.stderr')).read_text()
        assert ('Ran '+str(r['tests'])+' tests') in error and error.rstrip().endswith('OK')
    assert not (out/'closure.json').exists()
    write(raw/'closed-bindings.json',dict(source=bindings,artifacts=artifacts))
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,source_revision=revision,frozen_input_count=len(bindings),artifact_count=len(artifacts),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),performance_measurement=False))
    print('Closed16 parser controls;',len(bindings),'source inputs')
if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);main()
