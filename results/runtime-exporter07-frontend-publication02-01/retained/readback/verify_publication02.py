"""Finite saved publication evidence readback; no target imports or probes."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
BASE=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/verify_runtime_exporter07_metadata_build02_01.py')
assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='fa4a3e38ae2104f4e633d07dde71c59d845bcc876ef0490ba20e0dccd7f7e967'
spec=importlib.util.spec_from_file_location('_saved_readback_helpers',BASE);q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
raw,read,ref=q.raw,q.read,q.reference
ROOT,X,H=q.ROOT,q.X,q.H
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
W=X/'.work/hir-options-hash-exporter-publication-02'
OUT=X/'.work/runtime-exporter07-publication02-independent-readback-02.json'
KEY='89cb2751d9e6cfd4a9572dd8ab5405fae7480350bc9198bc5f1bc79fc35bceac'
SOURCES='213729fe32c89414d7872881cc7af9c0e59e4107b3bb87ae66e97bfc783fed40'
OPTIONS=['stable-cgu-partitioning','compiler-argv-record-v1','function-cache-auto','inline-leaves','trap-unsupported-calls','run-try-callbacks','host-proc-macro-opt-v1','entry-catalog','list-tests']
NAMES=['rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm']

def main():
    prior=read(X/'.work/runtime-exporter07-frontend02-independent-readback-01.json','db14cc78030de7b550b0f15855aef6720b056a9b384331976a7a422b2f173be3');assert prior['status']=='verified-closed-frontend'
    mb=read(X/'.work/runtime-exporter07-metadata-build02-independent-readback-01.json','816b487143b710e872a98fd9d8ca60ef7faa4f4e43c5f72c853dd5ee5a09a2cc')
    plan=read(H/'packet-01/plan.json','b73d54be6a0d561251bfa522eceb66c5fff21431554699b7d117ce0afa2ac32a');launch=read(H/'packet-01/launch.json','5fc9f8acda80fc34f799be9f8fa8502f902af8b40eb0b9b87004b6df1fda4185')
    ep=ROOT/'.work/runtime-exporter07-publication-execution-02';outer=X/'.work/experiments/hir-options-hash-exporter-publication-supervisor-02'
    e=read(ep/'record.json','827bb363a927299838e2a692ce5507ce9910bb1cca8f0a65b91664f08fd08847');s=read(outer/'status.json',e['outer_status_sha256']);op=read(outer/'plan.json',e['outer_plan_sha256'])
    t=read(W/'receipt.json','77139a7c2194637ef5efe42bd88dc0e6a75dac3b5cdcb6759c751f703f96cc2e');ref(t['result']);result=read(t['result']['path']);publication=read(W/'publication-plan.json');directory=R/'.work/interpreter-tools'/KEY
    assert (e['parent_pid'],e['pid'],t['pid'])==(13206,14420,14462) and e['status']=='finished' and e['returncode']==e['controller_returncode']==0 and e['supervisor_may_be_live'] is e['controller_may_be_live'] is False
    assert s['status']=='finished' and s['returncode']==0 and s['supervisor_pid']==e['pid'] and s['supervisor_parent_pid']==e['parent_pid'] and s['child_pid']==t['pid'] and t['parent_pid']==e['pid']
    assert e['command']==['/opt/homebrew/bin/python3','-B',str(X/'scripts/supervise_experiment.py'),'--supervise',str(outer/'plan.json')]
    assert s['command']==op['command'] and t['command']==s['command'][2:] and s['plan_sha256']==e['outer_plan_sha256'] and e['cwd']==s['cwd']==t['cwd']==str(X) and e['environment']==launch['environment']
    assert e['started_at']<=e['child_started_at']<=s['started_at']<=s['child_started_at']<=t['started_at']<=t['admitted_at']<=t['finished_at']<=s['finished_at']<=e['finished_at']
    assert raw(ep/'stdout',e['stdout_sha256'])==raw(ep/'stderr',e['stderr_sha256'])==b'';raw(outer/'command.log',s['log_sha256'])
    raw(H/'publication-launch.py',e['source_sha256']);assert e['source_sha256']=='c9a8fd5a578da48ea172a859733c6e913838f67bd82b7b7b8f90a04181e52179'
    assert t['status']=='passed' and t['phase']=='publication' and t['frontend_qualified'] is t['publication'] is True and t['application_qualified'] is t['performance_measurement'] is False
    assert t['compiler_builds']==t['VM_builds']==t['exporter_builds']==t['guest_executions']==t['signals']==t['retries']==0
    assert t['capacity']==dict(entry_gib=16,stop_gib=9,floor_gib=8) and t['wait_seconds']==600 and t['canonical_lock']==plan['canonical_lock'] and t['entry_free_bytes']>=16*2**30 and t['free_bytes_after']>=8*2**30
    flags=['inputs','sources','build-sources','frontend-sources','publication-sources','metadata-receipt','build-receipt','built-tools','frontend-receipt']
    command=[str(H/'publish.py')]
    for flag in flags:command.extend(['--'+flag+'-sha256',t[flag.replace('-','_')+'_sha256']])
    assert t['command']==command and t['inputs_sha256']==launch['inputs']['sha256'] and t['plan_sha256']==launch['plan']['sha256'] and t['publication_sources_sha256']==SOURCES
    for field in ['frontend_sources','publication_sources','metadata_receipt','build_receipt','built_tools','frontend_receipt']:assert e[field+'_sha256']==t[field+'_sha256']
    for name,field,count in [('sources.json','sources',11),('build-sources.json','build_sources',15)]:assert len(read(H/name,t[field+'_sha256'])['files'])==count
    assert t['tool_key']==result['tool_key']==publication['tool_key']==KEY and t['published_directory']==result['directory']==publication['directory']==str(directory) and t['published_tools_sha256']==t['result']['sha256']
    manifest=read(H/'publication-sources.json',SOURCES);front=read(H/'frontend-sources.json',t['frontend_sources_sha256']);assert len(manifest['files'])==25 and len(front['files'])==20
    assert manifest['policy']=='runtime-exporter07-publication-sources-v1' and manifest['frontend_sources']==dict(path=str(H/'frontend-sources.json'),sha256=t['frontend_sources_sha256'])
    extra={str(H/n) for n in ['publish.py','validate_published.py','frontend-sources.json']}|{str(R/'scripts'/n) for n in ['interpreter.py','workspace_cache.py']};assert set(manifest['files'])==set(front['files'])|extra and all(manifest['files'][p]==v for p,v in front['files'].items())
    for path,digest in manifest['files'].items():raw(path,digest)
    for stage in ['metadata','build','frontend']:
        for name,row in t[stage].items():
            if isinstance(row,dict):ref(row)
        terminal=read(t[stage]['receipt']['path']);assert terminal['status']=='passed' and terminal['finished_at']<=t['started_at']
        if stage!='frontend':assert t[stage]['receipt']==mb['phase_refs'][stage]['receipt'] and t[stage]['result']==mb['phase_refs'][stage]['result']
        else:assert t[stage]['receipt']==prior['receipt'] and t[stage]['result']==prior['result'] and t[stage]['run_plan']==prior['run_plan']
    built=read(t['build']['result']['path']);closures=read(t['frontend']['tool_closures']['path'])
    expected=dict(kind='owned-native-runtime-tools-v1',compiler_key=plan['runtime_key'],compiler_sysroot=plan['binding']['runtime']['default_sysroot'],binaries=built['binaries'],compiler_roles=plan['binding'],source=dict(owner=str(X),root=plan['source_root'],checkpoint=plan['source_checkpoint'],files={r['path']:r['sha256'] for r in plan['source_materialization'].values()},metadata=t['metadata']['receipt']),actual_build=dict(receipt=t['build']['receipt'],tools=t['build']['result'],evidence=built['evidence'],recipe=plan['future_build'],strip_failures=0),adopted_VM=plan['adopted_VM'],direct_frontend=t['frontend'],ordinary_launcher=dict(owner=str(R),source_files={p:h for p,h in manifest['files'].items() if Path(p).is_relative_to(R/'scripts')}),guest_execution_qualified=False,benchmark=False)
    assert len(expected['source']['files'])==238 and result['composition']==publication['composition']==expected and hashlib.sha256(json.dumps(expected,sort_keys=True,separators=(',',':')).encode()).hexdigest()==KEY
    assert result['guest_execution'] is result['benchmark'] is False and publication['required_export_options']==OPTIONS
    env=plan['launch_environment']|{'TMPDIR':str(W/'tmp')+'/'}
    commands=[dict(label='published-exporter',command=[str(directory/NAMES[0]),'--rust-interp-capabilities'],cwd=str(X),environment=env|{'DYLD_PRINT_LIBRARIES':'1'},expected=[0]),dict(label='published-wrapper',command=[str(directory/NAMES[1]),'--rust-interp-compiler-roles'],cwd=str(X),environment=env,expected=[0]),dict(label='ordinary-installed-reader',command=['/opt/homebrew/bin/python3','-B',str(H/'validate_published.py'),'--publication-sources-sha256',SOURCES,'--tool-key',KEY,'--runtime-compiler-key',plan['runtime_key']],cwd=str(R),environment=env,expected=[0])]
    assert publication['children']==commands and len(t['commands'])==3
    outcomes=[];previous=t['admitted_at']
    for i,(wanted,saved) in enumerate(zip(commands,t['commands'],strict=True)):
        path=W/'commands'/f'{i:03d}'/'receipt.json';assert saved['path']==str(path) and saved['label']==wanted['label'];child=read(path,saved['sha256'])
        assert child['status']=='finished' and child['returncode']==saved['returncode']==0 and child['pid']==saved['pid'] and child['supervisor_pid']==t['pid'] and child['parent_pid']==t['parent_pid']
        assert child['command']==wanted['command'] and child['environment']==wanted['environment'] and child['cwd']==wanted['cwd'] and previous<=child['started_at']<=child['finished_at']<=t['finished_at'];previous=child['finished_at']
        outcomes.append((child,raw(path.parent/'stdout',child['stdout_sha256']),raw(path.parent/'stderr',child['stderr_sha256'])))
    assert [result[k] for k in ['actual_exporter_probe','actual_wrapper_probe','installed_validation']]==[str(W/'commands'/f'{i:03d}'/'receipt.json') for i in range(3)]
    caps=json.loads(outcomes[0][1]);assert caps=={k:v for k,v in built['capabilities'].items() if k!='runtime_wrapper'} and json.loads(outcomes[1][1])==plan['binding'] and not outcomes[1][2]
    caps['runtime_wrapper']=dict(sha256=built['binaries'][NAMES[1]],compiler_roles=plan['binding']);caps.update(tool_key=KEY,exporter_sha256=built['binaries'][NAMES[0]])
    assert result['capabilities']==caps and set(OPTIONS)<=set(caps['export_options'])
    assert json.loads(outcomes[2][1])==dict(status='passed',tool_key=KEY,runtime_key=plan['runtime_key'],directory=str(directory)) and not outcomes[2][2]
    allowed={str(directory/NAMES[0])}|{v['resolved'] for v in closures[0]['identity']['libraries']};loaded=q.dyld(outcomes[0][2],outcomes[0][0]['pid'],allowed,plan['binding']['runtime_driver']['path'],result['loaded_images'])
    assert set(result['copied'])==set(NAMES) and sorted(p.name for p in directory.iterdir())==sorted(NAMES+['compiler.json','capabilities.json','ready.json']) and stat.S_IMODE(directory.lstat().st_mode)==0o555
    for name in NAMES:
        src=result['copied'][name]['source'];dest=result['copied'][name]['destination'];ref(dest)
        assert dest['path']==str(directory/name) and dest['sha256']==src['sha256']==built['binaries'][name] and dest['bytes']==src['bytes'] and stat.S_IMODE(dest['identity'][2])==0o555 and dest['identity'][:2]!=src['identity'][:2] and q.stamp(Path(src['path']))==src['identity']
        if name!='rust-interp-vm':ref(src);assert src==built['built_files'][name]
        else:assert src['path']==plan['adopted_VM']['binary']['path'] and src['sha256']==plan['adopted_VM']['binary']['sha256']
    for name,value in [('compiler.json',expected),('capabilities.json',caps),('ready.json',built['binaries'])]:assert read(directory/name)==value and stat.S_IMODE(q.FILES[str(directory/name)]['identity'][2])==0o444
    for parent,dirs,files in os.walk(W,followlinks=False):
        for name in dirs:assert not (Path(parent)/name).is_symlink()
        for name in files:raw(Path(parent)/name)
    for path,row in q.FILES.items():assert q.stamp(Path(path))==row['identity']
    report=dict(status='verified-closed-publication', readback_attempt=2, prior_readback_failure='reader01 expected nonexistent outer sources_sha256/build_sources_sha256 keys; KeyError before report creation; actual source manifests and controller pins remain required',reviewer='/root/workspace_capacity',observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),parent_pid=os.getppid(),execution=q.FILES[str(ep/'record.json')],receipt=q.FILES[str(W/'receipt.json')],result=t['result'],tool_key=KEY,directory=str(directory),commands=3,ordinary_installed_reader_passed=True,frontend_qualified=True,application_qualified=False,performance_qualified=False,compiler_calls=0,provider_probes=0,provider_payloads_rehashed=0,adopted_VM_source_check='current exact seven-field stamp and frozen digest; published destination full EOF/SHA',published_members=6,separate_binary_copies=3,loaded_images=loaded,checked_files=q.FILES)
    with OUT.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    raw(OUT);print(json.dumps(q.FILES[str(OUT)],sort_keys=True))

if __name__=='__main__':main()
