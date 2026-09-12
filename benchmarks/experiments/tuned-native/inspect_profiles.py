#!/usr/bin/env python3
"""Inspect effective native profiles without building or running project code."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from workflow_controls import native_environment
from workflow_io import capture,write_json as write,require_space
from workflow_cases import WORKFLOWS,WORKFLOW_VARIANTS

RUN='native-effective-profiles-01'
CASES=[('fre','token-phrase-allocation'),('pgrust','default'),('nushell','type-relations'),('ruff','default'),('rg-aot','default')]

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise RuntimeError(message)


def main():
    global RUN
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',type=int,choices=range(1,10),default=1)
    args=parser.parse_args();RUN=f'native-effective-profiles-{args.attempt:02}'
    work=ROOT/'.work'/RUN;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time());write(work/'status.json',status)
    try:
        with (ROOT/'.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            corpus=read(ROOT/'benchmarks/corpus.json')['projects'];results=[];commands=[]
            for project,variant in CASES:
                source=ROOT/'.work/sources'/project;marker=read(source/'.rust-interp-owned.json')
                if project=='rg-aot':
                    adapter=read(ROOT/'.work/private/workflow-rg-aot.json');case=adapter['case']
                    require(adapter['owner']==str(ROOT) and adapter['revision']==marker['revision'],'private adapter differs')
                else:case=WORKFLOWS[project] if variant=='default' else WORKFLOW_VARIANTS[project,variant]
                require(marker['owner']==str(ROOT) and marker['revision']==corpus[project]['revision'],'source ownership differs')
                require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==marker['revision'] and
                    not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip(),'source pin is modified')
                profiles={};counts={}
                for setting in ['repository','line-tables-only','none']:
                    env=os.environ.copy()
                    for name in list(env):
                        if name.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) or name in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','CARGO_BUILD_BUILD_DIR']:
                            env.pop(name)
                    env=native_environment(env,'o0-incremental',[]);env['CARGO_TERM_COLOR']='never'
                    if project=='fre':
                        for p in ['DEV','TEST']:env['CARGO_PROFILE_'+p+'_BUILD_OVERRIDE_OPT_LEVEL']='0'
                    if setting!='repository':
                        for p in ['DEV','TEST']:
                            env['CARGO_PROFILE_'+p+'_DEBUG']='0' if setting=='none' else setting
                            env['CARGO_PROFILE_'+p+'_SPLIT_DEBUGINFO']='unpacked'
                    command=['cargo','+nightly-2026-09-08','test','--no-run','--unit-graph','-Z','unstable-options',
                        '--manifest-path',str(source/'Cargo.toml'),'--package',case['package'],'--lib','--locked','--offline',
                        '--jobs','18','--target-dir',str(work/(project+'-target'))]
                    require_space(ROOT,8);label=project+'-'+setting
                    child,out,err=capture(command,cwd=source,env=env,receipt_path=work/'child.json',receipt=dict(label=label))
                    stdout=work/(label+'.json');stderr=work/(label+'.stderr');stdout.write_text(out);stderr.write_text(err)
                    require(child.returncode==0,'Cargo unit graph failed: '+label)
                    graph=json.loads(out);require(graph['version']==1 and len(graph['roots'])==1,'unexpected unit graph')
                    unit=graph['units'][graph['roots'][0]]
                    require(unit['mode']=='test' and unit['target']['kind']==['lib'],'not the selected library-test unit')
                    profile=unit['profile'];require(str(profile['opt_level'])=='0' and profile['incremental'],'native optimization controls changed')
                    profiles[setting]=profile;counts[setting]=len(graph['units'])
                    commands.append(dict(project=project,setting=setting,pid=child.pid,returncode=0,
                        stdout=str(stdout.relative_to(ROOT)),stdout_sha256=sha(stdout),stderr=str(stderr.relative_to(ROOT)),stderr_sha256=sha(stderr)))
                    write(work/'commands.json',commands)
                require(all(p['strip']==profiles['repository']['strip'] or
                    (setting=='none' and p['strip']=={'resolved':{'Named':'debuginfo'}})
                    for setting,p in profiles.items()),'unexpected symbol stripping policy')
                comparable={k:v for k,v in profiles['repository'].items() if k not in ['debuginfo','split_debuginfo','strip']}
                require(all({k:v for k,v in p.items() if k not in ['debuginfo','split_debuginfo','strip']}==comparable for p in profiles.values()),'non-debug root profile changed')
                result=dict(project=project,profiles=profiles,unit_counts=counts,
                    distinct_profile_count=len({json.dumps(v,sort_keys=True) for v in profiles.values()}))
                results.append(result);write(work/'profiles.json',results)
                print(project,{k:dict(debuginfo=v['debuginfo'],split_debuginfo=v.get('split_debuginfo')) for k,v in profiles.items()},flush=True)
            out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
            write(out/'summary.json',dict(status='passed',projects=results,queries=len(commands),builds=0,test_executions=0,
                raw=str(work.relative_to(ROOT)),commands_sha256=sha(work/'commands.json'),
                note='Cargo test --no-run --unit-graph only; no performance measurement. Private raw graphs stay local.'))
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
    except BaseException as error:
        status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise


if __name__=='__main__':main()
