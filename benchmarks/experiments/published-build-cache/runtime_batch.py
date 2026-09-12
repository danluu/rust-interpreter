"""Serialize the fixed sixteen completed guarded-Call cache archives."""
import argparse
from pathlib import Path
import subprocess
import time
import runtime

ROOT=runtime.ROOT
BASE=ROOT/'.work/parked-runtime-cache-batch-01'


def entries():
    return [(f'parked-slot-{phase}-{label}-{mode}-archive-01',
             runtime.workflow.run_id(phase,label)+':'+mode)
            for phase,label in runtime.workflow.ORDER
            for mode in ['native','check','baseline','candidate']]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action',choices=['prepare','apply','verify'],required=True)
    args=parser.parse_args()
    BASE.mkdir(mode=0o700,exist_ok=True)
    work=BASE/args.action;work.mkdir(exist_ok=False)
    qualification=runtime.driver.read(ROOT/'results/parked-workflow-cache-controls-01/summary.json')
    runtime.driver.require(qualification['status']=='passed' and
        all(runtime.driver.sha(ROOT/p)==h for p,h in qualification['sources'].items()), 'qualification source changed')
    records=[]
    for name,selection in entries():
        command=['python3','benchmarks/experiments/published-build-cache/runtime.py',args.action,'--name',name]
        if args.action=='prepare':command+=['--build',selection]
        with (work/(name+'.log')).open('x') as log:
            child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            status=dict(status='running',pid=child.pid,command=command,cwd=str(ROOT),started_at=time.time(),completed=len(records))
            runtime.driver.write_json(work/'status.json',status)
            code=child.wait()
        records.append(dict(name=name,selection=selection,command=command,pid=child.pid,returncode=code,
                            log_sha256=runtime.driver.sha(work/(name+'.log'))))
        runtime.driver.write_json(work/'records.json',records)
        if code:
            status.update(status='failed',returncode=code,finished_at=time.time())
            runtime.driver.write_json(work/'status.json',status)
            raise RuntimeError('archive action stopped: '+name)
        print(args.action,name,'completed',flush=True)
    status.update(status='finished',returncode=0,completed=len(records),finished_at=time.time())
    runtime.driver.write_json(work/'status.json',status)


if __name__=='__main__':main()
