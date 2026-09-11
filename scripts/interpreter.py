#!/usr/bin/env python3
"""Check a Cargo library and run supported functions in the custom VM.

Example: interpreter.py --manifest-path PROJECT/Cargo.toml --package hashfn
         --entry murmurhash32 -- 123

Repeat --entry with --test-body to run several zero-argument functions returning
unit or Result<(), E> in one command. Ordinary function inputs and output are integer bit
patterns. This prototype provides a guest allocator, but no general Rust main
or OS runtime. Test batches stop at the first failure.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
TOOLCHAIN='nightly-2026-09-08'


def installed_tools(key):
    """Load an immutable local tool build without rebuilding current sources."""
    if not isinstance(key,str) or len(key)!=64 or any(c not in '0123456789abcdef' for c in key):
        raise RuntimeError('tool key must contain 64 lowercase hexadecimal characters')
    directory=ROOT/'.work/interpreter-tools'/key
    try:
        manifest=json.loads((directory/'ready.json').read_text())
    except (OSError,ValueError) as error:
        raise RuntimeError('cannot read installed tool build '+key+': '+str(error)) from error
    if not isinstance(manifest,dict) or set(manifest)!={'rust-interp-vm','rust-interp-mir-export'}:
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
        for p in inputs:h.update(str(p.relative_to(ROOT)).encode()+b'\0'+p.read_bytes())
        return h.hexdigest()
    key=fingerprint()
    directory=ROOT/'.work/interpreter-tools'/key
    if not (directory/'ready.json').exists():
        subprocess.run(['cargo','+'+TOOLCHAIN,'build','--release','--locked','--offline','--jobs','4','-p','rust-interp-bytecode','-p','rust-interp-mir-export','--target-dir',str(ROOT/'.work/interpreter-build')],cwd=ROOT,check=True)
        if fingerprint()!=key:raise RuntimeError('compiler sources changed while building')
        directory.mkdir(parents=True,exist_ok=True)
        manifest={}
        for name in ['rust-interp-vm','rust-interp-mir-export']:
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


def main():
    started=time.perf_counter()
    timings={}
    stats=os.environ.get('RUST_INTERP_LAUNCH_STATS')=='1'
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-path',type=Path,default=Path('Cargo.toml'))
    parser.add_argument('--package',required=True)
    parser.add_argument('--jobs',type=int,default=4,help='Cargo build jobs (1..256)')
    selected=parser.add_mutually_exclusive_group(required=True)
    selected.add_argument('--entry',action='append',help='function to run; repeat for a batch of unit test bodies')
    selected.add_argument('--audit-entries',type=Path,help='JSON list of test body names to check for lowering support, without executing them')
    parser.add_argument('--retain-audit-bodies',action='store_true',help='retain bounded, hashed programs from a lowering audit for separate execution diagnostics')
    parser.add_argument('--features')
    parser.add_argument('--no-default-features',action='store_true')
    parser.add_argument('--instruction-limit',type=int,help='maximum VM instructions (default: 100000000)')
    parser.add_argument('--allocation-limit',type=int,help='maximum live guest allocations, independent of byte memory (0..1000000; default: 100000)')
    parser.add_argument('--engine',choices=['interpreter','jit'],default='interpreter')
    parser.add_argument('--jit-native-calls',action='store_true',help='experimental complete native call trees; requires --engine=jit')
    parser.add_argument('--tool-key',help='use an already installed immutable tool build, for reproducing or comparing runs')
    parser.add_argument('--cache-namespace',default='',help='use an independent artifact cache, for reproducible cold-build comparisons')
    parser.add_argument('--inline-leaves',action='store_true',help='experimental bounded bytecode leaf inlining at export; intended for JIT comparisons')
    parser.add_argument('--trap-unsupported-calls',action='store_true',help='experimental: stop execution at unavailable direct foreign calls and catch_unwind intrinsics instead of rejecting their export')
    parser.add_argument('--run-try-callbacks',action='store_true',help='experimental: execute catch_unwind try callbacks; actual panic/unwinding still fails; requires --trap-unsupported-calls')
    parser.add_argument('--std-mir',action='store_true',help='use reusable standard-library metadata with complete MIR')
    parser.add_argument('--timings',action='store_true',help='write Cargo\'s compilation timing report for this command')
    parser.add_argument('--test-body',action='store_true',help='invoke a function from the library unit-test target directly; libtest attributes are not implemented')
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if args.jit_native_calls and args.engine != 'jit':parser.error('--jit-native-calls requires --engine=jit')
    if not 1<=args.jobs<=256:parser.error('--jobs must be in 1..256')
    if args.run_try_callbacks and not args.trap_unsupported_calls:
        parser.error('--run-try-callbacks requires --trap-unsupported-calls')
    auditing=args.audit_entries is not None
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
    if not 1<=len(args.entry)<=maximum or len(set(args.entry))!=len(args.entry):
        parser.error(f'select between 1 and {maximum} distinct entries')
    if len(args.entry)>1 and (not args.test_body or [v for v in args.arguments if v!='--']):
        parser.error('multiple entries require --test-body and no function arguments')
    manifest=args.manifest_path.resolve()
    stage=time.perf_counter()
    tools,key=installed_tools(args.tool_key) if args.tool_key is not None else checked_tools()
    if args.inline_leaves:require_export_option(tools,key,'inline-leaves')
    if args.trap_unsupported_calls:require_export_option(tools,key,'trap-unsupported-calls')
    if args.run_try_callbacks:require_export_option(tools,key,'run-try-callbacks')
    timings['tools_seconds']=time.perf_counter()-stage
    if stats:timings.update(tool_key=key,engine=args.engine,jit_native_calls=args.jit_native_calls,inline_leaves=args.inline_leaves,trap_unsupported_calls=args.trap_unsupported_calls,run_try_callbacks=args.run_try_callbacks)
    std=None
    if args.std_mir:
        from std_mir import checked_std_mir
        stage=time.perf_counter()
        std=checked_std_mir(TOOLCHAIN)
        timings['std_mir_seconds']=time.perf_counter()-stage
    selection=args.entry[0] if len(args.entry)==1 else json.dumps(args.entry,separators=(',',':'))
    identity_input='shared-entries-v1\0'+str(manifest)+'\0'+args.package+'\0'+str(args.test_body)
    if std:identity_input+='\0std-mir:'+std[2]
    if args.cache_namespace:identity_input+='\0'+args.cache_namespace
    identity=hashlib.sha256(identity_input.encode()).hexdigest()[:24]
    work=ROOT/'.work/interpreter-workspaces'/key/identity
    work.mkdir(parents=True,exist_ok=True)
    # Keep the selected metadata sidecar stable through execution when two
    # launcher invocations select different entries in this target directory.
    invocation_lock=(work/'invocation.lock').open('a')
    fcntl.flock(invocation_lock,fcntl.LOCK_EX)
    env=os.environ.copy()
    # Preserve Cargo's feature/profile/rustflag behavior. Tool-specific outputs
    # and compiler selection are isolated from native build directories.
    for name in list(env):
        if name.startswith('RUST_INTERP_'):env.pop(name)
    env.update(RUSTC_WRAPPER=str(tools/'rust-interp-mir-export'),RUSTC_WORKSPACE_WRAPPER='',
               RUST_INTERP_EXPORT_PACKAGE=args.package,
               RUST_INTERP_OUTPUT=str(work/('audit.json' if auditing else 'program.rbc')),RUST_INTERP_EXPORT_TEST='1' if args.test_body else '0',CARGO_TARGET_DIR=str(work/'target'))
    if args.inline_leaves:env['RUST_INTERP_INLINE_LEAVES']='1'
    if args.trap_unsupported_calls:env['RUST_INTERP_TRAP_UNSUPPORTED_CALLS']='1'
    if args.run_try_callbacks:env['RUST_INTERP_RUN_TRY_CALLBACKS']='1'
    if auditing:
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
    command=['cargo','+'+TOOLCHAIN,'check','--manifest-path',str(manifest),'--package',args.package,'--lib','--locked','--offline','--jobs',str(args.jobs),'--message-format=json-render-diagnostics']
    if args.features:command+=['--features',args.features]
    if args.no_default_features:command+=['--no-default-features']
    # On the pinned Cargo, this selects Check { test: true } for exactly
    # --lib. --lib --tests instead adds both the ordinary library and every
    # test target, and required a separate metadata query for disambiguation.
    if args.test_body:command+=['--profile','test']
    if std:command+=['--target',std[1]]
    if args.timings:command+=['--timings']
    stage=time.perf_counter()
    result=subprocess.run(command,cwd=manifest.parent,env=env,stdout=subprocess.PIPE,text=True)
    timings['cargo_seconds']=time.perf_counter()-stage
    if result.returncode:return result.returncode
    artifacts=[]
    suffix='.audit.json' if auditing else '.rbc'
    for line in result.stdout.splitlines():
        try:
            event=json.loads(line)
            if event.get('reason')=='compiler-artifact' and bool(event['profile']['test'])==args.test_body:
                artifacts.extend(Path(p+suffix) for p in event['filenames'] if p.endswith('.rmeta') and Path(p+suffix).is_file())
        except json.JSONDecodeError:pass
    if len(artifacts)!=1 or not artifacts[0].is_file():raise RuntimeError('Cargo did not select a valid '+('audit report' if auditing else 'bytecode sidecar')+'; no program was run')
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
    if args.jit_native_calls:vm_command.append('--jit-native-calls')
    if args.instruction_limit is not None:vm_command+=['--instruction-limit',str(args.instruction_limit)]
    if args.allocation_limit is not None:vm_command+=['--allocation-limit',str(args.allocation_limit)]
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
    stage=time.perf_counter()
    result=subprocess.run([*vm_command,str(artifacts[0]),*values],env=env)
    timings['execution_seconds']=time.perf_counter()-stage
    timings['launcher_seconds']=time.perf_counter()-started
    if stats:print('rust-interp-launch: '+json.dumps(timings),file=sys.stderr)
    return result.returncode


if __name__=='__main__':
    try:sys.exit(main())
    except (RuntimeError,subprocess.CalledProcessError) as error:
        print('interpreter: '+str(error),file=sys.stderr)
        sys.exit(1)
