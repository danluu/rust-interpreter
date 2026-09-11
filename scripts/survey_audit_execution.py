#!/usr/bin/env python3
"""Compare retained ordinary tests with fresh native processes; no speedup claim."""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from interpreter import ROOT, TOOLCHAIN, installed_tools, validate_audit_pack, unavailable_call_failure


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection',type=Path,required=True,help='corpus audit summary.json')
    parser.add_argument('--entries',type=Path,help='optional JSON list selecting bodies from the verified collection')
    parser.add_argument('--vm-tool-key',help='optional immutable tool build whose VM executes the retained bytecode')
    parser.add_argument('--native-control-provenance',type=Path,help='reuse a verified native control from a previous batch at the same source pin and toolchain; fresh processes still run each test')
    parser.add_argument('--instruction-limit',type=int,default=100_000_000)
    parser.add_argument('--allocation-limit',type=int,help='explicit live-allocation allowance; omitted preserves the VM default')
    parser.add_argument('--jit-native-calls',action='store_true')
    parser.add_argument('--jit-native-call-stubs',action='store_true')
    parser.add_argument('--jit-persistent-registers',action='store_true')
    parser.add_argument('--jit-resumable-calls',action='store_true')
    parser.add_argument('--run-id',default='audit-execution-'+str(time.time_ns()))
    args=parser.parse_args()
    if not __debug__ or sys.flags.optimize:parser.error('execution surveys require enabled Python assertions')
    if args.instruction_limit<=0:parser.error('instruction limit must be positive')
    if args.allocation_limit is not None and not 0<=args.allocation_limit<2**64:
        parser.error('allocation limit must fit an unsigned 64-bit count')
    if args.jit_native_call_stubs and not args.jit_native_calls:
        parser.error('native Call stubs require native calls')
    if args.jit_resumable_calls and (args.jit_native_calls or args.jit_native_call_stubs):
        parser.error('resumable calls exclude native tree/stub calls')
    runtime_options={name:getattr(args,name) for name in
        ['jit_native_calls','jit_native_call_stubs','jit_persistent_registers','jit_resumable_calls']}
    vm_flags=['--'+name.replace('_','-') for name,enabled in runtime_options.items() if enabled]
    if args.allocation_limit is not None:vm_flags+=['--allocation-limit',str(args.allocation_limit)]
    if Path(args.run_id).name!=args.run_id or args.run_id in ['.','..']:parser.error('invalid run id')
    lock=(ROOT/'.work/benchmark.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    collection=json.loads(args.collection.read_text())
    report_path=ROOT/collection['raw']/'report.json'
    report=json.loads(report_path.read_text())
    guest_flags=collection.get('guest_rustflags',[])
    assert isinstance(guest_flags,list) and all(isinstance(flag,str) for flag in guest_flags)
    compilation_invocation=collection.get('compilation_invocation')
    invocation_path=None
    if compilation_invocation is not None:
        invocation_path=ROOT/collection['raw']/'invocation.json'
        assert compilation_invocation['path']==str(invocation_path.relative_to(ROOT))
        assert hashlib.sha256(invocation_path.read_bytes()).hexdigest()==compilation_invocation['sha256']
        invocation=json.loads(invocation_path.read_text())
        assert invocation['returncode']==0 and invocation['tool_key']==collection['tool_key']
        assert invocation['guest_rustflags']==guest_flags
        assert invocation['rustflags_environment']==(' '.join(guest_flags) if guest_flags else None)
    elif guest_flags:
        raise RuntimeError('MIR-tuned collection lacks a hashed compilation invocation')
    if report.get('trap_unsupported_externs') or collection.get('trap_unsupported_externs'):
        raise RuntimeError('foreign-only experimental collections require their archived matching replay driver')
    selected_rows=report['entries']
    if args.entries is not None:
        names=json.loads(args.entries.read_text())
        if not isinstance(names,list) or not names or not all(isinstance(n,str) and n for n in names):
            parser.error('--entries must contain a nonempty JSON list of names')
        if len(set(names))!=len(names) or not set(names).issubset(r['entry'] for r in selected_rows):
            parser.error('--entries contains duplicates or names absent from the collection')
        selected_rows=[r for r in selected_rows if r['entry'] in set(names)]
    assert report['executed'] is False and report['strict_frontend'] is True
    assert report['tool_key']==collection['tool_key']
    assert report.get('inline_leaves',False)==collection.get('inline_leaves',False)
    assert report.get('trap_unsupported_calls',False)==collection.get('trap_unsupported_calls',False)
    assert report.get('run_try_callbacks',False)==collection.get('run_try_callbacks',False)
    collection_tools,collection_key=installed_tools(report['tool_key'])
    collection_manifest=json.loads((collection_tools/'ready.json').read_text())
    assert collection_manifest==report['artifact_provenance']['tool_binaries']
    tools,key=installed_tools(args.vm_tool_key or collection_key)
    manifest=json.loads((tools/'ready.json').read_text())
    pack=Path(report['artifacts']['directory']);workspace=pack.parent
    assert workspace.parent==ROOT/'.work/interpreter-workspaces'/collection_key
    assert len(workspace.name)==24 and all(c in '0123456789abcdef' for c in workspace.name)
    invocation=(workspace/'invocation.lock').open('a');fcntl.flock(invocation,fcntl.LOCK_EX|fcntl.LOCK_NB)
    sidecar=Path(report['artifact_provenance']['audit_path'])
    assert sidecar.resolve().is_relative_to(workspace/'target')
    assert hashlib.sha256(sidecar.read_bytes()).hexdigest()==report['artifact_provenance']['audit_sha256']
    validate_audit_pack(report,workspace)
    project=collection['project'];revision=collection['revision'];source=ROOT/'.work/sources'/project
    corpus=json.loads((ROOT/'benchmarks/corpus.json').read_text())
    assert corpus['projects'][project]['revision']==revision
    owner=json.loads((source/'.rust-interp-owned.json').read_text())
    assert owner['owner']==str(ROOT) and owner['revision']==revision
    def source_check():
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==revision
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
    source_check()
    work=ROOT/'.work/runs'/args.run_id;work.mkdir(parents=True)
    inputs=[ROOT/'Cargo.toml',ROOT/'Cargo.lock',Path(__file__).resolve(),ROOT/'scripts/interpreter.py',
            report_path,sidecar,args.collection.resolve(),tools/'ready.json',tools/'rust-interp-vm']
    if args.entries is not None:inputs.append(args.entries.resolve())
    if invocation_path is not None:inputs.append(invocation_path)
    if args.native_control_provenance is not None:inputs.append(args.native_control_provenance.resolve())
    for folder in ['bytecode','mir-export']:
        inputs+=sorted((ROOT/'crates'/folder).rglob('*.rs'));inputs.append(ROOT/'crates'/folder/'Cargo.toml')
    frozen={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    def freeze():
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
    env=os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or name in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']:
            env.pop(name,None)
    env['CARGO_TERM_COLOR']='never'
    commands=[];results=[]
    def run(label,command,cwd,vm=False):
        command=list(map(str,command));command_env=dict(env)
        if vm:command_env['RUST_INTERP_VM_STATS']='1'
        start=time.perf_counter()
        p=subprocess.Popen(command,cwd=cwd,env=command_env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        identity=dict(pid=p.pid,parent_pid=os.getpid(),command=command,cwd=str(cwd),started_at=time.time(),status='running')
        (work/'active-command.json').write_text(json.dumps(identity))
        stdout,stderr=p.communicate();seconds=time.perf_counter()-start
        identity.update(status='finished',returncode=p.returncode);(work/'active-command.json').write_text(json.dumps(identity))
        row=dict(label=label,command=command,cwd=str(cwd),pid=p.pid,returncode=p.returncode,
                 stdout=stdout,stderr=stderr,seconds=seconds)
        commands.append(row)
        with (work/'commands.jsonl').open('a') as log:log.write(json.dumps(row)+'\n')
        return row
    try:
        metadata=run('cargo-metadata',['cargo','+'+TOOLCHAIN,'metadata','--manifest-path',source/'Cargo.toml',
                     '--no-deps','--format-version','1','--offline','--locked'],source)
        assert metadata['returncode']==0,metadata
        packages=[p for p in json.loads(metadata['stdout'])['packages'] if p['name']==collection['package']]
        assert len(packages)==1
        package=packages[0];cwd=Path(package['manifest_path']).parent
        assert cwd.resolve().is_relative_to(source)
        reused_native=None
        if args.native_control_provenance is None:
            native=run('build-native',['cargo','+'+TOOLCHAIN,'test','--manifest-path',source/'Cargo.toml',
                       '--package',collection['package'],'--lib','--no-run','--locked','--offline','--jobs','4',
                       '--target-dir',work/'native','--message-format=json-render-diagnostics'],source)
            assert native['returncode']==0,native['stderr'][-5000:]
            events=[json.loads(line) for line in native['stdout'].splitlines()]
            binaries=[Path(e['executable']) for e in events if e.get('reason')=='compiler-artifact'
                      and e.get('package_id')==package['id'] and e.get('executable')]
            assert len(binaries)==1
            binary=binaries[0];binary_digest=hashlib.sha256(binary.read_bytes()).hexdigest()
        else:
            control_path=args.native_control_provenance.resolve()
            assert control_path.is_relative_to(ROOT/'.work/runs')
            control=json.loads(control_path.read_text())
            assert control['project']==project and control['revision']==revision
            assert control['package']==package['name'] and control['toolchain']==TOOLCHAIN
            assert Path(control['cwd']).resolve()==cwd.resolve()
            binary=Path(control['binary']).resolve()
            assert binary.is_relative_to(ROOT/'.work/runs') and binary.is_file()
            binary_digest=hashlib.sha256(binary.read_bytes()).hexdigest()
            assert binary_digest==control['sha256']
            native={'seconds':0.0}
            reused_native=dict(path=str(control_path.relative_to(ROOT)),sha256=hashlib.sha256(control_path.read_bytes()).hexdigest())
        listed=run('native-list',[binary,'--list'],cwd);assert listed['returncode']==0
        names=[line.removesuffix(': test') for line in listed['stdout'].splitlines() if line.endswith(': test')]
        assert len(set(names))==len(names)
        assert set(r['entry'] for r in report['entries']).issubset(names)
        if reused_native is not None:assert names==control['test_names']
        (work/'native-provenance.json').write_text(json.dumps(dict(binary=str(binary),sha256=binary_digest,
            project=project,revision=revision,package=package['name'],cwd=str(cwd),test_names=names,
            toolchain=TOOLCHAIN,reused_from=reused_native),indent=2)+'\n')
        for index,row in enumerate(selected_rows):
            freeze();entry=row['entry'];meta=row.get('test_metadata',{})
            result=dict(entry=entry,lowering_status=row['status'],test_metadata=meta,
                        unavailable_calls=row.get('unavailable_calls',[]))
            if row['status']!='lowered':
                result.update(status='lowering-blocked',error=row.get('error'))
            elif meta.get('status')!='classified' or meta.get('harness')!='libtest':
                result['status']='unclassified-harness'
            elif meta.get('ignored') is True:
                result['status']='ignored'
            elif meta.get('should_panic') is True:
                result['status']='expected-panic-unsupported'
            else:
                assert meta['ordinary_test'] is True and meta['native_name']==entry
                a=run('native:'+entry,[binary,'--exact',entry,'--test-threads','1','--color','never'],cwd)
                result['native']=a
                if a['returncode']!=0:
                    result['status']='native-failure'
                elif not re.search(r'test result: ok\. 1 passed; 0 failed; 0 ignored;',a['stdout']):
                    result['status']='native-harness-mismatch'
                else:
                    artifact=pack/row['artifact']['file']
                    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==row['artifact']['sha256']
                    b=run('jit:'+entry,[tools/'rust-interp-vm','--engine','jit','--instruction-limit',str(args.instruction_limit),*vm_flags,artifact],cwd,vm=True)
                    result.update(jit=b,artifact_sha256=row['artifact']['sha256'])
                    if b['returncode']==0 and b['stdout'].strip()=='0':result['status']='passed'
                    elif b['returncode']!=0 and unavailable_call_failure(b['stderr'],row.get('unavailable_calls',[])):
                        result['status']='runtime-unsupported-call'
                        result['encountered_call']=unavailable_call_failure(b['stderr'],row['unavailable_calls'])
                    elif 'instruction limit exceeded' in b['stderr']:result['status']='instruction-limited'
                    elif 'memory limit exceeded' in b['stderr']:result['status']='memory-limited'
                    elif b['returncode']<0:result['status']='jit-crash'
                    else:result['status']='jit-failure'
                    result['jit_stats']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',b['stderr'])}
            results.append(result);(work/'results.json').write_text(json.dumps(results,indent=2)+'\n')
            if (index+1)%20==0 or result['status'] not in ['passed','lowering-blocked','ignored']:
                print(index+1,len(selected_rows),entry,result['status'],flush=True)
        freeze();assert hashlib.sha256(binary.read_bytes()).hexdigest()==binary_digest
        counts=dict(Counter(r['status'] for r in results))
        summary=dict(kind='execution-coverage-survey',project=project,package=package['name'],revision=revision,
            collection=str(args.collection.resolve().relative_to(ROOT)),tool_key=key,tool_binaries=manifest,
            inline_leaves=report.get('inline_leaves',False),
            guest_rustflags=guest_flags,compilation_invocation=compilation_invocation,
            trap_unsupported_calls=report.get('trap_unsupported_calls',False),run_try_callbacks=report.get('run_try_callbacks',False),
            collection_tool_key=collection_key,collection_tool_binaries=collection_manifest,
            instruction_limit=args.instruction_limit,engine='jit',counts=counts,selected=len(results),
            allocation_limit=args.allocation_limit,runtime_options=runtime_options,
            available_in_collection=len(report['entries']),
            selection=None if args.entries is None else dict(path=str(args.entries.resolve()),sha256=hashlib.sha256(args.entries.read_bytes()).hexdigest()),
            native_build_seconds=native['seconds'],native_binary_sha256=binary_digest,
            reused_native_control=reused_native,
            native_process_seconds=sum(r['native']['seconds'] for r in results if 'native' in r),
            jit_process_seconds=sum(r['jit']['seconds'] for r in results if 'jit' in r),
            raw=str(work.relative_to(ROOT)),frozen_inputs=frozen,performance_qualification=False,
            limitations=['Separate fresh processes per ordinary test; blocked and unsupported harness cases do not execute.',
                'A native failure does not count as an engine comparison; instruction and memory limits are separate outcomes.',
                'Passing a body with unavailable-call metadata means its tested path avoided those calls; it does not implement those platform functions.',
                'This is a coverage survey, not a complete suite or a production-edit speedup comparison.'])
        output=ROOT/'results'/args.run_id;output.mkdir()
        (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        lines=[f"# Execution coverage: {project} / {package['name']}",'',
            f"Compared retained ordinary test bodies with a {'hash-verified native control reused from the preceding batch' if reused_native else 'freshly built native control'} at the pinned source revision. Each test runs in a fresh process. Custom execution used the JIT with a {args.instruction_limit:,}-instruction limit per body. Original sources and tests were preserved.",'',
            f"Collection tool: `{collection_key}`. Execution tool: `{key}`. The original artifact pack and its collection provenance are verified independently of the selected VM.",'',
            '| Outcome | Bodies |','|---|---:|']
        lines += [f'| {name} | {count} |' for name,count in sorted(counts.items())]
        if vm_flags:lines += ['', 'Explicit VM options: `'+' '.join(vm_flags)+'`. Per-body runtime counters are retained in the raw results.']
        if guest_flags:lines += ['', 'Collected guest MIR flags: `'+ ' '.join(guest_flags)+'`. Their recorded compilation invocation is hash-verified; native controls use their ordinary Cargo profile.']
        lines += ['',*summary['limitations'],'',f"Native build: {native['seconds']:.3f} s. Native and JIT process totals are retained in JSON as diagnostics; they are not end-to-end production-edit measurements."]
        (output/'summary.md').write_text('\n'.join(lines)+'\n')
        print(json.dumps(summary,indent=2),flush=True)
    finally:
        source_check()
        (work/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')


if __name__=='__main__':main()
