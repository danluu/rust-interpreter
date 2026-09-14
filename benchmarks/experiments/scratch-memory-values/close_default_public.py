"""Close the reviewed inventory and its exact bounded retirement together."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45)
    inventory='default-public-cache-inventory-20260914-01'
    retirement='default-public-cache-retirement-20260914-01'
    raw=ROOT/'.work'/inventory
    files=json.loads((raw/'inventory.json').read_text());protected=json.loads((raw/'protected.json').read_text())
    assert len(files)==28664 and len(protected)==39995
    assert all(not (ROOT/r['path']).exists() for r in files)
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    for name,revision in [(inventory,'ff4d8b36'),(retirement,'df9455a9')]:
        raw=ROOT/'.work'/name;outer=ROOT/'.work/experiments'/name;out=ROOT/'results'/name
        s=json.loads((raw/'summary.json').read_text());p=json.loads((raw/'plan.json').read_text());t=json.loads((outer/'status.json').read_text())
        assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
        assert sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
        assert sha(raw/'plan.json')==s['plan_sha256'] and p['source_revision'].startswith(revision)
        script=t['command'][1]
        assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+script],cwd=ROOT)).hexdigest()==p['script_sha256']
        if name==inventory:
            assert s['read_only'] and s['files_removed']==0
            assert sha(raw/'inventory.json')==s['inventory_sha256'] and sha(raw/'protected.json')==s['protected_sha256']
        else:
            assert s['files_removed']==28664 and s['all_protected_hashes_unchanged']
            for file,digest in s['inventory_hashes'].items():assert sha(ROOT/'.work'/inventory/file)==digest
        proofs={str(f.relative_to(ROOT)):sha(f) for f in [raw/'summary.json',raw/'plan.json',outer/'status.json',outer/'plan.json',outer/'command.log']}
        proofs.update({str((ROOT/'.work'/inventory/f).relative_to(ROOT)):sha(ROOT/'.work'/inventory/f) for f in ['inventory.json','protected.json']})
        write(raw/'closed-proof.json',proofs)
        out.mkdir(exist_ok=False);(out/'summary.json').write_bytes((raw/'summary.json').read_bytes());(out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',source_revision=revision,all_protected_hashes_verified=True,protected_files=len(protected),manifest=str((raw/'closed-proof.json').relative_to(ROOT)),manifest_sha256=sha(raw/'closed-proof.json'),summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),performance_measurement=False))
        print('Closed',name)
