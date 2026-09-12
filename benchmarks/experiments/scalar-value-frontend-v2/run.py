"""Qualify real strict MIR exports before any scalar performance experiment."""
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
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'aggregate-byte-writes'))
from build_relocation import read,write,sha,require,environment
BASELINE='9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'
FLAGS=['-Zmir-opt-level=3','-Zinline-mir-threshold=400','-Zinline-mir-hint-threshold=800','-Zinline-mir-forwarder-threshold=240']

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    parser.add_argument('--build-run',required=True);args=parser.parse_args();run=args.run_id
    require(re.fullmatch(r'scalar-value-frontend-[0-9]{2}',run) and re.fullmatch(r'scalar-value-compiler-build-[0-9]{2}',args.build_run),'invalid run')
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time());write(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            build_path=ROOT/'results'/args.build_run/'summary.json';build=read(build_path)
            receipt_path=build_path.with_name('execution.json');receipt=read(receipt_path)
            require(build['status']=='passed' and build['tests']['debug']['passed']==build['tests']['release']['passed']==334 and receipt['all_processes_terminal'],'compiler not qualified')
            require(all(sha(ROOT/p)==h for p,h in receipt['evidence'].items()),'build evidence changed')
            proof=read(ROOT/build['provenance']);source=ROOT/proof['source']
            require(sha(ROOT/build['provenance'])==build['provenance_sha256'],'provenance changed')
            require(all(sha(source/p)==h for p,h in proof['copied_inputs'].items()),'compiled source changed')
            target=ROOT/'.work/diagnostic-builds'/args.build_run
            tools=target/'release';names=['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']
            fixture_sources=[HERE/'fixture.rs',ROOT/'benchmarks/experiments/aggregate-byte-writes/fixture.rs',ROOT/'tests/caller_fixture.rs',ROOT/'tests/scalar_constant_fixture.rs',ROOT/'tests/coercion_fixture.rs']
            files=[p for p in HERE.iterdir() if p.is_file()]+fixture_sources+[build_path,receipt_path,ROOT/build['provenance']]
            files+=[ROOT/'scripts'/name for name in ['interpreter.py','allocation_trace.py','std_mir.py']]
            files+=[tools/n for n in names]
            frozen={str(p.relative_to(ROOT)):sha(p) for p in files}
            commands=[];cases=[]
            def verify():require(all(sha(ROOT/p)==h for p,h in frozen.items()),'frontend frozen input changed')
            def command(label,argv,env=None,success=True,expected=None,error=None):
                verify();fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=8*1024**3,'eight-GiB floor rejected')
                argv=list(map(str,argv));out=work/(label+'.stdout');err=work/(label+'.stderr')
                with out.open('x') as stdout,err.open('x') as stderr:
                    child=subprocess.Popen(argv,cwd=ROOT,env=env or environment(),stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                    try:
                        status.update(status='running',child_pid=child.pid,command=argv,child_started_at=time.time(),child_cwd=str(ROOT),
                            child_identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True))
                        write(work/'status.json',status)
                    finally:code=child.wait()
                commands.append(dict(label=label,command=argv,pid=child.pid,returncode=code,files={str(p.relative_to(ROOT)):sha(p) for p in [out,err]}));write(work/'commands.json',commands)
                text=out.read_text().strip();errors=err.read_text()
                require((code==0)==success,label+' exit differs')
                require('internal compiler error' not in errors,label+' compiler crashed')
                if expected is not None:require(text==expected,label+' stdout differs')
                if error is not None:require(error in errors,label+' error differs')
                verify();return text,errors
            # Compile only a host artifact inspector against these exact release
            # libraries. It never executes guest instructions or supplies MIR.
            libraries=list((target/'release/build').glob('*/*/out/*.rlib'))
            extern=[]
            for crate in ['rust_interp_bytecode','serde_json']:
                matches=[p for p in libraries if p.name.startswith('lib'+crate+'-')]
                require(len(matches)==1,'ambiguous inspector dependency: '+crate)
                extern+=['--extern',crate+'='+str(matches[0]),'--extern',crate+'='+str(matches[0].with_suffix('.rmeta'))]
            libraries+=list((target/'release/build').glob('*/*/out/*.rmeta'))+list((target/'release/build').glob('*/*/out/*.dylib'))
            library_dirs=sorted(set(p.parent for p in libraries));search=[]
            for directory in library_dirs:search+=['-L','dependency='+str(directory)]
            for p in libraries:frozen[str(p.relative_to(ROOT))]=sha(p)
            inspector=work/'inspect'
            command('inspect-build',['rustc','+nightly-2026-09-08',HERE/'inspect.rs','--edition=2024',*extern,*search,'-o',inspector])
            frozen[str(inspector.relative_to(ROOT))]=sha(inspector)
            seeds=[0,1,7,255,2**63,2**64-1]
            modes=[('interpreter',['--engine','interpreter']),('jit',['--engine','jit']),
                ('both',['--engine','jit','--jit-resumable-calls','--jit-persistent-registers'])]
            for number,fixture in enumerate(fixture_sources):
                native=work/f'native-{number}'
                command(f'native-build-{number}',['rustc','+nightly-2026-09-08',fixture,'--edition=2024','-C','overflow-checks=off','-o',native])
                frozen[str(native.relative_to(ROOT))]=sha(native)
                wants=command(f'native-{number}',[native,*seeds])[0].splitlines();require(len(wants)==len(seeds),'native results missing')
                for enlarged in [False,True]:
                    previous=None
                    for scalar in [False,True]:
                        label=f'fixture-{number}-{int(enlarged)}-{int(scalar)}';artifact=work/(label+'.rbc')
                        env=environment();env.update(RUST_INTERP_ENTRY='rust_interp_entry',RUST_INTERP_OUTPUT=str(artifact))
                        if scalar:env['RUST_INTERP_SCALAR_VALUES']='1'
                        if enlarged:env['RUST_INTERP_INLINE_LEAVES']='1'
                        _,errors=command(label,[tools/'rust-interp-mir-export',fixture,'--crate-name','scalar_fixture','--edition=2024','--emit=metadata',
                            '-C','overflow-checks=off','-o',artifact.with_suffix('.rmeta'),*(FLAGS if enlarged else [])],env)
                        require(int.from_bytes(artifact.read_bytes()[:4],'little')==(6 if scalar else 5),'wrong artifact version')
                        diagnostic=json.loads(command(label+'-inspect',[inspector,artifact])[0])
                        promoted=[json.loads(line.split(': ',1)[1]) for line in errors.splitlines() if line.startswith('rust-interp-scalar-values: ')]
                        require(len(promoted)==int(scalar),'promotion receipt missing or leaked to control')
                        if scalar:
                            report=promoted[0]['report'];require(report['declined_functions']==0 and promoted[0]['capture_declines']==0,'fixture exhausted proof bounds')
                            if number==0:
                                require(report['argument_registers']>0 and report['result_registers']>0,'no ABI promotion')
                                require(report['value_arguments']>0 and report['value_destinations']>0,'no compiler value calls')
                            require(sum(len(f['calls']) for f in diagnostic['functions'])==report['value_calls'],'emitted calls differ from report')
                            if number==0 and not enlarged:
                                for function,admitted in [('mix',True),('recursive',True),('pointer_read',True),('projected',False)]:
                                    rows=[f for f in diagnostic['functions'] if f['name'].split('[')[0].rsplit('::',1)[-1]==function]
                                    require(len(rows)==1,'typed fixture identity missing: '+function)
                                    require((rows[0]['abi']['arguments'][0] is not None)==admitted,'typed admission differs: '+function)
                        else:previous=artifact
                        for seed,want in zip(seeds,wants):
                            for mode,flags in modes:
                                command(f'{label}-{mode}-{seed}',[tools/'rust-interp-vm',*flags,artifact,seed],expected=want)
                        frozen[str(artifact.relative_to(ROOT))]=sha(artifact)
                        cases.append(dict(label=label,source=str(fixture.relative_to(ROOT)),scalar=scalar,enlarged=enlarged,
                            artifact=str(artifact.relative_to(ROOT)),artifact_sha256=sha(artifact),promotion=promoted,
                            native_inputs=seeds,engine_cases=len(seeds)*len(modes)))
                    # Compare flag-off output with the retained production exporter.
                    artifact=work/f'baseline-{number}-{int(enlarged)}.rbc';env=environment();env.update(RUST_INTERP_ENTRY='rust_interp_entry',RUST_INTERP_OUTPUT=str(artifact))
                    if enlarged:env['RUST_INTERP_INLINE_LEAVES']='1'
                    baseline=ROOT/'.work/interpreter-tools'/BASELINE/'rust-interp-mir-export';frozen[str(baseline.relative_to(ROOT))]=sha(baseline)
                    command(f'baseline-{number}-{int(enlarged)}',[baseline,fixture,'--crate-name','scalar_fixture','--edition=2024','--emit=metadata',
                        '-C','overflow-checks=off','-o',artifact.with_suffix('.rmeta'),*(FLAGS if enlarged else [])],env)
                    require(artifact.read_bytes()==previous.read_bytes(),'flag-off bytecode changed from production')
            # Strict frontend errors in uncalled functions must prevent publication.
            for kind,bad,diagnostic in [('type','let _:u8="bad";','mismatched types'),
                ('borrow','let mut a=1;let b=&a;a=2;let _=*b;','cannot assign to')]:
                fixture=work/(kind+'.rs');fixture.write_text('pub fn rust_interp_entry(a:u64)->u64{a}\nfn unused(){'+bad+'}\nfn main(){}\n')
                artifact=fixture.with_suffix('.rbc');env=environment();env.update(RUST_INTERP_ENTRY='rust_interp_entry',RUST_INTERP_OUTPUT=str(artifact),RUST_INTERP_SCALAR_VALUES='1')
                command(kind,[tools/'rust-interp-mir-export',fixture,'--edition=2024','--emit=metadata','-o',fixture.with_suffix('.rmeta')],env,False,error=diagnostic)
                require(not artifact.exists(),'invalid program published')
            fixture=HERE/'fixture.rs';artifact=work/'partial.rbc';env=environment();env.update(RUST_INTERP_ENTRY='rust_interp_entry',RUST_INTERP_OUTPUT=str(artifact),RUST_INTERP_SCALAR_VALUES='1',RUST_INTERP_DEMAND_BODIES='1')
            command('partial',[tools/'rust-interp-mir-export',fixture,'--edition=2024','--emit=metadata','-o',artifact.with_suffix('.rmeta')],env,False,error='scalar values require strict frontend checking')
            require(not artifact.exists(),'partial scalar published')
            verify()
            result=dict(status='passed',tool_key=build['tool_key'],build_run=args.build_run,binaries={n:sha(tools/n) for n in names},
                cases=cases,commands=commands,frozen=frozen,strict_rejections=3,vm_executions=sum(c['engine_cases'] for c in cases),
                performance_measurement=False,production_change=False,runtime_published=False,
                limitation='Direct strict MIR exports qualified. Cargo flag toggles, audit packs, traces and real workflows remain.')
            write(work/'summary.json',result);out=ROOT/'results'/run;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print(dict(status='passed',commands=len(commands),vm_executions=result['vm_executions']))
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise

if __name__=='__main__':main()
