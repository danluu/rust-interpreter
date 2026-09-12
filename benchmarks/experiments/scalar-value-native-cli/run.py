"""Exercise scalar interpreter and native CLI modes using serialized artifacts."""
import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'aggregate-byte-writes'))
from build_relocation import read,write,sha,require,environment


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    run=parser.parse_args().run_id;require(re.fullmatch(r'scalar-abi-native-cli-[0-9]{2}',run),'invalid run')
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time());write(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=9*1024**3,'insufficient CLI build allowance')
            parent_path=ROOT/'results/scalar-abi-native-build-03/summary.json';parent=read(parent_path)
            receipt_path=parent_path.with_name('execution.json');receipt=read(receipt_path)
            require(parent['status']=='passed' and parent['tests']['debug']['passed']==parent['tests']['release']['passed']==310
                and receipt['all_processes_terminal'],'native library not qualified')
            for p,h in receipt['evidence'].items():require(sha(ROOT/p)==h,'parent execution changed')
            provenance=ROOT/parent['provenance'];require(sha(provenance)==parent['provenance_sha256'],'parent provenance changed')
            proof=read(provenance);original=ROOT/proof['source']
            require(all(sha(original/p)==h for p,h in proof['copied_inputs'].items()),'parent source changed')
            files=[p for p in HERE.iterdir() if p.is_file()]+[parent_path,receipt_path,provenance,
                ROOT/'benchmarks/experiments/aggregate-byte-writes/build_relocation.py',ROOT/'benchmarks/experiments/aggregate-byte-writes/build.py']
            frozen={str(p.relative_to(ROOT)):sha(p) for p in files}
            source=work/'tool-source';source.mkdir()
            for path,digest in proof['copied_inputs'].items():
                relative=Path(path);require(not relative.is_absolute() and '..' not in relative.parts,'invalid source path')
                destination=source/relative;destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(original/relative,destination);require(sha(destination)==digest,'source copy differs')
            shutil.copy2(HERE/'fixture.rs',source/'crates/bytecode/src/scalar_cli_fixture.rs')
            copied={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
            inputs=[source/'Cargo.toml',source/'Cargo.lock']
            for crate in ['bytecode','mir-export']:
                inputs+=sorted((source/'crates'/crate).rglob('*.rs'));inputs.append(source/'crates'/crate/'Cargo.toml')
            digest=hashlib.sha256()
            for p in inputs:digest.update(str(p.relative_to(source)).encode()+b'\0'+p.read_bytes())
            key=digest.hexdigest()
            write(work/'provenance.json',dict(source=str(source.relative_to(ROOT)),parent_tool_key=parent['tool_key'],tool_key=key,
                copied_inputs=copied,root_frozen=frozen,performance_measurement=False,runtime_published=False))
            commands=[];env=environment();env['RUST_INTERP_VM_STATS']='1'
            def verify():
                require(all(sha(ROOT/p)==h for p,h in frozen.items()),'frozen CLI input changed')
                require(all(sha(source/p)==h for p,h in copied.items()),'CLI source changed')
            def command(label,argv,code=0,expected=None,error=None):
                argv=list(map(str,argv));verify();fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=8*1024**3,'eight-GiB floor rejected')
                out=work/(label+'.stdout');err=work/(label+'.stderr')
                with out.open('x') as stdout,err.open('x') as stderr:
                    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                    try:
                        status.update(status='running',child_pid=child.pid,command=argv,child_started_at=time.time(),child_cwd=str(ROOT),
                            child_identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True))
                        write(work/'status.json',status)
                    finally:actual=child.wait()
                text=out.read_text().strip();errors=err.read_text()
                commands.append(dict(label=label,command=argv,pid=child.pid,returncode=actual,
                    files={str(p.relative_to(ROOT)):sha(p) for p in [out,err]}));write(work/'commands.json',commands)
                require(actual==code,label+' exit differs')
                if expected is not None:require(text==expected,label+' stdout differs')
                if error is not None:require(error in errors,label+' error differs')
                require('panicked at' not in errors and 'internal compiler error' not in errors,label+' crashed')
                verify();return text,errors
            target=ROOT/'.work/diagnostic-builds'/run;require(not target.exists(),'CLI target exists')
            command('build',['cargo','+nightly-2026-09-08','build','--release','--locked','--offline','--jobs','2',
                '--manifest-path',source/'Cargo.toml','--target-dir',target,'-p','rust-interp-bytecode','--bin','rust-interp-vm','--bin','scalar-cli-fixture'])
            vm=target/'release/rust-interp-vm';writer=target/'release/scalar-cli-fixture'
            for p in [vm,writer]:frozen[str(p.relative_to(ROOT))]=sha(p)
            command('fixtures',[writer,work])
            for name in ['scalar','legacy','bad-register','truncated']:frozen[str((work/(name+'.rbc')).relative_to(ROOT))]=sha(work/(name+'.rbc'))
            native=work/'native'
            command('native-build',['rustc','+nightly-2026-09-08',HERE/'native.rs','--edition=2024','-C','opt-level=0','-o',native])
            frozen[str(native.relative_to(ROOT))]=sha(native)
            seeds=[0,41,2**64-1]
            values=command('native',[native,*seeds])[0].splitlines()
            require(values==[str((n+7)%(2**64)) for n in seeds],'native reference differs')
            for engine in ['interpreter','jit']:
                for n,want in zip(seeds,values):
                    command(f'legacy-{engine}-{n}',[vm,'--engine',engine,work/'legacy.rbc',n],expected=want)
            modes=[('interpreter',['--engine','interpreter']),('jit',['--engine','jit']),
                ('persistent',['--engine','jit','--jit-persistent-registers']),
                ('resumable',['--engine','jit','--jit-resumable-calls']),
                ('both',['--engine','jit','--jit-resumable-calls','--jit-persistent-registers'])]
            for name,flags in modes:
                for n,want in zip(seeds,values):
                    _,stderr=command(f'scalar-{name}-{n}',[vm,*flags,work/'scalar.rbc',n],expected=want)
                    native_count=0 if name=='interpreter' else 3
                    require('instructions=4 ' in stderr and f'jit_instructions={native_count} ' in stderr,'scalar native statistics differ')
                profile=work/('profile-'+name+'.json')
                command('profile-'+name,[vm,*flags,'--profile',profile,work/'scalar.rbc',41],expected='48')
                p=read(profile);require(len(p['functions'])==1,'profile function count differs')
                f=p['functions'][0];hits=list(f['interpreted'])
                for pc,count in enumerate(f['jit_blocks']):
                    if count:
                        end=f['jit_block_ends'][pc];require(pc<end<=len(hits),'invalid profile range')
                        for i in range(pc,end):hits[i]+=count
                require(hits==[1,1,1,1] and not any(f['jit_tree_blocks']),'CLI per-PC profile differs')
                frozen[str(profile.relative_to(ROOT))]=sha(profile)
                for budget in range(6):
                    command(f'budget-{name}-{budget}',[vm,*flags,'--instruction-limit',budget,work/'scalar.rbc',41],
                        code=0 if budget>=4 else 1,expected='48' if budget>=4 else '',
                        error=None if budget>=4 else 'interpreter instruction limit exceeded')
            command('scalar-tree-rejected',[vm,'--engine','jit','--jit-native-calls',work/'scalar.rbc',41],code=1,expected='',
                error='scalar ABI does not support native tree/stub calls')
            command('bad-register-rejected',[vm,work/'bad-register.rbc',41],code=1,expected='',error='invalid scalar result register')
            command('truncated-rejected',[vm,work/'truncated.rbc',41],code=1,expected='',error='rust-interp-vm: ')
            command('wide-input-rejected',[vm,work/'scalar.rbc',2**64],code=1,expected='',error='entry argument exceeds its integer width')
            verify()
            result=dict(status='passed',tool_key=key,parent_tool_key=parent['tool_key'],commands=commands,frozen=frozen,
                provenance=str((work/'provenance.json').relative_to(ROOT)),provenance_sha256=sha(work/'provenance.json'),
                native_reference_inputs=seeds,successful_engine_cases=21,scalar_instruction_count=4,profile_instructions=4,native_instructions_per_success=3,native_modes=4,
                scalar_jit_supported=True,runtime_published=False,performance_measurement=False,
                limitation='Serialized fixture process checks only. Caller value operands, compiler promotion and real-workflow comparison remain.')
            write(work/'summary.json',result);out=ROOT/'results'/run;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print(dict(status='passed',commands=len(commands),native_reference_inputs=seeds,successful_engine_cases=21))
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise


if __name__=='__main__':main()
