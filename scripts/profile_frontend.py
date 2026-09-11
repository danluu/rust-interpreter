#!/usr/bin/env python3
"""Profile rustc passes across real production edits in a selected test workflow."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools
from std_mir import checked_std_mir
from workflow_cases import WORKFLOWS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',choices=WORKFLOWS,default='ruff')
    parser.add_argument('--run-id',default='frontend-profile-'+str(time.time_ns()))
    parser.add_argument('--edits',type=int,default=3)
    parser.add_argument('--build-tool-opt-level',type=int,choices=range(4),help='override optimization of host build scripts and proc macros')
    args=parser.parse_args()
    case=WORKFLOWS[args.project]
    if Path(args.run_id).name!=args.run_id or args.run_id in ['.','..']:
        parser.error('run-id must be a directory name')
    if not 1<=args.edits<=len(case['edits']):parser.error('invalid edit count')
    (ROOT/'.work').mkdir(exist_ok=True)
    lock=(ROOT/'.work/benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    tools,key=checked_tools()
    std=checked_std_mir(TOOLCHAIN)
    source=ROOT/'.work/sources'/args.project
    revision=json.loads((ROOT/'benchmarks/corpus.json').read_text())['projects'][args.project]['revision']
    marker=json.loads((source/'.rust-interp-owned.json').read_text())
    if marker['owner']!=str(ROOT) or marker['revision']!=revision:
        raise RuntimeError('snapshot ownership or revision mismatch')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()!=revision:
        raise RuntimeError('snapshot HEAD mismatch')
    if subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip():
        raise RuntimeError('snapshot has tracked changes')
    work=ROOT/'.work/runs'/args.run_id;work.mkdir(parents=True)
    file=source/case['file'];original=file.read_bytes();current=original
    test_marker='\n#[cfg(test)]\nmod tests {'
    assert original.decode().count(test_marker)==1
    original_tests=original.decode().split(test_marker)[1]
    env=os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or name in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']:
            env.pop(name,None)
    env.update(CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1',
               RUSTFLAGS='-Ztime-passes -Ztime-passes-format=json')
    if args.build_tool_opt_level is not None:
        for profile in ['DEV','TEST']:
            env[f'CARGO_PROFILE_{profile}_BUILD_OVERRIDE_OPT_LEVEL']=str(args.build_tool_opt_level)
    command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(source/'Cargo.toml'),
             '--package',case['package'],'--test-body','--engine','jit','--std-mir',
             '--instruction-limit','1000000000','--cache-namespace',args.run_id]
    for test in case['tests']:command+=['--entry',test]
    records=[]
    try:
        for state in range(args.edits+1):
            candidate=original.decode();label='cold-original'
            for label,old,new in case['edits'][:state]:
                assert candidate.count(old)==1,label
                candidate=candidate.replace(old,new)
            assert candidate.split(test_marker)[1]==original_tests
            if file.read_bytes()!=current:raise RuntimeError('source changed outside this profile')
            if state:current=candidate.encode();file.write_bytes(current)
            start=time.perf_counter()
            p=subprocess.Popen(command,cwd=source,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            stdout,stderr=p.communicate()
            # During warm edits only the selected package should compile, so
            # phase records cannot mix it with concurrent dependency compiles.
            selected=stderr.split('Checking '+case['package'])[-1]
            phases=[json.loads(line[6:]) for line in selected.splitlines() if line.startswith('time: {')]
            record=dict(state=state,label=label,pid=p.pid,command=command,
                        seconds=time.perf_counter()-start,returncode=p.returncode,
                        stdout=stdout,stderr=stderr,phases=phases,
                        source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),load=os.getloadavg())
            records.append(record);(work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
            assert p.returncode==0,stderr
            assert stdout.strip()=='0',stdout
            assert phases and 'Checking '+case['package'] in stderr
            if state:
                checked=[line.split()[1] for line in stderr.splitlines() if line.lstrip().startswith(('Checking ','Compiling '))]
                assert checked==[case['package']],checked
            print(state,label,round(record['seconds'],3),flush=True)
    finally:
        if file.read_bytes()!=current:raise RuntimeError('source changed outside this profile; refusing to overwrite it')
        file.write_bytes(original)
    values={}
    for r in records[1:]:
        grouped={}
        for phase in r['phases']:grouped[phase['pass']]=grouped.get(phase['pass'],0)+phase['time']
        for name,value in grouped.items():values.setdefault(name,[]).append(value)
    medians={k:statistics.median(v) for k,v in values.items()}
    result=dict(project=args.project,revision=revision,tool_key=key,std_mir_key=std[2],
                build_tool_opt_level=args.build_tool_opt_level,compiler_flags=env['RUSTFLAGS'],
                raw=str(work.relative_to(ROOT)),edits=args.edits,tests=case['tests'],
                test_source_unchanged=True,phase_median_seconds=medians,
                scripts_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'scripts/interpreter.py',ROOT/'scripts/workflow_cases.py',ROOT/'scripts/std_mir.py']},
                vm_sha256=hashlib.sha256((tools/'rust-interp-vm').read_bytes()).hexdigest(),
                exporter_sha256=hashlib.sha256((tools/'rust-interp-mir-export').read_bytes()).hexdigest())
    out=ROOT/'results'/args.run_id;out.mkdir()
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    report=f'# Frontend pass profile: {args.project}\n\n'
    report+=f'{args.edits} actual production edits, followed by the same existing test batch each time. '
    if args.build_tool_opt_level is not None:report+=f'Host build-tool optimization level is {args.build_tool_opt_level}. '
    report+='The first build primes a separate artifact cache and is excluded from the pass medians. '
    report+='These are instrumented diagnostic timings, not a performance comparison. Nested phases overlap; do not sum them.\n\n'
    report+='| Compiler pass | Median seconds |\n|---|---:|\n'
    report+=''.join(f'| {name} | {value:.6f} |\n' for name,value in sorted(medians.items(),key=lambda p:-p[1]))
    (out/'summary.md').write_text(report)
    print(out/'summary.md')


if __name__=='__main__':main()
