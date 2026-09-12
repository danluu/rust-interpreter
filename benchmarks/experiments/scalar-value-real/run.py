"""Execute original real assertions on legacy and freshly exported scalar artifacts."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'aggregate-byte-writes'))
from build_relocation import read,write,sha,require,environment,installed_tools
CONTROL='9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    run=parser.parse_args().run_id;require(re.fullmatch(r'scalar-value-real-[0-9]{2}',run),'invalid run')
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time());write(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            parent_path=ROOT/'results/scalar-value-cargo-01/summary.json';parent=read(parent_path)
            receipt_path=parent_path.with_name('execution.json');receipt=read(receipt_path)
            require(parent['status']=='passed' and parent['fixture_restored'] and receipt['all_processes_terminal'],'Cargo qualification incomplete')
            require(all(sha(ROOT/p)==h for p,h in receipt['evidence'].items()),'Cargo evidence changed')
            tools,key=installed_tools(parent['tool_key']);launcher=HERE.parent/'scalar-value-cargo/launcher.py'
            source=ROOT/'.work/sources/fre';marker_path=source/'.rust-interp-owned.json';marker=read(marker_path)
            require(marker['owner']==str(ROOT) and marker['revision']=='e0df0b010b156b030a02f073588d28703f4267f3','source ownership differs')
            frozen={str(p.relative_to(ROOT)):sha(p) for p in [parent_path,receipt_path,launcher,Path(__file__),marker_path]}
            for p in tools.iterdir():
                if p.is_file():frozen[str(p.relative_to(ROOT))]=sha(p)
            def verify():
                require(all(sha(ROOT/p)==h for p,h in frozen.items()),'real smoke input changed')
                require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==marker['revision'],'source revision changed')
                require(not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip(),'source modified')
            verify();cases=[];commands=[]
            # Previous exact two-workflow compiler smoke caches occupy 329,792
            # KiB combined. Reserve 1.5 GiB (>4x that plus artifact snapshots),
            # above the unchanged 8 GiB floor. Do not retire any old cache.
            fs=os.statvfs(ROOT);free=fs.f_bavail*fs.f_frsize
            require(free>=19*1024**3//2,'insufficient real smoke allowance')
            write(work/'plan.json',dict(tool_key=key,source_revision=marker['revision'],free_bytes=free,
                required_free_bytes=19*1024**3//2,floor_bytes=8*1024**3,allowance_bytes=3*1024**3//2,
                previous_smoke_allocated_kib=[138692,191100],performance_measurement=False))
            def command(label,argv,env):
                verify();fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=8*1024**3,'eight-GiB floor rejected');argv=list(map(str,argv))
                out=work/(label+'.stdout');err=work/(label+'.stderr')
                with out.open('x') as stdout,err.open('x') as stderr:
                    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                    try:
                        status.update(status='running',child_pid=child.pid,command=argv,child_started_at=time.time(),child_cwd=str(ROOT),
                            child_identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True));write(work/'status.json',status)
                    finally:code=child.wait()
                commands.append(dict(label=label,command=argv,pid=child.pid,returncode=code,files={str(p.relative_to(ROOT)):sha(p) for p in [out,err]}));write(work/'commands.json',commands)
                require(code==0 and out.read_text().strip()=='0',label+' original assertions failed')
                errors=err.read_text();statistics={}
                for line in errors.splitlines():
                    if re.fullmatch(r'[a-z_]+=\d+(?: [a-z_]+=\d+)*',line):
                        for name,value in re.findall(r'([a-z_]+)=(\d+)',line):
                            require(name not in statistics,'duplicate VM counter');statistics[name]=int(value)
                require(statistics.get('instructions',0)>0 and statistics.get('jit_resumable_calls',0)>0,'actual native calls missing')
                require(statistics.get('jit_declined_functions')==0,'unexpected JIT decline')
                verify();return errors,statistics
            for label in ['folded-literal-trie','token-phrase']:
                original_path=ROOT/'.work/runs'/('aggregate-relocation-e2e-01-'+label)/'records.json'
                rows=read(original_path);original=next(r for r in rows if r['cycle']==r['state']==0 and r['mode']=='candidate')
                call=original['calls'][0];argv=list(call['command'])
                require(len(original['artifacts'])==1 and argv[argv.index('--tool-key')+1]==CONTROL,'original selected tool differs')
                legacy=original_path.parent/'artifacts/candidate/cycle-0/0-0.rbc';require(sha(legacy)==original['artifacts'][0]['sha256'],'legacy artifact changed')
                frozen.update({str(p.relative_to(ROOT)):sha(p) for p in [original_path,legacy]})
                env=environment();env.pop('CARGO_BUILD_BUILD_DIR',None)
                env.update(RUST_INTERP_LAUNCH_STATS='1',RUST_INTERP_VM_STATS='1',RUSTFLAGS=call['rustflags'])
                if label=='token-phrase':env.update(CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL='0',CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL='0')
                _,old_stats=command(label+'-legacy',[tools/'rust-interp-vm','--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                    '--instruction-limit','100000000000','--allocation-limit','150000',legacy],env)
                argv[1]=str(launcher);argv[argv.index('--tool-key')+1]=key;argv[argv.index('--cache-namespace')+1]=run+':'+label;argv.append('--scalar-values')
                errors,statistics=command(label+'-scalar',argv,env)
                promoted=[json.loads(line.split(': ',1)[1]) for line in errors.splitlines() if line.startswith('rust-interp-scalar-values: ')]
                launched=[json.loads(line.split(': ',1)[1]) for line in errors.splitlines() if line.startswith('rust-interp-launch: ')]
                require(len(promoted)==len(launched)==1,'compiler/launch scalar receipt missing');launch=launched[0];report=promoted[0]
                require(launch['tool_key']==key and launch['scalar_values'] and launch['jit_resumable_calls'] and launch['jit_persistent_registers'],'executed scalar mode differs')
                require(report['report']['value_calls']>0 and report['report']['value_arguments']>0 and report['report']['value_destinations']>0,'no real caller value promotion')
                artifact=Path(launch['artifact_path']);require(sha(artifact)==launch['artifact_sha256'] and int.from_bytes(artifact.read_bytes()[:4],'little')==6,'scalar artifact identity differs')
                copy=work/(label+'.rbc');shutil.copy2(artifact,copy);require(sha(copy)==sha(artifact),'snapshot differs');frozen[str(copy.relative_to(ROOT))]=sha(copy)
                cases.append(dict(label=label,artifact=str(copy.relative_to(ROOT)),artifact_sha256=sha(copy),legacy_artifact_sha256=sha(legacy),
                    legacy_statistics=old_stats,scalar_statistics=statistics,promotion=report,source_revision=marker['revision'],guest_rustflags=call['rustflags'],
                    original_assertions_pass=True,scalar_artifact_version=6));write(work/'cases.json',cases)
                print(dict(label=label,original_assertions_pass=True,value_calls=report['report']['value_calls']),flush=True)
            verify();result=dict(status='passed',tool_key=key,cases=cases,commands=commands,frozen=frozen,source_unchanged=True,
                performance_measurement=False,production_change=False,limitation='Original selected bodies execute on legacy and scalar artifacts. Fresh paired edit/build/run histories and broader qualification remain.')
            write(work/'summary.json',result);out=ROOT/'results'/run;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise

if __name__=='__main__':main()
