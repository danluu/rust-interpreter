"""Close oversized-function diagnostic evidence, including any failed run."""
import hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import write_json as write
def read(path):return json.loads(path.read_text())

with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45)
    name=sys.argv[1];assert re.fullmatch(r'indexed-switches-parser-profile-\d{2}',name)
    raw=ROOT/'.work'/name;out=ROOT/'results'/name;outer=ROOT/'.work/experiments'/name
    terminal=read(outer/'status.json');assert terminal['owner']==str(ROOT) and terminal['status']=='finished'
    assert sha(outer/'command.log')==terminal['log_sha256']
    plan=read(raw/'plan.json');assert plan['owner']==str(ROOT)
    bindings={}
    for path,digest in plan['frozen'].items():
        assert sha(ROOT/path)==digest
        if path.startswith(('.work/','results/')):bindings[path]=dict(kind='retained',sha256=digest)
        else:
            data=subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==digest
            bindings[path]=dict(kind='git',revision=plan['source_revision'],sha256=digest)
    records=read(raw/'records.json');out.mkdir(exist_ok=True)
    assert not (out/'closure.json').exists()
    artifacts={str(p.relative_to(ROOT)):sha(p) for p in raw.rglob('*') if p.is_file()}
    if terminal['returncode']==0:
        summary=read(out/'summary.json')
        assert summary['status']=='passed' and summary['commands']==len(records)==1
        assert [r['label'] for r in records]==['candidate'] and all(r['returncode']==0 for r in records)
        assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
        assert sha(ROOT/summary['entropy_tape_path'])==summary['entropy_tape_sha256']
        for row in summary['comparisons']:
            for path,digest in row['evidence'].items():assert artifacts[path]==digest
    else:
        assert not (out/'summary.json').exists()
        write(out/'summary.json',dict(status='failed',source_revision=plan['source_revision'],commands=len(records),
            command_returncodes=[r['returncode'] for r in records],raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),performance_measurement=False))
    write(raw/'bindings.json',dict(source=bindings,artifacts=artifacts))
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision=plan['source_revision'],
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),all_hashes_verified=True,
        frozen_input_count=len(bindings),artifact_count=len(artifacts),bindings=str((raw/'bindings.json').relative_to(ROOT)),
        bindings_sha256=sha(raw/'bindings.json')))
    print(name,terminal['returncode'],len(bindings),'inputs;',len(artifacts),'artifacts verified')
