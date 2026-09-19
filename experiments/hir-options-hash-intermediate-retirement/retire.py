#!/usr/bin/env python3
"""Retire only 4,646 admitted ordinary intermediate files; keep every directory."""
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
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
N=X/'.work/hir-options-hash-compiler-01'
S=N/'source'
ROOT=S/'build/aarch64-apple-darwin/stage1-rustc'
WORK=OWNER/'.work/hir-options-hash-intermediate-retirement-01'
PACKET=HERE/'plan-01'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
sys.path.insert(0,str(OWNER/'experiments/stable-cgu'))
import owned_stage as owned

def read(path):return json.loads(Path(path).read_bytes())
def identity(value):
    info=value if isinstance(value,os.stat_result) else Path(value).lstat()
    return {key:getattr(info,'st_'+key) for key in FIELDS}
def require(value,message):
    if not value:raise RuntimeError(message)
def capacity():return owned.disk(OWNER,9)
def sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*2**20),b''):
            capacity();result.update(block)
    return result.hexdigest()
def file(path):
    path=Path(path);before=identity(path)
    require(path.resolve(strict=True)==path and stat.S_ISREG(before['mode']),'ordinary canonical file required')
    digest=sha(path);require(identity(path)==before,'file changed while hashing')
    return dict(identity=before,sha256=digest)
def inventory(root,hashes=True):
    require(root.resolve(strict=True)==root and root.is_dir() and not root.is_symlink(),'ordinary root required')
    rows={'.':dict(kind='directory',identity=identity(root))};allocated=0;seen=set()
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            path=Path(parent)/name;before=identity(path);key=str(path.relative_to(root))
            inode=(before['dev'],before['ino'])
            if inode not in seen:allocated+=path.lstat().st_blocks*512;seen.add(inode)
            if stat.S_ISREG(before['mode']):
                rows[key]=dict(kind='file',**(file(path) if hashes else dict(identity=before)))
            elif stat.S_ISDIR(before['mode']):rows[key]=dict(kind='directory',identity=before)
            else:
                require(stat.S_ISLNK(before['mode']),'unsupported special entry')
                resolved=path.resolve(strict=True);require(resolved.is_relative_to(N),'link escapes admitted namespace')
                rows[key]=dict(kind='link',identity=before,target=os.readlink(path),resolved=str(resolved))
            require(identity(path)==before,'entry changed during inventory')
    return rows,allocated

