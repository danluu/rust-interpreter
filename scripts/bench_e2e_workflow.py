#!/usr/bin/env python3
"""Edit production code, then execute existing project tests."""
import argparse
import fcntl
import hashlib
import itertools
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools, installed_tools, require_export_option


from workflow_cases import WORKFLOWS, WORKFLOW_VARIANTS


def guest_test_failure(stderr):
    """Recognize runtime test panics, excluding compiler and resource failures."""
    prefix='rust-interp-vm: guest trap: '
    for line in stderr.splitlines():
        if not line.startswith(prefix):continue
        message=line.removeprefix(prefix)
        if 'assertion' in message or 'panicking::' in message:return True
        # These compiler-known panic helpers also implement failed unwrap/expect.
        for crate in ['core','std']:
            for helper in ['option::unwrap_failed','option::expect_failed','result::unwrap_failed']:
                if message.startswith(crate+'::'+helper+' '):return True
    return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',default='e2e-workflow-'+str(time.time_ns()))
    parser.add_argument('--project',choices=[*WORKFLOWS,'rg-aot'],default='fre')
    parser.add_argument('--workflow',default='default',help='additional named workload within a project')
    parser.add_argument('--batch',action='store_true',help='invoke all custom test entries in one command')
    parser.add_argument('--cargo-timings',action='store_true',help='collect Cargo unit timing reports in every mode; report generation remains timed')
    parser.add_argument('--vary-selection',action='store_true',help='change the selected tests to match each production edit')
    parser.add_argument('--std-mir',action='store_true',help='use the reusable metadata-only standard library for custom engines')
    parser.add_argument('--build-tool-opt-level',type=int,choices=range(4),help='optimize host build tools equally for all engines')
    parser.add_argument('--instruction-limit',type=int,default=1000000000,help='explicit per-command guest instruction budget')
    parser.add_argument('--guest-mir-opt-level',type=int,choices=range(4),help='explicit MIR optimization for custom-engine Cargo commands; native retains its Cargo profile')
    parser.add_argument('--baseline-guest-mir-opt-level',type=int,choices=range(4),help='replace baseline guest MIR flags with this level and no inlining-threshold overrides; requires --baseline-tool-key')
    parser.add_argument('--guest-mir-inline-scale',type=int,choices=[1,2,4,8],help='scale the pinned MIR inlining cost limits; requires --guest-mir-opt-level=3')
    parser.add_argument('--inline-leaves',action='store_true',help='inline bytecode leaves for custom engines, or only the candidate in a paired comparison')
    parser.add_argument('--baseline-inline-leaves',action='store_true',help='also inline leaves with the installed baseline, to isolate a runtime change')
    parser.add_argument('--trap-unsupported-calls',action='store_true',help='explicit unavailable foreign/catch_unwind stops in every custom engine; strict frontend checking remains enabled')
    parser.add_argument('--run-try-callbacks',action='store_true',help='execute normal-return try callbacks; actual unwinding fails; requires --trap-unsupported-calls')
    parser.add_argument('--baseline-tool-key',help='compare an installed baseline with the candidate build on every edit, alongside native')
    parser.add_argument('--candidate-tool-key',help='use a retained candidate in a paired comparison; defaults to the current build')
    parser.add_argument('--comparison-engine',choices=['interpreter','jit'],help='engine for both tool builds; defaults to jit when comparing')
    parser.add_argument('--expect-identical-bytecode',action='store_true',help='require matching executed bytecode when isolating a runtime change')
    args=parser.parse_args()
    if args.run_try_callbacks and not args.trap_unsupported_calls:
        parser.error('--run-try-callbacks requires --trap-unsupported-calls')
    if args.candidate_tool_key is not None and args.baseline_tool_key is None:
        parser.error('--candidate-tool-key requires --baseline-tool-key')
    if (args.comparison_engine is not None or args.expect_identical_bytecode) and args.baseline_tool_key is None:
        parser.error('--comparison-engine and --expect-identical-bytecode require --baseline-tool-key')
    if args.baseline_inline_leaves and args.baseline_tool_key is None:parser.error('--baseline-inline-leaves requires --baseline-tool-key')
    if args.baseline_guest_mir_opt_level is not None and args.baseline_tool_key is None:parser.error('--baseline-guest-mir-opt-level requires --baseline-tool-key')
    if args.expect_identical_bytecode and args.inline_leaves!=args.baseline_inline_leaves:parser.error('identical bytecode requires matching leaf-inlining options')
    if args.guest_mir_inline_scale is not None and args.guest_mir_opt_level!=3:
        parser.error('--guest-mir-inline-scale requires --guest-mir-opt-level=3')
    guest_flags=[]
    if args.guest_mir_opt_level is not None:guest_flags.append(f'-Zmir-opt-level={args.guest_mir_opt_level}')
    inline_thresholds=None
    if args.guest_mir_inline_scale is not None:
        inline_thresholds={name:value*args.guest_mir_inline_scale for name,value in [('inline-mir-threshold',50),('inline-mir-hint-threshold',100),('inline-mir-forwarder-threshold',30)]}
        guest_flags += [f'-Z{name}={value}' for name,value in inline_thresholds.items()]
    baseline_guest_flags=list(guest_flags) if args.baseline_guest_mir_opt_level is None else [f'-Zmir-opt-level={args.baseline_guest_mir_opt_level}']
    if not 1<=args.instruction_limit<2**64:parser.error('instruction limit must fit a positive u64')
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('--run-id must be a directory name')
    revision=json.loads((ROOT/'benchmarks/corpus.json').read_text())['projects'][args.project]['revision']
    if args.workflow!='default':
        if (args.project,args.workflow) not in WORKFLOW_VARIANTS:
            parser.error('unknown project/workflow combination')
        case=WORKFLOW_VARIANTS[args.project,args.workflow]
    elif args.project=='rg-aot':
        adapter=json.loads((ROOT/'.work/private/workflow-rg-aot.json').read_text())
        if adapter['owner']!=str(ROOT) or adapter['revision']!=revision:
            raise RuntimeError('private workflow ownership or revision mismatch')
        case=adapter['case']
    else:
        case=WORKFLOWS[args.project]
    private=case.get('private',False)
    tests=case['tests'];edits=case['edits'];package=case['package']
    lock=(ROOT/'.work/benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    tools,key=installed_tools(args.candidate_tool_key) if args.candidate_tool_key is not None else checked_tools()
    modes=['native','interpreter','jit']
    mode_tools={mode:dict(engine=mode,tool_key=key,directory=tools) for mode in modes[1:]}
    if args.baseline_tool_key is not None:
        baseline,baseline_key=installed_tools(args.baseline_tool_key)
        if baseline_key==key and baseline_guest_flags==guest_flags and args.baseline_inline_leaves==args.inline_leaves:
            parser.error('baseline and candidate must differ in tool build, guest MIR flags, or leaf-inlining choice')
        engine=args.comparison_engine or 'jit'
        modes=['native','baseline','candidate']
        mode_tools={'baseline':dict(engine=engine,tool_key=baseline_key,directory=baseline),
                    'candidate':dict(engine=engine,tool_key=key,directory=tools)}
    for mode,config in mode_tools.items():
        config['inline_leaves']=args.baseline_inline_leaves if mode=='baseline' else args.inline_leaves
        config['guest_flags']=baseline_guest_flags if mode=='baseline' else guest_flags
    if args.trap_unsupported_calls:
        for config in mode_tools.values():require_export_option(config['directory'],config['tool_key'],'trap-unsupported-calls')
    if args.run_try_callbacks:
        for config in mode_tools.values():require_export_option(config['directory'],config['tool_key'],'run-try-callbacks')
    tool_builds={mode:dict(engine=config['engine'],tool_key=config['tool_key'],inline_leaves=config['inline_leaves'],
                 trap_unsupported_calls=args.trap_unsupported_calls,run_try_callbacks=args.run_try_callbacks,guest_rustflags=config['guest_flags'],
                 vm_sha256=hashlib.sha256((config['directory']/'rust-interp-vm').read_bytes()).hexdigest(),
                 exporter_sha256=hashlib.sha256((config['directory']/'rust-interp-mir-export').read_bytes()).hexdigest())
                 for mode,config in mode_tools.items()}
    comparison_orders=list(itertools.permutations(modes))
    # Cover all six orders while alternating which custom build runs first.
    # A five-edit workflow uses the first five; retain the exact order below.
    comparison_orders=[comparison_orders[i] for i in [0,1,2,4,3,5]]
    std=None
    if args.std_mir:
        from std_mir import checked_std_mir
        std=checked_std_mir(TOOLCHAIN) # Shared setup is recorded separately.
    source=ROOT/'.work/sources'/args.project
    marker=json.loads((source/'.rust-interp-owned.json').read_text())
    if marker['owner']!=str(ROOT) or marker['revision']!=revision:
        raise RuntimeError('snapshot ownership or revision mismatch')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()!=revision:
        raise RuntimeError('snapshot HEAD mismatch')
    if subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip():
        raise RuntimeError('snapshot has tracked changes')
    work=ROOT/'.work/runs'/args.run_id
    work.mkdir(parents=True)
    script_paths=[Path(__file__).resolve(),ROOT/'scripts/interpreter.py',ROOT/'scripts/workflow_cases.py',ROOT/'scripts/std_mir.py']
    frozen_scripts={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in script_paths}
    file=source/case['file']
    original=file.read_bytes();current=original
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
    records=[];orders=[]
    def invoke(mode,state,label,success):
        assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in frozen_scripts.items()),'benchmark scripts changed during the run'
        manifest=str(source/'Cargo.toml')
        selected=tests
        if args.vary_selection and state>0:
            selected=[tests[i] for i in case['selections'][state-1]]
        if mode=='native':
            commands=[['cargo','+'+TOOLCHAIN,'test','--manifest-path',manifest,
                       '--package',package,'--lib','--locked','--offline','--jobs','4',
                       '--target-dir',str(work/'native'),*(['--timings'] if args.cargo_timings else []),'--','--exact','--test-threads=1',*selected]]
        else:
            config=mode_tools[mode]
            base=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',manifest,
                  '--package',package,'--test-body','--engine',config['engine'],'--instruction-limit',str(args.instruction_limit),
                  '--cache-namespace',args.run_id+':'+mode]
            if args.baseline_tool_key is not None:base+=['--tool-key',config['tool_key']]
            if config['inline_leaves']:base+=['--inline-leaves']
            if args.trap_unsupported_calls:base+=['--trap-unsupported-calls']
            if args.run_try_callbacks:base+=['--run-try-callbacks']
            if std:base+=['--std-mir']
            if args.cargo_timings:base+=['--timings']
            commands=[[*base,*[arg for test in selected for arg in ['--entry',test]]]] if args.batch else [[*base,'--entry',test] for test in selected]
        start=time.perf_counter();calls=[]
        child_env=env.copy()
        if mode!='native' and config['guest_flags']:
            child_env['RUSTFLAGS']=' '.join(config['guest_flags'])
        for command in commands:
            child_start=time.perf_counter()
            p=subprocess.Popen(command,cwd=source,env=child_env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            active=dict(pid=p.pid,parent_pid=os.getpid(),command=command,cwd=str(source),
                        mode=mode,state=state,label=label,rustflags=child_env.get('RUSTFLAGS'),started_at=time.time(),status='running')
            (work/'active-command.json').write_text(json.dumps(active,indent=2)+'\n')
            stdout,stderr=p.communicate()
            active.update(status='finished',returncode=p.returncode)
            (work/'active-command.json').write_text(json.dumps(active,indent=2)+'\n')
            calls.append(dict(pid=p.pid,command=command,rustflags=child_env.get('RUSTFLAGS'),seconds=time.perf_counter()-child_start,
                              returncode=p.returncode,stdout=stdout,stderr=stderr))
            if p.returncode:break
        elapsed=time.perf_counter()-start
        snapshots=[]
        record=dict(mode=mode,state=state,label=label,tests=selected,seconds=elapsed,
                    source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                    calls=calls,load=os.getloadavg())
        if args.baseline_tool_key is not None or args.trap_unsupported_calls:
            record.update(engine=None if mode=='native' else mode_tools[mode]['engine'],
                          tool_key=None if mode=='native' else mode_tools[mode]['tool_key'],artifacts=snapshots)
        records.append(record)
        # Preserve command evidence even if provenance validation or copying
        # below fails. Source restoration still runs in the outer finally.
        (work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
        if (args.baseline_tool_key is not None or args.trap_unsupported_calls) and mode!='native':
            # Snapshot the sidecar actually selected and executed by the
            # launcher. Diagnostic copying is outside the command timer.
            for index,call in enumerate(calls):
                launches=[json.loads(line.split('rust-interp-launch: ',1)[1]) for line in call['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
                assert len(launches)==1,'missing executed-artifact provenance'
                launch=launches[0];call['launch']=launch
                assert launch['tool_key']==config['tool_key'] and launch['engine']==config['engine']
                assert launch.get('inline_leaves',False)==config['inline_leaves']
                assert launch.get('trap_unsupported_calls',False)==args.trap_unsupported_calls
                assert launch.get('run_try_callbacks',False)==args.run_try_callbacks
                artifact=Path(launch['artifact_path']).resolve()
                assert artifact.is_relative_to(ROOT/'.work/interpreter-workspaces'/config['tool_key'])
                assert 0<launch['artifact_bytes']<=64*1024*1024
                payload=artifact.read_bytes()
                assert len(payload)==launch['artifact_bytes'] and hashlib.sha256(payload).hexdigest()==launch['artifact_sha256']
                snapshot=work/'artifacts'/mode/f'{state}-{index}.rbc';snapshot.parent.mkdir(parents=True,exist_ok=True)
                with snapshot.open('xb') as destination:destination.write(payload)
                snapshots.append(dict(path=str(snapshot.relative_to(ROOT)),sha256=launch['artifact_sha256'],bytes=len(payload)))
        if args.cargo_timings:
            reports=[];record['cargo_timings']=reports
            for index,call in enumerate(calls):
                if mode=='native':
                    target=work/'native'
                else:
                    launches=[json.loads(line.split('rust-interp-launch: ',1)[1]) for line in call['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
                    assert len(launches)==1,'missing launcher timing provenance'
                    artifact=Path(launches[0]['artifact_path']).resolve()
                    scope=ROOT/'.work/interpreter-workspaces'/config['tool_key']
                    targets=[p for p in artifact.parents if p.name=='target' and p.is_relative_to(scope)]
                    assert len(targets)==1,'unexpected Cargo target directory'
                    target=targets[0]
                timing_root=(target/'cargo-timings').resolve()
                report=(timing_root/'cargo-timing.html').resolve(strict=True)
                assert report.parent==timing_root and report.name.startswith('cargo-timing')
                assert report.is_file() and report.stat().st_size<=64*1024*1024
                payload=report.read_bytes()
                snapshot=work/'cargo-timings'/mode/f'{state}-{index}.html';snapshot.parent.mkdir(parents=True,exist_ok=True)
                with snapshot.open('xb') as destination:destination.write(payload)
                reports.append(dict(path=str(snapshot.relative_to(ROOT)),sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload)))
        (work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
        if success:
            assert all(c['returncode']==0 for c in calls),calls[-1]['stderr']
            assert len(calls)==len(commands)
            if mode=='native':assert f'{len(selected)} passed' in calls[0]['stdout'],calls[0]['stdout']
            else:assert all(c['stdout'].strip()=='0' for c in calls),calls
        else:
            assert calls[-1]['returncode']!=0,calls
            text=calls[-1]['stdout']+calls[-1]['stderr']
            if mode=='native':
                # assert!(condition, "custom message") need not print the
                # word "assertion". Require libtest's selected-body failure,
                # so compiler errors cannot satisfy the negative control.
                assert 'test result: FAILED.' in calls[-1]['stdout'],text
                assert any(f'test {test} ... FAILED' in calls[-1]['stdout'] for test in selected),text
            else:
                assert guest_test_failure(calls[-1]['stderr']),text
        assert any(('Compiling ' if mode=='native' else 'Checking ')+package in c['stderr'] for c in calls),'edited crate did not compile'
        print(mode,state,label,round(record['seconds'],3),flush=True)
    try:
        # Different modes each have their own caches. A cold successful original
        # build is followed by a wrong production edit, then cumulative body
        # refactors. Test code is byte-for-byte unchanged throughout.
        for state in [0,-1,*range(1,len(edits)+1)]:
            candidate=original.decode()
            label='cold-original'
            if state==-1:
                label,old,new=case['negative']
                assert candidate.count(old)==1
                candidate=candidate.replace(old,new)
            elif state>0:
                for label,old,new in edits[:state]:
                    assert candidate.count(old)==1,(label,candidate.count(old))
                    candidate=candidate.replace(old,new)
            assert candidate.split(test_marker)[1]==original_tests,'test source changed'
            order=(modes if state%2==0 else list(reversed(modes)))
            if args.baseline_tool_key is not None and state>0:order=comparison_orders[(state-1)%len(comparison_orders)]
            orders.append(dict(state=state,modes=list(order)))
            for mode in order:
                if file.read_bytes()!=current:raise RuntimeError('source changed outside this benchmark')
                current=candidate.encode();file.write_bytes(current)
                invoke(mode,state,label,state!=-1)
            if args.baseline_tool_key is not None:
                paired=[next(r for r in records if r['mode']==mode and r['state']==state) for mode in ['baseline','candidate']]
                assert paired[0]['source_sha256']==paired[1]['source_sha256']
                same=[a['sha256'] for a in paired[0]['artifacts']]==[a['sha256'] for a in paired[1]['artifacts']]
                if args.expect_identical_bytecode:assert same,'baseline and candidate exported different bytecode; cannot isolate the runtime change'
            elif args.trap_unsupported_calls:
                custom=[next(r for r in records if r['mode']==mode and r['state']==state) for mode in ['interpreter','jit']]
                assert custom[0]['source_sha256']==custom[1]['source_sha256']
                assert [a['sha256'] for a in custom[0]['artifacts']]==[a['sha256'] for a in custom[1]['artifacts']],'custom engines exported different artifacts'
    finally:
        if file.read_bytes()!=current:raise RuntimeError('source changed outside this benchmark; refusing to overwrite it')
        file.write_bytes(original)
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in frozen_scripts.items()),'benchmark scripts changed during the run'
    med={m:statistics.median(r['seconds'] for r in records if r['mode']==m and r['state']>0) for m in modes}
    result=dict(project=args.project,workflow=args.workflow,revision=revision,
                tests=f'{len(tests)} existing private test bodies' if private else tests,
                edits=[e[0] for e in edits],
                workload=case['workload'],case_sha256=hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest(),
                test_source_unchanged=True,batch=args.batch,cargo_timings=args.cargo_timings,vary_selection=args.vary_selection,raw=str(work.relative_to(ROOT)),
                build_tool_opt_level=args.build_tool_opt_level,
                instruction_limit=args.instruction_limit,
                inline_leaves=args.inline_leaves,baseline_inline_leaves=args.baseline_inline_leaves,
                trap_unsupported_calls=args.trap_unsupported_calls,run_try_callbacks=args.run_try_callbacks,
                guest_mir_opt_level=args.guest_mir_opt_level,
                baseline_guest_mir_opt_level=args.baseline_guest_mir_opt_level,baseline_guest_rustflags=baseline_guest_flags,
                guest_mir_inline_scale=args.guest_mir_inline_scale,
                guest_mir_inline_thresholds=inline_thresholds,guest_rustflags=guest_flags,
                tool_key=key,candidate_tool_key_requested=args.candidate_tool_key,wrong_production_edit_rejected=True,median_seconds=med,
                std_mir=None if std is None else dict(key=std[2],setup_seconds=std[3]['setup_seconds'],build_seconds=std[3]['build_seconds'],metadata_bytes=std[3]['metadata_bytes']),
                cold_success_seconds={r['mode']:r['seconds'] for r in records if r['state']==0},
                scripts_sha256=frozen_scripts,tool_builds=tool_builds,mode_orders=orders,
                vm_sha256=hashlib.sha256((tools/'rust-interp-vm').read_bytes()).hexdigest(),
                exporter_sha256=hashlib.sha256((tools/'rust-interp-mir-export').read_bytes()).hexdigest(),
                samples=[{k:v for k,v in r.items() if k!='calls' and not (private and k=='tests')} for r in records])
    if args.baseline_tool_key is not None:
        pairs=[]
        for state in range(1,len(edits)+1):
            before=next(r for r in records if r['mode']=='baseline' and r['state']==state)
            after=next(r for r in records if r['mode']=='candidate' and r['state']==state)
            stages={name:{stage:sum(call['launch'][stage] for call in row['calls']) for stage in ['cargo_seconds','execution_seconds','artifact_hash_seconds','launcher_seconds']} for name,row in [('baseline',before),('candidate',after)]}
            pairs.append(dict(state=state,source_sha256=before['source_sha256'],baseline_seconds=before['seconds'],candidate_seconds=after['seconds'],
                              difference_seconds=after['seconds']-before['seconds'],stage_seconds=stages,
                              identical_bytecode=[a['sha256'] for a in before['artifacts']]==[a['sha256'] for a in after['artifacts']]))
        result['comparison']=dict(engine=args.comparison_engine or 'jit',baseline_tool_key=args.baseline_tool_key,candidate_tool_key=key,
                                  identical_bytecode_required=args.expect_identical_bytecode,pairs=pairs,
                                  candidate_pair_wins=sum(p['difference_seconds']<0 for p in pairs),
                                  median_paired_difference_seconds=statistics.median(p['difference_seconds'] for p in pairs))
    out=ROOT/'results'/args.run_id;out.mkdir()
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    report=f'# Production edits and existing {args.project} tests\n\n{case["workload"]}.\n\n'
    report+=f'{len(edits)} cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. '
    report+=('Custom engines use one command.\n\n' if args.batch else 'Custom engines use a serial launcher command per test.\n\n')
    if args.cargo_timings:
        report+='Every mode enables Cargo unit timing reports. Report generation is included in the command time; snapshot copying follows the timer. Snapshot paths and hashes are recorded with each sample.\n\n'
    if args.baseline_tool_key is not None:
        comparison=result['comparison']
        report+=f"Baseline and candidate use `{comparison['engine']}` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.\n\n"
        equality_note = ('Bytecode equality is required and verified.' if args.expect_identical_bytecode else
                         f"Bytecode is identical in {sum(pair['identical_bytecode'] for pair in comparison['pairs'])}/{len(edits)} pairs; both artifacts are retained for every pair.")
        report+=f"The candidate wins {comparison['candidate_pair_wins']}/{len(edits)} complete-command pairs. The median paired candidate-minus-baseline difference is {comparison['median_paired_difference_seconds']:+.3f} s. {equality_note} Per-edit Cargo and execution stages are retained in JSON.\n\n"
    if args.trap_unsupported_calls:
        report+='Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.\n\n'
    if args.build_tool_opt_level is not None:
        report+=f'Host build scripts, procedural macros, and their build dependencies use optimization level {args.build_tool_opt_level} in every mode. Their first compilation is included in cold command times.\n\n'
    if args.baseline_guest_mir_opt_level is not None:
        report+=f"Baseline custom commands use `RUSTFLAGS={' '.join(baseline_guest_flags)}`; candidate commands use `RUSTFLAGS={' '.join(guest_flags)}`. Native retains its Cargo profile. Both configurations preserve strict checking. Exact per-mode flags and all resulting artifacts are retained.\n\n"
    elif guest_flags:
        flags=' '.join(guest_flags)
        report+=f'Custom-engine Cargo commands explicitly set `RUSTFLAGS={flags}`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.\n\n'
    if args.vary_selection:
        report+='Test selection changes with each production edit. Each mode runs the same selection at each state; the exact selections are recorded in summary.json.\n\n'
    report+='| Mode | Median edited workflow seconds | Cold workflow seconds |\n|---|---:|---:|\n'
    report+=''.join(f'| {m} | {v:.3f} | {result["cold_success_seconds"][m]:.3f} |\n' for m,v in med.items())
    report+='\nCold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.\n'
    if std:report+=f'\nCustom engines use the shared metadata-only standard library. Its original installation took {std[3]["setup_seconds"]:.3f} s, including {std[3]["build_seconds"]:.3f} s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.\n'
    (out/'summary.md').write_text(report)
    print(out/'summary.md')


if __name__=='__main__':main()
