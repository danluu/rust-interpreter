#!/usr/bin/env python3
"""Retain exact negative-source deltas and remove six completed copied sysroots."""
import argparse
import gzip
import hashlib
import io
import tarfile
import json
import os
from pathlib import Path
import stat
import sys
import time

from assess import OWNER,R,ROOTS,OUT as ASSESSMENT,base,VICTIM
FIELDS=base.FIELDS
read,sha,identity,snapshot,history=base.read,base.sha,base.identity,base.snapshot,base.history
ORIGINAL=R/'results/mono-production-source-observables-02'
SHARED=OWNER/'results/completed-source-prefix-preservation-01'
PRESERVED=OWNER/'.work/completed-source-prefix-preservation-01/receipt.json'
ADMITTED=OWNER/'.work/completed-source-prefix-preservation-admission-02/receipt.json'

HERE=Path(__file__).resolve().parent
WORK=OWNER/'.work/completed-negative-source-cleanup-01'
RESULT=OWNER/'results/completed-negative-source-preservation-01'
sys.path.insert(0,str(OWNER/'experiments/stable-cgu'))
import owned_stage as owned

def require(value,message):
    if not value:raise RuntimeError(message)


def outer(name):
    return R/'.work/experiments'/('mono-production-source-observables-'+('shared-supervisor-01' if name=='shared-01' else 'supervisor-'+name))
def validate_outer(name):
    hist,unused=history(name);root=outer(name);status=read(root/'status.json');plan=read(root/'plan.json')
    require(status['status']=='finished' and status['returncode']==(1 if name=='01' else 0),'original supervisor outcome differs')
    require(status['child_pid']==hist['parent_pid'] and status['cwd']==str(R) and status['command']==plan['command'],'original supervisor association differs')
    require(sha(root/'plan.json')==status['plan_sha256'] and sha(root/'command.log')==status['log_sha256'] and status['started_at']<=hist['completed_at']<=status['finished_at'],'original supervisor hash/time differs')
    return status

