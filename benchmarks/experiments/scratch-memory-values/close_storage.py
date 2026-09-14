"""Publish compact receipts for these exact completed storage operations."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

def main():
    name,revision=sys.argv[1:]
    assert name in ['runtime-storage-inventory-20260914-01','closed-scratch-memory-values-parser-incremental-retirement-01']
    raw=ROOT/'.work'/name;outer=ROOT/'.work/experiments'/name;out=ROOT/'results'/name
    summary=json.loads((raw/'summary.json').read_text());terminal=json.loads((outer/'status.json').read_text())
    assert summary['status']=='passed' and terminal['status']=='finished' and terminal['returncode']==0
    assert terminal['owner']==terminal['cwd']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256'] and sha(outer/'plan.json')==terminal['plan_sha256']
    script=terminal['command'][1]
    script_hash=hashlib.sha256(subprocess.check_output(['git','show',revision+':'+script],cwd=ROOT)).hexdigest()
    assert sha(ROOT/script)==script_hash
    proofs={script:script_hash}
    if name.startswith('runtime-storage'):
        assert summary['commands']==2 and summary['files_removed']==0 and not summary['eligibility_established']
        assert sha(raw/'records.json')==summary['records_sha256']
        records=json.loads((raw/'records.json').read_text());assert len(records)==2
        for row in records:
            assert row['returncode']==0 and row['command'][0]=='du'
            for stream in ['stdout','stderr']:
                p=raw/(row['label']+'.'+stream);assert sha(p)==row[stream+'_sha256'];proofs[str(p.relative_to(ROOT))]=sha(p)
    else:
        assert summary['completed_commands']==88 and summary['all_protected_hashes_unchanged']
        for file,key in [('plan','plan_sha256'),('inventory','inventory_sha256'),('protected','protected_manifest_sha256')]:
            assert sha(raw/(file+'.json'))==summary[key]
        plan=json.loads((raw/'plan.json').read_text());assert plan['owner']==str(ROOT) and plan['script_sha256']==script_hash
        inventory=json.loads((raw/'inventory.json').read_text());assert len(inventory)==summary['files_removed']
        assert all(not (ROOT/r['path']).exists() for r in inventory)
        protected=json.loads((raw/'protected.json').read_text());assert len(protected)==summary['protected_files']
        assert all(sha(ROOT/p)==h for p,h in protected.items());proofs.update(protected)
    for p in raw.iterdir():
        if p.is_file():proofs[str(p.relative_to(ROOT))]=sha(p)
    write(raw/'verified.json',proofs)
    out.mkdir(exist_ok=False)
    (out/'summary.json').write_bytes((raw/'summary.json').read_bytes());(out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision=revision,verified_files=len(proofs),all_hashes_verified=True,
        manifest=str((raw/'verified.json').relative_to(ROOT)),manifest_sha256=sha(raw/'verified.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),performance_measurement=False))
    print(name,len(proofs),'verified files')

if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);main()
