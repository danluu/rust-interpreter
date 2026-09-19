#!/usr/bin/env python3
"""Read-only byte/identity assessment of six completed negative source copies."""
import importlib.util
import json
from pathlib import Path
import stat
import time

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[1]
spec=importlib.util.spec_from_file_location('prefix_assess',HERE.parent/'completed-source-prefix-cleanup/assess.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
R=base.R
VICTIM='lib/rustlib/src/rust/library/core/src/panic.rs'
ROOTS={name+'-'+kind:R/'.work'/('mono-production-source-observables-'+name)/('negative-'+kind)
       for name in base.NAMES for kind in ['missing','corrupt']}
OUT=OWNER/'.work/completed-negative-source-assessment-01.json'

def main():
    assert Path.cwd()==OWNER and not OUT.exists()
    started=time.time();roots={};originals={};proofs={};original_dirs={}
    for name in base.NAMES:
        history,plan=base.history(name);work=Path(history['work']);controls=base.read(work/'controls.json')
        expected=plan['std_readiness']['off']['sysroot_files'];original=Path(plan['copy_proofs']['off']['original'])
        assert expected==plan['copy_proofs']['off']['files']
        original_rows,_=base.snapshot(original,False)
        assert {p for p,row in original_rows.items() if stat.S_ISREG(row['mode'])}==set(expected)
        for relative,digest in expected.items():
            source=original/relative;before=base.identity(source)
            if str(source) not in originals:
                assert base.sha(source)==digest and base.identity(source)==before
                originals[str(source)]=dict(sha256=digest,identity=before)
            else:assert originals[str(source)]==dict(sha256=digest,identity=before)
        original_dirs[str(original)]={p:row for p,row in original_rows.items() if stat.S_ISDIR(row['mode'])}
        assert len(controls['negatives'])==2
        commands=base.read(work/'commands.json')
        for index,kind in enumerate(['missing','corrupt']):
            key=name+'-'+kind;root=ROOTS[key];control=controls['negatives'][index]
            assert control['kind']==kind and control['sysroot']==str(root) and control['changed_source']==str(root/VICTIM)
            assert control['expected_sha256']==expected[VICTIM] and control['command_index']==22+index
            after=control['after_files'];assert {p:h for p,h in after.items() if p!=VICTIM}=={p:h for p,h in expected.items() if p!=VICTIM}
            assert (VICTIM not in after) if kind=='missing' else (after[VICTIM]!=expected[VICTIM])
            command=commands[22+index]
            assert command['label']=='negative-'+kind and command['returncode']==command['expected_returncode']==1
            assert command['command'][command['command'].index('--sysroot')+1]==str(root)
            diagnostics=[json.loads(line) for line in command['stderr'].splitlines() if line.startswith('{')]
            assert any(d.get('code') and d['code'].get('code')=='E0080' for d in diagnostics)
            assert control['validator_rejection']
            rows,allocated=base.snapshot(root)
            assert {p for p,row in rows.items() if stat.S_ISREG(row['mode'])}==set(after)
            for relative,digest in after.items():
                assert base.sha(root/relative)==digest
                ref=original_rows[relative];copy=rows[relative]
                assert (ref['dev'],ref['ino'])!=(copy['dev'],copy['ino'])
            if kind=='missing':assert not (root/VICTIM).exists()
            else:assert (root/VICTIM).read_bytes()==b'X'*6751
            assert all(max(row['mtime_ns'],row['ctime_ns'])/1e9<=history['completed_at'] for row in rows.values())
            assert base.snapshot(root)[0]==rows
            roots[key]=dict(root=str(root),entries=rows,allocated_bytes=allocated,original=str(original),history=history,
                retained_files={p:str(original/p) for p in after if p!=VICTIM},negative=control,
                historical_stamps_available=False,absence=VICTIM if kind=='missing' else None,
                divergent_file=dict(relative=VICTIM,sha256=after[VICTIM],bytes=6751) if kind=='corrupt' else None)
        assert base.snapshot(original,False)[0]==original_rows
        for filename in ['plan.json','result.json','commands.json','controls.json','source-snapshots/qualify_std_source_observables.py']:
            proofs[str(work/filename)]=base.sha(work/filename)
    result=dict(status='assessed-not-deleted',owner=str(OWNER),source_owner=str(R),started_at=started,finished_at=time.time(),
        roots=roots,retained_original_files=originals,retained_original_directories=original_dirs,proofs=proofs,
        entries=sum(len(row['entries']) for row in roots.values()),allocated_bytes=sum(row['allocated_bytes'] for row in roots.values()),
        limitations=['No canonical admission or open-handle proof yet.','Negative copies have no historical complete stamp map; only current exact identities are bound.',
                    '01 remains the failed38-command history; 02/shared remain passed61 histories.','Three corrupt 6751-byte payloads require independent retention before removal.'])
    with OUT.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(assessment=str(OUT),sha256=base.sha(OUT),entries=result['entries'],allocated_bytes=result['allocated_bytes'],original_files=len(originals))))

if __name__=='__main__':main()