def history():
    """Replay retained failed16/failed7 associations; no producer is rerun."""
    evidence=read(OWNER/'.work/hir-options-hash-intermediate-content-01.json')
    result=[]
    for index,proof in enumerate(evidence['histories']):
        path=Path(proof['path']);require(sha(path)==proof['sha256'],'historical terminal changed')
        terminal=read(path);count=16 if index==0 else 7
        require(terminal['status']=='failed' and len(terminal['commands'])==count,'failed history relabeled')
        expected_plan=X/('experiments/hir-options-hash/compiler-build-02/plan.json' if index==0 else 'experiments/hir-options-hash/compiler-build-continuation-01/plan.json')
        plan=read(expected_plan);rows=plan['children'][:16] if index==0 else plan['children'][16:23]
        previous=terminal['admitted_at']
        require(len(proof['children'])==count,'retained child count differs')
        for local,(ref,retained,wanted) in enumerate(zip(terminal['commands'],proof['children'],rows,strict=True)):
            child_path=path.parent/'commands'/f'{local:03}'/'receipt.json';child=read(child_path)
            require(ref==dict(path=str(child_path),sha256=sha(child_path),pid=child['pid'],command=wanted['argv']),'child association changed')
            require(retained['path']==str(child_path) and retained['sha256']==ref['sha256'],'content assessment history changed')
            failed=index==1 and local==6
            require(child['status']==('failed' if failed else 'finished') and child['returncode']==int(failed),'actual child outcome changed')
            require(child['command']==wanted['argv'] and child['cwd']==wanted['cwd']==str(S) and child['environment']==wanted['environment'],'actual command route changed')
            require(child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid'],'actual child ownership changed')
            require(previous<=child['started_at']<=child['finished_at']<=terminal['finished_at'],'actual history reordered');previous=child['finished_at']
            for stream,row in retained['streams'].items():
                raw=child_path.parent/stream
                require(row['path']==str(raw) and row['bytes']==raw.stat().st_size and sha(raw)==row['sha256']==child[stream+'_sha256'],'actual raw history changed')
        result.append(dict(path=str(path),sha256=sha(path),status=terminal['status'],children=count))
    return result

class Retirement:
    def __init__(self,digest):
        require(Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize,'fixed owner/Python required')
        require(sha(PACKET/'inputs.json')==digest,'freeze differs')
        self.freeze=read(PACKET/'inputs.json');self.plan=read(PACKET/'plan.json');self.assessment=read(PACKET/'assessment.json')
        require(self.plan['root']==str(ROOT) and self.plan['files']==4646 and self.plan['remove_directories'] is False,'scope differs')
        require(dict(os.environ)==self.plan['environment'],'environment differs')
        self.guard();require(not WORK.exists() and not WORK.is_symlink(),'fresh evidence required');WORK.mkdir()
        self.record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),children=[],deleted=[],benchmark=False)
        self.save()
    def save(self):owned.write(WORK/'receipt.json',self.record)
    def guard(self):
        require(list(os.uname())==self.plan['platform'],'platform changed')
        require(str(Path(sys.executable).resolve(strict=True))==self.plan['python'],'Python route changed')
        for name in self.assessment['transition']['consumer']['absent_before_retirement']:
            path=Path(name);require(not path.exists() and not path.is_symlink(),'consumer prepared or started before retirement: '+name)
        for name,row in self.freeze['files'].items():require(file(Path(name))==row,'frozen evidence/source changed: '+name)
        for name,row in self.plan['executors'].items():
            path=Path(name)
            require(str(path.resolve(strict=True))==row['resolved'] and identity(path)==row['route_identity'] and file(Path(row['resolved']))==row['file'],'executor route changed')
    def protected(self):
        for name,expected in self.assessment['protected_roots'].items():
            require(inventory(Path(name))[0]==expected,'protected provider tree changed: '+name)
        for name,row in self.assessment['protected_files'].items():require(file(Path(name))==row,'protected file changed: '+name)
        require(history()==self.assessment['history'],'historical proof changed')
    def probe(self,spec):
        out=WORK/'commands'/spec['label']
        try:owned.run(spec['argv'],cwd=OWNER,env=self.plan['environment'],out=out,capacity_root=OWNER,expected=tuple(spec['expected']),pass_fds=(self.lockfd,))
        finally:
            if (out/'receipt.json').exists():self.record['children'].append(dict(label=spec['label'],path=str(out/'receipt.json'),sha256=sha(out/'receipt.json')));self.save()
        require((out/'stderr').read_bytes()==b'' and (out/'stdout').stat().st_size<2**20,'unexpected probe output')
        return read(out/'receipt.json'),(out/'stdout').read_text()
    def remove_files(self,rows,selected):
        """Held-root traversal; only exact ordinary single-link files are unlinked."""
        expected=json.loads(json.dumps(rows));flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
        outer_expected=self.assessment['outer_parent'];outer_fd=os.open(ROOT.parent,flags);root_fd=None
        def fst(fd):return identity(os.fstat(fd))
        def at(parent,name):return identity(os.stat(name,dir_fd=parent,follow_symlinks=False))
        try:
            require(fst(outer_fd)==outer_expected,'outer parent changed')
            require(at(outer_fd,ROOT.name)==expected['.']['identity'],'root route changed')
            root_fd=os.open(ROOT.name,flags,dir_fd=outer_fd)
            require(fst(root_fd)==expected['.']['identity'],'opened root differs')
            for name in sorted(selected):
                capacity();parts=Path(name).parts
                require(parts and not Path(name).is_absolute() and '..' not in parts and name in expected,'invalid selected path')
                require(at(outer_fd,ROOT.name)==expected['.']['identity'] and fst(root_fd)==expected['.']['identity'],'held root changed')
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
                    fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent)
                    require(fst(fd)==before,'opened file changed')
                    # Rehash the held descriptor, not a path that could be swapped.
                    digest=hashlib.sha256()
                    while block:=os.read(fd,8*2**20):capacity();digest.update(block)
                    require(digest.hexdigest()==row['sha256'] and fst(fd)==before and at(parent,parts[-1])==before and fst(parent)==parent_before,'held bytes/entry changed')
                    os.unlink(parts[-1],dir_fd=parent)
                    after=fst(fd);parent_after=fst(parent)
                    require(all(after[k]==before[k] for k in ['dev','ino','mode','size','mtime_ns']) and after['nlink']==0,'unexpected inode after unlink')
                    require(all(parent_after[k]==parent_before[k] for k in ['dev','ino','mode','nlink']),'directory identity changed during unlink')
                    expected[key]['identity']=parent_after;del expected[name]
                    entry=dict(path=str(ROOT/name),relative=name,before=before,after=after,sha256=row['sha256'],parent_before=parent_before,parent_after=parent_after,time=time.time())
                    with (WORK/'deleted.jsonl').open('a') as ledger:ledger.write(json.dumps(entry,sort_keys=True)+'\n');ledger.flush();os.fsync(ledger.fileno())
                    self.record['deleted'].append(str(ROOT/name))
                finally:
                    if fd is not None:os.close(fd)
                    os.close(parent)
            require(fst(outer_fd)==outer_expected,'outer parent changed during retirement')
        finally:
            if root_fd is not None:os.close(root_fd)
            os.close(outer_fd)
        return expected
    def run(self):
        try:
            with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
                self.lockfd=fd;self.record.update(status='running',admitted_at=time.time(),free_bytes_before=capacity());self.save()
                self.guard();self.protected()
                rows,allocated=inventory(ROOT);require(rows==self.assessment['entries'],'full target changed')
                selected=self.assessment['selected'];require(len(selected)==4646,'selected list differs')
                # Original catalog bytes already exist outside N and are bound
                # by the freeze. Preserve stamp bytes and explicit transitions
                # outside N before the first unlink, without copying cache data.
                (WORK/'retained').mkdir()
                for name,row in self.assessment['stamp_files'].items():
                    source=Path(name);require(file(source)==row,'stamp changed before retention')
                    destination=WORK/'retained'/source.name
                    with destination.open('xb') as output:output.write(source.read_bytes())
                    require(sha(destination)==row['sha256'],'retained stamp differs')
                owned.write(WORK/'transition.json',self.assessment['transition'])
                owned.write(WORK/'retained-evidence.json',dict(inputs_sha256=sha(PACKET/'inputs.json'),assessment_sha256=sha(PACKET/'assessment.json'),outside_namespace_inputs=[name for name in self.freeze['files'] if not Path(name).is_relative_to(N)],original_histories=self.assessment['history']))
                child,text=self.probe(self.plan['commands'][0]);require(child['returncode']==1 and not text,'target has open handles or mappings')
                child,text=self.probe(self.plan['commands'][1])
                for line in text.splitlines():
                    fields=line.split();require(len(fields)>=9,'malformed exact PID observation')
                    require(fields[3:8]!=self.plan['owned_start_times'].get(fields[0]),'original compiler owner is still alive')
                self.guard();self.protected();require(inventory(ROOT)[0]==rows,'target changed after quiescence')
                owned.write(WORK/'admitted-inventory.json',dict(entries=rows,allocated_bytes_observation=allocated))
                remaining=self.remove_files(rows,selected)
                current,after_allocated=inventory(ROOT);require(current==remaining,'remaining tree/membership differs')
                self.protected();self.guard()
                require(len(self.record['deleted'])==4646 and len(set(self.record['deleted']))==4646 and len(self.record['children'])==2,'incomplete retirement')
                owned.write(WORK/'remaining-inventory.json',dict(entries=current,allocated_bytes_observation=after_allocated))
                self.record.update(status='passed',retired_files=4646,removed_directories=0,private_stamp_entries_preserved=256,
                    check_stamp_now_incomplete=True,historical_snapshot_retired_entries=1690,check_stamp_retired_entries=143,
                    protected_providers_unchanged=True,remaining_inventory_sha256=sha(WORK/'remaining-inventory.json'),
                    deleted_ledger_sha256=sha(WORK/'deleted.jsonl'),transition_sha256=sha(WORK/'transition.json'),free_bytes_after=capacity())
        except BaseException as error:self.record.update(status='failed',error=repr(error));raise
        finally:self.record['finished_at']=time.time();self.save()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True);args=parser.parse_args();Retirement(args.inputs_sha256).run()
