#!/usr/bin/env python3
"""Retire exactly one redundant provider from the completed original toolchain."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import time

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[1]
WORK=OWNER/'.work/oxc-original-llvm-retirement-01'
ASSESSMENT=OWNER/'.work/oxc-original-llvm-provider-capacity-assessment-01.json'
TARGET=OWNER/'.work/oxc-native-setup-01/rustup/toolchains/1.98.1-aarch64-apple-darwin/lib/libLLVM.dylib'
PREFIX=TARGET.parents[1]
sys.path.insert(0,str(OWNER/'experiments/stable-cgu'))
import owned_stage as owned
FIELDS=['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']
def read(p):return json.loads(p.read_bytes())
def ident(p):return fields(p.lstat())
def fields(s):return {k:getattr(s,'st_'+k) for k in FIELDS}
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def bounded_hash(stream):
    digest=hashlib.sha256()
    while block:=stream.read(2**20):owned.disk(OWNER,9);digest.update(block)
    return digest.hexdigest()

class Stage:
    def __init__(self,digest):
        assert Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize
        assert sha(HERE/'inputs.json')==digest
        self.freeze=read(HERE/'inputs.json');self.plan=read(HERE/'plan.json');self.assessment=read(ASSESSMENT)
        assert self.plan['target']==str(TARGET)==self.assessment['target']
        assert dict(os.environ)==self.plan['environment'] and list(os.uname())==self.plan['platform']
        assert not WORK.exists() and not WORK.is_symlink();WORK.mkdir()
        self.record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),children=[],deleted=[],
            benchmark=False,scope='Retirement of original native01 toolchain completeness; not a cache-only deletion.')
        self.save()
    def save(self):owned.write(WORK/'receipt.json',self.record)
    def guard(self):
        for name,row in self.freeze['files'].items():
            p=Path(name);assert p.resolve(strict=True)==p and ident(p)==row['identity'] and sha(p)==row['sha256'] and ident(p)==row['identity'],name
        for name,row in self.plan['executors'].items():
            p=Path(name);assert str(p.resolve(strict=True))==row['resolved'] and ident(p)==row['route_identity']
            assert ident(Path(row['resolved']))==row['file_identity'] and sha(p)==row['sha256']
        for name,row in self.plan['protected_aliases'].items():
            p=Path(name);assert p.is_symlink() and ident(p)==row['identity'] and os.readlink(p)==row['target'] and str(p.resolve(strict=True))==row['resolved']
        for name,row in self.plan['protected_routes'].items():
            p=Path(name);assert p.resolve(strict=True)==p and ident(p)==row['identity'] and sha(p)==row['sha256'] and ident(p)==row['identity']
            assert (row['identity']['dev'],row['identity']['ino'])!=(self.assessment['identity']['dev'],self.assessment['identity']['ino'])
        for name,row in self.plan['historical_receipts'].items():
            receipt=read(Path(name));assert sha(Path(name))==row['sha256'] and receipt['status']==row['status'] and receipt['finished_at']==row['finished_at']
        archive=Path(self.assessment['archive']);assert sha(archive)==self.assessment['archive_sha256']
        with tarfile.open(archive,'r:xz') as stream:
            member=stream.getmember(self.assessment['archive_member'])
            assert member.isfile() and member.size==self.assessment['identity']['size']
            assert bounded_hash(stream.extractfile(member))==self.assessment['sha256']
            while stream.fileobj.read(2**20):owned.disk(OWNER,9)
        assert read(Path(self.plan['inventory']))['lib/libLLVM.dylib']==self.assessment['original_inventory']['record']
    def probe(self,row):
        out=WORK/'commands'/row['label']
        try:owned.run(row['argv'],cwd=OWNER,env=self.plan['environment'],out=out,capacity_root=OWNER,expected=(1,),pass_fds=(self.fd,))
        finally:
            if (out/'receipt.json').exists():self.record['children'].append(dict(path=str(out/'receipt.json'),sha256=sha(out/'receipt.json'),label=row['label']));self.save()
        assert (out/'stdout').read_bytes()==(out/'stderr').read_bytes()==b''
        assert read(out/'receipt.json')['returncode']==1
    def remove(self):
        before=self.assessment['identity'];assert stat.S_ISREG(before['mode']) and before['nlink']==1
        assert TARGET.parent.resolve(strict=True)==TARGET.parent and ident(TARGET.parent)==self.plan['parent_identity']
        parent=os.open(TARGET.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        fd=None
        try:
            assert fields(os.fstat(parent))==self.plan['parent_identity']
            assert fields(os.stat(TARGET.name,dir_fd=parent,follow_symlinks=False))==before
            fd=os.open(TARGET.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent)
            assert fields(os.fstat(fd))==before
            with os.fdopen(os.dup(fd),'rb') as stream:assert bounded_hash(stream)==self.assessment['sha256']
            assert fields(os.fstat(fd))==before and fields(os.stat(TARGET.name,dir_fd=parent,follow_symlinks=False))==before
            assert ident(TARGET.parent)==fields(os.fstat(parent))==self.plan['parent_identity']
            owned.disk(OWNER,9)
            os.unlink(TARGET.name,dir_fd=parent)
            after=fields(os.fstat(fd));assert after['nlink']==0 and all(after[k]==before[k] for k in ['dev','ino','mode','size','mtime_ns'])
            assert not TARGET.exists() and not TARGET.is_symlink()
            row=dict(path=str(TARGET),before=before,unlinked_open_fd=after,time=time.time(),parent_after=fields(os.fstat(parent)))
            owned.write(WORK/'deleted.json',row);self.record['deleted']=[row];self.record['original_toolchain_retired']=True;self.save()
        finally:
            if fd is not None:os.close(fd)
            os.close(parent)
    def run(self):
        try:
            with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
                self.fd=fd;self.record.update(status='running',admitted_at=time.time(),free_bytes_before=owned.disk(OWNER,9));self.save()
                self.guard();assert ident(TARGET)==self.assessment['identity'] and sha(TARGET)==self.assessment['sha256']
                for row in self.plan['commands']:self.probe(row)
                self.guard();self.remove();self.guard()
                assert len(self.record['children'])==2 and len(self.record['deleted'])==1 and not TARGET.exists()
                self.record.update(status='passed',original_toolchain_complete=False,official_archive_unchanged=True,qualified_copies_and_R_X_routes_unchanged=True,
                    historical_guards_not_relabelled=True,free_bytes_after=owned.disk(OWNER,9))
        except BaseException as error:self.record.update(status='failed',error=repr(error));raise
        finally:self.record['finished_at']=time.time();self.save()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);Stage(parser.parse_args().inputs_sha256).run()
