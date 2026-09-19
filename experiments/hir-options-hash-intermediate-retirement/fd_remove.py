"""Exact ordinary-file unlink with durable intent and completion observations.

Caller supplies a complete admitted tree, selected files, outer identity and
capacity check. This module never discovers scope, removes directories, changes
permissions, or invokes another process.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')

def identity(info):return {key:getattr(info,'st_'+key) for key in FIELDS}
def require(value,message):
    if not value:raise RuntimeError(message)
def event(path,value):
    with path.open('a') as output:
        output.write(json.dumps(value,sort_keys=True)+'\n');output.flush();os.fsync(output.fileno())
def post_unlink(before,after,parent_before,parent_after,parent,remaining_names):
    require(all(after[k]==before[k] for k in ['dev','ino','mode','size','mtime_ns']) and after['nlink']==0,'unexpected inode after unlink')
    require(all(parent_after[k]==parent_before[k] for k in ['dev','ino','mode']),'directory identity changed during unlink')
    require(sorted(os.listdir(parent))==sorted(remaining_names),'directory membership changed beyond exact unlink')

def remove_files(root,rows,selected,outer_expected,ledger,capacity):
    expected=json.loads(json.dumps(rows));flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    require(root.resolve(strict=True)==root and root.is_dir() and not root.is_symlink(),'ordinary exact root required')
    require(set(selected)<=set(expected) and '.' not in selected,'selection escapes inventory')
    children={name:set() for name,row in expected.items() if row['kind']=='directory'}
    for name in expected:
        if name!='.':children[str(Path(name).parent)].add(Path(name).name)
    outer_fd=os.open(root.parent,flags);root_fd=None
    def fst(fd):return identity(os.fstat(fd))
    def at(parent,name):return identity(os.stat(name,dir_fd=parent,follow_symlinks=False))
    try:
        require(fst(outer_fd)==outer_expected,'outer parent changed')
        require(at(outer_fd,root.name)==expected['.']['identity'],'root route changed')
        root_fd=os.open(root.name,flags,dir_fd=outer_fd)
        require(fst(root_fd)==expected['.']['identity'],'opened root differs')
        for name in sorted(selected):
            capacity();parts=Path(name).parts
            require(parts and not Path(name).is_absolute() and '..' not in parts and name in expected,'invalid selected path')
            require(at(outer_fd,root.name)==expected['.']['identity'] and fst(root_fd)==expected['.']['identity'],'held root changed')
            parent=os.dup(root_fd);key='.';fd=None
            try:
                for part in parts[:-1]:
                    require(fst(parent)==expected[key]['identity'],'held ancestor changed')
                    child_key=part if key=='.' else key+'/'+part
                    require(expected[child_key]['kind']=='directory' and at(parent,part)==expected[child_key]['identity'],'ancestor route changed')
                    child=os.open(part,flags,dir_fd=parent)
                    try:require(fst(child)==expected[child_key]['identity'],'opened ancestor changed')
                    except BaseException:os.close(child);raise
                    os.close(parent);parent=child;key=child_key
                row=expected[name];before=row['identity'];parent_before=expected[key]['identity']
                require(row['kind']=='file' and before['nlink']==1 and stat.S_ISREG(before['mode']),'selected file has alias or wrong type')
                require(at(parent,parts[-1])==before and fst(parent)==parent_before,'entry or mutation parent changed')
                require(set(os.listdir(parent))==children[key],'pre-unlink directory membership differs')
                fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent)
                require(fst(fd)==before,'opened file changed')
                digest=hashlib.sha256()
                while block:=os.read(fd,8*2**20):capacity();digest.update(block)
                require(digest.hexdigest()==row['sha256'] and fst(fd)==before and at(parent,parts[-1])==before and fst(parent)==parent_before,'held bytes/entry changed')
                intent=dict(path=str(root/name),relative=name,before=before,sha256=row['sha256'],parent_before=parent_before)
                event(ledger,dict(intent,event='intent',time=time.time()))
                # Revalidate after durable intent publication as well.
                require(fst(fd)==before and at(parent,parts[-1])==before and fst(parent)==parent_before,'entry changed after intent')
                os.unlink(parts[-1],dir_fd=parent)
                event(ledger,dict(intent,event='unlinked',time=time.time()))
                # Every fallible postcondition follows durable completion.
                after=fst(fd);parent_after=fst(parent);remaining=children[key]-{parts[-1]}
                post_unlink(before,after,parent_before,parent_after,parent,remaining)
                event(ledger,dict(path=str(root/name),relative=name,event='validated',after=after,parent_after=parent_after,time=time.time()))
                children[key]=remaining;expected[key]['identity']=parent_after;del expected[name]
            finally:
                if fd is not None:os.close(fd)
                os.close(parent)
        require(fst(outer_fd)==outer_expected,'outer parent changed during retirement')
    finally:
        if root_fd is not None:os.close(root_fd)
        os.close(outer_fd)
    return expected
