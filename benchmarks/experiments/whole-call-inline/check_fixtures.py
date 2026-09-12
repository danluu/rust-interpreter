#!/usr/bin/env python3
"""Strict native/interpreter/JIT differentials for the whole-call candidate."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import random
import re
import subprocess
import time
from build import ROOT,CONTROL,environment,read,write,sha,require,installed_tools
HERE=Path(__file__).resolve().parent
FIXTURES=ROOT/'benchmarks/experiments/aggregate-byte-writes'

FLAGS=['-Zmir-opt-level=3','-Zinline-mir-threshold=400','-Zinline-mir-hint-threshold=800','-Zinline-mir-forwarder-threshold=240']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True);parser.add_argument('--build-run',required=True)
    args=parser.parse_args()
    require(re.fullmatch(r'whole-call-fixtures-[0-9]{2}',args.run_id) and re.fullmatch(r'whole-call-build-[0-9]{2}',args.build_run),'invalid run ID')
    work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time())
    write(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            build_path=ROOT/'results'/args.build_run/'summary.json';build=read(build_path)
            require(build['status']=='passed' and build['tests']['debug']['passed']==build['tests']['release']['passed']==300 and build['control_tool_key']==CONTROL,'unqualified compiler')
            candidate,_=installed_tools(build['tool_key']);parent,_=installed_tools(CONTROL)
            sources=[FIXTURES/'fixture.rs',ROOT/'tests/caller_fixture.rs',ROOT/'tests/scalar_constant_fixture.rs',ROOT/'tests/coercion_fixture.rs']
            frozen={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),build_path,*sources]}
            for directory in [parent,candidate]:
                for name in build['binaries']:frozen[str((directory/name).relative_to(ROOT))]=sha(directory/name)
            require(all(sha(candidate/n)==sha(parent/n) for n in ['rust-interp-rustc-wrapper']),'unchanged wrapper differs')
            records=[];cases=[]
            def verify():require(all(sha(ROOT/p)==h for p,h in frozen.items()),'frozen input changed')
            def run(command,env=None,success=True):
                verify();fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=8*1024**3,'eight-GiB floor rejected');command=list(map(str,command));start=time.time()
                with (work/(str(len(records))+'.stdout')).open('x') as out,(work/(str(len(records))+'.stderr')).open('x') as err:
                    child=subprocess.Popen(command,cwd=ROOT,env=env or environment(),stdin=subprocess.DEVNULL,stdout=out,stderr=err)
                    status.update(status='running',child_pid=child.pid,child_started_at=start,command=command)
                    write(work/'status.json',status);code=child.wait()
                stdout=Path(out.name).read_text();stderr=Path(err.name).read_text()
                row=dict(command=command,pid=child.pid,started_at=start,finished_at=time.time(),returncode=code,
                    stdout=str(Path(out.name).relative_to(ROOT)),stderr=str(Path(err.name).relative_to(ROOT)),
                    stdout_sha256=sha(Path(out.name)),stderr_sha256=sha(Path(err.name)))
                records.append(row)
                with (work/'commands.jsonl').open('a') as log:log.write(json.dumps(row)+'\n')
                require((code==0)==success,'unexpected command status: '+str(len(records)-1))
                require('internal compiler error' not in stderr,'compiler crashed')
                return stdout.strip(),stderr
            seeds=[0,1,2,6,7,8,127,255,256,2**63-1,2**63,2**64-1]+[random.Random(i).getrandbits(64) for i in range(20)]
            for source in sources:
                native=work/(source.stem+'-native')
                run(['rustc','+nightly-2026-09-08',source,'--edition=2024','-C','overflow-checks=off','-o',native])
                wants=run([native,*seeds])[0].splitlines();require(len(wants)==len(seeds),'native output missing')
                for mode,flags in [('ordinary',[]),('enlarged',FLAGS)]:
                    for label,directory in [('baseline',parent),('candidate',candidate)]:
                        artifact=work/(source.stem+'-'+mode+'-'+label+'.rbc')
                        env=environment();env.update(RUST_INTERP_OUTPUT=str(artifact),RUST_INTERP_ENTRY='rust_interp_entry',RUST_INTERP_DEMAND_BODIES='0')
                        if mode=='enlarged':env['RUST_INTERP_INLINE_LEAVES']='1'
                        _,errors=run([directory/'rust-interp-mir-export',source,'--crate-name','relocation_case','--edition=2024','--emit=metadata',
                            '-C','overflow-checks=off','-o',artifact.with_suffix('.rmeta'),*flags],env)
                        relocated=[json.loads(line.split(': ',1)[1]) for line in errors.splitlines() if line.startswith('rust-interp-aggregate-frames: ')]
                        require(len(relocated)==1,'missing transformation receipt')
                        if source==sources[0]:require(relocated[0]['functions']>0,'fixture missed relocation')
                        for seed,want in zip(seeds,wants):
                            for engine in ['interpreter','jit']:
                                runtime=[] if engine=='interpreter' else ['--jit-persistent-registers','--jit-resumable-calls']
                                output,_=run([directory/'rust-interp-vm','--engine',engine,*runtime,artifact,seed])
                                require(output==want,'native differential mismatch')
                        cases.append(dict(source=str(source.relative_to(ROOT)),mode=mode,tool=label,artifact=str(artifact.relative_to(ROOT)),
                            artifact_sha256=sha(artifact),seeds=len(seeds),engines=['interpreter','jit'],relocation=relocated))
                        print(json.dumps(dict(source=source.name,mode=mode,tool=label,passed=True)),flush=True)
            # Strict checking of uncalled code remains part of compilation.
            for kind,bad in [('type','let _: u8="bad";'),('borrow','let mut a=1;let b=&a;a=2;let _=*b;')]:
                source=work/(kind+'.rs');source.write_text('pub fn rust_interp_entry(a:u64)->u64{a}\nfn unused(){'+bad+'}\nfn main(){}\n')
                artifact=source.with_suffix('.rbc');env=environment();env.update(RUST_INTERP_ENTRY='rust_interp_entry',RUST_INTERP_OUTPUT=str(artifact))
                run([candidate/'rust-interp-mir-export',source,'--edition=2024','--emit=metadata','-o',source.with_suffix('.rmeta')],env,False)
                require(not artifact.exists(),'invalid program published')
            verify()
            result=dict(status='passed',tool_key=build['tool_key'],baseline_tool_key=CONTROL,cases=cases,commands=len(records),
                vm_executions=len(cases)*len(seeds)*2,strict_rejections=2,frozen=frozen,performance_measurement=False,
                commands_path=str((work/'commands.jsonl').relative_to(ROOT)),commands_sha256=sha(work/'commands.jsonl'))
            write(work/'summary.json',result);out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise

if __name__=='__main__':main()
