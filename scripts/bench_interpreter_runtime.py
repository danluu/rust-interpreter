#!/usr/bin/env python3
"""Execution scaling for saved, matching native and custom-bytecode revisions."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
from bench_interpreter import ROOT, BUILD, CASES, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',default='interpreter-edits-01')
    args=parser.parse_args()
    lock=(ROOT/'.work/benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    baseline=ROOT/'.work/runs'/args.baseline
    work=ROOT/'.work'/('interpreter-runtime-'+str(time.time_ns()))
    work.mkdir()
    records=[]
    for case in ['rg-aot','pgrust-hash','pgrust-numeric','fre','ruff','nushell']:
        seed=CASES[case].get('seed',0)
        for count in [0,1024,16384,131072]:
            outputs={}
            for rep in range(5):
                for mode in (['native','vm'] if rep%2==0 else ['vm','native']):
                    command=[baseline/case/'target-native/debug/interpreter-corpus-driver',seed,count] if mode=='native' else [BUILD/'rust-interp-vm',baseline/case/'program.rbc',seed,count]
                    env=os.environ.copy();env['RUST_INTERP_VM_STATS']='1'
                    start=time.perf_counter()
                    p=subprocess.Popen(list(map(str,command)),cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                    pid=p.pid
                    stdout,stderr=p.communicate()
                    records.append(dict(case=case,count=count,rep=rep,mode=mode,seconds=time.perf_counter()-start,pid=pid,returncode=p.returncode,stdout=stdout,stderr=stderr))
                    if p.returncode:raise RuntimeError(stderr)
                    outputs[mode]=stdout
                if outputs['native']!=outputs['vm']:raise RuntimeError('output mismatch')
            print(case,count,flush=True)
            (work/'samples.json').write_text(json.dumps(records,indent=2))
    rows=['# Custom interpreter execution scaling','','Five alternating samples per condition, using previously built matching revisions; executable startup has been warmed. Each iteration calls the selected production routine. These are routine throughput probes, not full application workloads.','','| Routine | Calls | Native s | Interpreter s |','|---|---:|---:|---:|']
    for case in CASES:
        for count in [0,1024,16384,131072]:
            med=lambda mode:statistics.median(r['seconds'] for r in records if r['case']==case and r['count']==count and r['mode']==mode)
            rows.append(f'| {case} | {count} | {med("native"):.4f} | {med("vm"):.4f} |')
    out=ROOT/'results'/args.baseline
    (out/'runtime.md').write_text('\n'.join(rows)+'\n')
    (out/'runtime.json').write_text(json.dumps(dict(raw=str(work.relative_to(ROOT)),vm_sha256=sha(BUILD/'rust-interp-vm'),samples=[{k:v for k,v in r.items() if k not in ['stdout','stderr','pid']} for r in records]),indent=2)+'\n')


if __name__=='__main__':main()
