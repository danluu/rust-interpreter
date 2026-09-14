"""Read allocated sizes for existing caches; this does not authorize deletion."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,write_json as write
NAME='runtime-storage-inventory-20260914-01'
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);raw=ROOT/'.work'/NAME;raw.mkdir(exist_ok=False)
    rows=[]
    for label,depth,path in [('runs',1,'.work/runs'),('workspaces',2,'.work/interpreter-workspaces')]:
        command=['du','-k','-d',str(depth),path]
        child,out,err=capture(command,cwd=ROOT,env=dict(os.environ),receipt_path=raw/'active.json',receipt=dict(stage=label))
        (raw/(label+'.stdout')).write_text(out);(raw/(label+'.stderr')).write_text(err)
        record=dict(label=label,command=command,pid=child.pid,returncode=child.returncode,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')))
        rows.append(record);write(raw/'records.json',rows);assert child.returncode==0 and not err
        parsed=[dict(allocated_kib=int(line.split('\t',1)[0]),path=line.split('\t',1)[1]) for line in out.splitlines()]
        top=sorted(parsed,key=lambda r:r['allocated_kib'],reverse=True)[:35];write(raw/(label+'-largest.json'),top)
        print(label,json.dumps(top),flush=True)
    write(raw/'summary.json',dict(status='passed',owner=str(ROOT),commands=2,files_removed=0,eligibility_established=False,raw=str(raw.relative_to(ROOT)),records_sha256=sha(raw/'records.json')))
