#!/usr/bin/env python3
"""Preserve the exact parked public artifact snapshots with independent COW files."""
import argparse
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from reclaim_workflow_objects import sha, no_open_files, identifier
from verify_repeated_workflow import verify, require
from workflow_io import write_json
from archive_workflow_cache import sync_directory

PRIMARY={
    'call-slot-primary-01':'24e3383754a3b131c49915721716a14d1fb62f550f100e3a49a58a1b8a153576',
    'budget-register-primary-01':'dd08195a7e2fd531a77da45335a73aded38a4c223c9135a13b66ec3d97e12a54',
}
FIELDS=['device','inode','bytes','mode','uid','gid','mtime_ns','links','flags']


def read(path):return json.loads(path.read_text())


def info(path):
    require(path.resolve(strict=True)==path,'noncanonical snapshot')
    s=path.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and not getattr(s,'st_flags',0),
            'snapshot is not a plain independent file')
    require(s.st_uid==os.getuid() and not s.st_mode & (stat.S_ISUID|stat.S_ISGID), 'snapshot ownership or privilege bits differ')
    return dict(device=s.st_dev,inode=s.st_ino,bytes=s.st_size,mode=stat.S_IMODE(s.st_mode),
        uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,atime_ns=s.st_atime_ns,
        links=s.st_nlink,flags=getattr(s,'st_flags',0))


def same(path,expected):
    actual=info(path)
    require(all(actual[k]==expected[k] for k in FIELDS),'snapshot changed: '+str(path))


def clone(source,destination):
    require(sys.platform=='darwin','this experiment requires macOS clonefile')
    libc=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
    call=libc.clonefile
    call.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int];call.restype=ctypes.c_int
    if call(os.fsencode(source),os.fsencode(destination),0)!=0:
        code=ctypes.get_errno()
        raise OSError(code,os.strerror(code),str(destination))


def replace_duplicate(source,target,source_info,target_info,digest,temporary):
    require(source!=target and temporary.parent==target.parent and not temporary.exists(), 'invalid staging identity')
    same(source,source_info);same(target,target_info)
    require(sha(source)==sha(target)==digest, 'duplicate payload identity differs')
    clone(source,temporary)
    # Metadata is separate for a clone. Do not chown another user's evidence.
    os.chmod(temporary,target_info['mode'])
    os.utime(temporary,ns=(target_info['atime_ns'],target_info['mtime_ns']))
    current=info(temporary)
    require(all(current[k]==target_info[k] for k in ['bytes','mode','uid','gid','mtime_ns']) and
        current['inode'] not in [source_info['inode'],target_info['inode']] and sha(temporary)==digest,
        'staged clone does not preserve bytes, metadata or independent identity')
    with temporary.open('rb') as stream:os.fsync(stream.fileno())
    same(source,source_info);same(target,target_info)
    os.replace(temporary,target)
    sync_directory(target.parent)
    require(sha(target)==digest,'published clone payload changed')
    return info(target)


def evidence():
    proofs={};snapshots={};directories=[];runs=[]
    for primary,digest in PRIMARY.items():
        path=ROOT/'results'/primary/'summary.json'
        require(sha(path)==digest,'parked primary identity changed')
        summary=read(path)
        require(summary['status']=='passed' and not summary['primary_gates_passed'] and summary['source_restored'],
            'primary is not a completed parked experiment')
        proofs.update(summary['evidence']);proofs[str(path.relative_to(ROOT))]=digest
        for case in summary['cases']:
            run=case['run_id'];runs.append(run)
            require(run==primary.removesuffix('-primary-01')+'-'+case['phase']+'-01-'+case['label'] and
                case['phase'] in ['aa','e2e'] and case['label'] in ['folded-literal-trie','token-phrase'], 'unknown workflow')
            report=read(ROOT/'results'/run/'summary.json')
            require(report['project']=='fre' and report['raw']=='.work/runs/'+run, 'snapshot owner differs')
            checked=verify(report)
            require(checked['edited_pairs']==15 and checked['exact_artifact_hashes_verified']==42,'incomplete workflow proof')
            folder=ROOT/report['raw'];directories.append(folder/'artifacts')
            supervisor=read(ROOT/'.work/experiments'/run/'status.json')
            controller=read(ROOT/'.work'/run/'status.json')
            require(supervisor['status']==controller['status']=='finished' and
                supervisor['returncode']==controller['returncode']==0 and supervisor['owner']==str(ROOT) and
                supervisor['child_pid']==controller['pid'], 'workflow still active or ownership differs')
            for row in read(folder/'records.json'):
                for artifact in row.get('artifacts',[]):
                    path=ROOT/artifact['path']
                    require(path.is_relative_to(folder/'artifacts') and path.suffix=='.rbc' and
                        artifact['path'] not in snapshots, 'unknown or duplicated snapshot path')
                    snapshots[artifact['path']]=dict(sha256=artifact['sha256'],bytes=artifact['bytes'])
    require(len(runs)==len(set(runs))==8 and len(snapshots)==336 and sum(x['bytes'] for x in snapshots.values())<=16*1024**3,
            'snapshot catalogue or byte bound differs')
    require(all(sha(ROOT/p)==h for p,h in proofs.items()),'external evidence changed')
    return snapshots,proofs,directories


def sources():
    paths=[Path(__file__),HERE/'PLAN.md',HERE/'check.py']
    paths += [ROOT/'scripts'/p for p in ['reclaim_workflow_objects.py','verify_repeated_workflow.py','workflow_io.py','archive_workflow_cache.py']]
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}


