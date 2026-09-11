#!/usr/bin/env python3
"""Compare production-body edits through a checked custom VM and native Cargo.

Each target is a real library crate plus a small integer-input consumer. Full
applications are not interpreted. Source changes and re-exports are restored
even on failure; existing modifications cause an immediate refusal.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'benchmarks'))
from interpreter_cases import CASES, adapter

TOOLCHAIN = 'nightly-2026-09-08'
BUILD = ROOT / '.work/interpreter-build/release'
CORPUS = json.loads((ROOT / 'benchmarks/corpus.json').read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextlib.contextmanager
def source_changes(case):
    source = ROOT / '.work/sources' / case['project']
    marker = json.loads((source / '.rust-interp-owned.json').read_text())
    revision = CORPUS['projects'][case['project']]['revision']
    if marker.get('owner') != str(ROOT) or marker.get('revision') != revision:
        raise RuntimeError('source ownership mismatch')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()!=revision:
        raise RuntimeError('source revision mismatch')
    if subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip():
        raise RuntimeError('source has existing tracked modifications')
    directory = source / case['directory']
    edit = directory / case['file']
    original = {edit:edit.read_bytes()}
    text = original[edit].decode()
    if text.count(case['old'])!=1:
        raise RuntimeError('edit anchor is not unique: ' + str(edit))
    current = dict(original)
    try:
        if case.get('module'):
            root = directory / 'src/lib.rs'
            original[root]=root.read_bytes()
            current[root]=original[root]+('\n#[doc(hidden)]\npub use '+case['module']+'::rust_interp_entry;\n').encode()
            root.write_bytes(current[root])
        def set_state(state):
            if edit.read_bytes()!=current[edit]:
                raise RuntimeError('edited source changed outside benchmark')
            replacement = case['old'] if state==0 else case['replacements'][state-1]
            current[edit]=(text.replace(case['old'],replacement)+adapter(case)).encode()
            edit.write_bytes(current[edit])
        set_state(0)
        yield directory,set_state
    finally:
        for path,content in original.items():
            if path.read_bytes()!=current[path]:
                raise RuntimeError('refusing to overwrite an external change to '+str(path))
            path.write_bytes(content)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cases',nargs='*',choices=list(CASES))
    parser.add_argument('--edits',type=int,default=5,choices=range(1,6))
    parser.add_argument('--count',type=int,default=1024)
    parser.add_argument('--run-id',default='interpreter-'+str(time.time_ns()))
    parser.add_argument('--only',choices=['vm','native'],help='coverage diagnosis; excluded from speed comparisons')
    args=parser.parse_args()
    lock=(ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    work=ROOT / '.work/runs' / args.run_id
    work.mkdir(parents=True)
    log=[]
    def run(command,cwd,env=None,allow_fail=False):
        start=time.perf_counter()
        output=work / f'{len(log):04}.log'
        with output.open('w') as stream:
            p=subprocess.Popen(list(map(str,command)),cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,text=True)
            record=dict(command=list(map(str,command)),cwd=str(cwd),pid=p.pid,started_ns=time.time_ns(),load=os.getloadavg(),log=str(output))
            p.wait()
        record.update(seconds=time.perf_counter()-start,returncode=p.returncode)
        log.append(record)
        (work / 'commands.json').write_text(json.dumps(log,indent=2))
        if p.returncode and not allow_fail: raise RuntimeError('command failed: '+str(output))
        return record,output.read_text()

    records=[]
    provenance=dict(toolchain=TOOLCHAIN,platform=platform.platform(),exporter_sha256=sha(BUILD/'rust-interp-mir-export'),vm_sha256=sha(BUILD/'rust-interp-vm'),cases_sha256=sha(ROOT/'benchmarks/interpreter_cases.py'),harness_sha256=sha(Path(__file__)),count=args.count)
    for name in args.cases or list(CASES):
        case=CASES[name]
        print(name+': preparing owned source',flush=True)
        try:
            with source_changes(case) as (directory,set_state):
                driver=work / name / 'driver'
                (driver / 'src').mkdir(parents=True)
                manifest='[package]\nname = "interpreter-corpus-driver"\nversion = "0.1.0"\nedition = "2024"\n[workspace]\n[dependencies]\nsubject = { package = '+json.dumps(case['package'])+', path = '+json.dumps(str(directory))+' }\n[profile.dev]\n'+case['profile']
                (driver / 'Cargo.toml').write_text(manifest)
                (driver / 'src/main.rs').write_text('fn main() { let a: Vec<String> = std::env::args().collect(); println!("{}", subject::rust_interp_entry(a[1].parse().unwrap(), a[2].parse().unwrap())); }\n')
                base=os.environ.copy()
                for key in list(base):
                    if key.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or key in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']:
                        base.pop(key,None)
                base.update(CARGO_TERM_COLOR='never',RUSTC_WRAPPER='',RUSTC_WORKSPACE_WRAPPER='')
                # Resolve once, then use an immutable driver lockfile for both modes.
                run(['cargo','+'+TOOLCHAIN,'generate-lockfile','--offline'],driver,base)
                output=work / name / 'program.rbc'
                seed=case.get('seed',0)
                previous={}
                modes=[args.only] if args.only else ['native','vm']
                for state in range(args.edits+1):
                    set_state(state)
                    order=modes if state%2==0 else list(reversed(modes))
                    pair={}
                    for mode in order:
                        target=work / name / ('target-'+mode)
                        env=base.copy();env['CARGO_TARGET_DIR']=str(target)
                        if mode=='vm':
                            env.update(RUSTC_WRAPPER=str(BUILD/'rust-interp-mir-export'),RUST_INTERP_EXPORT_CRATE=case['crate'],RUST_INTERP_ENTRY='rust_interp_entry',RUST_INTERP_OUTPUT=str(output))
                        build,text=run(['cargo','+'+TOOLCHAIN,'check' if mode=='vm' else 'build','--locked','--offline','--jobs','4','--message-format=json'],driver,env,allow_fail=True)
                        if build['returncode']:
                            records.append(dict(case=name,state=state,mode=mode,status='unsupported-or-build-failure',log=build['log']))
                            raise RuntimeError('build failed: '+build['log'])
                        artifacts=[]
                        for line in text.splitlines():
                            try:
                                event=json.loads(line)
                                if event.get('reason')=='compiler-artifact':artifacts.append(event)
                            except json.JSONDecodeError:pass
                        changed=[a for a in artifacts if a['target']['name']==case['crate'] and not a['fresh']]
                        if not changed:raise RuntimeError('sample did not rebuild the edited subject crate')
                        command=[BUILD/'rust-interp-vm',output,seed,args.count] if mode=='vm' else [target/'debug/interpreter-corpus-driver',seed,args.count]
                        execution,value=run(command,driver,base)
                        if mode in previous and value==previous[mode]:raise RuntimeError('edit did not change the observed output')
                        previous[mode]=value
                        pair[mode]=value
                        record=dict(case=name,project=case['project'],package=case['package'],revision=CORPUS['projects'][case['project']]['revision'],state=state,mode=mode,status='ok',build_seconds=build['seconds'],run_seconds=execution['seconds'],total_seconds=build['seconds']+execution['seconds'],value=value.strip(),build_log=build['log'],lock_sha256=sha(driver/'Cargo.lock'))
                        if mode=='vm':
                            record.update(bytecode_bytes=output.stat().st_size,export_stats=[line for line in text.splitlines() if line.startswith('rust-interp-export:')])
                        records.append(record)
                        print(f'{name} state={state} {mode}: build={build["seconds"]:.3f}s run={execution["seconds"]:.3f}s',flush=True)
                    if len(pair)==2 and pair['vm']!=pair['native']:raise RuntimeError('native/interpreter output mismatch')
                # Longer execution reveals whether interpreter time eats the build saving.
                if not args.only:
                    for count in [0,256,16384]:
                        values={}
                        for mode in ['native','vm']:
                            target=work / name / ('target-'+mode)
                            command=[BUILD/'rust-interp-vm',output,seed,count] if mode=='vm' else [target/'debug/interpreter-corpus-driver',seed,count]
                            execution,value=run(command,driver,base)
                            values[mode]=value
                            records.append(dict(case=name,mode=mode,status='runtime',count=count,seconds=execution['seconds']))
                        if values['vm']!=values['native']:raise RuntimeError('longer runtime output mismatch')
        except Exception as error:
            print(name+': '+str(error),flush=True)
            records.append(dict(case=name,status='failed',error=str(error)))
        finally:
            (work / 'samples.json').write_text(json.dumps(dict(provenance=provenance,samples=records),indent=2))
    out=ROOT/'results'/args.run_id
    out.mkdir(parents=True)
    # Public report contains aggregate performance, not private compiler logs.
    report=['# Custom interpreter: production-body edits','', 'Strict rustc checking; selected library routines, not full applications. Cold is one build with an empty target and downloaded dependencies. Warm is one measurement for each distinct body edit. Runtime is included.','', '| Case | Mode | Cold build/run s | Warm build s | Warm run s | Warm total s |', '|---|---|---:|---:|---:|---:|']
    for name in args.cases or list(CASES):
        for mode in ['native','vm']:
            samples=[r for r in records if r['case']==name and r.get('mode')==mode and r['status']=='ok']
            cold=[r for r in samples if r['state']==0]
            warm=[r for r in samples if r['state']>0]
            if cold and warm:
                med=lambda field:statistics.median(r[field] for r in warm)
                report.append(f'| {name} | {mode} | {cold[0]["total_seconds"]:.3f} | {med("build_seconds"):.3f} | {med("run_seconds"):.3f} | {med("total_seconds"):.3f} |')
    report.extend(['','Failures: '+str(sum(r['status']=='failed' for r in records))+'. Raw records: `.work/runs/'+args.run_id+'`.',''])
    (out/'summary.md').write_text('\n'.join(report))
    (out/'summary.json').write_text(json.dumps(dict(provenance=provenance,samples=[{k:v for k,v in r.items() if k not in ['log','build_log','error','value']} for r in records]),indent=2)+'\n')
    print(out/'summary.md')
    if any(r['status']=='failed' for r in records):raise SystemExit(1)


if __name__=='__main__':main()
