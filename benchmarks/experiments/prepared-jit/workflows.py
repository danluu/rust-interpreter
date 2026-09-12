#!/usr/bin/env python3
"""Qualify and describe real edited commands with native/fresh/prepared test isolation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
import bench_e2e_workflow as bench
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from suite_reports import read_report, validate_report
from verify_repeated_workflow import verify
from workflow_controls import native_environment
from workflow_io import capture, require_space, write_json as write
from workflow_measurements import child_usage, child_cpu_since

REFERENCES={
    'pgrust':'aggregate-relocation-heldout-01-pgrust',
    'token':'export-reuse-screen-token-01',
    'folded':'aggregate-relocation-e2e-01-folded-literal-trie',
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=REFERENCES,required=True)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    assert re.fullmatch('prepared-suite-'+args.case+r'-\d{2}',args.run_id)
    assert not any(name.startswith('DYLD_') for name in os.environ),'ambient native interposition is unsupported'
    build_path=ROOT/'results/prepared-jit-build-04/summary.json'
    build=json.loads(build_path.read_text())
    assert build['status']=='passed' and all(row==dict(passed=320,ignored=1) for row in build['tests'].values())
    tool,key=installed_tools(build['tool_key'])
    ref_path=ROOT/'results'/REFERENCES[args.case]/'summary.json'
    reference=json.loads(ref_path.read_text())
    work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
    command=[str(ROOT/'scripts/bench_e2e_workflow.py'),'--run-id',args.run_id,
        '--project',reference['project'],'--workflow',reference['workflow'],'--batch','--cycles','1',
        '--jobs','2','--native-profile','repository','--native-test-threads','1',
        '--baseline-tool-key',key,'--candidate-tool-key',key,'--comparison-engine','jit',
        '--compare-isolated-batches','--expect-identical-bytecode','--check-floor','--std-mir',
        '--baseline-jit-resumable-calls','--candidate-jit-resumable-calls',
        '--baseline-jit-persistent-registers','--candidate-jit-persistent-registers',
        '--lock-wait-seconds','45','--minimum-free-gib','8','--instruction-limit',str(reference['instruction_limit'])]
    for flag,field in [('guest-mir-opt-level','guest_mir_opt_level'),('guest-mir-inline-scale','guest_mir_inline_scale'),
                       ('build-tool-opt-level','build_tool_opt_level'),('allocation-limit','allocation_limit')]:
        if reference.get(field) is not None:command+=['--'+flag,str(reference[field])]
    if reference['inline_leaves']:command+=['--inline-leaves','--baseline-inline-leaves']
    for flag in ['trap-unsupported-calls','run-try-callbacks']:
        if reference.get(flag.replace('-','_')):command+=['--'+flag]
    paths=[Path(__file__),Path(__file__).with_name('WORKFLOWS.md'),build_path,ref_path]
    paths += [ROOT/'scripts'/name for name in ['bench_e2e_workflow.py','interpreter.py','workflow_io.py',
        'workflow_controls.py','workflow_measurements.py','workflow_cases.py','workflow_case_file.py',
        'workflow_jobs.py','verify_repeated_workflow.py','std_mir.py','native_suite.py','suite_reports.py','compare_saved_runtime.py']]
    paths += [tool/name for name in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper','ready.json']]
    frozen={str(path.relative_to(ROOT)):sha(path) for path in paths}
    write(work/'plan.json',dict(command=command,frozen=frozen,minimum_start_gib=9 if args.case=='pgrust' else 10,
        scope='one-cycle descriptive qualification, no default-promotion or general speedup claim'))
    require_space(ROOT,9 if args.case=='pgrust' else 10)
    original_argv=sys.argv
    try:
        sys.argv=command;bench.main()
    finally:
        sys.argv=original_argv
    out=ROOT/'results'/args.run_id
    report=json.loads((out/'summary.json').read_text())
    checked=verify(report);write(out/'verification.json',checked)
    rows=json.loads((ROOT/report['raw']/'records.json').read_text())
    # Rebuild the restored original through each existing cache, without mixing
    # this correctness control into the five source-edit timing pairs.
    source=ROOT/'.work/sources'/reference['project']
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
    env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','CARGO_PROFILE_')) and
        k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER',
                  'CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
    env.update(CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
    if reference.get('build_tool_opt_level') is not None:
        for profile in ['DEV','TEST']:env['CARGO_PROFILE_'+profile+'_BUILD_OVERRIDE_OPT_LEVEL']=str(reference['build_tool_opt_level'])
    restored=[];artifacts=[]
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        for mode in ['native','baseline','candidate','check']:
            if mode=='check':
                prior=json.loads((ROOT/report['raw']/'check-records.json').read_text())[-1]
                command=list(prior['command']);child_env=native_environment(env,'repository',[]);suite_path=None
            else:
                prior=[row for row in rows if row['mode']==mode][-1]
                call=prior['calls'][0];command=list(call['command']);child_env=env.copy()
                suite_path=work/(mode+'-restored.json')
                command[command.index('--suite-report')+1]=str(suite_path)
                if mode=='native':child_env=native_environment(env,'repository',[])
                elif call.get('rustflags'):child_env['RUSTFLAGS']=call['rustflags']
            require_space(ROOT,8)
            start=time.perf_counter();before=child_usage()
            child,stdout,stderr=capture(command,cwd=source,env=child_env,receipt_path=work/'active.json',
                receipt=dict(mode=mode,phase='restored-original'))
            row=dict(mode=mode,command=command,seconds=time.perf_counter()-start,cpu=child_cpu_since(before),
                returncode=child.returncode,stdout=stdout,stderr=stderr)
            restored.append(row);write(work/'restoration.json',restored)
            assert child.returncode==0,stderr
            assert ('Compiling ' if mode=='native' else 'Checking ')+command[command.index('--package')+1] in stderr
            if suite_path is not None:
                suite,digest=read_report(suite_path)
                validate_report(suite,prior['tests'],'native' if mode=='native' else 'fresh' if mode=='baseline' else 'prepared',True)
                row['suite_sha256']=digest
            if mode in ['baseline','candidate']:
                launches=[json.loads(line.removeprefix('rust-interp-launch: ')) for line in stderr.splitlines() if line.startswith('rust-interp-launch: ')]
                assert len(launches)==1 and launches[0]['suite_report_sha256']==digest
                launch=launches[0];artifact=Path(launch['artifact_path'])
                payload=artifact.read_bytes();assert hashlib.sha256(payload).hexdigest()==launch['artifact_sha256']
                with (work/(mode+'-restored.rbc')).open('xb') as destination:destination.write(payload)
                row['artifact_sha256']=launch['artifact_sha256'];artifacts.append(launch['artifact_sha256'])
            write(work/'restoration.json',restored)
        assert len(artifacts)==2 and artifacts[0]==artifacts[1]
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
    assert all(sha(ROOT/path)==digest for path,digest in frozen.items())
    pairs=report['comparison']['pairs']
    result=dict(status='passed',case=args.case,tool_key=key,primary_commands=len(rows),check_commands=checked['check_commands'],
        restored_commands=len(restored),edited_pairs=len(pairs),source_restored=True,test_source_unchanged=True,
        wrong_edit_assertions_match=True,paired_bytecode_identical=True,
        wall_ratio=statistics.median(p['candidate_seconds']/p['baseline_seconds'] for p in pairs),
        cpu_ratio=statistics.median(p['candidate_cpu_seconds']/p['baseline_cpu_seconds'] for p in pairs),
        median_seconds=report['median_seconds'],cold_seconds=report['cold_success_seconds'],
        scope='Five distinct edits, descriptive only. Native uses one process per test; no full-libtest or unchanged-build claim.',
        raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),restoration_sha256=sha(work/'restoration.json'))
    write(out/'isolated-assessment.json',result);print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
