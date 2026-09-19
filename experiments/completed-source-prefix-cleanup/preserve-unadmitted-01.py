#!/usr/bin/env python3
"""Retain declared shared history and verify the committed01/02 archive."""
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

from assess import OWNER,R,ROOTS,read,sha,identity,history

ORIGINAL=R/'results/mono-production-source-observables-02'
RESULT=OWNER/'results/completed-source-prefix-preservation-01'
WORK=OWNER/'.work/completed-source-prefix-preservation-01'
ARCHIVED_ONLY={'failed01/referenced-artifacts/entry.rbc','failed01/referenced-artifacts/entry.calls.json','failed01/referenced-artifacts.json'}

def outer(name):
    return R/'.work/experiments'/('mono-production-source-observables-'+('shared-supervisor-01' if name=='shared-01' else 'supervisor-'+name))

def validate_outer(name):
    hist,unused=history(name);root=outer(name);status=read(root/'status.json');plan=read(root/'plan.json')
    assert status['status']=='finished' and status['returncode']==(1 if name=='01' else 0)
    assert status['child_pid']==hist['parent_pid'] and status['cwd']==str(R) and status['command']==plan['command']
    assert sha(root/'plan.json')==status['plan_sha256'] and sha(root/'command.log')==status['log_sha256']
    assert status['started_at']<=hist['completed_at']<=status['finished_at']
    return status

def verify_archive(root):
    manifest=read(root/'manifest.json');seen={}
    with tarfile.open(root/'evidence.tar.gz','r:gz') as archive:
        members=archive.getmembers();assert len(members)==len(manifest) and {m.name for m in members}==set(manifest)
        for member in members:
            proof=manifest[member.name]
            assert member.isfile() or (member.islnk() and member.linkname in seen and seen[member.linkname]==proof['sha256'])
            stream=archive.extractfile(member);digest=hashlib.sha256();size=0
            while block:=stream.read(2**20):digest.update(block);size+=len(block)
            assert size==proof['bytes'] and digest.hexdigest()==proof['sha256'],member.name
            seen[member.name]=digest.hexdigest()
        while archive.fileobj.read(2**20):pass
    # Explicit second gzip reader consumes the trailer even if tar buffered it.
    with gzip.open(root/'evidence.tar.gz','rb') as stream:
        while stream.read(2**20):pass
    return manifest

def main():
    assert Path.cwd()==OWNER and not RESULT.exists() and not WORK.exists()
    original=verify_archive(ORIGINAL);assert len(original)==641
    mapping={'failed01':ROOTS['01'].parent,'passed02':ROOTS['02'].parent,'supervisor01':outer('01'),'supervisor02':outer('02')}
    live={}
    for name,proof in original.items():
        prefix,sep,relative=name.partition('/')
        if prefix not in mapping:continue
        path=mapping[prefix]/relative
        if name in ARCHIVED_ONLY:
            assert not path.exists() and not path.is_symlink();continue
        assert path.resolve(strict=True)==path and path.is_file() and sha(path)==proof['sha256'] and path.stat().st_size==proof['bytes'],path
        live[str(path)]=dict(archive_member=name,sha256=proof['sha256'],bytes=proof['bytes'])
    for name in ROOTS:validate_outer(name)
    shared=ROOTS['shared-01'].parent;terminal=read(shared/'result.json')
    sources={}
    for name,digest in terminal['evidence_files'].items():
        path=shared/name;assert path.resolve(strict=True)==path and path.is_file() and sha(path)==digest
        sources['shared01/'+name]=path
    sources['shared01/result.json']=shared/'result.json'
    for name in ['plan.json','status.json','command.log']:sources['shared-supervisor01/'+name]=outer('shared-01')/name
    assert len(sources)==304 and sum(p.stat().st_size for p in sources.values())<64*2**20
    before={str(path):identity(path) for path in sources.values()}
    manifest={name:dict(bytes=path.stat().st_size,sha256=sha(path)) for name,path in sources.items()}
    WORK.mkdir();RESULT.mkdir()
    with tarfile.open(RESULT/'evidence.tar.gz','x:gz',dereference=True) as archive:
        for name,path in sources.items():archive.add(path,arcname=name,recursive=False)
    with (RESULT/'manifest.json').open('x') as stream:json.dump(manifest,stream,indent=2,sort_keys=True);stream.write('\n')
    assert verify_archive(RESULT)==manifest
    for path,stamp in before.items():assert identity(Path(path))==stamp
    result=dict(status='retained-not-deleted',original_archive=dict(path=str(ORIGINAL),sha256=sha(ORIGINAL/'evidence.tar.gz'),manifest_sha256=sha(ORIGINAL/'manifest.json'),members=641),
                original_live_evidence=live,original_archived_only={name:original[name] for name in sorted(ARCHIVED_ONLY)},
                shared_archive=dict(path=str(RESULT),sha256=sha(RESULT/'evidence.tar.gz'),manifest_sha256=sha(RESULT/'manifest.json'),members=304),
                shared_sources={name:dict(path=str(path),identity=before[str(path)],**manifest[name]) for name,path in sources.items()},
                limitation='Reversible evidence-only archive creation; no benchmark, compiler, canonical admission, process-control or deletion command was run.')
    with (WORK/'receipt.json').open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(receipt=str(WORK/'receipt.json'),receipt_sha256=sha(WORK/'receipt.json'),archive_sha256=sha(RESULT/'evidence.tar.gz'),members=304)))
if __name__=='__main__':main()
