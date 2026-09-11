#!/usr/bin/env python3
"""Survey selected existing test bodies without executing them."""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',choices=['pgrust','fre','nushell','ruff'],required=True)
    parser.add_argument('--package',required=True)
    parser.add_argument('--entries',type=Path,required=True,help='JSON names from the native test listing')
    parser.add_argument('--discovery-record',type=Path,required=True,help='native --list command and provenance JSON')
    subset=parser.add_mutually_exclusive_group()
    subset.add_argument('--sample',type=int,help='deterministic name-hash sample; default is the complete list')
    subset.add_argument('--selection',type=Path,help='explicit subset of the verified native listing, for bounded audit batches')
    parser.add_argument('--std-mir',action='store_true')
    parser.add_argument('--guest-mir-opt-level',type=int,choices=range(4),help='explicit MIR optimization for the collected guest programs')
    parser.add_argument('--guest-mir-inline-scale',type=int,choices=[1,2,4,8],help='scale pinned MIR inlining thresholds; requires --guest-mir-opt-level=3')
    parser.add_argument('--inline-leaves',action='store_true',help='apply the experimental bounded leaf inliner to each exported body')
    parser.add_argument('--trap-unsupported-calls',action='store_true',help='retain explicit runtime stops for unavailable direct foreign calls and catch_unwind intrinsics')
    parser.add_argument('--run-try-callbacks',action='store_true',help='run catch_unwind try callbacks; actual unwinding remains unsupported')
    parser.add_argument('--retain-audit-bodies',action='store_true',help='retain bounded, hashed programs for a separate execution survey')
    parser.add_argument('--run-id',default='lowering-audit-'+str(time.time_ns()))
    args=parser.parse_args()
    if args.guest_mir_inline_scale is not None and args.guest_mir_opt_level!=3:
        parser.error('--guest-mir-inline-scale requires --guest-mir-opt-level=3')
    guest_flags=[]
    if args.guest_mir_opt_level is not None:guest_flags.append(f'-Zmir-opt-level={args.guest_mir_opt_level}')
    inline_thresholds=None
    if args.guest_mir_inline_scale is not None:
        inline_thresholds={name:value*args.guest_mir_inline_scale for name,value in [('inline-mir-threshold',50),('inline-mir-hint-threshold',100),('inline-mir-forwarder-threshold',30)]}
        guest_flags += [f'-Z{name}={value}' for name,value in inline_thresholds.items()]
    if Path(args.run_id).name!=args.run_id or args.run_id in ['.','..']:parser.error('invalid run-id')
    discovery=json.loads(args.discovery_record.read_text())
    names=json.loads(args.entries.read_text())
    listed=[line.removesuffix(': test') for line in discovery['stdout'].splitlines() if line.endswith(': test')]
    assert discovery['returncode']==0 and sorted(listed)==sorted(names) and len(set(names))==len(names)
    assert names and all(isinstance(s,str) and s for s in names)
    benchmark=json.loads((ROOT/'results'/discovery['source_benchmark']/'summary.json').read_text())
    assert benchmark['project']==args.project and benchmark['test_source_unchanged']
    revision=json.loads((ROOT/'benchmarks/corpus.json').read_text())['projects'][args.project]['revision']
    assert benchmark['revision']==revision
    source=ROOT/'.work/sources'/args.project
    marker=json.loads((source/'.rust-interp-owned.json').read_text())
    assert marker['owner']==str(ROOT) and marker['revision']==revision
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==revision
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
    lock=(ROOT/'.work/benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    tools,key=checked_tools()
    selected=sorted(names)
    if args.selection is not None:
        selected=json.loads(args.selection.read_text())
        if not isinstance(selected,list) or not selected or not all(isinstance(s,str) for s in selected):
            parser.error('--selection must contain a nonempty JSON list of test names')
        if len(set(selected))!=len(selected) or not set(selected).issubset(names):
            parser.error('--selection contains duplicate or undiscovered names')
        selected=sorted(selected)
    if args.sample is not None:
        if not 1<=args.sample<=len(names):parser.error('sample must be between 1 and the discovered count')
        selected=sorted(sorted(names,key=lambda s:hashlib.sha256(('rust-interp-audit-v1:'+s).encode()).digest())[:args.sample])
    if len(selected)>4096:parser.error('select at most 4096 bodies per audit')
    work=ROOT/'.work/runs'/args.run_id;work.mkdir(parents=True)
    selection=work/'entries.json';selection.write_text(json.dumps(selected,indent=2)+'\n')
    env=os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or name in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']:
            env.pop(name,None)
    env.update(CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
    if guest_flags:env['RUSTFLAGS']=' '.join(guest_flags)
    command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(source/'Cargo.toml'),
             '--package',args.package,'--test-body','--audit-entries',str(selection),
             '--cache-namespace',args.run_id]
    if args.std_mir:command+=['--std-mir']
    if args.inline_leaves:command+=['--inline-leaves']
    if args.trap_unsupported_calls:command+=['--trap-unsupported-calls']
    if args.run_try_callbacks:command+=['--run-try-callbacks']
    if args.retain_audit_bodies:command+=['--retain-audit-bodies']
    start=time.perf_counter()
    # Preserve live compiler/audit diagnostics without buffering away progress.
    with (work/'report.json').open('w') as output, (work/'compiler.log').open('w') as errors:
        p=subprocess.Popen(command,cwd=source,env=env,text=True,stdout=output,stderr=errors)
        record=dict(command=command,pid=p.pid,source_project=args.project,revision=revision,
                    source_benchmark=discovery['source_benchmark'],tool_key=key,inline_leaves=args.inline_leaves,
                    guest_rustflags=guest_flags,rustflags_environment=env.get('RUSTFLAGS'),
                    guest_mir_opt_level=args.guest_mir_opt_level,guest_mir_inline_thresholds=inline_thresholds,
                    trap_unsupported_calls=args.trap_unsupported_calls,run_try_callbacks=args.run_try_callbacks,
                    entries_sha256=hashlib.sha256(selection.read_bytes()).hexdigest(),
                    discovery=discovery)
        (work/'invocation.json').write_text(json.dumps(record,indent=2)+'\n')
        code=p.wait()
    record.update(returncode=code,seconds=time.perf_counter()-start,load=os.getloadavg())
    (work/'invocation.json').write_text(json.dumps(record,indent=2)+'\n')
    assert code==0,(work/'compiler.log').read_text()[-6000:]
    report=json.loads((work/'report.json').read_text())
    assert report['tool_key']==key and report['executed'] is False and report['strict_frontend'] is True
    assert [r['entry'] for r in report['entries']]==selected
    assert ('artifacts' in report)==args.retain_audit_bodies
    assert report.get('inline_leaves',False)==args.inline_leaves
    assert report.get('trap_unsupported_calls',False)==args.trap_unsupported_calls
    assert report.get('run_try_callbacks',False)==args.run_try_callbacks
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==revision
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
    metadata_counts=Counter(r.get('test_metadata',{}).get('status','absent') for r in report['entries'])
    ordinary_lowered=sum(r['status']=='lowered' and r.get('test_metadata',{}).get('ordinary_test') is True for r in report['entries'])
    ignored=sum(r.get('test_metadata',{}).get('ignored') is True for r in report['entries'])
    expected_panics=sum(r.get('test_metadata',{}).get('should_panic') is True for r in report['entries'])
    blockers=Counter()
    for row in report['entries']:
        if row['status']=='blocked':
            prefix,separator,message=row['error'].partition(': ')
            blockers[message if separator else prefix]+=1
    summary=dict(project=args.project,package=args.package,revision=revision,discovered=len(names),
                 sampled=len(selected),sample_method='explicit verified subset' if args.selection is not None else 'all' if args.sample is None else 'SHA256(rust-interp-audit-v1:name)',
                 lowered=report['lowered'],blocked=report['blocked'],executed=False,strict_frontend=True,
                 std_mir=args.std_mir,inline_leaves=args.inline_leaves,tool_key=key,lowering_seconds=report['lowering_seconds'],
                 guest_rustflags=guest_flags,guest_mir_opt_level=args.guest_mir_opt_level,
                 guest_mir_inline_scale=args.guest_mir_inline_scale,guest_mir_inline_thresholds=inline_thresholds,
                 compilation_invocation=dict(path=str((work/'invocation.json').relative_to(ROOT)),sha256=hashlib.sha256((work/'invocation.json').read_bytes()).hexdigest()),
                 trap_unsupported_calls=args.trap_unsupported_calls,run_try_callbacks=args.run_try_callbacks,
                 command_seconds=record['seconds'],raw=str(work.relative_to(ROOT)),
                 retained_artifacts=report.get('artifacts'),artifact_provenance=report.get('artifact_provenance'),
                 test_metadata_counts=dict(metadata_counts),ordinary_lowered=ordinary_lowered,ignored=ignored,expected_panics=expected_panics,
                 artifact_retention_seconds=report.get('artifact_retention_seconds'),
                 blockers=[dict(error=message,count=count) for message,count in blockers.most_common()],
                 scripts_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'scripts/interpreter.py']},
                 vm_sha256=hashlib.sha256((tools/'rust-interp-vm').read_bytes()).hexdigest(),
                 exporter_sha256=hashlib.sha256((tools/'rust-interp-mir-export').read_bytes()).hexdigest())
    out=ROOT/'results'/args.run_id;out.mkdir()
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    text=f'# Test-body lowering audit: {args.project} / {args.package}\n\n'
    text+=f'{report["lowered"]} of {len(selected)} selected bodies lowered; {report["blocked"]} were blocked. The native binary listed {len(names)} test bodies. '
    text+='Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.\n\n'
    if guest_flags:text+='Guest MIR flags: `'+ ' '.join(guest_flags)+'`. The exact collection invocation and RUSTFLAGS are recorded and hashed; native controls retain their ordinary Cargo profile.\n\n'
    if args.inline_leaves:text+='The experimental bounded bytecode leaf inliner ran on each lowered body. Execution evidence for default bytecode does not establish that these transformed artifacts pass.\n\n'
    if args.run_try_callbacks:text+='Try callbacks execute on the normal-return path. Actual panic, unwinding and VM faults fail execution; no caught-panic result is synthesized.\n\n'
    elif args.trap_unsupported_calls:text+='Unavailable foreign and catch_unwind intrinsic calls remain explicit terminal traps. A retained body may still stop at one during execution; call-site metadata is recorded per body.\n\n'
    if args.retain_audit_bodies:
        pack=report['artifacts']
        text+=f"Retained {pack['files']} independently validated programs ({pack['bytes']:,} serialized bytes). Each file has a writer-recorded SHA-256 checked by the launcher; the manifest belongs to Cargo's exact selected metadata sidecar. These programs have not been executed. Test-harness metadata still needs inspection before a broad execution survey.\n\n"
    if args.retain_audit_bodies and metadata_counts.get('classified'):
        text+=f"Compiler test metadata identifies {ordinary_lowered} lowered ordinary tests, {ignored} ignored tests, and {expected_panics} expected-panic tests. Lowering and harness classifications are separate; none is counted as executed.\n\n"
    text+='| First lowering blocker | Bodies |\n|---|---:|\n'
    text+=''.join(f'| {message.replace("|","&#124;").replace(chr(10)," ")} | {count} |\n' for message,count in blockers.most_common())
    (out/'summary.md').write_text(text)
    print(out/'summary.md')


if __name__=='__main__':main()
