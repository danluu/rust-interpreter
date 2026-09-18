"""Close the source-frozen primary protocol and launcher controls."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write


def main():
    name=sys.argv[1];revision=sys.argv[2]
    assert re.fullmatch(r'scalar-indirect-screen-protocol-\d{2}',name)
    out=ROOT/'results'/name;raw=ROOT/'.work'/name;outer=ROOT/'.work/experiments'/name
    summary=json.loads((out/'summary.json').read_text());terminal=json.loads((outer/'status.json').read_text())
    assert summary['status']=='passed' and summary['tests']==13 and summary['observation_controls']==5 and summary['observation_controls_reused']==5
    assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256']
    assert sha(raw/'inputs.json')==summary['inputs_sha256']
    bindings={}
    for path,h in json.loads((raw/'inputs.json').read_text()).items():
        assert sha(ROOT/path)==h
        if path.startswith('.work/'):
            bindings[path]=dict(kind='retained',sha256=h)
        else:
            payload=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
            assert hashlib.sha256(payload).hexdigest()==h
            bindings[path]=dict(kind='git',revision=revision,sha256=h)
    for file,key in [('stdout','stdout_sha256'),('stderr','stderr_sha256'),
        ('record.json','record_sha256')]:
        assert sha(raw/file)==summary[key]
    assert not (out/'closure.json').exists()
    write(raw/'source-bindings.json',bindings)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision=revision,frozen_inputs=len(bindings),all_hashes_verified=True,
        bindings=str((raw/'source-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'source-bindings.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print(len(bindings),'protocol inputs and all logs verified')


if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        main()
