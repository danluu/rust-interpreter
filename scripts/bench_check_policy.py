#!/usr/bin/env python3
"""Isolate full versus demand body checking with identical rustc invocations.

Dependency preparation happens through Cargo first. Timed invocations replay
the selected crate's compiler inputs directly, using separate incremental
directories. This is a frontend experiment, not a Cargo-compatible demand mode.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

from bench_interpreter import ROOT, BUILD, TOOLCHAIN, CASES, source_changes, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',default='interpreter-edits-01')
    parser.add_argument('--cases',nargs='+',default=['rg-aot','pgrust-hash','pgrust-numeric','fre','ruff','nushell'],choices=list(CASES))
    args=parser.parse_args()
    lock=(ROOT/'.work/benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    run_id='check-policy-'+str(time.time_ns())
    work=ROOT/'.work/runs'/run_id
    work.mkdir()
    baseline=ROOT/'.work/runs'/args.baseline
    old=json.loads((baseline/'samples.json').read_text())
    count=old['provenance']['count']
    expected={(r['case'],r['state']):r['value'] for r in old['samples'] if r.get('mode')=='native' and r['status']=='ok'}
    records=[]
    commands=[]
    def run(command,cwd,env,allow_fail=False):
        start=time.perf_counter()
        p=subprocess.Popen(list(map(str,command)),cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        pid=p.pid
        stdout,stderr=p.communicate()
        rec=dict(command=list(map(str,command)),cwd=str(cwd),pid=pid,seconds=time.perf_counter()-start,returncode=p.returncode,stdout=stdout,stderr=stderr)
        commands.append(rec)
        (work/'commands.json').write_text(json.dumps(commands,indent=2))
        if p.returncode and not allow_fail:raise RuntimeError(stderr[-2500:])
        return rec
    for name in args.cases:
        case=CASES[name]
        print(name+': capture exact compiler inputs',flush=True)
        with source_changes(case) as (_,set_state):
            capture=work/(name+'-invocation.json')
            base=os.environ.copy()
            for key in list(base):
                if key.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or key in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']:
                    base.pop(key,None)
            base.update(RUSTC_WRAPPER=str(BUILD/'rust-interp-mir-export'),RUSTC_WORKSPACE_WRAPPER='',RUST_INTERP_EXPORT_CRATE=case['crate'],RUST_INTERP_ENTRY='rust_interp_entry',RUST_INTERP_OUTPUT=str(work/(name+'-capture.rbc')),RUST_INTERP_CAPTURE=str(capture),CARGO_TARGET_DIR=str(baseline/name/'target-vm'))
            run(['cargo','+'+TOOLCHAIN,'check','--locked','--offline','--jobs','4'],baseline/name/'driver',base)
            invocation=json.loads(capture.read_text())
            original=invocation['args'][1:]
            for state in range(6):
                set_state(state)
                for mode in (['strict','demand','demand-cache'] if state%2==0 else ['demand-cache','demand','strict']):
                    folder=work/name/mode
                    folder.mkdir(parents=True,exist_ok=True)
                    compiler_args=[]
                    i=0
                    while i<len(original):
                        arg=original[i]
                        if arg=='--out-dir':
                            compiler_args.extend([arg,str(folder)]);i+=2;continue
                        if arg=='-C' and original[i+1].startswith('incremental='):
                            compiler_args.extend(['-C','incremental='+str(folder/'incremental')]);i+=2;continue
                        if arg.startswith('-Cincremental='):
                            compiler_args.append('-Cincremental='+str(folder/'incremental'));i+=1;continue
                        if arg.startswith('--emit='):arg='--emit=metadata'
                        compiler_args.append(arg);i+=1
                    env=base.copy();env.update(invocation['env'])
                    env.pop('RUST_INTERP_CAPTURE',None)
                    env.update(RUST_INTERP_DEMAND_BODIES='0' if mode=='strict' else '1',RUST_INTERP_DEMAND_CACHE='1' if mode=='demand-cache' else '0',RUST_INTERP_OUTPUT=str(folder/'program.rbc'))
                    compilation=run([BUILD/'rust-interp-mir-export',*compiler_args],invocation['cwd'],env,allow_fail=True)
                    if compilation['returncode']:
                        records.append(dict(case=name,state=state,mode=mode,status='unsupported',seconds=compilation['seconds']))
                        print(name+' '+mode+' unsupported; see raw command log',flush=True)
                        continue
                    execution=run([BUILD/'rust-interp-vm',folder/'program.rbc',case.get('seed',0),count],ROOT,env)
                    if execution['stdout'].strip()!=expected[name,state]:raise RuntimeError('output differs from native baseline')
                    if mode!='strict' and 'PARTIAL validation' not in execution['stderr']:raise RuntimeError('partial artifact was not marked')
                    records.append(dict(case=name,state=state,mode=mode,status='ok',compile_seconds=compilation['seconds'],run_seconds=execution['seconds'],total_seconds=compilation['seconds']+execution['seconds'],stats=[l for l in compilation['stderr'].splitlines() if l.startswith('rust-interp-export:')]))
                    print(f'{name} edit={state} {mode}: {compilation["seconds"]:.3f}s',flush=True)
            (work/'samples.json').write_text(json.dumps(records,indent=2))
    out=ROOT/'results'/run_id
    out.mkdir()
    report=['# Checking policy experiment','','Dependencies are prepared before timing. These are direct rustc invocations for the selected crate, not complete Cargo loops. Both demand modes perform partial validation of the selected static call graph. Demand-cache commits rustc semantic caches; demand leaves the session unfinished. Five distinct body edits per mode.','','| Case | Strict compiler s | Demand compiler s | Demand with committed cache s |','|---|---:|---:|---:|']
    for name in args.cases:
        values={}
        for mode in ['strict','demand','demand-cache']:
            rows=[r for r in records if r['case']==name and r['mode']==mode and r['state']>0 and r['status']=='ok']
            values[mode]=statistics.median(r['compile_seconds'] for r in rows) if len(rows)==5 else None
        report.append('| '+name+' | '+' | '.join(f'{values[m]:.3f}' if values[m] is not None else 'unsupported' for m in ['strict','demand','demand-cache'])+' |')
    (out/'summary.md').write_text('\n'.join(report)+'\n')
    (out/'summary.json').write_text(json.dumps(dict(exporter_sha256=sha(BUILD/'rust-interp-mir-export'),vm_sha256=sha(BUILD/'rust-interp-vm'),baseline=args.baseline,samples=records),indent=2)+'\n')
    print(out/'summary.md')


if __name__=='__main__':main()
