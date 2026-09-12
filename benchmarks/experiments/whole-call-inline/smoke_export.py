#!/usr/bin/env python3
"""Export and execute original real workloads with the isolated whole-call compiler."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from build import ROOT, HERE, CONTROL, environment, installed_tools, read, require, sha, write


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--build-run',required=True)
    args=parser.parse_args()
    require(re.fullmatch(r'whole-call-export-smoke-[0-9]{2}',args.run_id) and re.fullmatch(r'whole-call-build-[0-9]{2}',args.build_run),'invalid run ID')
    work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time())
    write(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            build_work=ROOT/'.work'/args.build_run
            build_path=ROOT/'results'/args.build_run/'summary.json'
            build=read(build_path);proof=read(build_work/'provenance.json')
            require(read(build_work/'status.json')['status']=='finished' and build['status']=='passed' and
                    build['tests']['debug']['passed']==build['tests']['release']['passed']==300 and build['experimental_whole_call_inline'],'candidate build not qualified')
            directory,_=installed_tools(build['tool_key']);parent,_=installed_tools(CONTROL)
            for name in ['rust-interp-rustc-wrapper']:
                require(sha(directory/name)==sha(parent/name)==build['binaries'][name],'unchanged wrapper differs')
            source=ROOT/'.work/sources/fre';marker=read(source/'.rust-interp-owned.json')
            require(marker['owner']==str(ROOT) and marker['revision']=='e0df0b010b156b030a02f073588d28703f4267f3','source ownership differs')
            frozen=dict(proof['root_frozen'])
            frozen.update({str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),build_path,build_work/'provenance.json']})
            def verify():
                require(all(sha(ROOT/p)==h for p,h in frozen.items()),'frozen input changed')
                require(all(sha(ROOT/proof['source']/p)==h for p,h in proof['copied_inputs'].items()),'diagnostic source changed')
                require(all(sha(directory/p)==h for p,h in build['binaries'].items()),'diagnostic binary changed')
                require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==marker['revision'],'source pin changed')
                require(not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip(),'source modified')
            verify();cases=[];commands=[]
            for label in ['folded-literal-trie','token-phrase']:
                fs=os.statvfs(ROOT);free=fs.f_bavail*fs.f_frsize
                require(free>=16_159_814_452,'insufficient space reserve')
                original_path=ROOT/'.work/runs'/('aggregate-relocation-e2e-01-'+label)/'records.json'
                rows=read(original_path);original=next(r for r in rows if r['cycle']==0 and r['state']==0 and r['mode']=='candidate')
                call=original['calls'][0];command=list(call['command'])
                require(len(original['artifacts'])==1 and command[command.index('--tool-key')+1]==CONTROL,'reference tool differs')
                command[command.index('--tool-key')+1]=build['tool_key']
                command[command.index('--cache-namespace')+1]=args.run_id+':'+label
                frozen[str(original_path.relative_to(ROOT))]=sha(original_path)
                verify()
                env=environment();env.update(RUST_INTERP_LAUNCH_STATS='1',RUST_INTERP_VM_STATS='1',RUSTFLAGS=call['rustflags'])
                if label=='token-phrase':
                    env.update(CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL='0',CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL='0')
                with (work/(label+'.stdout')).open('x') as out,(work/(label+'.stderr')).open('x') as err:
                    child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
                    status.update(status='running',label=label,child_pid=child.pid,command=command,child_started_at=time.time())
                    write(work/'status.json',status);code=child.wait()
                record=dict(command=command,pid=child.pid,returncode=code,started_at=status['child_started_at'],finished_at=time.time(),
                    free_bytes_before=free,rustflags=call['rustflags'],files={str((work/(label+s)).relative_to(ROOT)):sha(work/(label+s)) for s in ['.stdout','.stderr']})
                commands.append(record);write(work/'commands.json',commands)
                require(code==0 and (work/(label+'.stdout')).read_text().strip()=='0','original workload failed')
                errors=(work/(label+'.stderr')).read_text()
                inventories=[json.loads(line.split(': ',1)[1]) for line in errors.splitlines() if line.startswith('rust-interp-aggregate-frames: ')]
                launches=[json.loads(line.split(': ',1)[1]) for line in errors.splitlines() if line.startswith('rust-interp-launch: ')]
                require(len(inventories)==1 and len(launches)==1,'missing relocation/launch output')
                require(inventories[0]['functions']>0 and inventories[0]['static_bytes_saved']>0 and inventories[0]['initialization_unchanged'],'relocation did not apply')
                launch=launches[0]
                require(launch['tool_key']==build['tool_key'] and launch['jit_resumable_calls'] and launch['jit_persistent_registers'] and
                        not launch['jit_native_calls'] and not launch['jit_native_call_stubs'],'runtime options differ')
                artifact=Path(launch['artifact_path'])
                require(sha(artifact)==launch['artifact_sha256'] and sha(artifact)!=original['artifacts'][0]['sha256'],'candidate artifact missing or unchanged')
                shutil.copy2(artifact,work/(label+'.rbc'))
                write(work/(label+'-inventory.json'),inventories)
                stats={}
                for line in errors.splitlines():
                    if re.fullmatch(r'[a-z_]+=\d+(?: [a-z_]+=\d+)*',line):
                        for k,v in re.findall(r'([a-z_]+)=(\d+)',line):
                            require(k not in stats,'duplicate VM counter');stats[k]=int(v)
                require(stats.get('jit_declined_functions')==0 and stats.get('instructions',0)>0,'missing VM statistics or native declines')
                verify()
                result=dict(label=label,artifact=str((work/(label+'.rbc')).relative_to(ROOT)),artifact_sha256=sha(work/(label+'.rbc')),
                    inventory=str((work/(label+'-inventory.json')).relative_to(ROOT)),inventory_sha256=sha(work/(label+'-inventory.json')),
                    inventories=len(inventories),statistics=stats,bytecode_identical=False,original_assertions_pass=True,
                    source_revision=marker['revision'],guest_rustflags=call['rustflags'])
                cases.append(result);write(work/'cases.json',cases)
                print(json.dumps(dict(label=label,bytecode_identical=False,inventories=len(inventories),
                    relocation=inventories[0])),flush=True)
            verify()
            result=dict(status='passed',tool_key=build['tool_key'],parent_tool_key=CONTROL,binaries=build['binaries'],
                cases=cases,frozen=frozen,commands=commands,source_unchanged=True,production_change=False,performance_measurement=False,
                note='Fresh changed-artifact exports execute original assertions using the rebuilt candidate VM. This is correctness smoke, not a timed comparison or broad qualification.',experimental_whole_call_inline=True)
            write(work/'summary.json',result);out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise


if __name__=='__main__':main()
