"""Close all nineteen parser-screen controls and source bindings."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45)
    name='indexed-switches-parser-protocol-01';revision=sys.argv[1]
    raw=ROOT/'.work'/name;out=ROOT/'results'/name;outer=ROOT/'.work/experiments'/name
    summary=read(out/'summary.json');terminal=read(outer/'status.json')
    assert summary['status']=='passed' and summary['tests']==19 and summary['commands']==2
    assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256']
    assert sha(raw/'inputs.json')==summary['inputs_sha256'] and sha(raw/'records.json')==summary['records_sha256']
    bindings={}
    for path,digest in read(raw/'inputs.json').items():
        assert sha(ROOT/path)==digest,path
        if path.startswith(('.work/','results/')):bindings[path]=dict(kind='retained',sha256=digest)
        else:
            data=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==digest,path
            bindings[path]=dict(kind='git',revision=revision,sha256=digest)
    rows=read(raw/'records.json');assert [(r['label'],r['tests'],r['returncode']) for r in rows]==[('matched',9,0),('original',10,0)]
    for row in rows:
        for stream in ['stdout','stderr']:assert sha(raw/(row['label']+'.'+stream))==row[stream+'_sha256']
    assert not (out/'closure.json').exists()
    write(raw/'bindings.json',bindings);(out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision=revision,all_hashes_verified=True,
        frozen_inputs=len(bindings),bindings=str((raw/'bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'bindings.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print(len(bindings),'frozen inputs; all 19 control outcomes verified')
