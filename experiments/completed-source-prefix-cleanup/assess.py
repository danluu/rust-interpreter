#!/usr/bin/env python3
"""Read-only assessment of exactly three redundant, completed source copies."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

OWNER=Path(__file__).resolve().parents[2]
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
NAMES=['01','02','shared-01']
ROOTS={name:R/'.work'/('mono-production-source-observables-'+name)/'second-prefix' for name in NAMES}
FIELDS=['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']
ASSESSMENT=OWNER/'.work/completed-source-prefix-assessment-01.json'

def read(path):return json.loads(Path(path).read_bytes())
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def identity(path):
    value=Path(path).lstat();return {name:getattr(value,'st_'+name) for name in FIELDS}
def snapshot(root,require_single_link=True):
    assert root.resolve(strict=True)==root and root.is_dir()
    rows={'.':identity(root)};allocated=root.stat().st_blocks*512
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            path=Path(parent)/name;row=identity(path)
            assert path.resolve(strict=True)==path and (stat.S_ISREG(row['mode']) or stat.S_ISDIR(row['mode'])),path
            if require_single_link and stat.S_ISREG(row['mode']):assert row['nlink']==1,('outside hardlink',path)
            rows[str(path.relative_to(root))]=row;allocated+=path.stat().st_blocks*512
    return rows,allocated

def history(name):
    work=ROOTS[name].parent;plan=read(work/'plan.json');terminal=read(work/'result.json');commands=read(work/'commands.json')
    expected=38 if name=='01' else 61
    assert plan['owner']==str(R) and set(plan['copy_proofs'])=={'native','off','on'}
    assert terminal['status']==('failed' if name=='01' else 'passed')
    assert len(commands)==expected and terminal.get('completed_commands',terminal.get('commands'))==expected
    if name=='01':assert terminal['error']=="RuntimeError('source qualification command failed: off-unmapped-exported')"
    else:assert terminal['source_restored'] is True and terminal['plan_sha256']==sha(work/'plan.json')
    parent=None;previous=0
    children={}
    for index,row in enumerate(commands):
        path=work/f'{index:03}-child.json';child=read(path)
        assert child['status']=='finished' and child['label']==row['label'] and child['command']==row['command'] and child['cwd']==row['cwd']
        assert child['returncode']==row['returncode']
        if name=='01' and index==37:assert row['returncode']==1 and row['expected_returncode']==0
        else:assert row['returncode']==row['expected_returncode']
        assert previous<=child['started_at']<=child['finished_at'];previous=child['finished_at']
        if parent is None:parent=child['parent_pid']
        assert child['parent_pid']==parent
        children[path.name]=sha(path)
    return dict(work=str(work),status=terminal['status'],commands=expected,completed_at=previous,parent_pid=parent,
                plan_sha256=sha(work/'plan.json'),terminal_sha256=sha(work/'result.json'),commands_sha256=sha(work/'commands.json'),children=children,
                limitation='Original receipts bind PID/parent and times, but do not contain full per-child process-start identities or complete environments; none are inferred.'),plan

def main():
    assert Path.cwd()==OWNER and not ASSESSMENT.exists()
    started=time.time();roots={};originals={};proofs={}
    for name,root in ROOTS.items():
        hist,plan=history(name);rows,allocated=snapshot(root)
        assert set(path.name for path in root.iterdir())=={'native','off','on'}
        roles={}
        for role,proof in plan['copy_proofs'].items():
            copy=root/role;original=Path(proof['original'])
            assert proof['path']==str(copy) and original.is_relative_to(R/'.work')
            assert all(not original.is_relative_to(other) for other in ROOTS.values())
            entries,unused=snapshot(copy)
            assert set(entries)==set(proof['stamps'])
            transitions=set()
            for relative,old in proof['stamps'].items():
                current=entries[relative]
                actual=[current[key] for key in ['dev','ino','mode','size','mtime_ns','ctime_ns']]
                assert actual[1:]==old[1:],('changed beyond historical device transition',name,role,relative)
                transitions.add((old[0],actual[0]))
            assert transitions=={(16777231,16777229)},transitions
            files={relative for relative,row in entries.items() if stat.S_ISREG(row['mode'])}
            assert files==set(proof['files'])
            original_rows,unused=snapshot(original,False)
            assert {p for p,row in original_rows.items() if stat.S_ISREG(row['mode'])}==files
            retained={}
            for relative,digest in proof['files'].items():
                source=original/relative;destination=copy/relative
                before=identity(source);assert (before['dev'],before['ino'])!=(entries[relative]['dev'],entries[relative]['ino'])
                source_key=str(source)
                if source_key not in originals:
                    assert sha(source)==digest and identity(source)==before
                    originals[source_key]=dict(sha256=digest,identity=before)
                else:assert originals[source_key]==dict(sha256=digest,identity=before)
                assert sha(destination)==digest
                retained[relative]=source_key
            assert snapshot(copy)[0]==entries and snapshot(original,False)[0]==original_rows
            controls=read(root.parent/'controls.json')
            if name!='01':
                assert controls['second_prefix_final'][role]==dict(path=str(copy),files_sha256=proof['files_sha256'],files_unchanged=True,stamps_unchanged=True)
            roles[role]=dict(original=str(original),retained_files=retained,files_sha256=proof['files_sha256'],historical_device_transition=[16777231,16777229])
        assert snapshot(root)[0]==rows
        assert all(max(row['mtime_ns'],row['ctime_ns'])/1e9<=hist['completed_at'] for row in rows.values()),name
        roots[name]=dict(root=str(root),entries=rows,allocated_bytes=allocated,roles=roles,history=hist)
        for file in ['plan.json','result.json','commands.json','controls.json']:
            proofs[str(root.parent/file)]=sha(root.parent/file)
    result=dict(status='assessed-not-deleted',owner=str(OWNER),source_owner=str(R),started_at=started,finished_at=time.time(),
                roots=roots,retained_original_files=originals,proofs=proofs,
                allocated_bytes=sum(row['allocated_bytes'] for row in roots.values()),entries=sum(len(row['entries']) for row in roots.values()),
                limitations=['No open-handle proof or canonical admission yet.','Retained originals remain live, unchanged files.','01 remains a failed38-command history.'])
    with ASSESSMENT.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(assessment=str(ASSESSMENT),sha256=sha(ASSESSMENT),entries=result['entries'],allocated_bytes=result['allocated_bytes'],original_files=len(originals))))
if __name__=='__main__':main()
