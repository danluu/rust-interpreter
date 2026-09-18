"""Close the saved-suite audit without new guest work."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45)
    name='interpreted-switch-census-01';raw=ROOT/'.work'/name;out=ROOT/'results'/name;outer=ROOT/'.work/experiments'/name
    plan=read(raw/'plan.json');summary=read(out/'summary.json');terminal=read(outer/'status.json')
    assert summary['status']=='passed' and len(summary['profiles'])==4 and summary['new_guest_commands']==0
    assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==plan['owner']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256'] and sha(raw/'plan.json')==summary['plan_sha256']
    bindings={}
    for path,digest in plan['frozen'].items():
        assert sha(ROOT/path)==digest,path
        if path.startswith(('.work/','results/')):bindings[path]=dict(kind='retained',sha256=digest)
        else:
            payload=subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)
            assert hashlib.sha256(payload).hexdigest()==digest,path
            bindings[path]=dict(kind='git',revision=plan['source_revision'],sha256=digest)
    for path,digest in summary.get('artifacts',{}).items():assert sha(ROOT/path)==digest
    assert not (out/'closure.json').exists()
    write(raw/'bindings.json',bindings);(out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision=plan['source_revision'],all_hashes_verified=True,
        frozen_inputs=len(bindings),bindings=str((raw/'bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'bindings.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print(len(bindings),'inputs and terminal verified; no new guest commands')
