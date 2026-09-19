#!/usr/bin/env python3
"""Canonical readback of existing exact archives; creates no payload copy."""
import hashlib
import os
from pathlib import Path
import sys
import time
import preserve as p
from assess import OWNER,ROOTS,read,sha,identity,history

sys.path.insert(0,str(OWNER/'experiments/stable-cgu'))
import owned_stage as owned
WORK=OWNER/'.work/completed-source-prefix-preservation-admission-02'

def capacity():return owned.disk(OWNER,9)
def bounded_sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(2**20):capacity();digest.update(block)
    return digest.hexdigest()

def main():
    assert Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    assert not WORK.exists() and not WORK.is_symlink();WORK.mkdir()
    record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),children=[],archive_creation=False,
                source_sha256=sha(Path(__file__)),prior_receipt_sha256=sha(p.WORK/'receipt.json'))
    owned.write(WORK/'receipt.json',record)
    try:
        with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
            record.update(status='running',admitted_at=time.time(),free_bytes_before=capacity(),canonical_inode=os.fstat(fd).st_ino);owned.write(WORK/'receipt.json',record)
            prior=read(p.WORK/'receipt.json');assert prior['status']=='retained-not-deleted'
            original=p.verify_archive(p.ORIGINAL,capacity);shared=p.verify_archive(p.RESULT,capacity)
            assert len(original)==641 and len(shared)==304
            archives={}
            for root,key in [(p.ORIGINAL,'original_archive'),(p.RESULT,'shared_archive')]:
                assert bounded_sha(root/'evidence.tar.gz')==prior[key]['sha256'] and sha(root/'manifest.json')==prior[key]['manifest_sha256']
                archives[str(root)]=dict(archive_sha256=prior[key]['sha256'],manifest_sha256=prior[key]['manifest_sha256'],members=prior[key]['members'])
            for name,row in prior['original_live_evidence'].items():
                path=Path(name);before=identity(path)
                assert path.resolve(strict=True)==path and path.stat().st_size==row['bytes'] and bounded_sha(path)==row['sha256']
                assert original[row['archive_member']]=={key:row[key] for key in ['sha256','bytes']} and identity(path)==before
            for name,row in prior['original_archived_only'].items():assert original[name]==row
            for name,row in prior['shared_sources'].items():
                path=Path(row['path']);assert identity(path)==row['identity'] and bounded_sha(path)==row['sha256']
                assert shared[name]=={key:row[key] for key in ['sha256','bytes']} and identity(path)==row['identity']
            for name in ROOTS:capacity();history(name);p.validate_outer(name)
            assert sha(p.WORK/'receipt.json')==record['prior_receipt_sha256'] and sha(Path(__file__))==record['source_sha256']
            record.update(status='passed',archives=archives,complete_member_bytes_and_gzip_trailers_verified=True,
                          original_live_refs=len(prior['original_live_evidence']),archived_only_refs=3,shared_members=304,free_bytes_after=capacity(),
                          limitation='This admits existing retained bytes under the canonical lock; it does not retroactively supervise the explicitly unsupervised archive creation.')
    except BaseException as error:record.update(status='failed',error=repr(error));raise
    finally:record['finished_at']=time.time();owned.write(WORK/'receipt.json',record)
    print(dict(receipt=str(WORK/'receipt.json'),sha256=sha(WORK/'receipt.json'),status=record['status']))
if __name__=='__main__':main()
