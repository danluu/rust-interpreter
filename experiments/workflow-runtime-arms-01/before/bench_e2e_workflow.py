#!/usr/bin/env python3
"""Edit production code, then execute existing project tests."""
import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools, installed_tools, require_export_option


from workflow_cases import WORKFLOWS, WORKFLOW_VARIANTS
from workflow_measurements import child_usage, child_cpu_since, initial_modes, mode_order, per_edit_spread, sample_path, source_states
from workflow_controls import (native_command, native_environment, native_toolchain, inspect_native_toolchain,
                               revalidate_native_toolchain, native_identity_environment, exporter_seconds)
from workflow_io import SourceEdit, capture, require_space, write_json
from workflow_case_file import load as load_case_file, source_file
from workflow_projects import WORKFLOW_ONLY_PROJECTS, project_revision
from workflow_jobs import UniqueJobCount, resolve_build_jobs
from compare_saved_runtime import acquire_lock, lock_wait_seconds
from suite_reports import guest_test_failure, read_report, validate_report
import workflow_compiler


def build_metrics(launch):
    """Validate the measured pre-VM boundary; never infer it by subtraction."""
    def number(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('build timing must be finite and nonnegative')
        return value

    def cpu(value):
        fields = {key: number(value[key]) for key in ['user_seconds', 'system_seconds', 'total_seconds']}
        if not math.isclose(fields['total_seconds'], fields['user_seconds'] + fields['system_seconds'], rel_tol=1e-9, abs_tol=1e-8):
            raise ValueError('build CPU total differs from user plus system')
        return fields

    try:
        wall = number(launch['build_to_ready_seconds'])
        build_cpu = cpu(launch['build_to_ready_cpu'])
        own = cpu(launch['build_to_ready_cpu']['self'])
        children = cpu(launch['build_to_ready_cpu']['children'])
        cargo = cpu(launch['cargo_cpu'])
        for key in build_cpu:
            if not math.isclose(build_cpu[key], own[key] + children[key], rel_tol=1e-9, abs_tol=1e-8):
                raise ValueError('build CPU total differs from self plus children')
            if cargo[key] > children[key] + 1e-8:
                raise ValueError('Cargo CPU exceeds pre-VM child CPU')
        if wall <= 0 or build_cpu['total_seconds'] <= 0:
            raise ValueError('build-to-ready measurement must be positive')
        if wall > number(launch['launcher_seconds']) or number(launch['cargo_seconds']) > wall:
            raise ValueError('build-to-ready wall is outside its launcher/Cargo bounds')
        if wall + number(launch['execution_seconds']) > launch['launcher_seconds'] + 1e-8:
            raise ValueError('build-to-ready and execution stages overlap')
        return dict(build_to_ready_seconds=wall, build_to_ready_cpu_seconds=build_cpu['total_seconds'],
                    cargo_cpu_seconds=cargo['total_seconds'])
    except (KeyError, TypeError) as error:
        raise ValueError('missing or malformed build-to-ready timing') from error


def check_aa_settings(configs, jobs):
    if set(configs) != {'baseline', 'candidate'} or configs['baseline'] != configs['candidate'] or jobs['baseline'] != jobs['candidate']:
        raise ValueError('A/A control requires identical tools, guest/runtime settings, and Cargo jobs')


def cache_workspace(command, artifact, scope, namespace):
    """Bind the explicit namespace to a distinct actual Cargo workspace."""
    if command.count('--cache-namespace') != 1:
        raise ValueError('expected exactly one cache namespace')
    index = command.index('--cache-namespace')
    if index + 1 == len(command) or command[index + 1] != namespace:
        raise ValueError('cache namespace differs from its recorded mode')
    relative = Path(artifact).resolve().relative_to(scope.resolve())
    if len(relative.parts) < 3 or relative.parts[1] != 'target':
        raise ValueError('executed artifact is outside a scoped Cargo target')
    return str(scope.resolve() / relative.parts[0])


def restored_sample(cycles, modes, paired, original):
    return dict(cycle=cycles, state=-2, phase='restored-original', label='restored-original',
                source=original, modes=mode_order(modes, cycles, -2, paired))


def main():
    with ExitStack() as cleanup:
        return run_workflow(cleanup)


def run_workflow(cleanup):
    if not __debug__:
        raise RuntimeError('benchmark validation uses assertions; run Python without -O')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',default='e2e-workflow-'+str(time.time_ns()))
    parser.add_argument('--lock-wait-seconds',type=lock_wait_seconds,default=0,help='bounded wait for the shared benchmark lock; default fails immediately')
    parser.add_argument('--workload-lock',type=Path,help='explicit shared workload lock; defaults to this workspace benchmark.lock')
    parser.add_argument('--project',choices=[*WORKFLOWS,*WORKFLOW_ONLY_PROJECTS,'rg-aot'],default='fre')
    parser.add_argument('--workflow',default='default',help='additional named workload within a project')
    parser.add_argument('--case-file',type=Path,help='bounded public workflow JSON inside this workspace; mutually exclusive with a named workflow')
    parser.add_argument('--batch',action='store_true',help='invoke all custom test entries in one command')
    parser.add_argument('--compare-isolated-batches',action='store_true',help='compare fresh and prepared per-test JIT state; native builds once and runs each test in a separate process')
    parser.add_argument('--cycles',type=int,default=1,help='repeat the actual edit sequence after rebuilding an original-source anchor (1..30)')
    parser.add_argument('--initial-mode-order',type=lambda value:value.split(','),help='comma-separated permutation of the three modes; rotates cold-run order without changing mode settings')
    parser.add_argument('--minimum-free-gib',type=int,default=8,help='refuse to start a command below this free-space threshold; not a disk reservation')
    parser.add_argument('--jobs',type=int,action=UniqueJobCount,default=4,help='default Cargo jobs for custom engines and native (1..256)')
    parser.add_argument('--native-jobs',type=int,action=UniqueJobCount,help='override native/check Cargo jobs (1..256)')
    parser.add_argument('--baseline-jobs',type=int,action=UniqueJobCount,help='override baseline Cargo jobs in a paired comparison (1..256)')
    parser.add_argument('--candidate-jobs',type=int,action=UniqueJobCount,help='override candidate Cargo jobs in a paired comparison (1..256)')
    parser.add_argument('--native-profile',choices=['repository','o0-incremental'],default='repository',help='explicit native/check profile override; no fastest-native claim')
    parser.add_argument('--native-toolchain',type=native_toolchain,help='explicit installed native/check compiler; default keeps the existing nightly route; custom engines are unchanged')
    parser.add_argument('--native-test-threads',default='1',help='positive libtest thread count or default')
    parser.add_argument('--native-rustflag',action='append',default=[],help='one explicit native/check rustc argument; repeat, using --native-rustflag=VALUE')
    parser.add_argument('--check-floor',action='store_true',help='independently time cargo check of the library-test target after each primary mode triplet')
    parser.add_argument('--cargo-timings',action='store_true',help='collect Cargo unit timing reports in every mode; report generation remains timed')
    parser.add_argument('--vary-selection',action='store_true',help='change the selected tests to match each production edit')
    parser.add_argument('--std-mir',action='store_true',help='use the reusable metadata-only standard library for custom engines')
    parser.add_argument('--runtime-compiler-key',help='select one installed runtime compiler for both paired custom modes')
    parser.add_argument('--std-mir-key',help='select prepared shared source-containing std MIR for the explicit runtime compiler')
    parser.add_argument('--guest-rustflag',action='append',default=[],help='append one custom compiler argument; repeat using --guest-rustflag=VALUE')
    parser.add_argument('--baseline-guest-rustflag',action='append',default=None,help='replace the baseline appended arguments; requires a paired comparison')
    parser.add_argument('--build-tool-opt-level',type=int,choices=range(4),help='optimize host build tools equally for all engines')
    parser.add_argument('--instruction-limit',type=int,default=1000000000,help='explicit per-command guest instruction budget')
    parser.add_argument('--allocation-limit',type=int,help='explicit live guest allocation budget (default: VM default of 100000)')
    parser.add_argument('--guest-mir-opt-level',type=int,choices=range(4),help='explicit MIR optimization for custom-engine Cargo commands; native retains its Cargo profile')
    parser.add_argument('--baseline-guest-mir-opt-level',type=int,choices=range(4),help='replace baseline guest MIR flags with this level and no inlining-threshold overrides; requires --baseline-tool-key')
    parser.add_argument('--guest-mir-inline-scale',type=int,choices=[1,2,4,8],help='scale the pinned MIR inlining cost limits; requires --guest-mir-opt-level=3')
    parser.add_argument('--inline-leaves',action='store_true',help='inline bytecode leaves for custom engines, or only the candidate in a paired comparison')
    parser.add_argument('--baseline-inline-leaves',action='store_true',help='also inline leaves with the installed baseline, to isolate a runtime change')
    parser.add_argument('--trap-unsupported-calls',action='store_true',help='explicit unavailable foreign/catch_unwind stops in every custom engine; strict frontend checking remains enabled')
    parser.add_argument('--run-try-callbacks',action='store_true',help='execute normal-return try callbacks; actual unwinding fails; requires --trap-unsupported-calls')
    parser.add_argument('--baseline-tool-key',help='compare an installed baseline with the candidate build on every edit, alongside native')
    parser.add_argument('--candidate-tool-key',help='use a retained candidate in a paired comparison; defaults to the current build')
    parser.add_argument('--aa-control',action='store_true',help='require identical paired tools/settings in two isolated caches')
    parser.add_argument('--build-metrics',action='store_true',help='require measured build-to-ready wall and CPU for batched paired comparisons')
    parser.add_argument('--verify-restoration',action='store_true',help='build and execute the restored original after the source-edit context exits')
    parser.add_argument('--candidate-jit-native-call-stubs',action='store_true',help='also link candidate Calls into ordinary regions; requires --candidate-jit-native-calls')
    parser.add_argument('--candidate-jit-resumable-calls',action='store_true',help='enable resumable Calls in the paired JIT candidate')
    parser.add_argument('--candidate-jit-persistent-registers',action='store_true',help='enable persistent native registers in the paired JIT candidate')
    parser.add_argument('--baseline-jit-resumable-calls',action='store_true',help='enable resumable Calls in the paired JIT baseline')
    parser.add_argument('--baseline-jit-persistent-registers',action='store_true',help='enable persistent native registers in the paired JIT baseline')
    parser.add_argument('--candidate-jit-native-calls',action='store_true',help='enable experimental native call trees in the paired candidate only')
    parser.add_argument('--comparison-engine',choices=['interpreter','jit'],help='engine for both tool builds; defaults to jit when comparing')
    parser.add_argument('--expect-identical-bytecode',action='store_true',help='require matching executed bytecode when isolating a runtime change')
    args=parser.parse_args()
    try:
        compiler_arguments=workflow_compiler.arguments(args.runtime_compiler_key,args.std_mir_key)
        workflow_compiler.rustflags(args.guest_rustflag)
        if args.baseline_guest_rustflag is not None:workflow_compiler.rustflags(args.baseline_guest_rustflag)
    except RuntimeError as error:parser.error(str(error))
    if args.runtime_compiler_key is not None:
        if args.baseline_tool_key is None or args.candidate_tool_key is None or not args.batch:
            parser.error('--runtime-compiler-key requires a batched comparison with explicit baseline and candidate tools')
        if args.std_mir != (args.std_mir_key is not None):
            parser.error('--runtime-compiler-key with --std-mir requires an explicit prepared shared --std-mir-key')
        if args.build_tool_opt_level is not None:
            parser.error('--runtime-compiler-key currently requires repository host build profiles')
    if args.baseline_guest_rustflag is not None and args.baseline_tool_key is None:
        parser.error('--baseline-guest-rustflag requires --baseline-tool-key')
    encoded_guest_flags=bool(args.guest_rustflag or args.baseline_guest_rustflag is not None)
    native_selection=args.native_toolchain or TOOLCHAIN
    try:
        scheduled_modes=initial_modes(['native','baseline','candidate'] if args.baseline_tool_key is not None else ['native','interpreter','jit'],args.initial_mode_order)
        resolved_jobs=resolve_build_jobs(args.jobs,native=args.native_jobs,baseline=args.baseline_jobs,
            candidate=args.candidate_jobs,paired=args.baseline_tool_key is not None)
    except ValueError as error:parser.error(str(error))
    if args.candidate_jit_native_call_stubs and not args.candidate_jit_native_calls:parser.error('--candidate-jit-native-call-stubs requires --candidate-jit-native-calls')
    if args.candidate_jit_persistent_registers and (args.baseline_tool_key is None or args.comparison_engine=='interpreter'):parser.error('--candidate-jit-persistent-registers requires a paired JIT comparison')
    if args.candidate_jit_resumable_calls and (args.baseline_tool_key is None or args.comparison_engine=='interpreter'):parser.error('--candidate-jit-resumable-calls requires a paired JIT comparison')
    if args.candidate_jit_resumable_calls and (args.candidate_jit_native_calls or args.candidate_jit_native_call_stubs):parser.error('--candidate-jit-resumable-calls cannot be combined with native tree/stub calls')
    if args.candidate_jit_native_calls and (args.baseline_tool_key is None or args.comparison_engine=='interpreter'):parser.error('--candidate-jit-native-calls requires a paired JIT comparison')
    for option in ['baseline_jit_resumable_calls','baseline_jit_persistent_registers']:
        if getattr(args,option) and (args.baseline_tool_key is None or args.comparison_engine=='interpreter'):
            parser.error('--'+option.replace('_','-')+' requires a paired JIT comparison')
    if not 1<=args.cycles<=30:parser.error('cycles must be in 1..30')
    if not 1<=args.minimum_free_gib<=1024:parser.error('minimum-free-gib must be in 1..1024')
    if not 1<=args.jobs<=256 or (args.native_jobs is not None and not 1<=args.native_jobs<=256):parser.error('jobs must be in 1..256')
    if args.native_test_threads!='default' and (not args.native_test_threads.isdigit() or not 1<=int(args.native_test_threads)<=256):parser.error('native-test-threads must be default or in 1..256')
    if any(not flag or '\x1f' in flag or '\x00' in flag for flag in args.native_rustflag):parser.error('native rustflags must be nonempty arguments without NUL or unit separators')
    native_jobs=resolved_jobs['native']
    if args.run_try_callbacks and not args.trap_unsupported_calls:
        parser.error('--run-try-callbacks requires --trap-unsupported-calls')
    if args.candidate_tool_key is not None and args.baseline_tool_key is None:
        parser.error('--candidate-tool-key requires --baseline-tool-key')
    if args.aa_control and (args.baseline_tool_key is None or not args.batch):parser.error('--aa-control requires --baseline-tool-key and --batch')
    if args.build_metrics and (args.baseline_tool_key is None or not args.batch):parser.error('--build-metrics requires --baseline-tool-key and --batch')
    if args.verify_restoration and (args.baseline_tool_key is None or not args.batch):parser.error('--verify-restoration requires --baseline-tool-key and --batch')
    if args.aa_control and args.compare_isolated_batches:parser.error('A/A control cannot compare different isolated-batch settings')
    if args.compare_isolated_batches:
        if (not args.batch or args.baseline_tool_key is None or args.comparison_engine=='interpreter'
                or not args.baseline_jit_resumable_calls or not args.candidate_jit_resumable_calls
                or args.candidate_jit_native_calls or args.candidate_jit_native_call_stubs
                or args.native_test_threads!='1' or args.vary_selection):
            parser.error('--compare-isolated-batches requires a fixed batched paired resumable JIT selection and one native test thread')
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
    baseline_guest_flags+=args.guest_rustflag if args.baseline_guest_rustflag is None else args.baseline_guest_rustflag
    guest_flags+=args.guest_rustflag
    if not 1<=args.instruction_limit<2**64:parser.error('instruction limit must fit a positive u64')
    if args.allocation_limit is not None and not 0<=args.allocation_limit<=1000000:
        parser.error('allocation limit must be in 0..1000000')
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('--run-id must be a directory name')
    if args.project in WORKFLOW_ONLY_PROJECTS and args.case_file is None:
        parser.error('this development project requires --case-file')
    revision=project_revision(ROOT,args.project)
    case_proof=None
    workflow_label=args.workflow
    if args.case_file is not None:
        if args.workflow!='default' or args.project=='rg-aot':
            parser.error('--case-file requires a public project and the default workflow selector')
        case_path=args.case_file.resolve(strict=True)
        if not case_path.is_relative_to(ROOT):parser.error('--case-file must be inside this workspace')
        case,case_proof=load_case_file(case_path,args.project,revision)
        workflow_label=case_proof['label']
    elif args.workflow!='default':
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
    if args.compare_isolated_batches and len(tests)<2:parser.error('isolated batch comparison requires at least two tests')
    workload_lock=ROOT/'.work/benchmark.lock' if args.workload_lock is None else args.workload_lock.resolve(strict=True)
    lock=cleanup.enter_context(workload_lock.open('a'))
    if args.lock_wait_seconds:
        acquire_lock(lock,args.lock_wait_seconds)
    else:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    work=ROOT/'.work/runs'/args.run_id
    work.mkdir(parents=True)
    native_identity=None
    native_identity_calls=[]
    native_identity_path=work/'native-toolchain.json'
    identity_base=os.environ.copy()
    identity_env=native_identity_environment(identity_base)
    identity_record=dict(toolchain=args.native_toolchain,calls=native_identity_calls,identity=None,final_identity=None)
    def identity_command(command):
        receipt_path=work/f'native-identity-{len(native_identity_calls)}.json'
        child,stdout,stderr=capture(command,cwd=ROOT,env=identity_env,receipt_path=receipt_path,
            receipt=dict(mode='native-toolchain-identity',stage='setup' if native_identity is None else 'final',environment=identity_env))
        row=dict(command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr,
            stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(stderr.encode()).hexdigest(),
            receipt_path=str(receipt_path.relative_to(ROOT)),receipt=json.loads(receipt_path.read_bytes()),
            receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest())
        native_identity_calls.append(row)
        write_json(native_identity_path,identity_record)
        return row
    if args.native_toolchain is not None:
        native_identity=inspect_native_toolchain(args.native_toolchain,identity_command,
            environment=identity_base,source=ROOT/'.work/sources'/args.project)
        identity_record['identity']=native_identity
        write_json(native_identity_path,identity_record)
    tools,key=installed_tools(args.candidate_tool_key) if args.candidate_tool_key is not None else checked_tools()
    modes=['native','interpreter','jit']
    mode_tools={mode:dict(engine=mode,tool_key=key,directory=tools) for mode in modes[1:]}
    if args.baseline_tool_key is not None:
        baseline,baseline_key=installed_tools(args.baseline_tool_key)
        if (not args.aa_control and baseline_key==key and baseline_guest_flags==guest_flags and
            args.baseline_inline_leaves==args.inline_leaves and
            not args.compare_isolated_batches and
            resolved_jobs['baseline']==resolved_jobs['candidate'] and
            not args.candidate_jit_native_calls and
            args.candidate_jit_persistent_registers==args.baseline_jit_persistent_registers and
            args.candidate_jit_resumable_calls==args.baseline_jit_resumable_calls):
            parser.error('baseline and candidate must differ in tool build, guest settings, or Cargo worker count')
        engine=args.comparison_engine or 'jit'
        modes=['native','baseline','candidate']
        mode_tools={'baseline':dict(engine=engine,tool_key=baseline_key,directory=baseline),
                    'candidate':dict(engine=engine,tool_key=key,directory=tools)}
    for mode,config in mode_tools.items():
        config['inline_leaves']=args.baseline_inline_leaves if mode=='baseline' else args.inline_leaves
        config['jit_resumable_calls']=(args.baseline_jit_resumable_calls if mode=='baseline' else args.candidate_jit_resumable_calls and mode=='candidate')
        config['jit_persistent_registers']=(args.baseline_jit_persistent_registers if mode=='baseline' else args.candidate_jit_persistent_registers and mode=='candidate')
        config['jit_native_call_stubs']=args.candidate_jit_native_call_stubs and mode=='candidate'
        config['jit_native_calls']=args.candidate_jit_native_calls and mode=='candidate'
        config['guest_flags']=baseline_guest_flags if mode=='baseline' else guest_flags
    runtime=None
    runtime_proof=None
    if args.runtime_compiler_key is not None:
        from runtime_compiler import load_runtime_compiler
        from runtime_tools import validate_tool_runtime
        runtime=load_runtime_compiler(ROOT,args.runtime_compiler_key)
        runtime.environment(os.environ)
        for config in mode_tools.values():
            validate_tool_runtime(config['directory'],config['tool_key'],runtime)
        runtime_proof=workflow_compiler.runtime_receipt(runtime)
    if args.aa_control:
        try:check_aa_settings(mode_tools,resolved_jobs)
        except ValueError as error:parser.error(str(error))
    controlled_caches=args.aa_control or args.build_metrics
    cache_namespaces={mode:args.run_id+':'+mode for mode in mode_tools}
    cache_workspaces={}
    if args.trap_unsupported_calls:
        for config in mode_tools.values():require_export_option(config['directory'],config['tool_key'],'trap-unsupported-calls')
    if args.run_try_callbacks:
        for config in mode_tools.values():require_export_option(config['directory'],config['tool_key'],'run-try-callbacks')
    tool_builds={mode:dict(engine=config['engine'],tool_key=config['tool_key'],jit_persistent_registers=config['jit_persistent_registers'],jit_resumable_calls=config['jit_resumable_calls'],inline_leaves=config['inline_leaves'],jit_native_calls=config['jit_native_calls'],jit_native_call_stubs=config['jit_native_call_stubs'],
                 trap_unsupported_calls=args.trap_unsupported_calls,run_try_callbacks=args.run_try_callbacks,guest_rustflags=config['guest_flags'],
                 vm_sha256=hashlib.sha256((config['directory']/'rust-interp-vm').read_bytes()).hexdigest(),
                 exporter_sha256=hashlib.sha256((config['directory']/'rust-interp-mir-export').read_bytes()).hexdigest())
                 for mode,config in mode_tools.items()}
    std=None
    if args.std_mir:
        from std_mir import checked_std_mir
        std_options={} if runtime is None else dict(custom=runtime,policy='source-paths-v2-shared',prepared_key=args.std_mir_key)
        std=checked_std_mir(TOOLCHAIN,**std_options) # Shared setup is recorded separately.
    std_selection=None if std is None else dict(key=std[2],sysroot=str(std[0]),target=std[1])
    source=ROOT/'.work/sources'/args.project
    marker=json.loads((source/'.rust-interp-owned.json').read_text())
    if marker['owner']!=str(ROOT) or marker['revision']!=revision:
        raise RuntimeError('snapshot ownership or revision mismatch')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()!=revision:
        raise RuntimeError('snapshot HEAD mismatch')
    if subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip():
        raise RuntimeError('snapshot has tracked changes')
    script_paths=[Path(__file__).resolve(),ROOT/'scripts/interpreter.py',ROOT/'scripts/workflow_cases.py',ROOT/'scripts/workflow_case_file.py',ROOT/'scripts/workflow_projects.py',ROOT/'scripts/workflow_measurements.py',ROOT/'scripts/workflow_controls.py',ROOT/'scripts/workflow_io.py',ROOT/'scripts/std_mir.py',ROOT/'scripts/workflow_jobs.py']
    script_paths+=[ROOT/'scripts/native_suite.py',ROOT/'scripts/suite_reports.py',ROOT/'scripts/compare_saved_runtime.py',
                  ROOT/'scripts/workspace_cache.py',ROOT/'scripts/test_discovery.py',ROOT/'scripts/workflow_compiler.py']
    if runtime is not None:
        script_paths += [ROOT/'scripts'/name for name in ['runtime_compiler.py','runtime_tools.py','custom_compiler.py','std_mir_source_paths.py']]
    if case_proof is not None:
        payload=case_path.read_bytes()
        if hashlib.sha256(payload).hexdigest()!=case_proof['sha256']:raise RuntimeError('case file changed during preparation')
        snapshot=work/'case.json'
        with snapshot.open('xb') as output:output.write(payload)
        case_proof['snapshot']=str(snapshot.relative_to(ROOT))
        script_paths += [case_path,snapshot]
    frozen_scripts={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in script_paths}
    file=source_file(source,case)
    subprocess.run(['git','ls-files','--error-unmatch','--',case['file']],cwd=source,check=True,stdout=subprocess.DEVNULL)
    original=file.read_bytes();current=original
    # Detect missing/ambiguous replacements or test mutations before commands.
    list(source_states(original.decode(),case,1,scheduled_modes,args.baseline_tool_key is not None))
    env=os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or name in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']:
            env.pop(name,None)
    env.update(CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
    if args.build_tool_opt_level is not None:
        for profile in ['DEV','TEST']:
            env[f'CARGO_PROFILE_{profile}_BUILD_OVERRIDE_OPT_LEVEL']=str(args.build_tool_opt_level)
    records=[];orders=[];transitions=[];built_sources={mode:None for mode in modes}
    check_records=[]
    def check_reference(sample):
        digest=hashlib.sha256(current).hexdigest()
        if file.read_bytes()!=current:raise RuntimeError('source changed before Cargo-check control')
        previous=check_records[-1]['source_sha256'] if check_records else None
        if sample['phase']!='cold' and previous==digest:raise RuntimeError('unchanged Cargo-check source')
        command=native_command(native_selection,source/'Cargo.toml',package,work/'check',native_jobs,
            args.native_test_threads,[],check=True,cargo=None if native_identity is None else native_identity['tools']['cargo']['resolved'])
        child_env=native_environment(env,args.native_profile,args.native_rustflag,compiler=native_identity)
        require_space(work,args.minimum_free_gib)
        before=child_usage();start=time.perf_counter()
        child,stdout,stderr=capture(command,cwd=source,env=child_env,receipt_path=work/'active-command.json',
            receipt=dict(mode='check-floor',cycle=sample['cycle'],state=sample['state'],phase=sample['phase'],
                         native_environment=None if native_identity is None else {k:child_env[k] for k in ['RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER']}))
        elapsed=time.perf_counter()-start;cpu=child_cpu_since(before)
        row=dict(cycle=sample['cycle'],state=sample['state'],phase=sample['phase'],source_sha256=digest,
            previous_source_sha256=previous,seconds=elapsed,cpu_seconds=cpu['total_seconds'],cpu=cpu,
            command=command,returncode=child.returncode,stdout=stdout,stderr=stderr,load=os.getloadavg(),
            native_environment=None if native_identity is None else {k:child_env[k] for k in ['RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER']})
        check_records.append(row);write_json(work/'check-records.json',check_records)
        if child.returncode or 'Checking '+package not in stderr:raise RuntimeError('Cargo-check control did not successfully check the edited target: '+stderr)
        if file.read_bytes()!=current:raise RuntimeError('source changed during Cargo-check control')
        print('check-floor',sample['cycle'],sample['state'],round(elapsed,3),flush=True)
    def invoke(mode,sample):
        state=sample['state'];cycle=sample['cycle'];phase=sample['phase'];label=sample['label'];success=state!=-1
        source_digest=hashlib.sha256(current).hexdigest()
        previous_source=built_sources[mode]
        if phase!='cold':
            assert previous_source is not None and previous_source!=source_digest,'sample did not change this mode’s previous source'
        assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in frozen_scripts.items()),'benchmark scripts changed during the run'
        manifest=str(source/'Cargo.toml')
        selected=tests
        if args.vary_selection and state>0:
            selected=[tests[i] for i in case['selections'][state-1]]
        suite_path=None
        if args.compare_isolated_batches:
            suite_path=work/'suites'/mode/sample_path(sample,0,args.cycles,'json')
            suite_path.parent.mkdir(parents=True,exist_ok=True)
        if mode=='native':
            commands=[native_command(native_selection,manifest,package,work/'native',native_jobs,
                args.native_test_threads,selected,timings=args.cargo_timings,
                cargo=None if native_identity is None else native_identity['tools']['cargo']['resolved'])]
            if suite_path is not None:
                commands=[[sys.executable,str(ROOT/'scripts/native_suite.py'),'--manifest-path',manifest,
                    '--package',package,'--target-dir',str(work/'native'),'--jobs',str(native_jobs),
                    *(['--native-toolchain',native_selection,'--native-cargo',native_identity['tools']['cargo']['resolved']] if native_identity else []),
                    '--test-threads=1','--suite-report',str(suite_path),
                    *(['--timings'] if args.cargo_timings else []),*[a for test in selected for a in ['--entry',test]]]]
        else:
            config=mode_tools[mode]
            base=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',manifest,
                  '--package',package,'--jobs',str(resolved_jobs[mode]),'--test-body','--engine',config['engine'],'--instruction-limit',str(args.instruction_limit),
                  '--cache-namespace',cache_namespaces[mode]]
            if args.baseline_tool_key is not None:base+=['--tool-key',config['tool_key']]
            base+=compiler_arguments
            if runtime is not None:base+=['--rustflag='+flag for flag in config['guest_flags']]
            if args.allocation_limit is not None:base+=['--allocation-limit',str(args.allocation_limit)]
            if config['inline_leaves']:base+=['--inline-leaves']
            if config['jit_resumable_calls']:base+=['--jit-resumable-calls']
            if config['jit_persistent_registers']:base+=['--jit-persistent-registers']
            if config['jit_native_calls']:base+=['--jit-native-calls']
            if config['jit_native_call_stubs']:base+=['--jit-native-call-stubs']
            if args.trap_unsupported_calls:base+=['--trap-unsupported-calls']
            if args.run_try_callbacks:base+=['--run-try-callbacks']
            if std:base+=['--std-mir']
            if args.cargo_timings:base+=['--timings']
            if suite_path is not None:
                base+=['--isolated-batch','fresh' if mode=='baseline' else 'prepared','--suite-report',str(suite_path)]
            commands=[[*base,*[arg for test in selected for arg in ['--entry',test]]]] if args.batch else [[*base,'--entry',test] for test in selected]
        start=time.perf_counter();calls=[]
        child_env=env.copy()
        if mode=='native':child_env=native_environment(env,args.native_profile,args.native_rustflag,compiler=native_identity)
        if mode!='native' and runtime is None:
            child_env=workflow_compiler.flag_environment(child_env,config['guest_flags'],encoded_guest_flags)
        for command in commands:
            require_space(work,args.minimum_free_gib)
            child_start=time.perf_counter()
            usage_before=child_usage()
            p,stdout,stderr=capture(command,cwd=source,env=child_env,receipt_path=work/'active-command.json',
                receipt=dict(mode=mode,cycle=cycle,state=state,phase=phase,label=label,
                    rustflags=child_env.get('RUSTFLAGS'),encoded_rustflags=child_env.get('CARGO_ENCODED_RUSTFLAGS'),
                    native_environment={k:child_env[k] for k in ['RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER']} if mode=='native' and native_identity else None))
            cpu=child_cpu_since(usage_before)
            calls.append(dict(pid=p.pid,command=command,rustflags=child_env.get('RUSTFLAGS'),seconds=time.perf_counter()-child_start,
                              encoded_rustflags=child_env.get('CARGO_ENCODED_RUSTFLAGS'),
                              native_environment={k:child_env[k] for k in ['RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER']} if mode=='native' and native_identity else None,
                              exporter_seconds=exporter_seconds(stderr) if mode!='native' else {},
                              cpu=cpu,returncode=p.returncode,stdout=stdout,stderr=stderr))
            if p.returncode:break
        elapsed=time.perf_counter()-start
        snapshots=[]
        record=dict(mode=mode,cycle=cycle,state=state,phase=phase,label=label,tests=selected,seconds=elapsed,
                    cpu_seconds=sum(c['cpu']['total_seconds'] for c in calls),previous_source_sha256=previous_source,
                    source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                    calls=calls,load=os.getloadavg())
        if args.baseline_tool_key is not None or args.trap_unsupported_calls or args.verify_restoration:
            record.update(engine=None if mode=='native' else mode_tools[mode]['engine'],
                          tool_key=None if mode=='native' else mode_tools[mode]['tool_key'],artifacts=snapshots)
        records.append(record)
        # Preserve command evidence even if provenance validation or copying
        # below fails. Source restoration still runs in the outer finally.
        write_json(work/'records.json',records)
        if (args.baseline_tool_key is not None or args.trap_unsupported_calls or args.verify_restoration) and mode!='native':
            # Snapshot the sidecar actually selected and executed by the
            # launcher. Diagnostic copying is outside the command timer.
            for index,call in enumerate(calls):
                launches=[json.loads(line.split('rust-interp-launch: ',1)[1]) for line in call['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
                assert len(launches)==1,'missing executed-artifact provenance'
                launch=launches[0];call['launch']=launch
                workflow_compiler.verify_flags(call,config['guest_flags'],encoded_guest_flags,runtime is not None)
                if runtime is not None:workflow_compiler.verify_runtime_call(call,runtime_proof,std_selection)
                assert launch['tool_key']==config['tool_key'] and launch['engine']==config['engine']
                assert launch.get('inline_leaves',False)==config['inline_leaves']
                assert launch.get('jit_resumable_calls',False)==config['jit_resumable_calls']
                assert launch.get('jit_persistent_registers',False)==config['jit_persistent_registers']
                assert launch.get('jit_native_calls',False)==config['jit_native_calls']
                assert launch.get('jit_native_call_stubs',False)==config['jit_native_call_stubs']
                assert launch.get('trap_unsupported_calls',False)==args.trap_unsupported_calls
                assert launch.get('run_try_callbacks',False)==args.run_try_callbacks
                if args.allocation_limit is not None:assert launch['allocation_limit']==args.allocation_limit
                artifact=Path(launch['artifact_path']).resolve()
                assert artifact.is_relative_to(ROOT/'.work/interpreter-workspaces'/config['tool_key'])
                if args.build_metrics:build_metrics(launch)
                if controlled_caches:
                    workspace=cache_workspace(call['command'],artifact,ROOT/'.work/interpreter-workspaces'/config['tool_key'],cache_namespaces[mode])
                    assert cache_workspaces.setdefault(mode,workspace)==workspace,'mode changed its Cargo workspace'
                    assert all(other==mode or path!=workspace for other,path in cache_workspaces.items()),'comparison modes shared a Cargo cache'
                assert 0<launch['artifact_bytes']<=64*1024*1024
                payload=artifact.read_bytes()
                assert len(payload)==launch['artifact_bytes'] and hashlib.sha256(payload).hexdigest()==launch['artifact_sha256']
                snapshot=work/'artifacts'/mode/sample_path(sample,index,args.cycles,'rbc');snapshot.parent.mkdir(parents=True,exist_ok=True)
                with snapshot.open('xb') as destination:destination.write(payload)
                item=dict(path=str(snapshot.relative_to(ROOT)),sha256=launch['artifact_sha256'],bytes=len(payload))
                snapshots.append(item)
                if launch.get('entry_catalog_path') is not None:
                    catalog=Path(launch['entry_catalog_path'])
                    assert catalog==Path(str(artifact)+'.entries.json') and not catalog.is_symlink()
                    assert 0<catalog.stat().st_size<=8*1024*1024
                    payload=catalog.read_bytes();digest=hashlib.sha256(payload).hexdigest()
                    assert digest==launch['entry_catalog_sha256']
                    descriptor=json.loads(payload)
                    assert descriptor['artifact_sha256']==item['sha256'] and [e['name'] for e in descriptor['entries']]==selected
                    catalog_snapshot=Path(str(snapshot)+'.entries.json')
                    with catalog_snapshot.open('xb') as destination:destination.write(payload)
                    item['entry_catalog']=dict(path=str(catalog_snapshot.relative_to(ROOT)),sha256=digest)
            if args.build_metrics:
                measured=[build_metrics(call['launch']) for call in calls]
                record.update({field:sum(row[field] for row in measured) for field in measured[0]})
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
                snapshot=work/'cargo-timings'/mode/sample_path(sample,index,args.cycles,'html');snapshot.parent.mkdir(parents=True,exist_ok=True)
                with snapshot.open('xb') as destination:destination.write(payload)
                reports.append(dict(path=str(snapshot.relative_to(ROOT)),sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload)))
        write_json(work/'records.json',records)
        if suite_path is not None:
            suite,suite_hash=read_report(suite_path)
            validate_report(suite,selected,'native' if mode=='native' else 'fresh' if mode=='baseline' else 'prepared',success)
            record['suite_report']=dict(path=str(suite_path.relative_to(ROOT)),sha256=suite_hash)
            if mode=='native':
                # Bind the built executable outside the complete-command timer,
                # just as the executed bytecode snapshots are copied outside it.
                executable=Path(suite['executable'])
                assert not executable.is_symlink() and executable.resolve().is_relative_to((work/'native').resolve())
                record['native_executable']=dict(path=str(executable),sha256=hashlib.sha256(executable.read_bytes()).hexdigest())
            else:
                assert calls[0]['launch']['suite_report_sha256']==record['suite_report']['sha256']
                assert calls[0]['launch']['suite_report_path']==str(suite_path)
            write_json(work/'records.json',records)
        if success:
            assert all(c['returncode']==0 for c in calls),calls[-1]['stderr']
            assert len(calls)==len(commands)
            if mode=='native' and suite_path is None:assert f'{len(selected)} passed' in calls[0]['stdout'],calls[0]['stdout']
            elif mode=='native':pass # The report above requires each exact original test to pass.
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
            elif suite_path is None:
                assert guest_test_failure(calls[-1]['stderr']),text
        assert any(('Compiling ' if mode=='native' else 'Checking ')+package in c['stderr'] for c in calls),'edited crate did not compile'
        if args.build_metrics or args.verify_restoration or args.aa_control:
            prefix=('Compiling ' if mode=='native' else 'Checking ')+package+' '
            assert any(line.strip().startswith(prefix) for call in calls for line in call['stderr'].splitlines()),'controlled source was not freshly compiled'
        assert record['source_sha256']==source_digest,'source changed during the command'
        built_sources[mode]=source_digest
        print(mode,cycle,state,label,round(record['seconds'],3),flush=True)
    require_space(work,args.minimum_free_gib)
    with SourceEdit(file,original) as source_edit:
        # Different modes each have their own caches. A cold successful original
        # build is followed by a wrong production edit, then cumulative body
        # refactors. Test code is byte-for-byte unchanged throughout.
        for sample in source_states(original.decode(),case,args.cycles,scheduled_modes,args.baseline_tool_key is not None):
            cycle=sample['cycle'];state=sample['state']
            if file.read_bytes()!=current:raise RuntimeError('source changed outside this benchmark')
            previous=hashlib.sha256(current).hexdigest()
            source_edit.replace(sample['source'])
            current=sample['source']
            current_digest=hashlib.sha256(current).hexdigest()
            if sample['phase']!='cold':assert previous!=current_digest,'repeated unchanged source state'
            orders.append({k:sample[k] for k in ['cycle','state','phase','modes']})
            transitions.append(dict(cycle=cycle,state=state,phase=sample['phase'],previous_source_sha256=previous,
                source_sha256=current_digest,content_changed=previous!=current_digest,previous_mode_sources=dict(built_sources)))
            write_json(work/'source-transitions.json',transitions)
            for mode in sample['modes']:
                if file.read_bytes()!=current:raise RuntimeError('source changed outside this benchmark')
                invoke(mode,sample)
            if args.baseline_tool_key is not None:
                paired=[next(r for r in records if r['mode']==mode and r['cycle']==cycle and r['state']==state) for mode in ['baseline','candidate']]
                assert paired[0]['source_sha256']==paired[1]['source_sha256']
                same=[a['sha256'] for a in paired[0]['artifacts']]==[a['sha256'] for a in paired[1]['artifacts']]
                if args.expect_identical_bytecode or args.aa_control:assert same,'baseline and candidate exported different bytecode; cannot isolate the runtime change'
            elif args.trap_unsupported_calls:
                custom=[next(r for r in records if r['mode']==mode and r['cycle']==cycle and r['state']==state) for mode in ['interpreter','jit']]
                assert custom[0]['source_sha256']==custom[1]['source_sha256']
                assert [a['sha256'] for a in custom[0]['artifacts']]==[a['sha256'] for a in custom[1]['artifacts']],'custom engines exported different artifacts'
            if args.check_floor:check_reference(sample)
    if args.verify_restoration:
        # Exercise the actual SourceEdit.__exit__ restoration, including its
        # fresh mtime, before declaring the workflow complete.
        assert file.read_bytes()==original,'original source restoration failed'
        previous=hashlib.sha256(current).hexdigest()
        current=original
        sample=restored_sample(args.cycles,scheduled_modes,args.baseline_tool_key is not None,original)
        original_digest=hashlib.sha256(original).hexdigest()
        assert previous!=original_digest,'final restoration did not change source'
        orders.append({k:sample[k] for k in ['cycle','state','phase','modes']})
        transitions.append(dict(cycle=sample['cycle'],state=sample['state'],phase=sample['phase'],
            previous_source_sha256=previous,source_sha256=original_digest,content_changed=True,
            previous_mode_sources=dict(built_sources)))
        write_json(work/'source-transitions.json',transitions)
        for mode in sample['modes']:
            assert file.read_bytes()==original,'restored source changed outside this benchmark'
            invoke(mode,sample)
        if args.baseline_tool_key is not None or args.trap_unsupported_calls:
            restored=[r for r in records if r['phase']=='restored-original' and r['mode']!='native']
            if args.expect_identical_bytecode or args.aa_control or args.trap_unsupported_calls and args.baseline_tool_key is None:
                assert [a['sha256'] for a in restored[0]['artifacts']]==[a['sha256'] for a in restored[1]['artifacts']],'restored paired bytecode differs'
        if args.check_floor:check_reference(sample)
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in frozen_scripts.items()),'benchmark scripts changed during the run'
    if native_identity is not None:
        identity_record['final_identity']=revalidate_native_toolchain(native_identity,identity_command,
            environment=identity_base,source=source)
        write_json(native_identity_path,identity_record)
    if runtime is not None:
        if load_runtime_compiler(ROOT,runtime.key)!=runtime:raise RuntimeError('runtime compiler changed during workflow')
        for config in mode_tools.values():validate_tool_runtime(config['directory'],config['tool_key'],runtime)
        if std is not None and checked_std_mir(TOOLCHAIN,**std_options)!=std:
            raise RuntimeError('prepared standard library changed during workflow')
    med={m:statistics.median(r['seconds'] for r in records if r['mode']==m and r['state']>0) for m in modes}
    result=dict(schema_version=2,project=args.project,workflow=workflow_label,revision=revision,cycles=args.cycles,initial_mode_order=scheduled_modes,
                minimum_free_gib=args.minimum_free_gib,
                tests=f'{len(tests)} existing private test bodies' if private else tests,
                edits=[e[0] for e in edits],
                workload=case['workload'],case_sha256=hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest(),
                test_source_unchanged=True,batch=args.batch,compare_isolated_batches=args.compare_isolated_batches,cargo_timings=args.cargo_timings,vary_selection=args.vary_selection,raw=str(work.relative_to(ROOT)),
                build_tool_opt_level=args.build_tool_opt_level,
                build_jobs=args.jobs,custom_build_jobs={mode:resolved_jobs[mode] for mode in mode_tools},
                native_control=dict(profile=args.native_profile,jobs=native_jobs,
                    test_threads=args.native_test_threads,rustflags=args.native_rustflag,
                    isolation='one native process per test' if args.compare_isolated_batches else 'ordinary libtest batch'),
                instruction_limit=args.instruction_limit,allocation_limit=args.allocation_limit,
                inline_leaves=args.inline_leaves,baseline_inline_leaves=args.baseline_inline_leaves,candidate_jit_persistent_registers=args.candidate_jit_persistent_registers,candidate_jit_resumable_calls=args.candidate_jit_resumable_calls,candidate_jit_native_calls=args.candidate_jit_native_calls,candidate_jit_native_call_stubs=args.candidate_jit_native_call_stubs,
                baseline_jit_resumable_calls=args.baseline_jit_resumable_calls,baseline_jit_persistent_registers=args.baseline_jit_persistent_registers,
                trap_unsupported_calls=args.trap_unsupported_calls,run_try_callbacks=args.run_try_callbacks,
                guest_mir_opt_level=args.guest_mir_opt_level,
                baseline_guest_mir_opt_level=args.baseline_guest_mir_opt_level,baseline_guest_rustflags=baseline_guest_flags,
                guest_mir_inline_scale=args.guest_mir_inline_scale,
                guest_mir_inline_thresholds=inline_thresholds,guest_rustflags=guest_flags,
                tool_key=key,candidate_tool_key_requested=args.candidate_tool_key,wrong_production_edit_rejected=True,median_seconds=med,
                median_cpu_seconds={m:statistics.median(r['cpu_seconds'] for r in records if r['mode']==m and r['state']>0) for m in modes},
                cpu_accounting='RUSAGE_CHILDREN deltas around one waited-for child tree at a time; user plus system CPU; excludes harness CPU',
                std_mir=None if std is None else dict(key=std[2],setup_seconds=std[3]['setup_seconds'],build_seconds=std[3]['build_seconds'],metadata_bytes=std[3]['metadata_bytes']),
                cold_success_seconds={r['mode']:r['seconds'] for r in records if r['phase']=='cold'},
                cycle_anchor_seconds=[dict(cycle=cycle,seconds={r['mode']:r['seconds'] for r in records if r['cycle']==cycle and r['phase']=='anchor'}) for cycle in range(1,args.cycles)],
                source_transitions=transitions,
                scripts_sha256=frozen_scripts,tool_builds=tool_builds,mode_orders=orders,
                vm_sha256=hashlib.sha256((tools/'rust-interp-vm').read_bytes()).hexdigest(),
                exporter_sha256=hashlib.sha256((tools/'rust-interp-mir-export').read_bytes()).hexdigest(),
                samples=[{k:v for k,v in r.items() if k!='calls' and not (private and k=='tests')} for r in records])
    if args.aa_control:result['aa_control']=True
    if args.workload_lock is not None:result['workload_lock']=str(workload_lock)
    if runtime is not None:result['guest_rustflag_encoding']='launcher-arguments'
    elif encoded_guest_flags:result['guest_rustflag_encoding']='cargo-unit-separator'
    if runtime is not None:result['runtime_compiler']=dict(runtime_proof,prepared_std=std_selection)
    if native_identity is not None:
        result['native_control'].update(toolchain=native_selection,identity=native_identity,
            identity_evidence=str(native_identity_path.relative_to(ROOT)),
            identity_evidence_sha256=hashlib.sha256(native_identity_path.read_bytes()).hexdigest())
    if args.build_metrics or args.verify_restoration or args.aa_control:result['build_controls']=dict(package=package)
    if controlled_caches:result.update(cache_namespaces=cache_namespaces,cache_workspaces=cache_workspaces)
    if args.verify_restoration:
        result['restored_original']=dict(verified=True,source_sha256=hashlib.sha256(original).hexdigest(),
            cycle=args.cycles,state=-2,commands=len(modes),excluded_from_edited_medians=True)
    if args.build_metrics:
        result['build_metrics']=dict(boundary='launcher start to validated artifact ready, before VM invocation',
            cpu_accounting='launcher self plus waited-for child CPU at the pre-VM boundary; user plus system',
            median_seconds={m:statistics.median(r['build_to_ready_seconds'] for r in records if r['mode']==m and r['state']>0) for m in mode_tools},
            median_cpu_seconds={m:statistics.median(r['build_to_ready_cpu_seconds'] for r in records if r['mode']==m and r['state']>0) for m in mode_tools})
    if case_proof is not None:result['case_file']=case_proof
    result['exporter_seconds']={}
    for mode in modes:
        if mode=='native':continue
        rows=[row for row in records if row['mode']==mode and row['state']>0]
        result['exporter_seconds'][mode]={}
        for phase in ['frontend','lowering','scalar-frames','scalar-promotion','inline','cfg']:
            complete=all(phase in c['exporter_seconds'] for row in rows for c in row['calls'])
            result['exporter_seconds'][mode][phase]=statistics.median(sum(c['exporter_seconds'][phase] for c in row['calls']) for row in rows) if complete else None
    result['check_floor']=None if not args.check_floor else dict(
        interpretation='Independent library-test Cargo-check control; executes no tests, including the wrong runtime edit; not a strict lower bound or subtractive attribution',
        timing_position='after each primary mode triplet; separate target/cache history; no Cargo timing-report generation',
        median_seconds=statistics.median(r['seconds'] for r in check_records if r['state']>0),
        median_cpu_seconds=statistics.median(r['cpu_seconds'] for r in check_records if r['state']>0),
        samples=[{k:v for k,v in r.items() if k not in ['stdout','stderr','command']} for r in check_records])
    if args.baseline_tool_key is not None:
        pairs=[]
        for cycle in range(args.cycles):
            for state in range(1,len(edits)+1):
                before=next(r for r in records if r['mode']=='baseline' and r['cycle']==cycle and r['state']==state)
                after=next(r for r in records if r['mode']=='candidate' and r['cycle']==cycle and r['state']==state)
                native=next(r for r in records if r['mode']=='native' and r['cycle']==cycle and r['state']==state)
                assert before['source_sha256']==after['source_sha256']==native['source_sha256']
                stages={name:{stage:sum(call['launch'][stage] for call in row['calls']) for stage in ['cargo_seconds','execution_seconds','artifact_hash_seconds','launcher_seconds']} for name,row in [('baseline',before),('candidate',after)]}
                pairs.append(dict(cycle=cycle,state=state,source_sha256=before['source_sha256'],baseline_seconds=before['seconds'],candidate_seconds=after['seconds'],
                                  native_seconds=native['seconds'],native_cpu_seconds=native['cpu_seconds'],
                                  baseline_cpu_seconds=before['cpu_seconds'],candidate_cpu_seconds=after['cpu_seconds'],
                                  cpu_difference_seconds=after['cpu_seconds']-before['cpu_seconds'],
                                  difference_seconds=after['seconds']-before['seconds'],stage_seconds=stages,
                                  identical_bytecode=[a['sha256'] for a in before['artifacts']]==[a['sha256'] for a in after['artifacts']]))
                if args.build_metrics:
                    for mode,row in [('baseline',before),('candidate',after)]:
                        for field in ['build_to_ready_seconds','build_to_ready_cpu_seconds','cargo_cpu_seconds']:
                            pairs[-1][mode+'_'+field]=row[field]
                    pairs[-1].update(build_to_ready_difference_seconds=after['build_to_ready_seconds']-before['build_to_ready_seconds'],
                        build_to_ready_cpu_difference_seconds=after['build_to_ready_cpu_seconds']-before['build_to_ready_cpu_seconds'])
        result['comparison']=dict(engine=args.comparison_engine or 'jit',baseline_tool_key=args.baseline_tool_key,candidate_tool_key=key,
                                  identical_bytecode_required=args.expect_identical_bytecode,pairs=pairs,
                                  candidate_pair_wins=sum(p['difference_seconds']<0 for p in pairs),
                                  median_paired_difference_seconds=statistics.median(p['difference_seconds'] for p in pairs),
                                  median_paired_cpu_difference_seconds=statistics.median(p['cpu_difference_seconds'] for p in pairs),
                                  per_edit=per_edit_spread(pairs))
    out=ROOT/'results'/args.run_id;out.mkdir()
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    report=f'# Production edits and existing {args.project} tests\n\n{case["workload"]}.\n\n'
    if args.allocation_limit is not None:
        report+=f'Custom engines explicitly allow {args.allocation_limit:,} live guest allocations and retain the 64 MiB guest-byte budget. Native Cargo uses its normal allocator.\n\n'
    report+=f'{len(edits)} cumulative production-body refactors across {args.cycles} cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. '
    report+=('Custom engines use one command.\n\n' if args.batch else 'Custom engines use a serial launcher command per test.\n\n')
    if args.cargo_timings:
        report+='Every mode enables Cargo unit timing reports. Report generation is included in the command time; snapshot copying follows the timer. Snapshot paths and hashes are recorded with each sample.\n\n'
    if args.aa_control:
        report+='This A/A control uses identical tools and settings with distinct recorded cache namespaces and Cargo workspaces. It measures control variability, not an optimization.\n\n'
    if args.verify_restoration:
        report+='After source restoration completed, every mode freshly compiled and executed the original tests. These final controls are excluded from edited medians and pairs.\n\n'
    if args.build_metrics:
        report+='Build-to-ready measurements end after the launcher validates the selected artifact and before VM invocation. CPU includes launcher self and its waited-for build children; no VM execution time is subtracted.\n\n'
        report+='| Mode | Median edited build-to-ready wall, s | Median edited build-to-ready CPU, s |\n|---|---:|---:|\n'
        for mode in mode_tools:
            report+=f'| {mode} | {result["build_metrics"]["median_seconds"][mode]:.3f} | {result["build_metrics"]["median_cpu_seconds"][mode]:.3f} |\n'
        report+='\n'
    if args.baseline_tool_key is not None:
        comparison=result['comparison']
        report+=f"Baseline and candidate use `{comparison['engine']}` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.\n\n"
        equality_note = ('Bytecode equality is required and verified.' if args.expect_identical_bytecode else
                         f"Bytecode is identical in {sum(pair['identical_bytecode'] for pair in comparison['pairs'])}/{len(comparison['pairs'])} pairs; both artifacts are retained for every pair.")
        report+=f"The candidate wins {comparison['candidate_pair_wins']}/{len(comparison['pairs'])} complete-command pairs. The median paired candidate-minus-baseline difference is {comparison['median_paired_difference_seconds']:+.3f} s wall and {comparison['median_paired_cpu_difference_seconds']:+.3f} s child CPU. {equality_note} Per-edit Cargo and execution stages are retained in JSON.\n\n"
        report+='| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |\n|---|---:|---:|---:|\n'
        for row in comparison['per_edit']:
            values=[' / '.join(f"{row['spread'][field][stat]:+.3f}" for stat in ['min','median','max']) for field in ['difference_seconds','cpu_difference_seconds']]
            report+=f"| {row['state']} | {row['samples']} | {' | '.join(values)} |\n"
        report+='\nThis is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.\n\n'
    if args.trap_unsupported_calls:
        report+='Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.\n\n'
    if args.build_tool_opt_level is not None:
        report+=f'Host build scripts, procedural macros, and their build dependencies use optimization level {args.build_tool_opt_level} in every mode. Their first compilation is included in cold command times.\n\n'
    if runtime is not None or encoded_guest_flags:
        report+=f"Custom compiler arguments are recorded separately for each mode: baseline `{json.dumps(baseline_guest_flags)}`, candidate `{json.dumps(guest_flags)}`. "
        report+=('The launcher applies these arguments only to application Cargo, after tool and standard-library selection. ' if runtime is not None else 'Cargo receives each argument through its unit-separator encoding. ')
        report+='Native retains its declared Cargo profile and compiler flags.\n\n'
    elif args.baseline_guest_mir_opt_level is not None:
        report+=f"Baseline custom commands use `RUSTFLAGS={' '.join(baseline_guest_flags)}`; candidate commands use `RUSTFLAGS={' '.join(guest_flags)}`. Native retains its Cargo profile. Both configurations preserve strict checking. Exact per-mode flags and all resulting artifacts are retained.\n\n"
    elif guest_flags:
        flags=' '.join(guest_flags)
        report+=f'Custom-engine Cargo commands explicitly set `RUSTFLAGS={flags}`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.\n\n'
    if args.vary_selection:
        report+='Test selection changes with each production edit. Each mode runs the same selection at each state; the exact selections are recorded in summary.json.\n\n'
    report+='| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |\n|---|---:|---:|---:|\n'
    report+=''.join(f'| {m} | {v:.3f} | {result["median_cpu_seconds"][m]:.3f} | {result["cold_success_seconds"][m]:.3f} |\n' for m,v in med.items())
    job_description=', '.join(f'{mode}={resolved_jobs[mode]}' for mode in mode_tools)
    report+=f'\nNative control: `{args.native_profile}`, {native_jobs} build jobs, `{args.native_test_threads}` test threads, explicit rustc arguments `{args.native_rustflag}`. Custom build jobs: {job_description}. This labels the configuration; it does not establish the fastest native control.\n'
    if args.check_floor:
        report+=f'\nIndependent Cargo-check reference: {result["check_floor"]["median_seconds"]:.3f} s wall / {result["check_floor"]["median_cpu_seconds"]:.3f} s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.\n'
    report+='\nExporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):\n\n| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for mode,stages in result['exporter_seconds'].items():
        report+='| '+mode+' | '+' | '.join('unreported' if stages[p] is None else f'{stages[p]:.3f}' for p in ['frontend','lowering','scalar-frames','scalar-promotion','inline','cfg'])+' |\n'
    if result['cycle_anchor_seconds']:
        report+='\n| Anchor cycle (zero-based) | '+' | '.join(modes)+' |\n|---|'+':---:|'*len(modes)+'\n'
        for row in result['cycle_anchor_seconds']:
            report+=f"| {row['cycle']} | "+' | '.join(f"{row['seconds'][mode]:.3f}" for mode in modes)+' |\n'
    report+='\nCPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.\n'
    report+=f'\nCold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. {len(edits)*args.cycles} edited samples per mode on a shared host do not establish a whole-suite or general performance result.\n'
    if args.candidate_jit_resumable_calls:report+='\nThe candidate enables native Calls/Returns with guest-frame continuations.\n'
    if args.candidate_jit_persistent_registers:report+='\nThe candidate enables persistent full-width native registers.\n'
    if args.baseline_jit_resumable_calls:report+='\nThe baseline enables native Calls/Returns with guest-frame continuations.\n'
    if args.baseline_jit_persistent_registers:report+='\nThe baseline enables persistent full-width native registers.\n'
    if args.candidate_jit_native_call_stubs:report+='\nCandidate native Calls are also linked with ordinary JIT regions.\n'
    if args.candidate_jit_native_calls:report+='\nThe candidate explicitly enables bounded native call trees; the baseline uses its ordinary JIT. Export/lowering options remain identical when artifact equality is required.\n'
    if std:report+=f'\nCustom engines use the shared metadata-only standard library. Its original installation took {std[3]["setup_seconds"]:.3f} s, including {std[3]["build_seconds"]:.3f} s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.\n'
    (out/'summary.md').write_text(report)
    print(out/'summary.md')


if __name__=='__main__':main()
