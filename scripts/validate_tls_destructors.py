#!/usr/bin/env python3
"""Qualify real TLS destructor ordering and normal callbacks with a selected VM."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from interpreter import ROOT, installed_tools, TOOLCHAIN
from std_mir import checked_std_mir


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--tool-key',required=True)
    options=['jit_native_calls','jit_native_call_stubs','jit_persistent_registers','jit_resumable_calls']
    for option in options:parser.add_argument('--'+option.replace('_','-'),action='store_true')
    args=parser.parse_args()
    if not __debug__ or sys.flags.optimize:parser.error('TLS qualification requires enabled Python assertions')
    if Path(args.run_id).name!=args.run_id or args.run_id in ['.','..']:parser.error('invalid run ID')
    if args.jit_native_call_stubs and not args.jit_native_calls:parser.error('native Call stubs require native calls')
    if args.jit_resumable_calls and (args.jit_native_calls or args.jit_native_call_stubs):
        parser.error('resumable calls exclude native tree/stub calls')
    runtime_options={name:getattr(args,name) for name in options}
    vm_flags=['--'+name.replace('_','-') for name,enabled in runtime_options.items() if enabled]
    root=ROOT
    lock=(root/'.work/benchmark.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    work=root/'.work'/args.run_id;work.mkdir(exist_ok=False)
    tools,key=installed_tools(args.tool_key);std,_,std_key,_=checked_std_mir(TOOLCHAIN)
    source=root/'tests/tls_destructor_fixture.rs'
    paths=[source,Path(__file__).resolve(),root/'scripts/interpreter.py',root/'scripts/std_mir.py',root/'Cargo.toml',root/'Cargo.lock',tools/'ready.json',tools/'rust-interp-vm',tools/'rust-interp-mir-export']
    paths+=sorted((root/'crates').rglob('*.rs'))
    frozen={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (work/'plan.json').write_text(json.dumps(dict(tool_key=key,runtime_options=runtime_options,
        std_mir_key=std_key,frozen_inputs=frozen,expected_commands=245,performance_measurement=False),indent=2)+'\n')
    env=os.environ.copy()
    for n in list(env):
     if n.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) or n in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','CARGO_INCREMENTAL']:env.pop(n)
    records=[];artifacts=[]
    def run(label,cmd,extra=None,ok=True):
     assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
     cmd=list(map(str,cmd))
     if cmd[:3]==[str(tools/'rust-interp-vm'),'--engine','jit']:cmd=[*cmd[:3],*vm_flags,*cmd[3:]]
     child_env=env|dict(extra or {})
     if cmd[0]==str(tools/'rust-interp-vm'):child_env['RUST_INTERP_VM_STATS']='1'
     p=subprocess.Popen(cmd,cwd=root,env=child_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
     identity=dict(pid=p.pid,parent_pid=os.getpid(),command=cmd,cwd=str(root),started_at=time.time(),status='running')
     (work/'active-command.json').write_text(json.dumps(identity));out,err=p.communicate();identity.update(status='finished',returncode=p.returncode,finished_at=time.time())
     (work/'active-command.json').write_text(json.dumps(identity));row=dict(label=label,identity=identity,stdout=out,stderr=err);records.append(row)
     with (work/'commands.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
     assert (p.returncode==0)==ok and 'internal compiler error' not in err,row
     return row
    seeds=[0,1,7,255,2**63,2**64-1]
    for mode,flags in [('mir0',['-Zmir-opt-level=0']),('mir3',['-Zmir-opt-level=3']),('optimized',['-O'])]:
     native=work/('native-'+mode);run('build-native-'+mode,['rustc','+'+TOOLCHAIN,source,'--edition=2024',*flags,'-o',native])
     expected={name:[run('native-'+mode+'-'+name,[native,name,s])['stdout'].strip() for s in seeds] for name in ['tls','try']}
     assert run('native-caught-panic-'+mode,[native,'panic',0])['stdout'].strip()=='91'
     test=work/('native-tests-'+mode);run('build-native-tests-'+mode,['rustc','+'+TOOLCHAIN,source,'--edition=2024','--test',*flags,'-o',test])
     row=run('native-tests-'+mode,[test,'--test-threads=1']);assert '4 passed; 0 failed' in row['stdout']
     for inline in [False,True]:
      for name,entry in [('tls','rust_interp_entry'),('try','try_entry'),('panic','panic_entry'),('batch',None)]:
       label=f'{mode}-inline{int(inline)}-{name}';output=work/(label+'.rbc')
       extra={'RUST_INTERP_OUTPUT':str(output),'RUST_INTERP_TRAP_UNSUPPORTED_CALLS':'1','RUST_INTERP_RUN_TRY_CALLBACKS':'1'}
       if inline:extra['RUST_INTERP_INLINE_LEAVES']='1'
       if name=='batch':extra.update(RUST_INTERP_ENTRIES=json.dumps(['a_first','b_after_first','c_after_second','d_final_test']),RUST_INTERP_EXPORT_TEST='1')
       else:extra['RUST_INTERP_ENTRY']=entry
       cmd=[tools/'rust-interp-mir-export',source,'--crate-name','tls_destructor_fixture','--edition=2024','--emit=metadata','--sysroot',std,*flags,'-o',work/(label+'.rmeta')]
       if name=='batch':cmd+=['--test']
       run('export-'+label,cmd,extra)
       call_report=json.loads(Path(str(output)+'.calls.json').read_text());assert call_report['run_try_callbacks'] and call_report['strict_frontend']
       assert call_report['artifact_sha256']==hashlib.sha256(output.read_bytes()).hexdigest()
       artifacts.append(dict(configuration=label,path=str(output.relative_to(root)),sha256=call_report['artifact_sha256'],unavailable_calls=call_report['unavailable_calls']))
       cases=[([], '0')] if name=='batch' else [([0],None)] if name=='panic' else [([s],want) for s,want in zip(seeds,expected[name])]
       for values,want in cases:
        for engine in ['interpreter','jit']:
         row=run(label+'-'+engine,[tools/'rust-interp-vm','--engine',engine,output,*values],ok=want is not None)
         if want is None:assert row['stdout'].strip()=='' and 'guest trap:' in row['stderr'],row
         else:assert row['stdout'].strip()==want,row
       print('PASS',label,flush=True)
    # Separate opt-in preserves the pre-existing strict rejection and terminal trap.
    for mode,extra in [('strict',{}),('trap',{'RUST_INTERP_TRAP_UNSUPPORTED_CALLS':'1'}),('missing-trap',{'RUST_INTERP_RUN_TRY_CALLBACKS':'1'})]:
     output=work/(mode+'.rbc');extra|={'RUST_INTERP_ENTRY':'try_entry','RUST_INTERP_OUTPUT':str(output)}
     row=run('option-'+mode,[tools/'rust-interp-mir-export',source,'--edition=2024','--emit=metadata','--sysroot',std,'-o',work/(mode+'.rmeta')],extra,ok=mode=='trap')
     if mode=='strict':assert 'unsupported intrinsic catch_unwind' in row['stderr']
     elif mode=='missing-trap':assert 'requires explicit unavailable-call trapping' in row['stderr']
     else:
      for engine in ['interpreter','jit']:
       row=run('trap-preserved-'+engine,[tools/'rust-interp-vm','--engine',engine,output,0],ok=False)
       assert 'unavailable intrinsic call: "catch_unwind"' in row['stderr']
    # Verify emitted runtime identity and actual transitions, not just the option request.
    vm_counts={'interpreter':0,'jit':0};native_calls=0;native_returns=0
    for row in records:
     cmd=row['identity']['command']
     if cmd[0]!=str(tools/'rust-interp-vm'):continue
     engine=cmd[cmd.index('--engine')+1];vm_counts[engine]+=1
     for option,enabled in runtime_options.items():
      flag='--'+option.replace('_','-')
      if cmd.count(flag)!=int(engine=='jit' and enabled):raise RuntimeError('TLS runtime option mismatch')
     if engine=='jit' and row['identity']['returncode']==0:
      stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',row['stderr'])}
      if 'jit_entries' not in stats:raise RuntimeError('missing TLS JIT statistics')
      native_calls+=stats.get('jit_resumable_calls',0);native_returns+=stats.get('jit_resumable_returns',0)
    if runtime_options['jit_resumable_calls'] and (native_calls==0 or native_returns==0):
     raise RuntimeError('resumable TLS transitions did not execute')
    if len(records)!=245 or vm_counts!={'interpreter':85,'jit':85}:
     raise RuntimeError('TLS qualification command matrix changed')
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in frozen.items()):
     raise RuntimeError('TLS qualification inputs changed')
    summary=dict(status='passed',tool_key=key,tool_binaries=json.loads((tools/'ready.json').read_text()),commands=len(records),configurations=24,artifacts=artifacts,frozen_inputs=frozen,std_mir_key=std_key,strict_frontend=True,real_std_destructor_list_tested=True,actual_unwinding_supported=False,runtime_options=runtime_options,vm_counts=vm_counts,resumable_calls=native_calls,resumable_returns=native_returns,performance_measurement=False)
    (work/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    out=root/'results'/args.run_id;out.mkdir(exist_ok=False)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('TLS_DESTRUCTOR_PASS',len(records),key,flush=True)


if __name__=='__main__':
    main()
