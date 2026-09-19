#!/usr/bin/env python3
"""Remove only duplicate original installed docs, preserving qualified copies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[1]
WORK=OWNER/'.work/oxc-original-docs-cleanup-01'
ASSESSMENT=OWNER/'.work/oxc-original-docs-capacity-assessment-01.json'
ROOT=OWNER/'.work/oxc-native-setup-01/rustup/toolchains/1.98.1-aarch64-apple-darwin/share/doc/rust'
RETAINED=OWNER/'.work/oxc-native-toolchain-composition-01/toolchain/share/doc/rust'
FIELDS=['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']
sys.path.insert(0,str(OWNER/'experiments/stable-cgu'))
import owned_stage as owned
def require(value,message):
    if not value:raise RuntimeError(message)
def read(p):return json.loads(p.read_bytes())
def identity(p):
    s=p.lstat();return {k:getattr(s,'st_'+k) for k in FIELDS}
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def snapshot(root):
    require(root.resolve(strict=True)==root,'root aliased');rows={'.':identity(root)};allocated=root.lstat().st_blocks*512
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(directory)/name;s=p.lstat();require(stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode),'special entry')
            require(p.resolve(strict=True)==p,'aliased entry')
            if stat.S_ISREG(s.st_mode):require(s.st_nlink==1,'outside file hardlink')
            rows[str(p.relative_to(root))]=identity(p);allocated+=s.st_blocks*512
    return rows,allocated

class Cleanup:
    def __init__(self,digest):
        require(Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize,'owner/Python differs')
        require(sha(HERE/'inputs.json')==digest,'freeze differs')
        self.freeze=read(HERE/'inputs.json');self.plan=read(HERE/'plan.json');self.assessment=read(ASSESSMENT)
        require(self.plan['root']==str(ROOT)==self.assessment['target'] and self.plan['retained']==str(RETAINED)==self.assessment['retained'],'fixed scope differs')
        require(dict(os.environ)==self.plan['environment'] and list(os.uname())==self.plan['platform'],'environment differs')
        require(not WORK.exists() and not WORK.is_symlink(),'fresh evidence required');WORK.mkdir()
        self.record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),children=[],deleted=[],directory_permissions=[],benchmark=False)
        self.save()
    def save(self):owned.write(WORK/'receipt.json',self.record)
    def guard(self):
        for name,row in self.freeze['files'].items():
            p=Path(name);require(p.resolve(strict=True)==p and identity(p)==row['identity'] and sha(p)==row['sha256'] and identity(p)==row['identity'],'frozen bytes changed: '+name)
        for name,row in self.plan['executors'].items():
            p=Path(name);require(str(p.resolve(strict=True))==row['resolved'] and identity(p)==row['route_identity'] and identity(Path(row['resolved']))==row['file_identity'] and sha(p)==row['sha256'],'executor differs')
        retirement=read(Path(self.plan['llvm_retirement']))
        require(retirement['status']=='passed' and retirement['original_toolchain_retired'] and not retirement['original_toolchain_complete'],'prior retirement differs')
        for name,row in self.plan['protected_aliases'].items():
            p=Path(name);require(p.is_symlink() and identity(p)==row['identity'] and os.readlink(p)==row['target'] and str(p.resolve(strict=True))==row['resolved'],'protected alias changed')
        for name,row in self.plan['protected_routes'].items():
            p=Path(name);require(p.resolve(strict=True)==p and identity(p)==row['identity'] and sha(p)==row['sha256'] and identity(p)==row['identity'],'protected provider changed')
    def preservation(self,original):
        a=self.assessment;kept,unused=snapshot(RETAINED);require(kept==a['retained_entries'],'retained documentation membership/identity changed')
        if original:
            current,allocated=snapshot(ROOT);require(current==a['entries'] and allocated<=a['allocated_bytes']+16*2**20,'original docs changed')
        inventories={name:read(Path(name)) for name in a['inventory_proofs']}
        for name,digest in a['files'].items():
            owned.disk(OWNER,9);key='share/doc/rust/'+name
            records=[inv[key] for inv in inventories.values()];require(records[0]==records[1] and records[0]['sha256']==digest,'historical inventory mapping changed')
            p=RETAINED/name;require(identity(p)==a['retained_entries'][name] and sha(p)==digest and identity(p)==a['retained_entries'][name],'retained documentation bytes changed')
            if original:
                q=ROOT/name;require(identity(q)==a['entries'][name] and sha(q)==digest and identity(q)==a['entries'][name],'original documentation bytes changed')
                require((a['entries'][name]['dev'],a['entries'][name]['ino'])!=(a['retained_entries'][name]['dev'],a['retained_entries'][name]['ino']),'documentation aliases retained copy')
        require(snapshot(RETAINED)[0]==a['retained_entries'],'retained documentation changed during verification')
        if original:require(snapshot(ROOT)[0]==a['entries'],'original documentation changed during verification')
    def probe(self,row):
        out=WORK/'commands'/row['label']
        try:owned.run(row['argv'],cwd=OWNER,env=self.plan['environment'],out=out,capacity_root=OWNER,expected=(1,),pass_fds=(self.lockfd,))
        finally:
            if (out/'receipt.json').exists():self.record['children'].append(dict(label=row['label'],path=str(out/'receipt.json'),sha256=sha(out/'receipt.json')));self.save()
        require((out/'stdout').read_bytes()==(out/'stderr').read_bytes()==b'' and read(out/'receipt.json')['returncode']==1,'documentation has open handles')

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
                self.guard();self.preservation(True)
                for row in self.plan['commands']:self.probe(row)
                self.guard();self.preservation(True)
                owned.write(WORK/'admitted-assessment.json',dict(path=str(ASSESSMENT),sha256=sha(ASSESSMENT),exact_entries=67312,retained_files=65826))
                rows=self.writable_directories(ROOT,self.assessment['entries']);self.save();self.remove(ROOT,rows)
                self.preservation(False);self.guard()
                require(len(self.record['deleted'])==67312 and len(self.record['children'])==2 and not ROOT.exists(),'incomplete exact cleanup')
                self.record.update(status='passed',deleted_entries=67312,retained_documentation_unchanged=True,compiler_providers_unchanged=True,original_toolchain_complete=False,free_bytes_after=owned.disk(OWNER,9))
        except BaseException as error:self.record.update(status='failed',error=repr(error));raise
        finally:self.record['finished_at']=time.time();self.save()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);Cleanup(parser.parse_args().inputs_sha256).execute()
