#!/usr/bin/env python3
"""Retain completed capacity-recovery evidence; no cleanup or compiler work."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile
import time

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[1]
WORK=OWNER/'.work/completed-negative-source-evidence-01'
RESULT=OWNER/'results/completed-negative-source-cleanup-01'
sys.path.insert(0,str(OWNER/'experiments/stable-cgu'))
import owned_stage as owned

def read(path):return json.loads(path.read_bytes())
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def identity(path):
    value=path.lstat();return {name:getattr(value,'st_'+name) for name in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}
def guard(freeze):
    for name,row in freeze['files'].items():
        path=Path(name);assert path.resolve(strict=True)==path and identity(path)==row['identity'] and sha(path)==row['sha256'],name

def main(expected):
    assert Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    assert sha(HERE/'inputs.json')==expected
    freeze=read(HERE/'inputs.json');plan=read(HERE/'plan.json')
    assert dict(os.environ)==plan['environment'] and list(os.uname())==plan['platform']
    executor=plan['executor'];route=Path(executor['path'])
    assert str(route.resolve(strict=True))==executor['resolved'] and identity(route)==executor['route_identity']
    assert str(Path(sys.executable).resolve(strict=True))==executor['resolved']
    assert len(plan['members'])==plan['member_count']<=128
    assert sum(row['bytes'] for row in plan['members'].values())==plan['logical_bytes']<plan['maximum_logical_bytes']==192*2**20
    assert plan['archive_limit_bytes']==32*2**20
    guard(freeze)
    assert not WORK.exists() and not WORK.is_symlink();WORK.mkdir()
    record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),children=[],compiler_or_cleanup_execution=False)
    owned.write(WORK/'receipt.json',record)
    try:
        with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
            record.update(status='running',admitted_at=time.time(),free_bytes_before=owned.disk(OWNER,9));owned.write(WORK/'receipt.json',record)
            guard(freeze)
            assert str(route.resolve(strict=True))==executor['resolved'] and identity(route)==executor['route_identity']
            for name in plan['passed_receipts']:assert read(Path(name))['status']=='passed'
            assert not RESULT.exists() and not RESULT.is_symlink();RESULT.mkdir()
            members={name:{key:row[key] for key in ['bytes','sha256']} for name,row in plan['members'].items()}
            owned.write(RESULT/'manifest.json',dict(members=members,prior_artifact_archives=plan['prior_artifact_archives'],
                scope='Completed six-negative-source cleanup history, exact frozen source/plan, complete deletion and directory permission ledgers, seven readonly probes, actual delta retention and unchanged originals checks. No compiler execution.'))
            class Reader:
                def __init__(self,stream):self.stream=stream;self.digest=hashlib.sha256();self.size=0
                def read(self,size):
                    owned.disk(OWNER,9);assert (RESULT/'evidence.tar.gz').stat().st_size<32*2**20
                    block=self.stream.read(size);self.digest.update(block);self.size+=len(block);return block
            class CappedOutput:
                def __init__(self,raw):self.raw=raw
                def write(self,value):
                    owned.disk(OWNER,9)
                    assert self.raw.tell()+len(value)<=plan['archive_limit_bytes'],'compressed evidence cap reached before write'
                    written=self.raw.write(value);assert written==len(value);return written
                def tell(self):return self.raw.tell()
                def flush(self):return self.raw.flush()
            with (RESULT/'evidence.tar.gz').open('xb') as raw,gzip.GzipFile(filename='',fileobj=CappedOutput(raw),mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as archive:
                for name,row in plan['members'].items():
                    path=Path(row['source']);assert identity(path)==freeze['files'][str(path)]['identity']
                    entry=tarfile.TarInfo(name);entry.mode=0o644;entry.mtime=0;entry.size=row['bytes']
                    with path.open('rb') as source:
                        reader=Reader(source);archive.addfile(entry,reader)
                        assert reader.size==row['bytes'] and reader.digest.hexdigest()==row['sha256']
                    assert identity(path)==freeze['files'][str(path)]['identity']
            assert (RESULT/'evidence.tar.gz').stat().st_size<32*2**20
            with tarfile.open(RESULT/'evidence.tar.gz','r:gz') as archive:
                actual=archive.getmembers();assert len(actual)==len(members) and {m.name for m in actual}==set(members)
                for member in actual:
                    expected=members[member.name];assert member.isfile() and member.size==expected['bytes']
                    digest=hashlib.sha256();stream=archive.extractfile(member)
                    while block:=stream.read(2**20):owned.disk(OWNER,9);digest.update(block)
                    assert digest.hexdigest()==expected['sha256']
                while archive.fileobj.read(2**20):owned.disk(OWNER,9)
            guard(freeze)
            assert str(route.resolve(strict=True))==executor['resolved'] and identity(route)==executor['route_identity']
            record.update(status='passed',members=len(members),logical_bytes=sum(v['bytes'] for v in members.values()),
                archive_sha256=sha(RESULT/'evidence.tar.gz'),manifest_sha256=sha(RESULT/'manifest.json'),
                full_member_bytes_and_gzip_trailer_verified=True,free_bytes_after=owned.disk(OWNER,9))
    except BaseException as error:record.update(status='failed',error=repr(error));raise
    finally:record['finished_at']=time.time();owned.write(WORK/'receipt.json',record)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);main(parser.parse_args().inputs_sha256)
