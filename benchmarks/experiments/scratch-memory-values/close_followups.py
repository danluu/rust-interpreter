"""Close preserved diagnostic compression and frozen full-protocol evidence."""
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
    assert re.fullmatch(r'(?:closed-diagnostic-json-compression-20|closed-runtime-screen-artifact-compression-0[67]|closed-runtime-full-artifact-compression-0[23]|scratch-memory-values-full-protocol-01|scratch-memory-values-parser-edits-protocol-02)',name)
    raw=ROOT/'.work'/name;out=ROOT/'results'/name;outer=ROOT/'.work/experiments'/name
    summary=json.loads((out/'summary.json').read_text());terminal=json.loads((outer/'status.json').read_text())
    assert summary['status']=='passed' and terminal['status']=='finished' and terminal['returncode']==0
    assert terminal['owner']==terminal['cwd']==str(ROOT)
    assert sha(outer/'command.log')==terminal['log_sha256'] and sha(outer/'plan.json')==terminal['plan_sha256']
    proofs={}
    if 'compression' in name:
        for key in ['plan','records']:assert sha(raw/(key+'.json'))==summary[key+'_sha256']
        plan=json.loads((raw/'plan.json').read_text());assert plan['owner']==str(ROOT) and plan['source_revision'].startswith(revision)
        script=terminal['command'][1];data=subprocess.check_output(['git','show',revision+':'+script],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==plan['script_sha256']
        proofs.update(plan['proofs']);proofs.update({r['path']:r['sha256'] for r in plan['files']})
        assert all(sha(ROOT/p)==h for p,h in proofs.items())
        rows=json.loads((raw/'records.json').read_text());assert len(rows)==summary['files']
        assert all(r['returncode']==0 and r['status']=='compressed' and r['source_sha256']==proofs[r['path']] for r in rows)
    elif 'parser-edits-protocol' in name:
        assert summary['tests']==16 and summary['commands']==2 and summary['guest_commands']==0
        assert sha(raw/'inputs.json')==summary['inputs_sha256'] and sha(raw/'records.json')==summary['records_sha256']
        for p,h in json.loads((raw/'inputs.json').read_text()).items():
            assert sha(ROOT/p)==h
            data=subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==h
            proofs[p]=h
        records=json.loads((raw/'records.json').read_text());assert [(r['label'],r['tests']) for r in records]==[('matched',6),('original',10)]
        for row in records:
            assert row['returncode']==0
            for stream in ['stdout','stderr']:
                p=raw/(row['label']+'.'+stream);assert sha(p)==row[stream+'_sha256'];proofs[str(p.relative_to(ROOT))]=sha(p)
            error=(raw/(row['label']+'.stderr')).read_text();assert ('Ran '+str(row['tests'])+' tests') in error and error.rstrip().endswith('OK')
    else:
        assert summary['tests']==23 and summary['guest_commands']==0
        assert sha(raw/'inputs.json')==summary['inputs_sha256']
        for p,h in json.loads((raw/'inputs.json').read_text()).items():
            assert sha(ROOT/p)==h
            data=subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT)
            assert hashlib.sha256(data).hexdigest()==h
            proofs[p]=h
        assert 'Ran 23 tests' in (raw/'stderr').read_text() and (raw/'stderr').read_text().rstrip().endswith('OK')
        for name in ['stdout','stderr']:proofs[str((raw/name).relative_to(ROOT))]=sha(raw/name)
    assert not (out/'closure.json').exists()
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(raw/'verified.json',proofs)
    write(out/'closure.json',dict(status='closed',source_revision=revision,verified_files=len(proofs),all_hashes_verified=True,
        manifest=str((raw/'verified.json').relative_to(ROOT)),manifest_sha256=sha(raw/'verified.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),performance_measurement=False))
    print(out.name,len(proofs),'hashes verified')
if __name__=='__main__':
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);main()
