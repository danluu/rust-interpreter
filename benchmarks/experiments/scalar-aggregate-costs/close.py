"""Close the offline machine-path census without reexecuting it."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
NAME='scalar-aggregate-costs-02'
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    out=ROOT/'results'/NAME;result=read(out/'summary.json');work=ROOT/result['raw']
    assert result['status']=='passed' and result['commands']==1 and result['controls']==14
    bindings={}
    def bind(path,digest=None):
        actual=sha(path)
        if digest is not None:assert actual==digest,path
        bindings[str(path.relative_to(ROOT))]=actual
    for kind in ['plan','records','details']:bind(work/(kind+'.json'),result[kind+'_sha256'])
    plan=read(work/'plan.json');assert plan['owner']==str(ROOT)
    sources={}
    for p,h in plan['frozen'].items():
        bind(ROOT/p,h)
        if not p.startswith(('.work/','results/')):
            spec=plan['source_revision']+':'+p
            assert hashlib.sha256(subprocess.check_output(['git','show',spec],cwd=ROOT)).hexdigest()==h
            sources[p]=dict(sha256=h,git_source=spec)
    record,=read(work/'records.json');assert record['returncode']==0
    for stream in ['stdout','stderr']:bind(work/('controls.'+stream),record[stream+'_sha256'])
    outer=ROOT/'.work/experiments'/NAME;terminal=read(outer/'status.json')
    assert terminal['owner']==terminal['cwd']==str(ROOT) and terminal['status']=='finished' and terminal['returncode']==0
    bind(outer/'plan.json',terminal['plan_sha256']);bind(outer/'command.log',terminal['log_sha256'])
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes());bind(out/'terminal.json');bind(out/'summary.json')
    write(work/'source-bindings.json',sources);write(work/'closure-evidence.json',bindings)
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,frozen_inputs=len(plan['frozen']),
        evidence_files=len(bindings),source_bindings=len(sources),summary_sha256=sha(out/'summary.json'),
        bindings=str((work/'source-bindings.json').relative_to(ROOT)),bindings_sha256=sha(work/'source-bindings.json'),
        evidence=str((work/'closure-evidence.json').relative_to(ROOT)),evidence_sha256=sha(work/'closure-evidence.json'),
        guest_commands=0,performance_measurement=False))
    print('Closed',NAME,len(bindings),'bindings')
