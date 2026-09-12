"""Qualify explicit caller value execution in an isolated tree; do not publish a runtime."""
import argparse
import fcntl
import hashlib
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import shutil
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'aggregate-byte-writes'))
from build_relocation import read,write,sha,require,installed_tools,environment
from tool_source_index import index
from inject import inject


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    run=parser.parse_args().run_id;require(re.fullmatch(r'scalar-value-calls-build-[0-9]{2}',run),'invalid run ID')
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time())
    write(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            fs=os.statvfs(ROOT);free=fs.f_bavail*fs.f_frsize;require(free>=12*1024**3,'insufficient isolated build allowance')
            parent_path=ROOT/'results/scalar-abi-native-build-03/summary.json';parent=read(parent_path)
            receipt_path=parent_path.with_name('execution.json');receipt=read(receipt_path)
            require(parent['status']=='passed' and receipt['all_processes_terminal'] and
                parent['tests']['debug']['passed']==parent['tests']['release']['passed']==310 and
                parent['tool_key']=='5ce80a8a226682586672e8f18188929718ceca70cc532ddc02ac39de964cde20','native parent not qualified')
            for p,h in receipt['evidence'].items():require(sha(ROOT/p)==h,'parent receipt changed')
            provenance=ROOT/parent['provenance'];require(sha(provenance)==parent['provenance_sha256'],'parent provenance changed')
            previous=read(provenance);original=ROOT/previous['source']
            require(all(sha(original/p)==h for p,h in previous['copied_inputs'].items()),'parent source changed')
            compiler=subprocess.check_output(['rustc','+nightly-2026-09-08','-vV'],text=True)
            require('commit-hash: cea272fa356e94bd2ee2cadf376630aa0683867a' in compiler,'wrong compiler')
            recipes=[p for p in HERE.iterdir() if p.is_file()]
            recipes += [parent_path,receipt_path,provenance,ROOT/'scripts/tool_source_index.py',ROOT/'scripts/interpreter.py',
                ROOT/'benchmarks/experiments/aggregate-byte-writes/build_relocation.py',
                ROOT/'benchmarks/experiments/aggregate-byte-writes/build.py',ROOT/'rust-toolchain.toml']
            frozen={str(p.relative_to(ROOT)):sha(p) for p in recipes}
            source=work/'tool-source';source.mkdir()
            for path,digest in previous['copied_inputs'].items():
                relative=Path(path);require(not relative.is_absolute() and '..' not in relative.parts,'invalid source path')
                destination=source/relative;destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(original/relative,destination);require(sha(destination)==digest,'copy differs')
            inject(source)
            inputs=[source/'Cargo.toml',source/'Cargo.lock']
            for crate in ['bytecode','mir-export']:
                inputs+=sorted((source/'crates'/crate).rglob('*.rs'));inputs.append(source/'crates'/crate/'Cargo.toml')
            digest=hashlib.sha256()
            for p in inputs:digest.update(str(p.relative_to(source)).encode()+b'\0'+p.read_bytes())
            key=digest.hexdigest();copied={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
            proof=dict(source=str(source.relative_to(ROOT)),parent_provenance=str(provenance.relative_to(ROOT)),parent_provenance_sha256=sha(provenance),
                parent_tool_key=parent['tool_key'],tool_key=key,compiler=compiler,root_frozen=frozen,copied_inputs=copied,
                production_change=False,runtime_published=False,scalar_guest_execution_supported=True,
                observed_free_bytes=free,required_free_bytes=12*1024**3)
            write(work/'provenance.json',proof)
            def verify():
                require(all(sha(ROOT/p)==h for p,h in frozen.items()),'frozen input changed')
                require(all(sha(source/p)==h for p,h in copied.items()),'isolated source changed')
            env=environment();commands=[];reports={}
            def command(label,argv):
                verify();fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=8*1024**3,'eight-GiB floor rejected')
                out=work/(label+'.log');err=work/(label+'.stderr')
                with out.open('x') as stdout,err.open('x') as stderr:
                    child=subprocess.Popen(argv,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                    try:
                        status.update(status='running',child_pid=child.pid,command=argv,child_started_at=time.time(),child_cwd=str(source),
                            child_identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True))
                        write(work/'status.json',status)
                    finally:code=child.wait()
                commands.append(dict(label=label,command=argv,pid=child.pid,returncode=code,
                    files={str(p.relative_to(ROOT)):sha(p) for p in [out,err]}))
                write(work/'commands.json',commands);require(code==0,label+' failed');verify()
            target=ROOT/'.work/diagnostic-builds'/run;require(not target.exists(),'build target already exists')
            cargo=['cargo','+nightly-2026-09-08'];flags=['--locked','--offline','--jobs','2','--manifest-path',str(source/'Cargo.toml'),'--target-dir',str(target)]
            for label,extra in [('debug',[]),('release',['--release'])]:
                command(label,cargo+['test','--workspace',*extra,*flags])
                text=(work/(label+'.log')).read_text()
                counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',text)
                passed=sum(int(p) for p,_,_ in counts);ignored=sum(int(i) for _,_,i in counts)
                names=re.findall(r'^test (scalar_abi::tests::\S+) \.\.\. ok$',text,re.M)
                runtime_names=re.findall(r'^test (scalar_abi::runtime::tests::\S+) \.\.\. ok$',text,re.M)
                native_names=re.findall(r'^test (scalar_abi::runtime::tests::native::\S+) \.\.\. ok$',text,re.M)
                value_names=re.findall(r'^test (scalar_abi::runtime::tests::value_calls::\S+) \.\.\. ok$',text,re.M)
                require(passed==318 and ignored==1 and all(int(f)==0 for _,f,_ in counts) and len(names)==8 and len(runtime_names)==20 and len(native_names)==5 and len(value_names)==7
                    and 'test native_continuation::tests::value_return_publication_checks_caller_register_width_and_tag_context ... ok' in text,'workspace qualification differs')
                reports[label]=dict(passed=passed,ignored=ignored,artifact_tests=names,scalar_runtime_tests=runtime_names,scalar_native_tests=native_names,value_call_tests=value_names)
            command('build',cargo+['build','--release','-p','rust-interp-bytecode','--bin','scalar-abi-check',*flags])
            checker=target/'release/scalar-abi-check';frozen[str(checker.relative_to(ROOT))]=sha(checker)
            cases=[]
            for label,expected in [('folded-literal-trie','cf45794029c9d2fe5538da4cb1f7c74e28f909da0c0a2825c1410ef2de25320e'),
                ('token-phrase','d4e1314465a7bbf8ff8b74caefb1a6dc1ea87a310e6f2c716b02e7b6e5f38096')]:
                artifact=ROOT/'.work/runs'/('aggregate-relocation-e2e-01-'+label)/'artifacts/candidate/cycle-0/0-0.rbc'
                require(sha(artifact)==expected,'original artifact changed');frozen[str(artifact.relative_to(ROOT))]=expected
                command(label,[str(checker),str(artifact)])
                output=(work/(label+'.log')).read_text().strip();require(re.fullmatch(r'version=5 functions=\d+ identical=true',output),'original roundtrip differs')
                cases.append(dict(label=label,artifact=str(artifact.relative_to(ROOT)),artifact_sha256=expected,output=output))
            verify()
            result=dict(status='passed',tool_key=key,parent_tool_key=parent['tool_key'],tests=reports,cases=cases,commands=commands,
                provenance=str((work/'provenance.json').relative_to(ROOT)),provenance_sha256=sha(work/'provenance.json'),frozen=frozen,
                production_change=False,runtime_published=False,scalar_runtime_tests=20,caller_value_tests=7,scalar_jit_execution_supported=True,performance_measurement=False,
                limitation='Caller value interpreter/native library APIs qualified. Typed compiler promotion and real-workflow comparison remain; no runtime published.')
            write(work/'summary.json',result);out=ROOT/'results'/run;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print(dict(status='passed',tests=reports,cases=cases))
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise


if __name__=='__main__':main()
