"""Test transparent filesystem compression on a new copy of one closed profile."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

NAME='closed-profile-compression-probe-01'

def metadata(path):
    s=path.lstat()
    assert path.resolve(strict=True)==path and path.is_file()
    return dict(size=s.st_size,blocks=s.st_blocks,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid,
        mtime_ns=s.st_mtime_ns,device=s.st_dev,inode=s.st_ino,links=s.st_nlink,flags=s.st_flags)

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        proof_path=ROOT/'results/heap-address-screen-token-01/closure.json'
        proof=json.loads(proof_path.read_text());assert proof['status']=='passed'
        profile_path=ROOT/'results/heap-address-profile-03/summary.json'
        profile=json.loads(profile_path.read_text());assert profile['status']=='passed'
        item,=[r for r in profile['comparisons'] if r['mode']=='control' and r['index']==0]
        source=ROOT/item['profile_path'];digest=item['profile_sha256']
        assert proof['evidence'][str(source.relative_to(ROOT))]==digest==sha(source)
        before=metadata(source);assert before['links']==1 and not before['mode'] & 0o111
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False);destination=work/'compressed-copy.json'
        write(work/'plan.json',dict(owner=str(ROOT),source=str(source.relative_to(ROOT)),source_sha256=digest,
            source_metadata=before,closure_sha256=sha(proof_path),profile_summary_sha256=sha(profile_path),
            script_sha256=sha(Path(__file__)),original_replacement_authorized_by_this_probe=False,
            scope='Create one new diagnostic copy only. Original paths, bytes, executables, caches and peer work remain untouched.'))
        command=['/usr/bin/ditto','--hfsCompression',str(source),str(destination)]
        require_space(ROOT,8);started=time.time();free=shutil.disk_usage(ROOT).free
        child,out,err=capture(command,cwd=ROOT,env=os.environ.copy(),receipt_path=work/'active.json',receipt=dict(label='compress-copy'))
        write(work/'command.json',dict(command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err))
        assert child.returncode==0,err
        assert sha(source)==sha(destination)==digest
        assert metadata(source)==before, 'original source metadata changed'
        copied=metadata(destination)
        allocation={label:int(subprocess.check_output(['du','-sk',str(path)],text=True).split()[0])*1024
            for label,path in [('source',source),('copy',destination)]}
        result=dict(status='passed',source_unchanged=True,source_sha256=digest,copy_sha256=sha(destination),
            source_metadata=before,copy_metadata=copied,allocated_bytes=allocation,
            allocation_ratio=allocation['copy']/allocation['source'],seconds=time.time()-started,
            free_before=free,free_after=shutil.disk_usage(ROOT).free,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),command_sha256=sha(work/'command.json'),performance_measurement=False)
        output=ROOT/'results'/NAME;output.mkdir(exist_ok=False);write(output/'summary.json',result)
        print(json.dumps(result),flush=True)

if __name__=='__main__':main()
