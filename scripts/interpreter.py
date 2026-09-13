#!/usr/bin/env python3
"""Check a Cargo library or integration-test target and run supported functions.

Example: interpreter.py --manifest-path PROJECT/Cargo.toml --package hashfn
         --entry murmurhash32 -- 123

Repeat --entry with --test-body to run several zero-argument functions returning
unit or Result<(), E> in one command. Ordinary function inputs and output are integer bit
patterns. This prototype provides a guest allocator, but no general Rust main
or OS runtime. Ordinary test batches stop at the first failure; optional isolated
batches report every selected test with fresh guest state.
Use --test-body --test-target NAME to select one Cargo integration-test target.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
from workspace_cache import workspace_cache_base, cache_subdirectory

ROOT=Path(__file__).resolve().parents[1]
TOOLCHAIN='nightly-2026-09-08'
LEGACY_TOOL_BINARIES=('rust-interp-vm','rust-interp-mir-export')
CURRENT_TOOL_BINARIES=(*LEGACY_TOOL_BINARIES,'rust-interp-rustc-wrapper')


def cpu_usage(who):
    usage=resource.getrusage(who)
    return usage.ru_utime,usage.ru_stime


def cpu_since(who, before):
    user,system=(after-start for after,start in zip(cpu_usage(who),before))
    return dict(user_seconds=user,system_seconds=system,total_seconds=user+system)


def installed_tools(key):
    """Load an immutable local tool build without rebuilding current sources."""
    if not isinstance(key,str) or len(key)!=64 or any(c not in '0123456789abcdef' for c in key):
        raise RuntimeError('tool key must contain 64 lowercase hexadecimal characters')
    directory=ROOT/'.work/interpreter-tools'/key
    try:
        manifest=json.loads((directory/'ready.json').read_text())
    except (OSError,ValueError) as error:
        raise RuntimeError('cannot read installed tool build '+key+': '+str(error)) from error
    if not isinstance(manifest,dict) or set(manifest) not in (set(LEGACY_TOOL_BINARIES),set(CURRENT_TOOL_BINARIES)):
        raise RuntimeError('invalid installed tool manifest')
    for name,digest in manifest.items():
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise RuntimeError('invalid installed tool digest')
        try:
            actual=hashlib.sha256((directory/name).read_bytes()).hexdigest()
        except OSError as error:
            raise RuntimeError('cannot read installed tool binary '+name+': '+str(error)) from error
        if actual!=digest:raise RuntimeError('interpreter binary integrity mismatch: '+name)
    return directory,key


def checked_tools():
    (ROOT/'.work').mkdir(exist_ok=True)
    with (ROOT/'.work/interpreter-tools.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _checked_tools_locked()


def _checked_tools_locked():
    inputs=[ROOT/'Cargo.toml',ROOT/'Cargo.lock']
    for folder in ['bytecode','mir-export']:
        inputs+=sorted((ROOT/'crates'/folder).rglob('*.rs'))
        inputs.append(ROOT/'crates'/folder/'Cargo.toml')
    def fingerprint():
        h=hashlib.sha256()
        # A pin change must not reuse binaries linked to the prior rustc_driver.
        # Explicit --tool-key builds retain their separate immutable identity.
        h.update(b'rust-interp-tools-v2\0'+TOOLCHAIN.encode()+b'\0')
        for p in inputs:h.update(str(p.relative_to(ROOT)).encode()+b'\0'+p.read_bytes())
        return h.hexdigest()
    key=fingerprint()
    directory=ROOT/'.work/interpreter-tools'/key
    if not (directory/'ready.json').exists():
        subprocess.run(['cargo','+'+TOOLCHAIN,'build','--release','--locked','--offline','--jobs','4','-p','rust-interp-bytecode','-p','rust-interp-mir-export','--target-dir',str(ROOT/'.work/interpreter-build')],cwd=ROOT,check=True)
        if fingerprint()!=key:raise RuntimeError('compiler sources changed while building')
        directory.mkdir(parents=True,exist_ok=True)
        manifest={}
        for name in CURRENT_TOOL_BINARIES:
            source=ROOT/'.work/interpreter-build/release'/name
            shutil.copy2(source,directory/name)
            manifest[name]=hashlib.sha256(source.read_bytes()).hexdigest()
        # Record capabilities when publishing this exact exporter, outside
        # measured launcher invocations. Older retained builds lack this file.
        probe=subprocess.run([str(directory/'rust-interp-mir-export'),'--rust-interp-capabilities'],
                             capture_output=True,text=True,timeout=10)
        if probe.returncode==0:
            capabilities=json.loads(probe.stdout)
            if capabilities.get('schema_version')!=1:raise RuntimeError('unsupported exporter capability schema')
            capabilities.update(tool_key=key,exporter_sha256=manifest['rust-interp-mir-export'])
            from frontend_workers import bind_wrapper_capability
            bind_wrapper_capability(directory,manifest,capabilities)
            (directory/'capabilities.json').write_text(json.dumps(capabilities,indent=2))
        (directory/'ready.json').write_text(json.dumps(manifest,indent=2))
    return installed_tools(key)


def require_export_option(directory, key, option):
    """Old immutable tools remain usable, but cannot silently ignore new options."""
    try:
        capabilities=json.loads((directory/'capabilities.json').read_text())
        manifest=json.loads((directory/'ready.json').read_text())
        if (capabilities['schema_version']!=1 or capabilities['tool_key']!=key or
            capabilities['exporter_sha256']!=manifest['rust-interp-mir-export'] or
            capabilities['bytecode_version']!=5 or option not in capabilities['export_options']):
            raise ValueError('capability does not match installed exporter')
    except (OSError,ValueError,KeyError,TypeError) as error:
        raise RuntimeError('installed exporter does not support --'+option+': '+key) from error


def entry_catalog_supported(directory, key):
    path=directory/'capabilities.json'
    if not path.exists():return False # Legacy immutable tool builds remain usable.
    caps=json.loads(path.read_text())
    if 'entry-catalog' not in caps.get('export_options',[]):return False
    require_export_option(directory,key,'entry-catalog')
    return True


def selected_entry_catalog(artifact, requested):
    path=Path(str(artifact)+'.entries.json')
    if path.is_symlink() or not path.is_file() or path.stat().st_size>8*1024*1024:
        raise RuntimeError('Cargo selected a missing or oversized entry catalog')
    try:report=json.loads(path.read_bytes())
    except (OSError,ValueError) as error:
        raise RuntimeError('Cargo selected an unreadable entry catalog') from error
    entries=report.get('entries') if isinstance(report,dict) else None
    if (not isinstance(report,dict) or report.get('schema_version')!=1 or report.get('bytecode_version')!=5 or
            not isinstance(entries,list) or not all(isinstance(entry,dict) for entry in entries) or
            [entry.get('name') for entry in entries]!=requested):
        raise RuntimeError('Cargo entry catalog does not match requested tests')
    # The VM binds this catalog to the exact bytecode bytes it reads; the
    # invocation lock keeps Cargo's selected sidecars fixed through execution.
    return path


def validate_audit_pack(report, work):
    """Verify immutable files named by Cargo's exact selected audit sidecar."""
    try:
        pack=report['artifacts']
        if (pack['kind']!='audit-body-pack' or pack['schema_version']!=1 or
            pack['max_body_bytes']!=64*1024*1024 or pack['max_pack_bytes']!=1024*1024*1024):
            raise ValueError('unsupported pack schema or limits')
        directory=Path(pack['directory'])
        parts=directory.name.split('-')
        if (not directory.is_absolute() or directory.parent!=work.resolve() or
            len(parts)!=4 or parts[:2]!=['audit','bodies'] or not all(x.isdigit() for x in parts[2:]) or
            directory.is_symlink() or not directory.is_dir()):
            raise ValueError('pack directory is outside the selected workspace')
        expected=set();total=0
        if len(report['entries'])>4096:raise ValueError('too many audit entries')
        for index,row in enumerate(report['entries']):
            if row['status']!='lowered':
                if 'artifact' in row:raise ValueError('blocked body has an artifact')
                continue
            item=row['artifact'];name=f'{index:04}.rbc'
            if item['file']!=name:raise ValueError('unexpected artifact filename')
            size=item['bytes'];digest=item['sha256']
            if type(size) is not int or not 0<size<=64*1024*1024:
                raise ValueError('artifact size outside limits')
            if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError('invalid artifact digest')
            total+=size
            if total>1024*1024*1024:raise ValueError('pack exceeds 1 GiB')
            artifact=directory/name
            if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size!=size:
                raise ValueError('missing or resized artifact')
            data=artifact.read_bytes()
            if len(data)!=size or hashlib.sha256(data).hexdigest()!=digest:
                raise ValueError('artifact digest mismatch')
            expected.add(name)
        if (type(pack['files']) is not int or type(pack['bytes']) is not int or
            pack['files']!=len(expected) or pack['bytes']!=total or
            {p.name for p in directory.iterdir()}!=expected):
            raise ValueError('pack contents do not match its manifest')
    except (OSError,KeyError,TypeError,ValueError,AttributeError) as error:
        raise RuntimeError('Cargo selected an invalid audit body pack: '+str(error)) from error


