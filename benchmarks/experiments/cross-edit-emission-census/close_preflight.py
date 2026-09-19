"""Preserve the unsupported cross-state artifact-equality assumption failure."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    name='cross-edit-emission-census-01';outer=ROOT/'.work/experiments'/name
    terminal=json.loads((outer/'status.json').read_text())
    assert terminal['status']=='finished' and terminal['returncode']==1 and terminal['owner']==str(ROOT)
    assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
    log=(outer/'command.log').read_text()
    assert "assert inputs[0]['sha256']==inputs[-1]['sha256']" in log and log.endswith('AssertionError\n')
    assert not (ROOT/'.work'/name).exists()
    path='benchmarks/experiments/cross-edit-emission-census/observe.py'
    original=subprocess.check_output(['git','show','774fc3dc:'+path],cwd=ROOT)
    assert hashlib.sha256(original).hexdigest()==sha(ROOT/path)
    prior=ROOT/'results/emitter-register-workspace-parser-screen-incremental-01'
    closed=json.loads((prior/'closure.json').read_text());summary=json.loads((prior/'summary.json').read_text())
    assert closed['status']=='closed' and sha(prior/'summary.json')==closed['summary_sha256']
    records=ROOT/summary['raw']/'records.json';assert sha(records)==summary['records_sha256']
    rows=[r for r in json.loads(records.read_text()) if r['mode']=='baseline']
    first,last=rows[0],rows[-1]
    assert first['state']==last['state']==0 and first['source_sha256']==last['source_sha256']
    assert first['artifact']['sha256']!=last['artifact']['sha256']
    for r in [first,last]:assert sha(ROOT/r['artifact']['path'])==r['artifact']['sha256']
    out=ROOT/'results'/name;out.mkdir(exist_ok=False)
    for filename in ['plan.json','status.json','command.log']:(out/filename).write_bytes((outer/filename).read_bytes())
    write(out/'summary.json',dict(status='preflight-failed',source_revision='774fc3dc',
        script=path,script_sha256=sha(ROOT/path),commands=0,original_project_guest_commands=0,
        reason='Source restoration does not imply cross-state artifact-byte identity.',
        source_restored=True,first_artifact=first['artifact'],restored_artifact=last['artifact'],
        records=str(records.relative_to(ROOT)),records_sha256=sha(records)))
    write(out/'closure.json',dict(status='closed',summary_sha256=sha(out/'summary.json'),
        terminal_sha256=sha(out/'status.json'),plan_sha256=sha(out/'plan.json'),log_sha256=sha(out/'command.log'),
        diagnostic_not_started=True,source_and_artifacts_unchanged=True))
    print('Closed preflight failure; no diagnostic or guest command started',flush=True)
