"""Close either outcome of the complete source-frozen full-protocol checks."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

def main():
    name,revision=sys.argv[1:3]
    assert re.fullmatch(r'runtime-composition-full-protocol-\d{2}',name)
    out=ROOT/'results'/name;raw=ROOT/'.work'/name;outer=ROOT/'.work/experiments'/name
    terminal=json.loads((outer/'status.json').read_text())
    assert terminal['status']=='finished' and terminal['owner']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256']
    bindings={}
    for path,h in json.loads((raw/'inputs.json').read_text()).items():
        if path.startswith(('.work/','results/')):
            assert sha(ROOT/path)==h;bindings[path]=dict(kind='retained',sha256=h)
        else:
            payload=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
            assert hashlib.sha256(payload).hexdigest()==h,path
            bindings[path]=dict(kind='git',revision=revision,sha256=h)
            if terminal['returncode']==0:assert sha(ROOT/path)==h,path
    for file in ['stdout','stderr']:
        bindings[str((raw/file).relative_to(ROOT))]=dict(kind='retained',sha256=sha(raw/file))
    stderr=(raw/'stderr').read_text();count=re.search(r'Ran (\d+) tests',stderr);assert count
    out.mkdir(exist_ok=True);assert not (out/'closure.json').exists()
    if terminal['returncode']==0:
        summary=json.loads((out/'summary.json').read_text())
        assert summary['status']=='passed' and summary['tests']==25 and summary['guest_commands']==0 and summary['commands']==1
        assert int(count[1])==25 and stderr.rstrip().endswith('OK')
        assert sha(raw/'inputs.json')==summary['inputs_sha256']
    else:
        assert not (out/'summary.json').exists()
        write(out/'summary.json',dict(status='failed',tests=int(count[1]),commands=1,guest_commands=0,
            raw=str(raw.relative_to(ROOT)),inputs_sha256=sha(raw/'inputs.json'),
            stdout_sha256=sha(raw/'stdout'),stderr_sha256=sha(raw/'stderr'),performance_measurement=False))
    write(raw/'source-bindings.json',bindings)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision=revision,frozen_inputs=len(bindings),all_hashes_verified=True,
        bindings=str((raw/'source-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'source-bindings.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print(name,len(bindings),'protocol inputs and logs verified')
if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);main()
