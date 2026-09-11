#!/usr/bin/env python3
"""Measure Cargo compilation units after actual production edits and test runs."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools
from std_mir import checked_std_mir
from workflow_cases import WORKFLOWS, WORKFLOW_VARIANTS


def unit_key(unit):
    return (unit['name'],unit['version'],unit['mode'],unit['target'],tuple(unit['features']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',choices=WORKFLOWS,default='nushell')
    parser.add_argument('--workflow',default='float-ranges')
    parser.add_argument('--run-id',default='cargo-profile-'+str(time.time_ns()))
    parser.add_argument('--edits',type=int,default=3)
    parser.add_argument('--build-tool-opt-level',type=int,choices=range(4))
    args=parser.parse_args()
    if args.workflow=='default':case=WORKFLOWS[args.project]
    elif (args.project,args.workflow) in WORKFLOW_VARIANTS:case=WORKFLOW_VARIANTS[args.project,args.workflow]
    else:parser.error('unknown project/workflow combination')
    if Path(args.run_id).name!=args.run_id or args.run_id in ['.','..']:
        parser.error('run-id must be a directory name')
    if not 1<=args.edits<=len(case['edits']):parser.error('invalid edit count')
    lock=(ROOT/'.work/benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    tools,key=checked_tools();std=checked_std_mir(TOOLCHAIN)
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
    env.update(CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
    if args.build_tool_opt_level is not None:
        for profile in ['DEV','TEST']:
            env[f'CARGO_PROFILE_{profile}_BUILD_OVERRIDE_OPT_LEVEL']=str(args.build_tool_opt_level)
    command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(source/'Cargo.toml'),
             '--package',case['package'],'--test-body','--engine','jit','--std-mir','--timings',
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
            record=dict(state=state,label=label,pid=p.pid,command=command,
                        seconds=time.perf_counter()-start,returncode=p.returncode,stdout=stdout,stderr=stderr,
                        source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),load=os.getloadavg())
            records.append(record);(work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
            assert p.returncode==0,stderr
            assert stdout.strip()=='0',stdout
            match=re.search(r'Timing report saved to (.+\.html)',stderr)
            assert match,stderr
            report=Path(match.group(1).strip('`')).resolve()
            assert report.is_relative_to(ROOT/'.work/interpreter-workspaces'),report
            content=report.read_text()
            units=json.JSONDecoder().raw_decode(content.split('const UNIT_DATA = ',1)[1])[0]
            assert units and any(u['name']==case['package'] for u in units)
            archived=work/f'timing-{state}.html';archived.write_text(content)
            record.update(units=units,timing_report=str(archived.relative_to(ROOT)),
                          timing_sha256=hashlib.sha256(archived.read_bytes()).hexdigest())
            (work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
            print(state,label,round(record['seconds'],3),'seconds;',len(units),'units',flush=True)
    finally:
        if file.read_bytes()!=current:raise RuntimeError('source changed outside this profile; refusing to overwrite it')
        file.write_bytes(original)
    per_edit=[{unit_key(u):u['duration'] for u in r['units']} for r in records[1:]]
    keys=set().union(*(values.keys() for values in per_edit))
    medians=[dict(name=k[0],version=k[1],mode=k[2],target=k[3],features=k[4],
                  seconds=statistics.median(values.get(k,0) for values in per_edit),
                  samples=[values.get(k,0) for values in per_edit]) for k in keys]
    medians.sort(key=lambda u:(-u['seconds'],u['name'],u['target']))
    result=dict(project=args.project,workflow=args.workflow,revision=revision,tool_key=key,std_mir_key=std[2],
                build_tool_opt_level=args.build_tool_opt_level,raw=str(work.relative_to(ROOT)),
                edits=args.edits,tests=case['tests'],test_source_unchanged=True,unit_medians=medians,
                median_command_seconds=statistics.median(r['seconds'] for r in records[1:]),
                scripts_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'scripts/interpreter.py',ROOT/'scripts/workflow_cases.py',ROOT/'scripts/std_mir.py']},
                vm_sha256=hashlib.sha256((tools/'rust-interp-vm').read_bytes()).hexdigest(),
                exporter_sha256=hashlib.sha256((tools/'rust-interp-mir-export').read_bytes()).hexdigest())
    out=ROOT/'results'/args.run_id;out.mkdir()
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    report=f'# Cargo compilation profile: {args.project} / {args.workflow}\n\n'
    report+=f'{args.edits} actual production edits, followed by the same existing test batch. The first build primes an independent cache and is excluded. '
    report+='These are instrumented diagnostic timings. Compilation units overlap; their durations do not sum to the complete command or its critical path. An unrecompiled unit counts as zero for that edit.\n\n'
    report+='| Package and target | Median compilation seconds |\n|---|---:|\n'
    report+=''.join(f'| {u["name"]}{u["target"]} | {u["seconds"]:.3f} |\n' for u in medians)
    report+='\nComplete Cargo timeline reports and exact unit features are retained with the raw records.\n'
    (out/'summary.md').write_text(report)
    print(out/'summary.md')


if __name__=='__main__':main()
