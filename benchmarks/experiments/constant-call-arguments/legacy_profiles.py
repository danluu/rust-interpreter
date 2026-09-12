"""Exact completed public diagnostics admitted for transparent compression."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from reclaim_workflow_objects import no_open_files

RUNS=['virtual-register-compaction-screen-01','native-register-cache-profile-drift-01',
      'call-result-copy-screen-01','native-cast-width-screen-01','native-memory-parts-screen-01',
      'packed-native-cache-screen-01','constant-dynamic-copy-screen-01','native-compare-bytes-screen-01',
      'native-paired-spills-screen-01','local-memory-forwarding-screen-01']


def inputs():
    values=[];proofs=[Path(__file__)];origins={}
    for run in RUNS:
        work=ROOT/'.work'/run;active=work/'active-command.json';records=work/'records.json';summary=work/'summary.json'
        a=json.loads(active.read_text());rows=json.loads(records.read_text());s=json.loads(summary.read_text())
        assert a['status']=='finished' and a['returncode']==0 and a['cwd']==str(ROOT)
        assert isinstance(s['status'],str) and s['status']
        no_open_files(work)
        profiles=[r for r in rows if '--profile' in r.get('command',[])]
        assert profiles and all(r['returncode']==0 for r in profiles)
        for row in profiles:
            command=row['command'];path=Path(command[command.index('--profile')+1])
            assert path.parent==work and path.suffix=='.json' and 'private' not in str(command) and 'rg-aot' not in str(command)
            expected=row.get('profile_sha256');digest=sha(path)
            if expected is not None:assert digest==expected
            # Some older successful commands recorded the output path without
            # its digest. Preserve those exact current bytes, with no claim
            # that maintenance establishes their original historical digest.
            origins[str(path.relative_to(ROOT))]='historical profile digest' if expected else 'current bytes before maintenance; historical command records path only'
            values.append((path,digest,run))
        proofs += [active,records,summary]
    run='native-pc-map-samples-01';work=ROOT/'.work'/run
    active=work/'active-vm.json';summary=work/'summary.json';a=json.loads(active.read_text());s=json.loads(summary.read_text())
    assert a['status']=='finished' and a['returncode']==0 and a['cwd']==str(ROOT)
    assert len(s['results'])==6;no_open_files(work)
    for row in s['results']:
        assert row['original_assertions_pass'] and row['mapping_verified'] and row['all_native_words_identical']
        path=ROOT/row['map'];assert path.is_relative_to(work) and sha(path)==row['map_sha256']
        record=path.with_name('vm.json');assert sha(record)==row['files'][str(record.relative_to(ROOT))]
        v=json.loads(record.read_text());assert v['status']=='finished' and v['returncode']==0 and v['cwd']==str(ROOT)
        values.append((path,row['map_sha256'],run));proofs.append(record)
        origins[str(path.relative_to(ROOT))]='historical map digest'
    proofs += [active,summary]
    process=subprocess.run(['ps','-axo','pid,ppid,lstart,tty,command'],capture_output=True,text=True)
    assert process.returncode==0 and not process.stderr
    roots=[str(ROOT/'.work'/r) for r in [*RUNS,run]]
    assert not any(any(root in line for root in roots) for line in process.stdout.splitlines()[1:])
    return values,proofs,origins