def unavailable_call_failure(stderr, sites):
    """Match a compiler-recorded unavailable boundary, including inliner context."""
    for site in sites:
        prefix='rust-interp-vm: guest trap: '+site['trap_message']
        if any(line.startswith((prefix+' in ',prefix+' [inlined from ')) for line in stderr.splitlines()):
            return site
    return None


def artifact_matches_target(event, test_body, test_target):
    """Only the requested Cargo target can supply execution bytecode."""
    if event.get('reason') != 'compiler-artifact' or bool(event['profile']['test']) != test_body:
        return False
    if test_target is None:
        return True  # Preserve the qualified library route.
    target = event.get('target', {})
    return target.get('kind') == ['test'] and target.get('name') == test_target


def main():
    with contextlib.ExitStack() as resources:
        return _main(resources)


def _main(resources):
    started=time.perf_counter()
    timings={}
    stats=os.environ.get('RUST_INTERP_LAUNCH_STATS')=='1'
    if stats:
        # RUSAGE_CHILDREN includes waited-for descendant trees. Combined with
        # RUSAGE_SELF this covers launcher work and completed build subprocesses,
        # including tool/std-MIR preparation; Python startup/imports are excluded.
        launcher_cpu_started=cpu_usage(resource.RUSAGE_SELF)
        children_cpu_started=cpu_usage(resource.RUSAGE_CHILDREN)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-path',type=Path,default=Path('Cargo.toml'))
    parser.add_argument('--package',required=True)
    parser.add_argument('--jobs',type=int,default=4,help='Cargo build jobs (1..256)')
    parser.add_argument('--frontend-workers',type=int,choices=[1,2],help='experimental explicit compiler frontend workers; omission keeps the pinned default of one')
    selected=parser.add_mutually_exclusive_group(required=True)
    selected.add_argument('--entry',action='append',help='function to run; repeat for a batch of unit test bodies')
    selected.add_argument('--test-filter',help='select ordinary nonignored libtest bodies by name substring in one checked compiler invocation')
    parser.add_argument('--test-exact',action='store_true',help='match --test-filter against the complete test name')
    selected.add_argument('--list-tests',action='store_true',help='list checked built-in test names and attributes without executing tests')
    selected.add_argument('--audit-entries',type=Path,help='JSON list of test body names to check for lowering support, without executing them')
    parser.add_argument('--retain-audit-bodies',action='store_true',help='retain bounded, hashed programs from a lowering audit for separate execution diagnostics')
    parser.add_argument('--allocation-trace',action='store_true',help='record bounded allocation origins and verify their binding to the selected bytecode before execution')
    parser.add_argument('--features')
    parser.add_argument('--no-default-features',action='store_true')
    parser.add_argument('--instruction-limit',type=int,help='maximum VM instructions (default: 100000000)')
    parser.add_argument('--allocation-limit',type=int,help='maximum live guest allocations, independent of byte memory (0..1000000; default: 100000)')
    parser.add_argument('--engine',choices=['interpreter','jit'],default='interpreter')
    parser.add_argument('--isolated-batch',choices=['fresh','prepared'],help='experimental separate guest state per selected test; runtime limits apply to each test')
    parser.add_argument('--suite-report',type=Path,help='new JSON result path for --isolated-batch')
    parser.add_argument('--suite-workers',type=int,help='isolated test workers, each owning its JIT (1..64; default: 1)')
    parser.add_argument('--jit-native-call-stubs',action='store_true',help='experimental Calls linked with ordinary regions; requires --jit-native-calls')
    parser.add_argument('--jit-resumable-calls',action='store_true',help='experimental native Calls over guest frames; requires JIT, excludes tree/stub calls')
    parser.add_argument('--jit-persistent-registers',action='store_true',help='experimental full-width values retained across native block edges; requires --engine=jit')
    parser.add_argument('--jit-native-calls',action='store_true',help='experimental complete native call trees; requires --engine=jit')
    parser.add_argument('--tool-key',help='use an already installed immutable tool build, for reproducing or comparing runs')
    parser.add_argument('--cache-namespace',default='',help='use an independent artifact cache, for reproducible cold-build comparisons')
    parser.add_argument('--function-cache',choices=['off','reuse','auto'],default='off',help='experimental compiler-validated function cache: reuse requires incremental tracking; auto uses full lowering when tracking is disabled; strict checking always runs (default: off)')
    parser.add_argument('--borrowck-cache',choices=['off','verify','reuse'],default='off',help='experimental compiler-validated borrow-check query cache for all compiled Cargo units; verify compares cached results while checking; reuse retains strict checking (default: off)')
    parser.add_argument('--workspace-cache-root',type=Path,help='existing cache parent; create a separate namespace for this checkout (default: .work/interpreter-workspaces)')
    parser.add_argument('--inline-leaves',action='store_true',help='experimental bounded bytecode leaf inlining at export; intended for JIT comparisons')
    parser.add_argument('--trap-unsupported-calls',action='store_true',help='experimental: stop execution at unavailable direct foreign calls and catch_unwind intrinsics instead of rejecting their export')
    parser.add_argument('--run-try-callbacks',action='store_true',help='experimental: execute catch_unwind try callbacks; actual panic/unwinding still fails; requires --trap-unsupported-calls')
    parser.add_argument('--std-mir',action='store_true',help='use reusable standard-library metadata with complete MIR')
    parser.add_argument('--toolchain-lookup',choices=['fresh','cached'],default='fresh',help='experimental dated-rustup identity cache; requires --std-mir (default: fresh)')
    parser.add_argument('--timings',action='store_true',help='write Cargo\'s compilation timing report for this command')
    parser.add_argument('--test-body',action='store_true',help='invoke a function from the library unit-test target directly; libtest attributes are not implemented')
    parser.add_argument('--test-target',help='select a named Cargo integration-test target; requires --test-body')
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if args.frontend_workers is not None:
        from frontend_workers import validate_selection, require_capability, namespace, receipt
        try:validate_selection(args,os.environ)
        except ValueError as error:parser.error(str(error))
    if args.toolchain_lookup!='fresh' and not args.std_mir:parser.error('--toolchain-lookup=cached requires --std-mir')
    if args.test_target is not None:
        if not args.test_body:parser.error('--test-target requires --test-body')
        if not args.test_target or any(c in args.test_target for c in '\x00\r\n'):
            parser.error('--test-target must be a nonempty Cargo target name')
    if args.jit_native_call_stubs and not args.jit_native_calls:parser.error('--jit-native-call-stubs requires --jit-native-calls')
    if args.jit_persistent_registers and args.engine != 'jit':parser.error('--jit-persistent-registers requires --engine=jit')
    if args.jit_resumable_calls and args.engine != 'jit':parser.error('--jit-resumable-calls requires --engine=jit')
    if args.jit_resumable_calls and (args.jit_native_calls or args.jit_native_call_stubs):parser.error('--jit-resumable-calls cannot be combined with native tree/stub calls')
    if args.jit_native_calls and args.engine != 'jit':parser.error('--jit-native-calls requires --engine=jit')
    if not 1<=args.jobs<=256:parser.error('--jobs must be in 1..256')
    if args.run_try_callbacks and not args.trap_unsupported_calls:
        parser.error('--run-try-callbacks requires --trap-unsupported-calls')
    auditing=args.audit_entries is not None
    listing=args.list_tests
    filtered=args.test_filter is not None
    if args.function_cache!='off' and (auditing or listing or args.allocation_trace):
        parser.error('--function-cache requires execution without discovery, audit or allocation tracing')
    if args.test_exact and not filtered:parser.error('--test-exact requires --test-filter')
    if filtered:
        if (not args.test_body or args.isolated_batch is None or args.arguments or
                args.retain_audit_bodies or len(args.test_filter.encode())>4096 or
                any(c in args.test_filter for c in '\x00\r\n')):
            parser.error('--test-filter requires --test-body, isolated execution, and a pattern of at most 4096 bytes without line breaks')
        args.entry=[]
    if listing:
        if (not args.test_body or args.arguments or args.engine!='interpreter' or
                args.instruction_limit is not None or args.allocation_limit is not None or
                args.isolated_batch is not None or args.suite_report is not None or args.jit_native_calls or
                args.jit_native_call_stubs or args.jit_resumable_calls or args.jit_persistent_registers or
                args.inline_leaves or args.trap_unsupported_calls or args.run_try_callbacks or
                args.allocation_trace or args.retain_audit_bodies):
            parser.error('--list-tests requires --test-body without execution or lowering options')
        args.entry=[]
    if (args.isolated_batch is None) != (args.suite_report is None):
        parser.error('--isolated-batch and --suite-report must be supplied together')
    if args.suite_workers is not None and (args.isolated_batch is None or not 1<=args.suite_workers<=64):
        parser.error('--suite-workers requires an isolated batch and a count in 1..64')
    if args.isolated_batch is not None:
        if auditing or not args.test_body or (not filtered and len(args.entry or []) < 2) or args.arguments:
            parser.error('--isolated-batch requires --test-filter or at least two --entry test bodies without audit or entry arguments')
        if args.engine != 'jit' or not args.jit_resumable_calls or args.jit_native_calls or args.jit_native_call_stubs:
            parser.error('--isolated-batch requires resumable JIT execution without tree/stub modes')
        if args.suite_report.exists() or args.suite_report.is_symlink() or not args.suite_report.parent.is_dir():
            parser.error('--suite-report requires a new file in an existing directory')
        args.suite_report=args.suite_report.resolve()
    if args.allocation_trace and auditing:
        parser.error('--allocation-trace cannot be combined with --audit-entries')
    if args.retain_audit_bodies and not auditing:
        parser.error('--retain-audit-bodies requires --audit-entries')
    if auditing:
        if not args.test_body or args.arguments or args.instruction_limit is not None or args.allocation_limit is not None:
            parser.error('--audit-entries requires --test-body and cannot take VM arguments or execution limits')
        try:
            if args.audit_entries.stat().st_size>8*1024*1024:parser.error('audit selection exceeds 8 MiB')
            args.entry=json.loads(args.audit_entries.read_text())
        except (OSError,ValueError) as error:
            parser.error('cannot read audit selection: '+str(error))
        if not isinstance(args.entry,list) or any(not isinstance(s,str) or not s or len(s.encode())>4096 for s in args.entry):
            parser.error('audit selection must be a JSON list of nonempty names, each at most 4096 bytes')
    if args.allocation_limit is not None and not 0<=args.allocation_limit<=1_000_000:
        parser.error('--allocation-limit must be between 0 and 1000000')
    if args.instruction_limit is not None and args.instruction_limit <= 0:
        parser.error('--instruction-limit must be positive')
    maximum=4096 if auditing else 256
    if not listing and not filtered and (not 1<=len(args.entry)<=maximum or len(set(args.entry))!=len(args.entry)):
        parser.error(f'select between 1 and {maximum} distinct entries')
    if len(args.entry)>1 and (not args.test_body or [v for v in args.arguments if v!='--']):
        parser.error('multiple entries require --test-body and no function arguments')
    try:
        cache_base=workspace_cache_base(ROOT,args.workspace_cache_root)
    except (OSError,ValueError) as error:
        parser.error('--workspace-cache-root: '+str(error))
    manifest=args.manifest_path.resolve()
    stage=time.perf_counter()
    tools,key=installed_tools(args.tool_key) if args.tool_key is not None else checked_tools()
    if args.frontend_workers is not None:
        require_export_option(tools,key,'frontend-workers-v1')
        capabilities=json.loads((tools/'capabilities.json').read_text())
        require_capability(tools,capabilities,json.loads((tools/'ready.json').read_text()))
        timings['frontend_workers']=receipt(args.frontend_workers,capabilities)
    if args.function_cache!='off':require_export_option(tools,key,'function-cache-'+args.function_cache)
    if args.borrowck_cache!='off':require_export_option(tools,key,'borrowck-cache')
    if listing:require_export_option(tools,key,'list-tests')
    if filtered:require_export_option(tools,key,'filtered-tests')
    if args.inline_leaves:require_export_option(tools,key,'inline-leaves')
    if args.trap_unsupported_calls:require_export_option(tools,key,'trap-unsupported-calls')
    if args.run_try_callbacks:require_export_option(tools,key,'run-try-callbacks')
    if args.allocation_trace:require_export_option(tools,key,'allocation-trace')
    timings['tools_seconds']=time.perf_counter()-stage
    if stats:timings.update(tool_key=key,engine=args.engine,jit_persistent_registers=args.jit_persistent_registers,jit_resumable_calls=args.jit_resumable_calls,jit_native_calls=args.jit_native_calls,jit_native_call_stubs=args.jit_native_call_stubs,inline_leaves=args.inline_leaves,trap_unsupported_calls=args.trap_unsupported_calls,run_try_callbacks=args.run_try_callbacks)
    if stats:timings['function_cache']=args.function_cache
    if stats:timings['borrowck_cache']=args.borrowck_cache
    std=None
    if args.std_mir:
        from std_mir import checked_std_mir
        stage=time.perf_counter()
        lookup_stats={}
        std=checked_std_mir(TOOLCHAIN,lookup=args.toolchain_lookup,lookup_stats=lookup_stats)
        timings['std_mir_seconds']=time.perf_counter()-stage
        if stats:timings['toolchain_lookup']=lookup_stats
    selection=args.entry[0] if len(args.entry)==1 else json.dumps(args.entry,separators=(',',':'))
    identity_input='shared-entries-v1\0'+str(manifest)+'\0'+args.package+'\0'+str(args.test_body)
    # Cargo already separates selected test units by target identity. Share
    # their compatible dependency metadata while the invocation lock and exact
    # compiler-artifact target match protect each selected sidecar.
    if args.test_target is not None:identity_input+='\0integration-targets-v1'
    if std:identity_input+='\0std-mir:'+std[2]
    if args.cache_namespace:identity_input+='\0'+args.cache_namespace
    # Keep mode changes from reusing Cargo freshness or incremental artifacts
    # generated without the requested compiler callbacks. The default identity
    # remains compatible with existing workspaces.
    if args.borrowck_cache!='off':
        identity_input='borrowck-cache-v1\0'+args.borrowck_cache+'\0'+identity_input
    if args.frontend_workers is not None:
        identity_input=namespace(args.frontend_workers,identity_input)
    identity=hashlib.sha256(identity_input.encode()).hexdigest()[:24]
    if args.workspace_cache_root is None:
        work=cache_base/key/identity
        work.mkdir(parents=True,exist_ok=True)
    else:
        work=cache_subdirectory(cache_base,key,identity)
        for name in ['target','invocation.lock']:
            if (work/name).is_symlink():
                raise RuntimeError('cache workspace contains a replacement symlink: '+name)
    if stats:timings['workspace_path']=str(work)
    # Keep the selected metadata sidecar stable through execution when two
    # launcher invocations select different entries in this target directory.
    invocation_lock=resources.enter_context((work/'invocation.lock').open('a'))
    fcntl.flock(invocation_lock,fcntl.LOCK_EX)
    env=os.environ.copy()
    # Preserve Cargo's feature/profile/rustflag behavior. Tool-specific outputs
    # and compiler selection are isolated from native build directories.
    for name in list(env):
        if name.startswith('RUST_INTERP_'):env.pop(name)
    tool_manifest=json.loads((tools/'ready.json').read_text())
    wrapper_name='rust-interp-rustc-wrapper' if 'rust-interp-rustc-wrapper' in tool_manifest else 'rust-interp-mir-export'
    timings['compiler_wrapper']=dict(name=wrapper_name,sha256=tool_manifest[wrapper_name])
    env.update(RUSTC_WRAPPER=str(tools/wrapper_name),RUSTC_WORKSPACE_WRAPPER='',
               RUST_INTERP_EXPORT_PACKAGE=args.package,
               RUST_INTERP_OUTPUT=str(work/('tests.json' if listing else 'audit.json' if auditing else 'program.rbc')),RUST_INTERP_EXPORT_TEST='1' if args.test_body else '0',CARGO_TARGET_DIR=str(work/'target'))
    if args.test_target is not None:
        # The existing compiler router also checks Cargo package/primary/test
        # identity. A same-package library or sibling test cannot export here.
        env['RUST_INTERP_EXPORT_CRATE']=args.test_target.replace('-', '_')
    if args.inline_leaves:env['RUST_INTERP_INLINE_LEAVES']='1'
    if args.trap_unsupported_calls:env['RUST_INTERP_TRAP_UNSUPPORTED_CALLS']='1'
    if args.run_try_callbacks:env['RUST_INTERP_RUN_TRY_CALLBACKS']='1'
    if args.allocation_trace:env['RUST_INTERP_ALLOCATION_TRACE']='1'
    if listing:
        env['RUST_INTERP_LIST_TESTS']='1'
    elif filtered:
        env['RUST_INTERP_TEST_FILTER']=json.dumps(dict(pattern=args.test_filter,exact=args.test_exact),separators=(',',':'))
    elif auditing:
        # Snapshot the selection under the invocation lock. Its content-addressed
        # path is tracked by rustc, avoiding argv/environment limits for suites.
        contents=json.dumps(args.entry,separators=(',',':')).encode()
        selection_file=work/('audit-selection-'+hashlib.sha256(contents).hexdigest()+'.json')
        if selection_file.exists():
            if selection_file.read_bytes()!=contents:raise RuntimeError('audit selection snapshot was modified')
        else:selection_file.write_bytes(contents)
        env['RUST_INTERP_AUDIT_SELECTION']=str(selection_file)
        if args.retain_audit_bodies:env['RUST_INTERP_RETAIN_AUDIT_BODIES']='1'
    elif len(args.entry)==1:env['RUST_INTERP_ENTRY']=args.entry[0]
    else:env['RUST_INTERP_ENTRIES']=selection
    if std:
        env['RUST_INTERP_STD_SYSROOT']=str(std[0])
        env['RUST_INTERP_STD_TARGET']=std[1]
    if stats:env['RUST_INTERP_VM_STATS']='1'
    command=['cargo','+'+TOOLCHAIN,'check','--manifest-path',str(manifest),'--package',args.package]
    command+=['--lib'] if args.test_target is None else ['--test',args.test_target]
    command+=['--locked','--offline','--jobs',str(args.jobs),'--message-format=json-render-diagnostics']
    if args.features:command+=['--features',args.features]
    if args.no_default_features:command+=['--no-default-features']
    # On the pinned Cargo, this selects Check { test: true } for exactly
    # --lib. --lib --tests instead adds both the ordinary library and every
    # test target, and required a separate metadata query for disambiguation.
    if args.test_body:command+=['--profile','test']
    if std:command+=['--target',std[1]]
    if args.timings:command+=['--timings']
    # Cargo CPU covers its waited-for child tree, excluding launcher CPU and
    # earlier tool/std-MIR preparation or later sidecar verification.
    if stats:cargo_cpu_started=cpu_usage(resource.RUSAGE_CHILDREN)
    stage=time.perf_counter()
    cargo_env=env
    if args.function_cache!='off' or args.borrowck_cache!='off' or args.frontend_workers is not None:
        cargo_env=env.copy()
        if args.frontend_workers is not None:cargo_env['RUST_INTERP_FRONTEND_WORKERS']=str(args.frontend_workers)
        if args.function_cache!='off':cargo_env['RUST_INTERP_FUNCTION_CACHE']=args.function_cache
        if args.borrowck_cache!='off':cargo_env['RUST_INTERP_BORROWCK_CACHE']=args.borrowck_cache
    result=subprocess.run(command,cwd=manifest.parent,env=cargo_env,stdout=subprocess.PIPE,text=True)
    timings['cargo_seconds']=time.perf_counter()-stage
    if stats:timings['cargo_cpu']=cpu_since(resource.RUSAGE_CHILDREN,cargo_cpu_started)
    if result.returncode:return result.returncode
    artifacts=[]
    suffix='.tests.json' if listing else '.audit.json' if auditing else '.rbc'
    for line in result.stdout.splitlines():
        try:
            event=json.loads(line)
            if artifact_matches_target(event,args.test_body,args.test_target):
                artifacts.extend(Path(p+suffix) for p in event['filenames'] if p.endswith('.rmeta') and Path(p+suffix).is_file())
        except json.JSONDecodeError:pass
    if len(artifacts)!=1 or not artifacts[0].is_file():raise RuntimeError('Cargo did not select a valid '+('test listing' if listing else 'audit report' if auditing else 'bytecode sidecar')+'; no program was run')
    if listing:
        from test_discovery import read_listing
        report,digest=read_listing(artifacts[0])
        report['tool_key']=key
        report['discovery_provenance']=dict(path=str(artifacts[0].resolve()),sha256=digest,
            exporter_sha256=tool_manifest['rust-interp-mir-export'])
        print(json.dumps(report,indent=2))
        timings.update(launcher_seconds=time.perf_counter()-started,executed=False,
            mode='test-discovery',discovery_count=report['count'],discovery_sha256=digest)
        if stats:print('rust-interp-launch: '+json.dumps(timings),file=sys.stderr)
        return 0
    if auditing:
        if artifacts[0].stat().st_size>64*1024*1024:raise RuntimeError('lowering audit report exceeds 64 MiB')
        audit_bytes=artifacts[0].read_bytes()
        report=json.loads(audit_bytes)
        if (report.get('kind')!='lowering-audit' or report.get('schema_version')!=1 or
            report.get('strict_frontend') is not True or report.get('executed') is not False or
            ('artifacts' in report)!=args.retain_audit_bodies or
            report.get('inline_leaves',False)!=args.inline_leaves or
            report.get('trap_unsupported_calls',False)!=args.trap_unsupported_calls or
            report.get('run_try_callbacks',False)!=args.run_try_callbacks or
            [r['entry'] for r in report['entries']]!=args.entry):
            raise RuntimeError('Cargo selected an incompatible lowering audit')
        if args.retain_audit_bodies:
            stage=time.perf_counter()
            validate_audit_pack(report,work)
            timings['audit_pack_verify_seconds']=time.perf_counter()-stage
            report['artifact_provenance']={
                'audit_path':str(artifacts[0].resolve()),
                'audit_sha256':hashlib.sha256(audit_bytes).hexdigest(),
                'selection_sha256':hashlib.sha256(contents).hexdigest(),
                'tool_binaries':json.loads((tools/'ready.json').read_text()),
            }
        report['tool_key']=key
        print(json.dumps(report,indent=2))
        timings['launcher_seconds']=time.perf_counter()-started
        if stats:print('rust-interp-launch: '+json.dumps(timings),file=sys.stderr)
        return 0
    if filtered:
        from test_discovery import read_selection
        stage=time.perf_counter()
        selection_path=Path(str(artifacts[0])+'.selection.json')
        report,digest=read_selection(selection_path,artifacts[0],args.test_filter,args.test_exact)
        args.entry=report['selected']
        timings.update(test_selection_path=str(selection_path),test_selection_sha256=digest,
            test_selection=dict(filter=report['filter'],discovered=report['count'],selected=args.entry,
                skipped_ignored=report['skipped_ignored']),test_selection_verify_seconds=time.perf_counter()-stage)
    if args.allocation_trace:
        from allocation_trace import selected_trace
        stage=time.perf_counter()
        trace=selected_trace(artifacts[0])
        trace.update(tool_key=key,exporter_sha256=tool_manifest['rust-interp-mir-export'])
        print('rust-interp-allocation-trace: '+json.dumps(trace),file=sys.stderr)
        if stats:
            timings.update(allocation_trace=trace,allocation_trace_verify_seconds=time.perf_counter()-stage)
    if args.trap_unsupported_calls:
        stage=time.perf_counter()
        call_path=Path(str(artifacts[0])+'.calls.json')
        if call_path.stat().st_size>8*1024*1024 or artifacts[0].stat().st_size>64*1024*1024:
            raise RuntimeError('unavailable-call report or bytecode exceeds its size bound')
        call_report=json.loads(call_path.read_bytes())
        if (call_report.get('kind')!='unavailable-calls' or call_report.get('schema_version')!=1 or
            call_report.get('trap_unsupported_calls') is not True or call_report.get('strict_frontend') is not True or
            call_report.get('run_try_callbacks',False)!=args.run_try_callbacks or
            call_report.get('artifact_sha256')!=hashlib.sha256(artifacts[0].read_bytes()).hexdigest()):
            raise RuntimeError('Cargo selected an incompatible unavailable-call report; no program was run')
        sites=call_report['unavailable_calls']
        if not isinstance(sites,list) or any(not isinstance(s,dict) or
                any(not isinstance(s.get(k),str) for k in ['kind','name','caller','trap_message']) for s in sites):
            raise RuntimeError('invalid unavailable-call call-site metadata')
        print('rust-interp-unavailable: '+json.dumps(call_report,separators=(',',':')),file=sys.stderr)
        if stats:timings.update(unavailable_calls=sites,call_report_path=str(call_path),
                               call_report_verify_seconds=time.perf_counter()-stage)
    values=args.arguments
    if values and values[0]=='--':values=values[1:]
    vm_command=[str(tools/'rust-interp-vm'),'--engine',args.engine]
    if args.jit_resumable_calls:vm_command.append('--jit-resumable-calls')
    if args.jit_persistent_registers:vm_command.append('--jit-persistent-registers')
    if args.jit_native_calls:vm_command.append('--jit-native-calls')
    if args.jit_native_call_stubs:vm_command.append('--jit-native-call-stubs')
    if args.instruction_limit is not None:vm_command+=['--instruction-limit',str(args.instruction_limit)]
    if args.allocation_limit is not None:vm_command+=['--allocation-limit',str(args.allocation_limit)]
    if args.isolated_batch is not None:
        vm_command+=['--isolated-batch',args.isolated_batch,'--suite-report',str(args.suite_report)]
        if args.suite_workers is not None:vm_command+=['--suite-workers',str(args.suite_workers)]
        if filtered or entry_catalog_supported(tools,key):
            catalog=selected_entry_catalog(artifacts[0],args.entry)
            vm_command+=['--suite-catalog',str(catalog)]
            timings['entry_catalog_path']=str(catalog)
            timings['entry_catalog_sha256']=hashlib.sha256(catalog.read_bytes()).hexdigest()
        timings.update(isolated_batch=args.isolated_batch,suite_report_path=str(args.suite_report),
                       suite_workers_requested=args.suite_workers or 1,
                       runtime_limits_scope='each isolated test')
    if stats:timings['allocation_limit']=args.allocation_limit if args.allocation_limit is not None else 100_000
    if stats:
        # The invocation lock protects the selected sidecar through execution.
        # Record its exact bytes for controlled full-command comparisons. Keep
        # diagnostics bounded even if the VM will reject an oversized artifact.
        stage=time.perf_counter()
        size=artifacts[0].stat().st_size
        digest=hashlib.sha256(artifacts[0].read_bytes()).hexdigest() if size<=64*1024*1024 else None
        timings.update(artifact_path=str(artifacts[0].resolve()),artifact_bytes=size,artifact_sha256=digest,
                       artifact_hash_seconds=time.perf_counter()-stage)
        # Ready means Cargo's selected artifact passed every launcher check and
        # its stats provenance is recorded. VM startup, decoding, validation and guest
        # execution are excluded. Audit-only commands never reach this boundary.
        timings['build_to_ready_seconds']=time.perf_counter()-started
        launcher_cpu=cpu_since(resource.RUSAGE_SELF,launcher_cpu_started)
        children_cpu=cpu_since(resource.RUSAGE_CHILDREN,children_cpu_started)
        timings['build_to_ready_cpu']={
            field:launcher_cpu[field]+children_cpu[field]
            for field in ('user_seconds','system_seconds','total_seconds')}
        timings['build_to_ready_cpu'].update(self=launcher_cpu,children=children_cpu)
    stage=time.perf_counter()
    result=subprocess.run([*vm_command,str(artifacts[0]),*values],env=env)
    timings['execution_seconds']=time.perf_counter()-stage
    if args.suite_report is not None and args.suite_report.is_file():
        if args.suite_report.stat().st_size>16*1024*1024:
            raise RuntimeError('suite report exceeds 16 MiB')
        timings['suite_report_sha256']=hashlib.sha256(args.suite_report.read_bytes()).hexdigest()
        from suite_reports import validate_runtime_limits
        suite=json.loads(args.suite_report.read_bytes())
        validate_runtime_limits(suite,args.instruction_limit,args.allocation_limit)
        timings['suite_workers']=suite.get('workers',1)
        if 'runtime_limits' in suite:timings['runtime_limits']=suite['runtime_limits']
    timings['launcher_seconds']=time.perf_counter()-started
    if stats:print('rust-interp-launch: '+json.dumps(timings),file=sys.stderr)
    return result.returncode


if __name__=='__main__':
    try:sys.exit(main())
    except (RuntimeError,subprocess.CalledProcessError) as error:
        print('interpreter: '+str(error),file=sys.stderr)
        sys.exit(1)
