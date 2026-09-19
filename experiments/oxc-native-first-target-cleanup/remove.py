#!/usr/bin/env python3
"""Retain final native01 artifacts, then remove only its completed derived target."""
import argparse
import gzip
import hashlib
import tarfile
import json
import os
from pathlib import Path
import stat
import sys
import time

from assess import OWNER,RUN,ROOT,ROOTS,OUTER,ARCHIVE,FIELDS,ASSESSMENT,read,sha,identity,snapshot,history

HERE=Path(__file__).resolve().parent
WORK=OWNER/'.work/oxc-native-first-target-cleanup-01'
RESULT=OWNER/'results/oxc-native-first-target-preservation-01'
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
    def archive(self,directory,expected_count,live=False):
        manifest=read(directory/'manifest.json')['members'];require(len(manifest)==expected_count,'archive count differs')
        with tarfile.open(directory/'evidence.tar.gz','r:gz') as archive:
            members=archive.getmembers()
            require(len(members)==expected_count and {m.name for m in members}==set(manifest),'archive membership differs')
            for member in members:
                proof=manifest[member.name];require(member.isfile() and member.size==proof['bytes'],'archive type/size differs')
                stream=archive.extractfile(member);digest=hashlib.sha256();size=0
                while block:=stream.read(2**20):
                    owned.disk(OWNER,9);size+=len(block);digest.update(block)
                require(size==proof['bytes'] and digest.hexdigest()==proof['sha256'],'archive member bytes differ')
                if live:
                    source=OWNER/member.name;before=identity(source)
                    require(source.resolve(strict=True)==source and sha(source)==proof['sha256'] and identity(source)==before,'historical evidence changed')
            while archive.fileobj.read(2**20):owned.disk(OWNER,9)
        return manifest
    def retain(self):
        require(not RESULT.exists() and not RESULT.is_symlink(),'fresh artifact archive required')
        assessment=read(ASSESSMENT);manifest={name:{key:row[key] for key in ['bytes','sha256']} for name,row in assessment['final_artifacts'].items()}
        require(len(manifest)==7 and sum(row['bytes'] for row in manifest.values())<112*2**20,'artifact retention bound differs')
        RESULT.mkdir();owned.write(RESULT/'manifest.json',dict(members=manifest,source_root=str(ROOT),assessment_sha256=sha(ASSESSMENT),
            scope='Seven actual final selected native01 output files. Earlier overwritten binaries are not claimed; clean performance remains unqualified.'))
        class Reader:
            def __init__(self,stream):self.stream=stream;self.digest=hashlib.sha256();self.size=0
            def read(self,size):
                owned.disk(OWNER,9)
                require((RESULT/'evidence.tar.gz').stat().st_size<64*2**20,'retention archive allocation exceeded')
                value=self.stream.read(size);self.digest.update(value);self.size+=len(value);return value
        with (RESULT/'evidence.tar.gz').open('xb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as archive:
            for name,row in assessment['final_artifacts'].items():
                source=Path(row['source']);require(identity(source)==row['identity'] and source.resolve(strict=True)==source,'artifact identity changed')
                with source.open('rb') as stream:
                    entry=tarfile.TarInfo(name);entry.size=row['bytes'];entry.mode=0o644;entry.mtime=0
                    reader=Reader(stream);archive.addfile(entry,reader)
                    require(reader.size==row['bytes'] and reader.digest.hexdigest()==row['sha256'] and identity(source)==row['identity'],'artifact changed during retention')
        require((RESULT/'evidence.tar.gz').stat().st_size<64*2**20,'retention archive exceeded final bound')
        self.archive(RESULT,7)
        self.record['retention']=dict(archive_sha256=sha(RESULT/'evidence.tar.gz'),manifest_sha256=sha(RESULT/'manifest.json'),members=7,
                                      full_gzip_trailer_verified=True,all_final_artifact_bytes_retained=True)
        self.save()
    def preservation(self,before):
        assessment=read(ASSESSMENT);terminal,outer,verification=history()
        require(assessment['status']=='assessed-not-deleted' and assessment['root']==str(ROOT),'wrong target assessment')
        self.archive(ARCHIVE,286,True)
        if 'retention' in self.record:
            retention=self.record['retention']
            require(sha(RESULT/'evidence.tar.gz')==retention['archive_sha256'] and sha(RESULT/'manifest.json')==retention['manifest_sha256'],'retained artifact archive changed')
            manifest=self.archive(RESULT,7)
            require(manifest=={name:{key:row[key] for key in ['bytes','sha256']} for name,row in assessment['final_artifacts'].items()},'retention mapping differs')
        if before:
            for name,row in assessment['final_artifacts'].items():
                source=ROOT/name;require(identity(source)==row['identity'] and sha(source)==row['sha256'],'final artifact changed')
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
        groups={}
        for name,row in rows.items():
            if stat.S_ISREG(row['mode']):groups.setdefault((row['dev'],row['ino']),[]).append(name)
        for names in groups.values():
            require(all(rows[name]==rows[names[0]] for name in names) and rows[names[0]]['nlink']==len(names),'outside hardlink or inconsistent inode identity')
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
                    aliases=groups[(before['dev'],before['ino'])]
                    require(before['nlink']==len(aliases) and at(parent,basename)==before,'file entry changed or has outside hardlink')
                    fd=os.open(basename,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent)
                    require(fst(fd)==before and at(parent,basename)==before and fst(parent)==expected[key],'opened file or parent changed')
                    os.unlink(basename,dir_fd=parent)
                    after=fst(fd)
                    require(all(after[field]==before[field] for field in ['dev','ino','mode','size','mtime_ns']) and after['nlink']==before['nlink']-1,'unexpected inode after unlink')
                    finished(name,parent,key);aliases.remove(name)
                    for alias in aliases:
                        alias_parent,alias_key,alias_name=parent_fd(alias)
                        try:require(at(alias_parent,alias_name)==after,'remaining hardlink changed');expected[alias]=after
                        finally:os.close(alias_parent)
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
                self.guard();assessment=self.preservation(True)
                rows,allocated=snapshot(ROOT)
                require(rows==assessment['entries'] and allocated<=assessment['allocated_bytes']+16*2**20,'target changed since assessment')
                child,text=self.probe(self.plan['commands'][0]);require(child['returncode']==1 and not text,'target has open handles')
                child,text=self.probe(self.plan['commands'][1])
                for line in text.splitlines():
                    fields=line.split();require(len(fields)>=9,'malformed process identity')
                    require(fields[3:8]!=self.plan['owned_start_times'].get(fields[0]),'original process remains alive')
                self.guard();require(snapshot(ROOT)[0]==rows,'target changed after quiescence')
                self.retain();self.preservation(True)
                owned.write(WORK/'admitted-inventory.json',rows)
                require(snapshot(ROOT)[0]==rows,'target changed before removal')
                writable=self.writable_directories(ROOT,rows);self.save();self.remove(ROOT,writable)
                self.preservation(False);self.guard()
                require(len(self.record['deleted'])==assessment['entry_count']==4595 and len(self.record['children'])==2,'incomplete exact removal')
                self.record.update(status='passed',deleted_entries=4595,target_absent=True,all_final_artifacts_retained=True,
                    clean_native_performance_qualified=False,free_bytes_after=owned.disk(OWNER,9))
        except BaseException as error:self.record.update(status='failed',error=repr(error));raise
        finally:self.record['finished_at']=time.time();self.save()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);args=parser.parse_args();Cleanup(args.inputs_sha256).execute()
