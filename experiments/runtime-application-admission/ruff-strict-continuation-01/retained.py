"""Bounded exact prior evidence/cache inventories; never follows symlinks."""
import hashlib
import os
from pathlib import Path
import stat

MAX_MEMBERS = 100000
MAX_BYTES = 6*2**30


def require(ok,message):
    if not ok:raise ValueError(message)


def stamp(path):
    s=path.lstat()
    return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]


def tree(root, *, skip=(), full=True, floor=lambda:None):
    root=Path(root);require(root.resolve(strict=True)==root and root.is_dir(),'ordinary prior tree required')
    result={};total=0
    def visit(path):
        nonlocal total
        relative=str(path.relative_to(root))
        if relative in skip:return
        require(len(result)<MAX_MEMBERS,'prior tree member bound exceeded')
        if len(result)%256==0:floor()
        before=stamp(path);kind=before[2]
        if stat.S_ISDIR(kind):
            result[relative]=dict(kind='directory',stamp=before)
            for child in sorted(path.iterdir()):visit(child)
        elif stat.S_ISLNK(kind):
            result[relative]=dict(kind='link',stamp=before,target=os.readlink(path))
        else:
            require(stat.S_ISREG(kind),'special prior tree member')
            total+=before[3];require(total<=MAX_BYTES,'prior tree byte bound exceeded')
            row=dict(kind='file',stamp=before)
            if full:
                with path.open('rb') as stream:row['sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
            result[relative]=row
        require(stamp(path)==before,'prior tree changed during read')
    visit(root)
    return result


def verify(root, expected, *, skip=(), full=True, floor=lambda:None):
    actual=tree(root,skip=skip,full=full,floor=floor)
    wanted=expected if full else {name:{k:v for k,v in row.items() if k!='sha256'} for name,row in expected.items()}
    require(actual==wanted,'prior evidence/cache inventory changed: '+str(root))
    return dict(members=len(actual),files=sum(row['kind']=='file' for row in actual.values()))
