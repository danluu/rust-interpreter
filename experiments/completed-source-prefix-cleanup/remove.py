#!/usr/bin/env python3
"""Remove only exact redundant second-prefix copies after evidence admission."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
import time

from assess import OWNER,R,ROOTS,FIELDS,ASSESSMENT,read,sha,identity,snapshot,history
import preserve
import qualify_preservation as qualified

HERE=Path(__file__).resolve().parent
WORK=OWNER/'.work/completed-source-prefix-cleanup-01'
sys.path.insert(0,str(OWNER/'experiments/stable-cgu'))
import owned_stage as owned

def require(value,message):
    if not value:raise RuntimeError(message)

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
    def preservation(self):
        proof=read(preserve.WORK/'receipt.json');assessment=read(ASSESSMENT)
        admission=read(qualified.WORK/'receipt.json')
        require(admission['status']=='passed' and admission['prior_receipt_sha256']==sha(preserve.WORK/'receipt.json') and
                admission['complete_member_bytes_and_gzip_trailers_verified'] is True,'retained bytes lack canonical admission')
        require(proof['status']=='retained-not-deleted' and assessment['status']=='assessed-not-deleted','evidence not qualified')
        original=preserve.verify_archive(preserve.ORIGINAL,qualified.capacity);shared=preserve.verify_archive(preserve.RESULT,qualified.capacity)
        require(len(original)==641 and len(shared)==304,'archive membership differs')
        for name,row in proof['original_live_evidence'].items():
            path=Path(name);require(sha(path)==row['sha256'] and path.stat().st_size==row['bytes'] and original[row['archive_member']]=={k:row[k] for k in ['sha256','bytes']},'original evidence changed')
        for name,row in proof['original_archived_only'].items():require(original[name]==row,'archived-only failure artifact changed')
        for name,row in proof['shared_sources'].items():
            path=Path(row['path']);require(identity(path)==row['identity'] and sha(path)==row['sha256'] and shared[name]=={k:row[k] for k in ['sha256','bytes']},'shared history changed')
        for name,root in ROOTS.items():
            current,unused=history(name);require(current==assessment['roots'][name]['history'],'historical command history changed')
            preserve.validate_outer(name)
        for name,row in assessment['retained_original_files'].items():
            path=Path(name);require(path.resolve(strict=True)==path and identity(path)==row['identity'] and qualified.bounded_sha(path)==row['sha256'],'retained original changed: '+name)
            require(identity(path)==row['identity'],'retained original changed during read')
        for name,row in read(HERE/'plan-01/original-directories.json').items():
            require(Path(name).resolve(strict=True)==Path(name) and identity(Path(name))==row,'retained original directory changed')
        return assessment
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
                    for role,proof in expected['roles'].items():
                        for relative,source in proof['retained_files'].items():require(qualified.bounded_sha(root/role/relative)==assessment['retained_original_files'][source]['sha256'],'copy content changed')
                    admitted[name]=rows
                    child,text=self.probe(self.plan['commands'][len(self.record['children'])]);require(child['returncode']==1 and not text,'copy has open handles')
                child,text=self.probe(self.plan['commands'][-1])
                for line in text.splitlines():
                    fields=line.split();require(len(fields)>=9,'malformed process identity')
                    require(fields[3:8]!=self.plan['owned_start_times'].get(fields[0]),'original process remains alive')
                self.guard();owned.write(WORK/'admitted-inventory.json',admitted)
                # Recheck every root before the first chmod/unlink, not just each
                # root when its turn arrives. Permission changes affect copies only.
                for name,root in ROOTS.items():require(snapshot(root)[0]==admitted[name],'copy changed after quiescence probes')
                for name,root in ROOTS.items():
                    require(snapshot(root)[0]==admitted[name],'copy changed before removal')
                    rows=self.writable_directories(root,admitted[name]);self.save();self.remove(root,rows)
                self.preservation();self.guard()
                require(len(self.record['deleted'])==52548 and len(self.record['children'])==4,'incomplete exact removal')
                self.record.update(status='passed',deleted_entries=52548,retained_originals_unchanged=True,all_three_copies_absent=True,free_bytes_after=owned.disk(OWNER,9))
        except BaseException as error:self.record.update(status='failed',error=repr(error));raise
        finally:self.record['finished_at']=time.time();self.save()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);args=parser.parse_args();Cleanup(args.inputs_sha256).execute()
