"""Read only the closed frontend02 evidence; never execute a target module."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

BASE=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/verify_runtime_exporter07_metadata_build02_01.py')
assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='fa4a3e38ae2104f4e633d07dde71c59d845bcc876ef0490ba20e0dccd7f7e967'
spec=importlib.util.spec_from_file_location('_closed_readback_helpers',BASE)
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
raw,read,ref=q.raw,q.read,q.reference
ROOT,X,H=q.ROOT,q.X,q.H
W=X/'.work/hir-options-hash-exporter-frontend-02'
OUT=X/'.work/runtime-exporter07-frontend02-independent-readback-01.json'


def split_check(data,split,allow):
    assert split['raw_bytes']==len(data) and split['raw_sha256']==hashlib.sha256(data).hexdigest()
    compiler=[];offset=0;lines=data.splitlines(keepends=True);assert len(lines)==len(split['segments'])
    for line,segment in zip(lines,split['segments'],strict=True):
        assert line.endswith(b'\n') and not line.endswith(b'\r\n') and segment['start']==offset and segment['end']==offset+len(line) and bytes.fromhex(segment['raw_hex'])==line
        offset+=len(line);body=line[:-1]
        if body.startswith(b'{'):
            obj=json.loads(body);assert segment==dict(start=offset-len(line),end=offset,raw_hex=line.hex(),channel='compiler',diagnostic=obj)
            assert obj['$message_type']=='diagnostic' and obj['level'] in ['error','warning','note','help','failure-note'];compiler.append(line)
        else:
            assert allow and segment['channel']=='telemetry';kind=segment['kind'];text=body.decode();prefix='rust-interp-'+kind+': ';assert text.startswith(prefix)
            if kind=='aggregate-frames':value=json.loads(text[len(prefix):])
            else:
                fields=[token.split('=',1) for token in text[len(prefix):].split()];assert len(dict(fields))==len(fields)
                value={key:token if key=='stage' else float(token) if key in ['seconds','frontend_ms','lowering_ms'] else int(token) for key,token in fields}
            assert value==segment['values']
    assert offset==len(data) and b''.join(compiler).hex()==split['compiler_stderr_hex']


def main():
    packet=H/'packet-01';plan=read(packet/'plan.json','b73d54be6a0d561251bfa522eceb66c5fff21431554699b7d117ce0afa2ac32a');launch=read(packet/'launch.json','5fc9f8acda80fc34f799be9f8fa8502f902af8b40eb0b9b87004b6df1fda4185')
    prior=read(X/'.work/runtime-exporter07-metadata-build02-independent-readback-01.json','816b487143b710e872a98fd9d8ca60ef7faa4f4e43c5f72c853dd5ee5a09a2cc');assert prior['status']=='verified-closed-metadata-and-build'
    ep=ROOT/'.work/runtime-exporter07-frontend-execution-02';outer=X/'.work/experiments/hir-options-hash-exporter-frontend-supervisor-02'
    e=read(ep/'record.json','e33d753b318222575c38a710883c66e904d2804cb99745a6c9f5b532b57c7c97');s=read(outer/'status.json',e['outer_status_sha256']);op=read(outer/'plan.json',e['outer_plan_sha256']);t=read(W/'receipt.json','9e605e76ce386b737681a3bd38b10fc8dfbaa9dfb4af3f9ef05a8f450441d9fa')
    assert (e['parent_pid'],e['pid'],t['pid'])==(46235,47672,47675) and e['status']=='finished' and e['returncode']==e['controller_returncode']==0 and e['supervisor_may_be_live'] is e['controller_may_be_live'] is False
    assert s['status']=='finished' and s['returncode']==0 and s['supervisor_pid']==e['pid'] and s['supervisor_parent_pid']==e['parent_pid'] and s['child_pid']==t['pid'] and t['parent_pid']==e['pid']
    assert e['command']==['/opt/homebrew/bin/python3','-B',str(X/'scripts/supervise_experiment.py'),'--supervise',str(outer/'plan.json')]
    assert s['command']==op['command'] and t['command']==s['command'][2:] and s['plan_sha256']==e['outer_plan_sha256'] and e['cwd']==s['cwd']==t['cwd']==str(X) and e['environment']==launch['environment']
    assert e['started_at']<=e['child_started_at']<=s['started_at']<=s['child_started_at']<=t['started_at']<=t['admitted_at']<=t['finished_at']<=s['finished_at']<=e['finished_at']
    assert raw(ep/'stdout',e['stdout_sha256'])==raw(ep/'stderr',e['stderr_sha256'])==b'';raw(outer/'command.log',s['log_sha256'])
    assert t['status']=='passed' and t['frontend_qualified'] is t['source_restored'] is t['source_unchanged'] is True and t['published'] is t['application_qualified'] is t['performance_measurement'] is False
    assert t['compiler_builds']==t['VM_builds']==t['exporter_builds']==t['guest_executions']==t['signals']==t['retries']==0
    assert t['capacity']==dict(entry_gib=16,stop_gib=9,floor_gib=8) and t['wait_seconds']==600 and t['canonical_lock']==plan['canonical_lock'] and t['entry_free_bytes']>=16*2**30 and t['free_bytes_after']>=8*2**30
    for name in ['result','run_plan','tool_closures']:ref(t[name])
    for stage in ['metadata','build']:
        for name in ['receipt','result']:ref(t[stage][name]);assert t[stage][name]==prior['phase_refs'][stage][name]
    bt=read(t['build']['receipt']['path']);built=read(t['build']['result']['path']);assert bt['finished_at']<=t['started_at']
    for row in built['built_files'].values():ref(row)
    manifest=read(H/'frontend-sources.json',t['frontend_sources_sha256']);assert t['frontend_sources_sha256']==e['frontend_sources_sha256']=='4ece397a765fb4f41dd4f4277bff940a5a4dcb18ca39b8573292b71ee048c0f3' and len(manifest['files'])==20
    for path,digest in manifest['files'].items():raw(path,digest)
    for row in plan['source_materialization'].values():ref(row)
    r=read(t['run_plan']['path']);result=read(t['result']['path']);closures=read(t['tool_closures']['path'])
    assert r['binding']==plan['binding'] and r['capacity']==t['capacity'] and (r['direct_frontend_controls'],r['diagnostic_pairs'],r['fresh_loader_commands'],r['sdk_commands'])==(18,9,6,10)
    rows=r['application_commands'];assert len(rows)==18 and len(r['children'])==len(t['commands'])==34
    env=plan['launch_environment']|{'TMPDIR':str(W/'tmp')+'/'};sdk=[z for z in plan['children'] if z['label'].startswith('sdk-') and not z['label'].startswith('sdk-after-')];assert len(sdk)==5
    expected=[dict(z,environment=env,label='before-'+z['label']) for z in sdk]
    target=X/'.work/hir-options-hash-exporter-target-02';runtime=Path(plan['binding']['runtime']['default_sysroot']);b3=X/'.work/hir-options-hash-compiler-01/beta-sysroot';d2=plan['binding']['build']['executable']['path'];clang=next(z.split('=',1)[1] for z in plan['binding']['build_rustflags'] if z.startswith('-Clinker='))
    names=['rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm']
    for name in names:
        binary=plan['adopted_VM']['binary']['path'] if name==names[-1] else str(target/'release'/name)
        for flag in ['-L','-l']:expected.append(dict(label=name+flag,command=['/usr/bin/otool','-arch','arm64',flag,binary],cwd=str(X),environment=env,expected=[0]))
    specifications=[('exporter-capabilities','native','original',None),('wrapper-roles','native','original',None),('basic-native','native','original',None),('basic-export-explicit-R','basic','original',None),('basic-export-default-R','basic','original',None),('wrapper-export-R','basic','original',None),('wrapper-reject-D','basic','original','wrong-role'),('test-native','native','original',None),('test-export','test','original',None),('test-discovery','list','original',None),('uncalled-type-native','native','type','E0308'),('uncalled-type-export','basic','type','E0308'),('uncalled-borrow-native','native','borrow','E0515'),('uncalled-borrow-export','basic','borrow','E0515'),('restored-native','native','original',None),('restored-export','basic','original',None),('reject-build-sysroot-native','native','original','metadata'),('reject-build-sysroot-export','basic','original','metadata')]
    for row,(name,profile,state,error) in zip(rows,specifications,strict=True):
        assert (row['name'],row['profile'],row['state'],row['error'])==(name,profile,state,error)
        argv=row['argv'];test=name.startswith('test-')
        if name=='exporter-capabilities':want=[str(target/'release'/names[0]),'--rust-interp-capabilities']
        elif name=='wrapper-roles':want=[str(target/'release'/names[1]),'--rust-interp-compiler-roles']
        else:
            exe=str(runtime/'bin/rustc') if profile=='native' else str(target/'release'/(names[1] if name.startswith('wrapper-') else names[0]));want=[exe]
            if name.startswith('wrapper-'):want.append(d2 if error=='wrong-role' else str(runtime/'bin/rustc'))
            want+=['--crate-name','role_test' if test else 'role_basic','--edition=2024','--crate-type','lib' if test else 'bin','-Copt-level=0','-Cdebuginfo=0','-Clinker='+clang,'--error-format=json','--emit=metadata']
            if test:want+=['--test','-Zalways-encode-mir=yes']
            if name!='basic-export-default-R':want+=['--sysroot',str(b3 if error=='metadata' else runtime)]
            want+=[str(W/'fixture'/('test_export.rs' if test else 'basic.rs')),'-o',str(W/'outputs'/(name+'.rmeta'))]
        assert argv==want
        childenv=env|{'RUST_INTERP_COMPILER_ARGV_RECORD_DIR':str(W/'outputs'/(name+'-argv'))}
        if profile!='native':
            childenv.update(RUST_INTERP_EXPORT_CRATE='role_test' if profile in ['test','list'] else 'role_basic',RUST_INTERP_OUTPUT=str(W/'outputs'/(name+('.json' if profile=='list' else '.rbc'))))
            if profile in ['test','list']:childenv['RUST_INTERP_EXPORT_TEST']='1'
            if profile=='list':childenv['RUST_INTERP_LIST_TESTS']='1'
            else:childenv['RUST_INTERP_ENTRY']='selected' if profile=='test' else 'changing_value'
        expected.append(dict(label=name,command=argv,cwd=str(W/'fixture'),environment=childenv,expected=[1,2] if error else [0]))
    expected += [dict(z,environment=env,label='after-'+z['label']) for z in sdk];assert expected==r['children']
    actual={};previous=t['admitted_at']
    for index,(summary,wanted) in enumerate(zip(t['commands'],expected,strict=True)):
        p=W/'commands'/f'{index:03d}'/'receipt.json';assert summary['path']==str(p) and summary['label']==wanted['label'];child=read(p,summary['sha256'])
        assert child['status']=='finished' and child['returncode']==summary['returncode'] and child['returncode'] in wanted['expected'] and child['pid']==summary['pid'] and child['supervisor_pid']==t['pid'] and child['parent_pid']==t['parent_pid']
        assert child['command']==wanted['command'] and child['environment']==wanted['environment'] and child['cwd']==wanted['cwd'] and previous<=child['started_at']<=child['finished_at']<=t['finished_at'];previous=child['finished_at']
        stdout=raw(p.parent/'stdout',child['stdout_sha256']);stderr=raw(p.parent/'stderr',child['stderr_sha256']);actual[wanted['label']]=dict(receipt=child,path=str(p),stdout=stdout,stderr=stderr)
        if wanted.get('expected_stdout_sha256') is not None:assert child['stdout_sha256']==wanted['expected_stdout_sha256'] and not stderr
    originals={n:raw(Path(plan['source_root'])/'tests/fixtures/borrowck-cache'/n) for n in ['basic.rs','test_export.rs']}
    states={'original':originals['basic.rs'],'type':originals['basic.rs']+b'\nfn uncalled_type_error() -> u32 { "wrong" }\n','borrow':originals['basic.rs']+b"\nfn uncalled_borrow_error() -> &'static u32 { let value = 3; &value }\n"}
    for name,data in originals.items():assert raw(W/'fixture'/name)==data
    byname={}
    for row,saved in zip(rows,result['children'],strict=True):
        name=row['name'];outcome=actual[name];assert saved['name']==name and saved['receipt']==outcome['path'] and saved['receipt_sha256']==q.FILES[outcome['path']]['sha256'];ref(saved['source'])
        assert q.RAW[saved['source']['path']]==(originals['test_export.rs'] if name.startswith('test-') else states[row['state']])
        artifact=W/'outputs'/(name+('.json' if row['profile']=='list' else '.rbc'));argvdir=W/'outputs'/(name+'-argv')
        assert b'internal compiler error' not in outcome['stderr']
        if row['profile']=='native' or row['error']=='wrong-role':assert saved['compiler_argv'] is None and list(argvdir.iterdir())==[]
        else:
            ref(saved['compiler_argv']);assert list(argvdir.iterdir())==[Path(saved['compiler_argv']['path'])];fields=q.RAW[saved['compiler_argv']['path']].split(b'\0');assert fields[-1]==b'' and fields[:4]==[b'rust-interp-compiler-argv-v1',b'exported',str(runtime).encode(),str(W/'fixture').encode()]
            args=[v.decode() for v in fields[4:-1]];assert args[0]==str(runtime/'bin/rustc') if name=='wrapper-export-R' else args[0]==str(target/'release'/names[0])
            roots=[args[i+1] for i,v in enumerate(args) if v=='--sysroot']+[v.split('=',1)[1] for v in args if v.startswith('--sysroot=')];assert roots==[str(b3 if row['error']=='metadata' else runtime)]
            assert str(W/'fixture'/('test_export.rs' if name.startswith('test-') else 'basic.rs')) in args
        if row['error']=='wrong-role':assert saved['stderr_separation'] is None and outcome['stderr']==b"compiler executable does not match the exporter's runtime toolchain\n" and not outcome['stdout'] and not artifact.exists()
        else:
            split=saved['stderr_separation'];allow=row['profile'] in ['basic','test'] and not row['error'];split_check(outcome['stderr'],split,allow)
            diagnostics=[v['diagnostic'] for v in split['segments'] if v['channel']=='compiler']
            if row['error']:
                assert not artifact.exists() and any(v['level']=='error' for v in diagnostics)
                if row['error']!='metadata':assert any((v.get('code') or {}).get('code')==row['error'] for v in diagnostics)
            elif name=='exporter-capabilities':
                caps=json.loads(outcome['stdout']);assert not outcome['stderr'] and caps['compiler_roles']==plan['binding'] and caps['compiler_sysroot']==str(runtime) and caps['schema_version']==1 and caps['bytecode_version']==5
            elif name=='wrapper-roles':assert not outcome['stderr'] and json.loads(outcome['stdout'])==plan['binding']
            elif row['profile']=='list':
                v=read(artifact);assert (v['kind'],v['schema_version'],v['strict_frontend'],v['executed'],v['harness'],v['target'],v['count'])==('test-discovery',1,True,False,'libtest','aarch64-apple-darwin',1)
                assert len(v['tests'])==1 and v['tests'][0]['name']=='selected' and v['tests'][0]['status']=='classified' and v['tests'][0]['ordinary_test'] is True;assert raw(Path(row['argv'][-1]+'.tests.json'))==q.RAW[str(artifact)]
            elif row['profile']!='native':
                assert raw(artifact) and raw(Path(row['argv'][-1]+'.rbc'))==q.RAW[str(artifact)];tele=[z for z in split['segments'] if z['channel']=='telemetry'];kinds=[z['kind'] for z in tele];base=['aggregate-frames','scalar-frames','scalar-promotion'];assert kinds in [base+['cfg','export'],base+['forwarding','cfg','export']] and all(z['values']['stage']=='final' for z in tele if z['kind']=='forwarding') and tele[-1]['values']['bytes']==len(q.RAW[str(artifact)])
        if saved['artifact'] is not None:assert saved['artifact']['path']==str(artifact);ref(saved['artifact'])
        else:assert not artifact.exists()
        byname[name]=saved
    pairs=[['basic-native','basic-export-explicit-R'],['test-native','test-export'],['uncalled-type-native','uncalled-type-export'],['uncalled-borrow-native','uncalled-borrow-export'],['restored-native','restored-export'],['reject-build-sysroot-native','reject-build-sysroot-export'],['basic-native','basic-export-default-R'],['basic-native','wrapper-export-R'],['test-native','test-discovery']]
    assert result['comparison_pairs']==pairs
    for a,b in pairs:assert actual[a]['stdout']==actual[b]['stdout'] and byname[a]['stderr_separation']['compiler_stderr_hex']==byname[b]['stderr_separation']['compiler_stderr_hex']
    for name in ['basic-export-default-R','wrapper-export-R','restored-export']:assert q.RAW[byname[name]['artifact']['path']]==q.RAW[byname['basic-export-explicit-R']['artifact']['path']]
    assert (actual['basic-native']['stdout'],actual['basic-native']['stderr'])==(actual['restored-native']['stdout'],actual['restored-native']['stderr'])
    assert result['bytecode_parity'] is result['raw_compiler_diagnostic_parity'] is result['source_restored'] is result['telemetry_losslessly_retained'] is True and result['whole_stderr_parity'] is False and result['guest_executions']==0
    assert [z['name'] for z in closures]==names
    for saved in closures:
        name=saved['name'];binary=plan['adopted_VM']['binary']['path'] if name==names[-1] else built['built_files'][name]['path'];assert saved['binary']['path']==binary
        if name!=names[-1]:assert saved['binary']==built['built_files'][name] and {k:saved[k] for k in ['identity','state']}==built['tool_closures'][name]
        else:assert saved['binary']['sha256']==plan['adopted_VM']['binary']['sha256'] and saved['identity']['libraries']==[]
        for flag in ['-L','-l']:assert saved['fresh_inspections'][flag]==actual[name+flag]['path'] and not actual[name+flag]['stderr']
    # Complete only this closed owned evidence tree; no target/provider walk.
    for parent,dirs,files in os.walk(W,followlinks=False):
        for name in dirs:assert not (Path(parent)/name).is_symlink()
        for name in files:raw(Path(parent)/name)
    for path,row in q.FILES.items():assert q.stamp(Path(path))==row['identity']
    report=dict(status='verified-closed-frontend',observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewer='/root/workspace_capacity',pid=os.getpid(),parent_pid=os.getppid(),checked_files=q.FILES,execution=q.FILES[str(ep/'record.json')],receipt=q.FILES[str(W/'receipt.json')],result=t['result'],run_plan=t['run_plan'],children=34,frontend_controls=18,diagnostic_pairs=9,lossless_separations=17,plain_wrong_role_refusal=1,source_restored=True,provider_payloads_rehashed=0,compiler_calls=0,provider_probes=0,publication_qualified=False,application_qualified=False,performance_qualified=False)
    with OUT.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    raw(OUT);print(json.dumps(q.FILES[str(OUT)],sort_keys=True))


if __name__=='__main__':main()
