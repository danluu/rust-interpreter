"""Check explicit experimental installation and Cargo scalar artifact selection."""
import argparse
import fcntl
import importlib.util
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
from build_relocation import read,write,sha,require,environment

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();run=args.run_id;require(re.fullmatch(r'scalar-value-cargo-[0-9]{2}',run),'invalid run')
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time());write(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            parent_path=ROOT/'results/scalar-value-frontend-02/summary.json';parent=read(parent_path)
            receipt_path=parent_path.with_name('execution.json');receipt=read(receipt_path)
            require(parent['status']=='passed' and parent['vm_executions']==360 and parent['strict_rejections']==3 and receipt['all_processes_terminal'],'frontend unqualified')
            require(all(sha(ROOT/p)==h for p,h in receipt['evidence'].items()),'frontend evidence changed')
            source_key=parent['tool_key'];target=ROOT/'.work/diagnostic-builds'/parent['build_run']/'release'
            require(all(sha(target/n)==h for n,h in parent['binaries'].items()),'qualified binaries changed')
            control_key='9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223'
            control=ROOT/'.work/interpreter-tools'/control_key
            control_manifest=read(control/'ready.json')
            require(all(sha(control/n)==h for n,h in control_manifest.items()),'production components changed')
            expected=dict(parent['binaries']);expected['rust-interp-rustc-wrapper']=control_manifest['rust-interp-rustc-wrapper']
            components={name:(control if name=='rust-interp-rustc-wrapper' else target)/name for name in expected}
            composition=dict(kind='scalar-shared-wrapper',schema_version=1,compiler_runtime_source_key=source_key,
                wrapper_source_key=control_key,binaries=expected)
            import hashlib
            key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()

            fixture=HERE.parent/'scalar-value-frontend-v2/fixture.rs'
            files=[p for p in HERE.iterdir() if p.is_file()]+[parent_path,receipt_path,fixture]
            files+=[ROOT/'scripts'/n for n in ['interpreter.py','allocation_trace.py','std_mir.py']]
            files+=[control/'ready.json',*components.values()]
            frozen={str(p.relative_to(ROOT)):sha(p) for p in files};commands=[];snapshots=[];checks=[]
            def verify():require(all(sha(ROOT/p)==h for p,h in frozen.items()),'Cargo qualification input changed')
            def command(label,argv,env=None,success=True,expected=None,error=None):
                verify();fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=8*1024**3,'eight-GiB floor rejected')
                argv=list(map(str,argv));out=work/(label+'.stdout');err=work/(label+'.stderr')
                with out.open('x') as stdout,err.open('x') as stderr:
                    child=subprocess.Popen(argv,cwd=ROOT,env=env or environment(),stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                    try:
                        status.update(status='running',child_pid=child.pid,command=argv,child_started_at=time.time(),child_cwd=str(ROOT),
                            child_identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True));write(work/'status.json',status)
                    finally:code=child.wait()
                commands.append(dict(label=label,command=argv,pid=child.pid,returncode=code,files={str(p.relative_to(ROOT)):sha(p) for p in [out,err]}));write(work/'commands.json',commands)
                text=out.read_text().strip();errors=err.read_text();require((code==0)==success,label+' exit differs')
                require('internal compiler error' not in errors,label+' compiler crashed')
                if expected is not None:require(text==expected,label+' stdout differs')
                if error is not None:require(error in errors,label+' error differs')
                verify();return text,errors
            def snapshot(label,path):
                path=Path(path);copy=work/(label+path.suffix);require(not copy.exists(),'snapshot collision')
                data=path.read_bytes();copy.write_bytes(data);digest=sha(copy);require(digest==sha(path),'snapshot changed')
                frozen[str(copy.relative_to(ROOT))]=digest;snapshots.append(dict(label=label,source=str(path),copy=str(copy.relative_to(ROOT)),sha256=digest));return copy
            # Installation is by explicit immutable key; normal source selection
            # remains the production key. Publish ready.json last under lock.
            with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
                fcntl.flock(publication,fcntl.LOCK_EX|fcntl.LOCK_NB)
                tools=ROOT/'.work/interpreter-tools'/key
                if not tools.exists():
                    tools.mkdir()
                    for name,digest in expected.items():
                        shutil.copy2(components[name],tools/name);require(sha(tools/name)==digest,'installed binary differs')
                    cap=json.loads(command('capabilities',[tools/'rust-interp-mir-export','--rust-interp-capabilities'])[0])
                    require(cap['schema_version']==1 and cap['bytecode_version']==5 and cap['artifact_versions']==[5,6] and 'scalar-values' in cap['export_options'],'scalar capability missing')
                    cap.update(tool_key=key,exporter_sha256=expected['rust-interp-mir-export']);write(tools/'capabilities.json',cap)
                    write(tools/'source.json',dict(tool_key=key,qualification=str(parent_path.relative_to(ROOT)),qualification_sha256=sha(parent_path),composition=composition,key_algorithm='SHA256 canonical sorted compact composition JSON',production_change=False))
                    write(tools/'ready.json',expected)
                require(read(tools/'ready.json')==expected,'existing tool manifest differs')
                for name,digest in expected.items():require(sha(tools/name)==digest,'installed tool changed')
            for p in tools.iterdir():
                if p.is_file():frozen[str(p.relative_to(ROOT))]=sha(p)
            spec=importlib.util.spec_from_file_location('scalar_cargo_launcher',HERE/'launcher.py');launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
            launcher.installed_tools(key);launcher.require_export_option(tools,key,'scalar-values')
            project=work/'project';project.mkdir();manifest=project/'Cargo.toml';lib=project/'lib.rs'
            manifest.write_text('[package]\nname="scalar-publication"\nversion="0.1.0"\nedition="2024"\n[lib]\npath="lib.rs"\n[workspace]\n')
            (project/'Cargo.lock').write_text('version = 4\n\n[[package]]\nname = "scalar-publication"\nversion = "0.1.0"\n')
            original=fixture.read_bytes();lib.write_bytes(original)
            for p in [manifest,project/'Cargo.lock']:frozen[str(p.relative_to(ROOT))]=sha(p)
            env=environment();env.pop('CARGO_BUILD_BUILD_DIR',None);env['RUST_INTERP_LAUNCH_STATS']='1'
            base=[sys.executable,HERE/'launcher.py','--manifest-path',manifest,'--package','scalar-publication','--tool-key',key,'--cache-namespace',run,'--jobs','2']
            native_target=work/'native-target'
            text,_=command('native-tests',['cargo','+nightly-2026-09-08','test','--manifest-path',manifest,'--lib','--locked','--offline','--jobs','2','--target-dir',native_target,'--','--test-threads=1'],env)
            require('test result: ok. 1 passed; 0 failed;' in text,'native assertion fixture missing')
            numeric=base+['--entry','rust_interp_entry']
            last=None
            for i,scalar in enumerate([False,True,True,False,True]):
                flags=['--scalar-values'] if scalar else []
                _,errors=command(f'toggle-{i}',numeric+flags+['--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--','0'],env,expected='66')
                rows=[json.loads(line.split(': ',1)[1]) for line in errors.splitlines() if line.startswith('rust-interp-launch: ')];require(len(rows)==1,'launcher receipt missing')
                row=rows[0];require(row['scalar_values']==scalar,'launcher scalar identity missing')
                artifact=Path(row['artifact_path']);require(sha(artifact)==row['artifact_sha256'],'selected artifact hash differs')
                require(int.from_bytes(artifact.read_bytes()[:4],'little')==(6 if scalar else 5),'Cargo flag not tracked')
                if i==2:require(row['artifact_sha256']==last['artifact_sha256'],'unchanged scalar artifact differs')
                snapshot(f'toggle-{i}-artifact',artifact);checks.append(dict(label=f'toggle-{i}',version=6 if scalar else 5,artifact_sha256=row['artifact_sha256']))
                last=row
            # Mismatch an owned cached sidecar, then restore exact bytes even if
            # rejection fails. This checks selection correctness, not no-op speed.
            artifact=Path(last['artifact_path']);saved=artifact.read_bytes()
            try:
                artifact.write_bytes((5).to_bytes(4,'little')+saved[4:])
                _,errors=command('wrong-header',numeric+['--scalar-values','--','0'],env,False,expected='',error='incompatible bytecode version; no program was run')
                require('rust-interp-vm:' not in errors,'mismatched artifact executed')
            finally:artifact.write_bytes(saved)
            require(sha(artifact)==last['artifact_sha256'],'sidecar restoration failed')
            for kind,bad in [('type','let _:u8="bad";'),('borrow','let mut a=1;let b=&a;a=2;let _=*b;')]:
                try:
                    lib.write_bytes(original+('\nfn unused_bad(){'+bad+'}\n').encode())
                    _,errors=command('cargo-'+kind,numeric+['--scalar-values','--','0'],env,False,expected='')
                    require('rust-interp-vm:' not in errors and 'rust-interp-launch:' not in errors,'invalid Cargo source executed stale artifact')
                finally:lib.write_bytes(original)
                require(lib.read_bytes()==original,'fixture restoration failed')
            command('restored',numeric+['--scalar-values','--','0'],env,expected='66')
            for scalar in [False,True]:
                flags=['--scalar-values'] if scalar else []
                command(f'assertions-{int(scalar)}',base+flags+['--entry','scalar_assertions','--test-body','--engine','jit','--jit-resumable-calls','--jit-persistent-registers'],env,expected='0')
                _,errors=command(f'trace-{int(scalar)}',numeric+flags+['--allocation-trace','--','0'],env,expected='66')
                trace=[json.loads(line.split(': ',1)[1]) for line in errors.splitlines() if line.startswith('rust-interp-allocation-trace: ')];require(len(trace)==1,'trace receipt missing')
                trace=trace[0];require(sha(Path(trace['artifact_path']))==trace['artifact_sha256'],'trace artifact hash differs')
                a=snapshot(f'trace-{int(scalar)}-artifact',trace['artifact_path']);t=snapshot(f'trace-{int(scalar)}-events',trace['path'])
                from allocation_trace import validate_trace
                require(validate_trace(t.read_bytes(),sha(a))==trace['events'],'trace event binding differs')
                selection=work/f'audit-selection-{int(scalar)}.json';write(selection,['scalar_assertions'])
                text,_=command(f'audit-{int(scalar)}',base+flags+['--audit-entries',selection,'--retain-audit-bodies','--test-body'],env)
                audit=json.loads(text);require(audit['bytecode_version']==(6 if scalar else 5) and audit['scalar_values']==scalar,'audit scalar identity differs')
                require(len(audit['entries'])==1 and audit['entries'][0]['status']=='lowered','assertion audit blocked')
                directory=Path(audit['artifacts']['directory']);body=directory/'0000.rbc';snapshot(f'audit-{int(scalar)}-body',body)
                require(int.from_bytes(body.read_bytes()[:4],'little')==(6 if scalar else 5),'audit body header differs')
                command(f'audit-body-{int(scalar)}',[tools/'rust-interp-vm','--engine','jit','--jit-resumable-calls','--jit-persistent-registers',body],env,expected='0')
                # Even a hash-consistent pack must reject a version mismatch.
                corrupt=json.loads(json.dumps(audit));corrupt['bytecode_version']=5 if scalar else 6
                try:launcher.validate_audit_pack(corrupt,directory.parent)
                except RuntimeError as error:require('version differs from audit' in str(error),'wrong audit rejection')
                else:raise RuntimeError('mismatched audit version accepted')
            verify();require(lib.read_bytes()==original,'fixture left modified')
            result=dict(status='passed',tool_key=key,source_tool_key=source_key,composition=composition,binaries=expected,experimental_tool_installed=True,production_change=False,performance_measurement=False,
                commands=commands,checks=checks,snapshots=snapshots,frozen=frozen,cargo_flag_states=[5,6,6,5,6],
                original_assertion_engines=['native','jit-v5','jit-v6'],strict_cargo_rejections=2,wrong_header_rejections=1,
                trace_versions=[5,6],audit_versions=[5,6],audit_version_rejections=2,fixture_restored=True,
                limitation='Cargo/fixture correctness qualified. Fresh original workload assertions and complete-command performance histories remain.')
            write(work/'summary.json',result);out=ROOT/'results'/run;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print(dict(status='passed',commands=len(commands),tool_key=key))
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise

if __name__=='__main__':main()