def plain_metadata(paths,directories):
    for directory in directories:
        no_open_files(directory)
        result=subprocess.run(['/usr/bin/xattr','-r',str(directory)],capture_output=True,text=True)
        require(result.returncode==0 and not result.stdout and not result.stderr,'unsupported snapshot attributes')
    result=subprocess.run(['/bin/ls','-lde',*[str(p) for p in paths]],capture_output=True,text=True)
    require(result.returncode==0 and not result.stderr and len(result.stdout.splitlines())==len(paths) and
        all('+' not in line[:11] for line in result.stdout.splitlines()), 'unsupported snapshot ACLs')


def prepare(run):
    work=ROOT/'.work'/run;out=ROOT/'results'/run
    require(not work.exists() and not out.exists(),'clone identity already exists')
    qualification=read(ROOT/'results/artifact-clone-controls-01/summary.json')
    require(qualification['status']=='passed' and qualification['sources']==sources() and
        qualification['independent_write_checks']==2 and qualification['rejections']==3,
        'clone preservation qualification differs')
    selected,proofs,directories=evidence()
    plain_metadata([ROOT/p for p in selected],directories)
    files={};canonical={};replacements=[]
    for name,expected in sorted(selected.items()):
        path=ROOT/name;details=info(path)
        require(details['bytes']==expected['bytes'] and sha(path)==expected['sha256'],'snapshot payload differs')
        same(path,details);files[name]=dict(**details,sha256=expected['sha256'])
        group=(expected['sha256'],expected['bytes'],details['device'])
        if group in canonical:replacements.append(dict(source=canonical[group],target=name))
        else:canonical[group]=name
    require(len(files)<=1000 and replacements,'empty or unbounded duplicate selection')
    work.mkdir(mode=0o700);out.mkdir()
    plan=dict(owner=str(ROOT),run=run,sources=sources(),proofs=proofs,files=files,replacements=replacements,
        qualification_sha256=sha(ROOT/'results/artifact-clone-controls-01/summary.json'),
        directories=[str(p.relative_to(ROOT)) for p in directories],prepared_at=time.time(),
        logical_redundant_bytes=sum(files[r['target']]['bytes'] for r in replacements))
    write_json(work/'plan.json',plan);write_json(out/'plan.json',plan)
    write_json(work/'status.json',dict(status='prepared',plan_sha256=sha(work/'plan.json')))
    print(dict(status='prepared',files=len(files),duplicates=len(replacements),logical_redundant_bytes=plan['logical_redundant_bytes']),flush=True)


def apply(run):
    work=ROOT/'.work'/run;out=ROOT/'results'/run
    plan=read(work/'plan.json');status=read(work/'status.json')
    require(plan['owner']==str(ROOT) and plan['run']==run and status['status']=='prepared' and
        plan['sources']==sources() and sha(work/'plan.json')==status['plan_sha256']==sha(out/'plan.json'),'clone plan changed')
    require(sha(ROOT/'results/artifact-clone-controls-01/summary.json')==plan['qualification_sha256'], 'qualification receipt changed')
    committed=subprocess.run(['git','show',f'HEAD:results/{run}/plan.json'],cwd=ROOT,capture_output=True)
    require(committed.returncode==0 and committed.stdout==(work/'plan.json').read_bytes(), 'exact inventory must be reviewed and committed')
    selected,proofs,directories=evidence()
    require(proofs==plan['proofs'] and set(selected)==set(plan['files']),'evidence selection changed')
    plain_metadata([ROOT/p for p in selected],directories)
    for name,details in plan['files'].items():same(ROOT/name,details)
    status.update(status='applying',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),
        free_bytes_before=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize,completed=0)
    write_json(work/'status.json',status);records=[]
    try:
        for row in plan['replacements']:
            source,target=ROOT/row['source'],ROOT/row['target']
            temporary=target.with_name(target.name+'.cow-'+run)
            after=replace_duplicate(source,target,plan['files'][row['source']],plan['files'][row['target']],
                plan['files'][row['target']]['sha256'],temporary)
            records.append(dict(**row,after=after));write_json(work/'replacements.json',records)
            status['completed']=len(records);write_json(work/'status.json',status)
        selected_after,proofs_after,_=evidence()
        require(selected_after==selected and proofs_after==proofs,'final evidence differs')
        for name,before in plan['files'].items():
            actual=info(ROOT/name)
            require(all(actual[k]==before[k] for k in ['bytes','mode','uid','gid','mtime_ns']) and sha(ROOT/name)==before['sha256'],
                'final snapshot metadata or payload differs')
        status.update(status='completed',finished_at=time.time(),
            free_bytes_after=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize)
        write_json(work/'status.json',status)
        write_json(out/'summary.json',dict(**status,files=len(selected),proofs=proofs,sources=plan['sources'],
            logical_redundant_bytes=plan['logical_redundant_bytes'],all_bytes_and_paths_preserved=True,
            file_writes_independent=True,performance_measurement=False))
    except BaseException as error:
        status.update(status='failed; audit required',error=repr(error),finished_at=time.time())
        write_json(work/'status.json',status)
        raise
    print(dict(status='completed',files=len(selected),clones=len(records),free_bytes_before=status['free_bytes_before'],
        free_bytes_after=status['free_bytes_after']),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','apply']);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();identifier(args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        (prepare if args.action=='prepare' else apply)(args.run_id)


if __name__=='__main__':main()
