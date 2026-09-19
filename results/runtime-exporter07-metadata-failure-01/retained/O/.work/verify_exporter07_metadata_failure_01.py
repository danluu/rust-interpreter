"""Read only closed metadata01 receipts/raw and their finite source associations."""
import hashlib,json,os,re,stat,time
from pathlib import Path
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
H=ROOT/'experiments/runtime-exporter-after-installation07-01'
W=X/'.work/hir-options-hash-exporter-metadata-01'
E=ROOT/'.work/runtime-exporter07-metadata-execution-01'
S=X/'.work/experiments/hir-options-hash-exporter-metadata-supervisor-01'
seen={}
def read_bytes(p,digest=None):
 p=Path(p);s=p.lstat();assert p.resolve(strict=True)==p and stat.S_ISREG(s.st_mode) and s.st_size<=8*2**20
 b=p.read_bytes();assert p.lstat()==s
 row={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'identity':[s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]}
 assert digest is None or row['sha256']==digest
 assert seen.setdefault(str(p),row)==row
 return b
def read(p,digest=None):return json.loads(read_bytes(p,digest))
def main():
 started=time.time();rr=ROOT/'.work/runtime-exporter07-metadata-failure-root-readback-01.json'
 root=read(rr,'f25d33f45341be8f1cac0c26c543c6be99e970c2692c31281226f343ba48e303')
 phase=read(W/'receipt.json','15becee37c4dbb2972833352065bdcd9e76dcbcc0b4418e4997e7d68e5c3d5fe')
 parent=read(E/'record.json',root['parent_execution_sha256']);outer=read(S/'status.json',root['outer_status_sha256'])
 op=read(S/'plan.json',outer['plan_sha256']);plan=read(H/'packet-01/plan.json',phase['plan_sha256'])
 launch=read(H/'packet-01/launch.json',parent['launch_sha256']);inputs=read(H/'packet-01/inputs.json',phase['inputs_sha256'])
 assert parent['status']==outer['status']=='finished' and parent['returncode']==0 and outer['returncode']==parent['controller_returncode']==1
 assert parent['supervisor_may_be_live'] is parent['controller_may_be_live'] is False
 assert parent['pid']==outer['supervisor_pid']==phase['parent_pid']==44849 and outer['child_pid']==phase['pid']==44851
 assert parent['parent_pid']==outer['supervisor_parent_pid']==42711
 assert parent['signals']==parent['retries']==phase['signals']==phase['retries']==0
 assert parent['environment']==launch['environment']==plan['launch_environment']
 assert parent['command']==['/opt/homebrew/bin/python3','-B',str(X/'scripts/supervise_experiment.py'),'--supervise',str(S/'plan.json')]
 assert op['owner']==outer['owner']==parent['cwd']==outer['cwd']==phase['cwd']==str(X)
 assert op['command']==outer['command']==launch['command'] and phase['command']==op['command'][2:]
 assert op['supervisor_sha256']=='019608c2d37fcecb55ed436fafe3753498bfe11e1a1805a46ae49a59c7d6a1b2'
 assert phase['status']=='failed' and phase['error']=="RuntimeError('unrecognized actual dyld observation')" and 'result' not in phase
 assert phase['compiler_builds']==phase['exporter_builds']==phase['VM_builds']==phase['guest_executions']==0
 assert phase['application_qualified'] is phase['performance_measurement'] is False
 for n in ('stdout','stderr'):assert read_bytes(E/n,parent[n+'_sha256'])==b''
 log=read_bytes(S/'command.log',outer['log_sha256']);assert b"RuntimeError: unrecognized actual dyld observation" in log
 assert b'loaded_libraries' in log and b'self.metadata()' in log
 times=[parent['started_at'],parent['child_started_at'],outer['started_at'],phase['started_at'],phase['admitted_at'],phase['finished_at'],outer['finished_at'],parent['finished_at']]
 assert times==sorted(times) and all(type(t) in (int,float) and 0<t<=time.time() for t in times)
 sources=read(H/'sources.json',phase['sources_sha256']);assert sources['files']==inputs['files'] and len(inputs['files'])==10
 for name,digest in inputs['files'].items():read_bytes(name,digest);assert seen[name]==plan['files'][name]
 read_bytes(H/'execute.py',parent['source_sha256']);read_bytes(X/'scripts/supervise_experiment.py',op['supervisor_sha256'])
 assert len(phase['commands'])==len(plan['children'])==len(root['children'])==36
 children=[];dyld=[];last=phase['admitted_at'];expected_files={'receipt.json'}
 for i,(ref,wanted,checked) in enumerate(zip(phase['commands'],plan['children'],root['children'],strict=True)):
  p=W/'commands'/f'{i:03d}'/'receipt.json';assert ref['path']==str(p) and ref['label']==wanted['label']==checked['label']
  child=read(p,ref['sha256']);assert ref['sha256']==checked['receipt_sha256']
  assert child['status']=='finished' and child['returncode']==ref['returncode']==0 and child['pid']==ref['pid']==checked['pid']
  assert child['command']==wanted['command'] and child['environment']==wanted['environment'] and child['cwd']==wanted['cwd']
  assert child['supervisor_pid']==phase['pid'] and child['parent_pid']==phase['parent_pid']
  assert last<=child['started_at']<=child['finished_at']<=phase['finished_at'];last=child['finished_at']
  raw={n:read_bytes(p.parent/n,child[n+'_sha256']) for n in ('stdout','stderr')}
  if i not in (25,27):assert raw['stderr']==b''
  if wanted['expected_stdout_sha256'] is not None:assert child['stdout_sha256']==wanted['expected_stdout_sha256']
  if i in (25,27):
   role='build' if i==25 else 'runtime';assert raw['stdout'].decode()==plan['binding'][role]['verbose_version']
   loads=[];transitions=[];byname={};active=set()
   for line in raw['stderr'].decode().splitlines():
    match=re.fullmatch(r'dyld\[(\d+)\]: <([0-9A-Fa-f-]{36})> (/.+)',line)
    if match:
     assert int(match[1])==child['pid'];path=match[3];name=Path(path).name;assert name not in byname
     byname[name]=path;active.add(name);loads.append({'path':path,'uuid':match[2]})
     if not path.startswith(('/usr/lib/','/System/Library/')):assert path in plan['files']
    else:
     match=re.fullmatch(r'dyld\[(\d+)\]: move loaded to delayed: (.+)',line)
     assert match is not None and int(match[1])==child['pid'] and match[2] in active
     active.remove(match[2]);transitions.append(match[2])
   assert len(loads)==548 and len(transitions)==157
   driver=Path(plan['binding']['runtime_driver']['path']).name if role=='runtime' else next(n for n in byname if n.startswith('librustc_driver-'))
   assert driver in active
   dyld.append({'index':i,'pid':child['pid'],'sha256':child['stderr_sha256'],'uuid_load_lines':len(loads),'loaded_to_delayed_lines':len(transitions),'unknown_lines':0,'all_transition_names_prior_unique_loaded':True,'selected_driver_active_at_end':True})
  if i in (26,28):assert raw['stdout'].decode()==plan['binding']['build' if i==26 else 'runtime']['default_sysroot']+'\n'
  if i==30:
   metadata=json.loads(raw['stdout']);assert metadata['workspace_root']==str(X/'.work/hir-options-hash-exporter-source-01') and metadata['target_directory']==plan['metadata_target'] and len(metadata['packages'])==30
  children.append({'index':i,'label':wanted['label'],'receipt':seen[str(p)],'pid':child['pid'],'returncode':0,'stdout':seen[str(p.parent/'stdout')],'stderr':seen[str(p.parent/'stderr')]})
  expected_files|={str((p.parent/n).relative_to(W)) for n in ('receipt.json','stdout','stderr')}
 actual={str(p.relative_to(W)) for p in W.rglob('*') if p.is_file()};assert actual==expected_files and len(actual)==109
 assert {p.name for p in E.iterdir()}=={'record.json','stdout','stderr'} and {p.name for p in S.iterdir()}=={'plan.json','status.json','command.log'}
 assert not (W/'planned.json').exists() and not (W/'cargo-metadata.json').exists()
 for name,row in seen.items():
  p=Path(name);s=p.lstat();assert [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]==row['identity']
 result={'status':'independently-verified-closed-metadata01-failure','pid':os.getpid(),'parent_pid':os.getppid(),'started_at':started,'finished_at':time.time(),'root_readback':seen[str(rr)],'parent_execution':seen[str(E/'record.json')],'outer':seen[str(S/'status.json')],'phase':seen[str(W/'receipt.json')],'all36_children_closed0':True,'children':children,'dyld_streams':dyld,'failure':'Strict original loader stderr parser rejects ordinary move-loaded-to-delayed telemetry after all36 native metadata children have closed0.','metadata_qualification':False,'performance_claim':False,'builds':0,'planned_result_absent':True,'source_current_unchanged':True,'files_read':list(seen.values()),'target_imports':False,'provider_payload_walk':False,'workload_execution':False}
 dest=O/'.work/runtime-exporter07-metadata-failure-independent-readback-01.json'
 with dest.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
 print(json.dumps({'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'bytes':dest.stat().st_size,'children':36},sort_keys=True))
if __name__=='__main__':main()
