"""Verify exact completed-cache retirement without removing any further file."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
RUN='closed-session-runtime-parser-cache-retirement-01'
def read(p):return json.loads(p.read_text())


with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45)
    from workflow_io import require_space
    require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;outer=ROOT/'.work/experiments'/RUN
    summary=read(raw/'summary.json');plan=read(raw/'plan.json');terminal=read(outer/'status.json')
    assert summary['status']=='passed' and summary['all_protected_hashes_unchanged']
    assert plan['owner']==terminal['owner']==str(ROOT)
    assert terminal['status']=='finished' and terminal['returncode']==0
    assert sha(outer/'command.log')==terminal['log_sha256']
    assert sha(raw/'plan.json')==summary['plan_sha256']
    assert sha(raw/'inventory.json')==summary['inventory_sha256']
    assert sha(raw/'protected.json')==summary['protected_manifest_sha256']
    manifest=read(raw/'inventory.json');protected=read(raw/'protected.json')
    assert len(manifest)==summary['files_removed'] and sum(r['size'] for r in manifest)==summary['logical_bytes_removed']
    assert len(protected)==summary['protected_files']
    assert all(not (ROOT/r['path']).exists() for r in manifest)
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    revision=sys.argv[1];path=str(Path(__file__).with_name('retire.py').relative_to(ROOT))
    data=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
    assert hashlib.sha256(data).hexdigest()==plan['script_sha256']
    result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
    (result/'summary.json').write_bytes((raw/'summary.json').read_bytes())
    (result/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(result/'closure.json',dict(status='closed',source_revision=revision,script_sha256=plan['script_sha256'],
        all_removed_paths_absent=True,all_protected_hashes_unchanged=True,
        summary_sha256=sha(result/'summary.json'),terminal_sha256=sha(result/'terminal.json')))
    print(len(manifest),'removed paths absent;',len(protected),'protected hashes unchanged')
