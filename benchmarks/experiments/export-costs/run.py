#!/usr/bin/env python3
"""Build and measure a retained-compiler observer using ordinary Git source."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from interpreter import installed_tools
from workflow_io import capture, SourceEdit, require_space, write_json as write
from workflow_measurements import source_states, child_usage, child_cpu_since
from workflow_cases import WORKFLOW_VARIANTS
sys.path.insert(0,str(HERE.parent/'aggregate-byte-writes'))
from build_relocation import environment

CONTROL='9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'
SOURCE=ROOT/'.work/export-costs-source'
TARGET=ROOT/'.work/scalar-value-source/.work/diagnostic-builds/review-maintenance-release-02'

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise RuntimeError(message)


def invoke(work,label,command,env,*,cwd=ROOT):
    require_space(ROOT,8);before=child_usage();start=time.perf_counter()
    process,out,err=capture(list(map(str,command)),cwd=cwd,env=env,receipt_path=work/'child.json',receipt=dict(label=label))
    result=dict(label=label,command=list(map(str,command)),pid=process.pid,returncode=process.returncode,
                seconds=time.perf_counter()-start,cpu=child_cpu_since(before))
    for name,text in [('stdout',out),('stderr',err)]:
        path=work/(label+'.'+name);path.write_text(text);result[name]=str(path.relative_to(ROOT));result[name+'_sha256']=sha(path)
    return result,out,err


def build(work):
    retained,_=installed_tools(CONTROL);manifest=read(retained/'ready.json')
    maintenance=read(ROOT/'results/review-maintenance-01/summary.json')
    require(maintenance['status']=='passed' and maintenance['all_processes_terminal'],'reused host cache still active')
    require(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=SOURCE,text=True),'source modified')
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()
    source_paths=[SOURCE/'Cargo.toml',SOURCE/'Cargo.lock',SOURCE/'rust-toolchain.toml']
    source_paths += [p for p in (SOURCE/'crates').rglob('*') if p.is_file() and (p.suffix=='.rs' or p.name=='Cargo.toml')]
    frozen={str(p.relative_to(SOURCE)):sha(p) for p in source_paths}
    write(work/'plan.json',dict(source_commit=source_commit,source=str(SOURCE.relative_to(ROOT)),frozen=frozen,
                              reused_disposable_target=str(TARGET.relative_to(ROOT)),parent=CONTROL))
    commands=[];env=environment()
    for action in ['test','build']:
        command=['cargo','+nightly-2026-09-08',action,'--release','--locked','--offline','--jobs','2',
                 '--manifest-path',str(SOURCE/'Cargo.toml'),'--target-dir',str(TARGET),'-p','rust-interp-mir-export']
        if action=='build':command+=['--bin','rust-interp-mir-export']
        result,out,err=invoke(work,action,command,env,cwd=SOURCE);commands.append(result);write(work/'commands.json',commands)
        require(result['returncode']==0,action+' failed')
        if action=='test':
            counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;',out+err)
            require(counts and all(n=='0' for _,n in counts),'exporter tests incomplete')
            passed=sum(int(n) for n,_ in counts);require(passed==39,'unexpected exporter test coverage')
    require(all(sha(SOURCE/p)==h for p,h in frozen.items()),'build source changed')
    binaries=dict(manifest);binaries['rust-interp-mir-export']=sha(TARGET/'release/rust-interp-mir-export')
    composition=dict(kind='export-cost-observer',schema_version=1,source_commit=source_commit,
                     wrapper_and_vm_source_key=CONTROL,binaries=binaries)
    key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
        fcntl.flock(publication,fcntl.LOCK_EX|fcntl.LOCK_NB)
        installed=ROOT/'.work/interpreter-tools'/key;installed.mkdir(exist_ok=False)
        for name in binaries:
            shutil.copy2(TARGET/'release'/name if name=='rust-interp-mir-export' else retained/name,installed/name)
        capability,out,_=invoke(work,'capabilities',[installed/'rust-interp-mir-export','--rust-interp-capabilities'],env)
        require(capability['returncode']==0,'capability query failed');commands.append(capability)
        caps=json.loads(out);caps.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export'])
        write(installed/'capabilities.json',caps)
        write(installed/'source.json',dict(tool_key=key,composition=composition,files=frozen,
            source_commit=source_commit,key_algorithm='SHA256 of canonical composition JSON',source=str(SOURCE.relative_to(ROOT))))
        write(installed/'ready.json',binaries)
    return dict(status='passed',tool_key=key,binaries=binaries,composition=composition,source_commit=source_commit,
                exporter_tests=passed,commands=commands,source_manifest=str((work/'plan.json').relative_to(ROOT)),source_manifest_sha256=sha(work/'plan.json'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['build'])
    parser.add_argument('--attempt',type=int,choices=range(1,10),default=1)
    args=parser.parse_args();run=f'export-costs-{args.action}-{args.attempt:02}'
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time());write(work/'status.json',status)
    try:
        with (ROOT/'.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result=build(work)
            out=ROOT/'results'/run;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print({k:result[k] for k in ['status','tool_key','exporter_tests']},flush=True)
    except BaseException as error:
        status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise


if __name__=='__main__':main()