class Cleanup:
    def __init__(self,digest):
        require(Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize,'fixed owner/Python required')
        require(sha(HERE/'plan-01/inputs.json')==digest,'freeze differs')
        self.freeze=read(HERE/'plan-01/inputs.json');self.plan=read(HERE/'plan-01/plan.json')
        require(self.plan['roots']=={name:str(root) for name,root in ROOTS.items()},'fixed roots differ')
        require(dict(os.environ)==self.plan['environment'],'environment differs')
        self.guard();require(not WORK.exists() and not WORK.is_symlink(),'fresh evidence required');WORK.mkdir()
        self.owned=owned
        self.record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),children=[],deleted=[],directory_permissions=[],benchmark=False)
        self.save()
    def save(self):owned.write(WORK/'receipt.json',self.record)
    def guard(self):
        require(list(os.uname())==self.plan['platform'],'platform changed')
        for name,row in self.freeze['files'].items():
            path=Path(name)
            require(path.resolve(strict=True)==path and identity(path)==row['identity'] and sha(path)==row['sha256'],'frozen evidence/source changed: '+name)
        for name,row in self.plan['executors'].items():
            path=Path(name)
            require(str(path.resolve(strict=True))==row['resolved'] and identity(path)==row['route_identity'] and
                    identity(Path(row['resolved']))==row['file_identity'] and sha(path)==row['sha256'],'executor route changed')
    def bounded_sha(self,path):
        digest=hashlib.sha256()
        with Path(path).open('rb') as stream:
            while block:=stream.read(2**20):owned.disk(OWNER,9);digest.update(block)
        return digest.hexdigest()
    def archive(self,root,count):
        manifest=read(root/'manifest.json');seen={}
        with tarfile.open(root/'evidence.tar.gz','r:gz') as archive:
            members=archive.getmembers();require(len(members)==len(manifest)==count and {m.name for m in members}==set(manifest),'archive membership differs')
            for member in members:
                proof=manifest[member.name]
                require(member.isfile() or (member.islnk() and member.linkname in seen and seen[member.linkname]==proof['sha256']),'archive member type/link differs')
                stream=archive.extractfile(member);digest=hashlib.sha256();size=0
                while block:=stream.read(2**20):owned.disk(OWNER,9);digest.update(block);size+=len(block)
                require(size==proof['bytes'] and digest.hexdigest()==proof['sha256'],'archive content differs')
                seen[member.name]=digest.hexdigest()
            while archive.fileobj.read(2**20):owned.disk(OWNER,9)
        with gzip.open(root/'evidence.tar.gz','rb') as stream:
            while stream.read(2**20):owned.disk(OWNER,9)
        return manifest
    def preservation(self):
        proof=read(PRESERVED);admission=read(ADMITTED);assessment=read(ASSESSMENT)
        require(admission['status']=='passed' and admission['prior_receipt_sha256']==sha(PRESERVED) and admission['complete_member_bytes_and_gzip_trailers_verified'],'historical archive admission differs')
        original=self.archive(ORIGINAL,641);shared=self.archive(SHARED,304)
        for root,key in [(ORIGINAL,'original_archive'),(SHARED,'shared_archive')]:
            require(self.bounded_sha(root/'evidence.tar.gz')==proof[key]['sha256'] and sha(root/'manifest.json')==proof[key]['manifest_sha256'],'historical archive identity differs')
        for name,row in proof['original_live_evidence'].items():
            path=Path(name);before=identity(path)
            require(path.resolve(strict=True)==path and self.bounded_sha(path)==row['sha256'] and path.stat().st_size==row['bytes'] and identity(path)==before,'original history changed')
            require(original[row['archive_member']]=={key:row[key] for key in ['sha256','bytes']},'original archive association differs')
        for name,row in proof['original_archived_only'].items():require(original[name]==row,'archived-only failure evidence differs')
        for name,row in proof['shared_sources'].items():
            path=Path(row['path']);require(identity(path)==row['identity'] and self.bounded_sha(path)==row['sha256'] and identity(path)==row['identity'],'shared history changed')
            require(shared[name]=={key:row[key] for key in ['sha256','bytes']},'shared archive association differs')
        for name in base.NAMES:
            current,unused=history(name)
            require(all(current==assessment['roots'][name+'-'+kind]['history'] for kind in ['missing','corrupt']),'original outcomes/history changed')
            validate_outer(name)
        for name,row in assessment['retained_original_files'].items():
            path=Path(name);require(path.resolve(strict=True)==path and identity(path)==row['identity'] and self.bounded_sha(path)==row['sha256'] and identity(path)==row['identity'],'retained original changed')
        for root,rows in assessment['retained_original_directories'].items():
            for name,row in rows.items():
                path=Path(root) if name=='.' else Path(root)/name
                require(path.resolve(strict=True)==path and identity(path)==row,'retained original directory changed')
        if 'retention' in self.record:
            retained=self.record['retention'];require(sha(RESULT/'evidence.tar.gz')==retained['archive_sha256'] and sha(RESULT/'manifest.json')==retained['manifest_sha256'],'delta archive changed')
            require(self.archive(RESULT,4)==retained['members'],'retained actual deltas differ')
        return assessment
    def retain(self,assessment):
        require(not RESULT.exists() and not RESULT.is_symlink(),'fresh delta archive required')
        data={'absence-and-origin.json':(json.dumps(self.plan['deltas'],sort_keys=True,indent=2)+'\n').encode()}
        for name,root in ROOTS.items():
            row=assessment['roots'][name];victim=root/VICTIM
            if row['absence'] is not None:require(not victim.exists() and not victim.is_symlink(),'missing-source negative reappeared')
            else:
                require(identity(victim)==row['entries'][VICTIM],'corrupt-source identity changed')
                value=victim.read_bytes();require(value==b'X'*6751 and hashlib.sha256(value).hexdigest()==row['divergent_file']['sha256'] and identity(victim)==row['entries'][VICTIM],'corrupt-source bytes changed')
                data[name+'/panic.rs']=value
        require(len(data)==4 and sum(map(len,data.values()))<64*2**10,'delta archive scope/bound differs')
        RESULT.mkdir();manifest={name:dict(bytes=len(value),sha256=hashlib.sha256(value).hexdigest()) for name,value in data.items()}
        owned.write(RESULT/'manifest.json',manifest)
        class Capped:
            def __init__(self,raw):self.raw=raw
            def write(self,value):
                owned.disk(OWNER,9);require(self.raw.tell()+len(value)<=2**20,'delta archive cap reached before write')
                written=self.raw.write(value);require(written==len(value),'short archive write');return written
            def tell(self):return self.raw.tell()
            def flush(self):return self.raw.flush()
        with (RESULT/'evidence.tar.gz').open('xb') as raw,gzip.GzipFile(filename='',fileobj=Capped(raw),mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as archive:
            for name,value in data.items():
                item=tarfile.TarInfo(name);item.size=len(value);item.mode=0o644;item.mtime=0;archive.addfile(item,io.BytesIO(value))
        require(self.archive(RESULT,4)==manifest,'new actual delta readback failed')
        self.record['retention']=dict(archive_sha256=sha(RESULT/'evidence.tar.gz'),manifest_sha256=sha(RESULT/'manifest.json'),members=manifest,full_gzip_trailer_verified=True)
        self.save()
    def probe(self,spec):
        out=WORK/'commands'/spec['label']
        try:owned.run(spec['argv'],cwd=OWNER,env=self.plan['environment'],out=out,capacity_root=OWNER,expected=tuple(spec['expected']),pass_fds=(self.lockfd,))
        finally:
            if (out/'receipt.json').exists():self.record['children'].append(dict(label=spec['label'],path=str(out/'receipt.json'),sha256=sha(out/'receipt.json')));self.save()
        require((out/'stderr').read_bytes()==b'' and (out/'stdout').stat().st_size<1024**2,'unexpected probe diagnostics')
        return read(out/'receipt.json'),(out/'stdout').read_text()
    def writable_directories(self,root,rows):
        result=dict(rows)
        for name,row in rows.items():
            if not stat.S_ISDIR(row['mode']) or row['mode']&stat.S_IWUSR:continue
            path=root if name=='.' else root/name
            require(path.resolve(strict=True)==path and identity(path)==row,'directory changed before permission admission')
            fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:
                opened=os.fstat(fd);current={key:getattr(opened,'st_'+key) for key in FIELDS}
                require(current==row,'opened directory identity differs')
                owned.disk(OWNER,9)
                os.fchmod(fd,stat.S_IMODE(row['mode'])|stat.S_IWUSR)
                changed=os.fstat(fd);after={key:getattr(changed,'st_'+key) for key in FIELDS}
                require(all(after[key]==row[key] for key in ['dev','ino','nlink','size','mtime_ns']) and
                        after['mode']==(row['mode']|stat.S_IWUSR) and identity(path)==after,'unexpected permission transition')
                result[name]=after
                transition=dict(path=str(path),before=row,after=after,time=time.time())
                with (WORK/'directory-permissions.jsonl').open('a') as ledger:ledger.write(json.dumps(transition)+'\n')
                self.record['directory_permissions'].append(transition)
            finally:os.close(fd)
        return result

    def remove(self, root, rows):
        """All mutations are relative to held, exact no-follow directory FDs."""
        expected=dict(rows)
        outer_expected=identity(root.parent)
        flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
        def fst(fd):
            value=os.fstat(fd);return {key:getattr(value,'st_'+key) for key in FIELDS}
        def at(parent,name):
            value=os.stat(name,dir_fd=parent,follow_symlinks=False)
            return {key:getattr(value,'st_'+key) for key in FIELDS}
        outer_fd=os.open(root.parent,flags)
        root_fd=None
        try:
            require(fst(outer_fd)==outer_expected,'opened outer parent differs')
            require(at(outer_fd,root.name)==expected['.'],'root route changed')
            root_fd=os.open(root.name,flags,dir_fd=outer_fd)
            require(fst(root_fd)==expected['.'],'opened root differs')
            def parent_fd(name):
                require(name!='.' and not Path(name).is_absolute() and '..' not in Path(name).parts,'invalid relative target')
                require(at(outer_fd,root.name)==expected['.'] and fst(root_fd)==expected['.'],'held root differs')
                fd=os.dup(root_fd);key='.'
                try:
                    parts=Path(name).parts[:-1]
                    for part in parts:
                        require(fst(fd)==expected[key],'held ancestor changed')
                        child_key=part if key=='.' else key+'/'+part
                        require(at(fd,part)==expected[child_key],'ancestor route changed')
                        child=os.open(part,flags,dir_fd=fd)
                        try:require(fst(child)==expected[child_key],'opened ancestor changed')
                        except BaseException:os.close(child);raise
                        os.close(fd);fd=child;key=child_key
                    require(fst(fd)==expected[key],'mutation parent differs')
                    return fd,key,Path(name).name
                except BaseException:os.close(fd);raise
            def finished(name,parent,key):
                del expected[name]
                if key is not None:
                    after=fst(parent);before=expected[key]
                    require(all(after[field]==before[field] for field in ['dev','ino','mode']),'parent replaced during owned mutation')
                    expected[key]=after
                self.record['deleted'].append(str(root if name=='.' else root/name))
                with (WORK/'deleted.jsonl').open('a') as ledger:
                    ledger.write(json.dumps(dict(path=str(root if name=='.' else root/name),time=time.time()))+'\n')
            for name in sorted(name for name,row in rows.items() if stat.S_ISREG(row['mode'])):
                owned.disk(OWNER,9);parent,key,basename=parent_fd(name);fd=None
                try:
                    before=expected[name]
                    require(before['nlink']==1 and at(parent,basename)==before,'file entry changed or has outside hardlink')
                    fd=os.open(basename,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent)
                    require(fst(fd)==before and at(parent,basename)==before and fst(parent)==expected[key],'opened file or parent changed')
                    os.unlink(basename,dir_fd=parent)
                    after=fst(fd)
                    require(all(after[field]==before[field] for field in ['dev','ino','mode','size','mtime_ns']) and after['nlink']==0,'unexpected inode after unlink')
                    finished(name,parent,key)
                finally:
                    if fd is not None:os.close(fd)
                    os.close(parent)
            for name in sorted([name for name in expected if name!='.'],key=lambda value:(len(Path(value).parts),value),reverse=True):
                owned.disk(OWNER,9);parent,key,basename=parent_fd(name);fd=None
                try:
                    before=expected[name];require(stat.S_ISDIR(before['mode']) and at(parent,basename)==before,'directory entry changed')
                    fd=os.open(basename,flags,dir_fd=parent)
                    require(fst(fd)==before and not os.listdir(fd) and at(parent,basename)==before and fst(parent)==expected[key],'directory not exact/empty')
                    os.rmdir(basename,dir_fd=parent);finished(name,parent,key)
                finally:
                    if fd is not None:os.close(fd)
                    os.close(parent)
            owned.disk(OWNER,9)
            require(set(expected)=={'.'} and fst(root_fd)==expected['.'] and not os.listdir(root_fd),'root not exact/empty')
            require(fst(outer_fd)==outer_expected and at(outer_fd,root.name)==expected['.'],'outer root binding changed')
            os.rmdir(root.name,dir_fd=outer_fd);finished('.',outer_fd,None)
            require(not expected and not root.exists() and not root.is_symlink(),'removal incomplete')
        finally:
            if root_fd is not None:os.close(root_fd)
            os.close(outer_fd)


    def execute(self):
        try:
            with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
                self.lockfd=fd;self.record.update(status='running',admitted_at=time.time(),free_bytes_before=owned.disk(OWNER,9));self.save()
                self.guard();assessment=self.preservation();admitted={}
                for name,root in ROOTS.items():
                    rows,allocated=snapshot(root);expected=assessment['roots'][name]
                    require(rows==expected['entries'] and allocated<=expected['allocated_bytes']+16*2**20,'copy identity/membership/allocation changed')
                    # Rehash actual duplicate payload immediately before removal admission.
                    for relative,digest in expected['negative']['after_files'].items():require(self.bounded_sha(root/relative)==digest,'negative-copy content changed')
                    if expected['absence'] is not None:require(not (root/VICTIM).exists() and not (root/VICTIM).is_symlink(),'negative absence changed')
                    admitted[name]=rows
                    child,text=self.probe(self.plan['commands'][len(self.record['children'])]);require(child['returncode']==1 and not text,'copy has open handles')
                child,text=self.probe(self.plan['commands'][-1])
                for line in text.splitlines():
                    fields=line.split();require(len(fields)>=9,'malformed process identity')
                    require(fields[3:8]!=self.plan['owned_start_times'].get(fields[0]),'original process remains alive')
                self.guard();self.retain(assessment);self.preservation();owned.write(WORK/'admitted-inventory.json',admitted)
                # Recheck every root before the first chmod/unlink, not just each
                # root when its turn arrives. Permission changes affect copies only.
                for name,root in ROOTS.items():require(snapshot(root)[0]==admitted[name],'copy changed after quiescence probes')
                for name,root in ROOTS.items():
                    require(snapshot(root)[0]==admitted[name],'copy changed before removal')
                    rows=self.writable_directories(root,admitted[name]);self.save();self.remove(root,rows)
                self.preservation();self.guard()
                require(len(self.record['deleted'])==27657 and len(self.record['children'])==7,'incomplete exact removal')
                self.record.update(status='passed',deleted_entries=27657,retained_originals_unchanged=True,all_six_negative_copies_absent=True,free_bytes_after=owned.disk(OWNER,9))
        except BaseException as error:self.record.update(status='failed',error=repr(error));raise
        finally:self.record['finished_at']=time.time();self.save()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);args=parser.parse_args();Cleanup(args.inputs_sha256).execute()
