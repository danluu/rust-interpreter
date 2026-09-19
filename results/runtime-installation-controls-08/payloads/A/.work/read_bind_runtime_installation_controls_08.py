"""Read the closed preparation; bind only its actual packet/source constants."""
from pathlib import Path
import ast,difflib,hashlib,json,stat,time
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
H=R/'experiments/runtime-installation-controls-08';E=R/'.work/runtime-installation-controls-preparation-execution-08';D=A/'.work/runtime-installation-controls08-source-derivation-01'
B=A/'.work/runtime-installation-controls08-actual-packet-binding-01'
assert not B.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def stamp(p):
 s=Path(p).lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
v=read(D/'handoff.json');assert sha(D/'handoff.json')=='ca2e9912b72026d3af605d0fbfe69558127e20b4a877df37534ad7514fee47f5'
for name,row in v['sources'].items():assert sha(name)==row['sha256']
r=read(E/'record.json');f=read(H/'inputs.json');launch=read(H/'launch.json');raw=read(E/'stdout')
assert r['status']=='finished' and r['returncode']==0 and r['parent_pid']==55826 and r['pid']==56541
assert r['supervisor_parent_pid']==80990 and r['observation_errors']==[] and r['disk_samples']==[]
assert r['started_at']<=r['admitted_at']<=r['child_started_at']<=r['finished_at']<=r['canonical_released_at']
assert r['command']==[f['python'],'-B',str(H/'prepare.py')] and r['cwd']==str(R) and r['environment']==f['environment']
assert r['capacity']==dict(entry_gib=10,stop_gib=9,floor_gib=8)==f['capacity']==launch['capacity']
assert r['free_bytes_before']>=10*2**30 and r['free_bytes_after']>=9*2**30
assert r['canonical_lock']=='/Users/danluu/dev/rust-interp/.work/benchmark.lock' and r['wait_seconds']==600
for s in ['stdout','stderr']:assert r[s+'_sha256']==sha(E/s)
assert not (E/'stderr').read_bytes()
assert r['execution_source_sha256']==sha(R/'.work/prepare_runtime_installation_controls_08_once.py')==sha(E/'source/execution.py')
assert r['owned_source_sha256']==sha(E/'source/owned_stage.py')
for name,digest in r['source_sha256'].items():assert digest==sha(H/name)==sha(E/'source'/name)
assert set(r['source_sha256'])=={'run.py','child.py','prepare.py'}
assert raw==r['prepared_packet']==dict(status='prepared-unrun',controls=48,files=48,bytes=1952550,inputs_sha256=sha(H/'inputs.json'),launch_sha256=sha(H/'launch.json'))
assert sha(H/'inputs.json')=='cbf17e5449b6562ddc780f41a3202f5cf3a25515cf83a04b10f9c830520b9715'
assert sha(H/'launch.json')=='66c6af2a949c8afc78afc04acfd954786b51810b250b41605b767b7b26c50a54'
assert f['status']=='prepared-unrun' and f['owner']==str(R) and f['expected_names']==v['expected_names'] and len(set(f['expected_names']))==48
assert set(f['files'])==set(v['prospective_files']) and f['routes']==v['prospective_routes'] and len(f['routes'])==49
current={}
for name,row in f['files'].items():
 p=Path(name);before=stamp(p);assert p.resolve(strict=True)==p and stat.S_ISREG(before[2])
 assert before==row['stamp'] and before[3]==v['prospective_files'][name]['size'] and sha(p)==row['sha256'] and stamp(p)==before
 current[name]=dict(sha256=row['sha256'],stamp=before)
assert sum(row['stamp'][3] for row in current.values())==1952550
for name,resolved in f['routes'].items():assert str(Path(name).resolve(strict=True))==resolved
assert launch['status']=='prepared-unrun-awaiting-review' and launch['controls']==48 and launch['expected_children']==1
assert launch['inputs_sha256']==sha(H/'inputs.json') and launch['helper_sha256']==sha(H/'run.py')
assert launch['environment']==f['environment'] and launch['owner']==str(R) and launch['bounds']==f['bounds']
assert launch['command']==[f['python'],'-B',str(R/'scripts/supervise_experiment.py'),'--run-id','runtime-installation-controls-supervisor-08','--',f['python'],'-B',str(H/'run.py'),'--inputs-sha256',sha(H/'inputs.json')]
assert f['command']==[f['python'],'-B',str(H/'child.py')]
assert f['bounds']==dict(child_alarm_seconds=120,child_cpu_seconds=60,maximum_file_bytes=256*1024,maximum_writable_names=256,maximum_directory_names=2048,maximum_cumulative_child_file_payload_bytes=258*256*1024,maximum_retained_stage_file_bytes=2*2**20)
assert all(f[k]==0 for k in ['compiler_calls','provider_probes','B3_compositions'])
assert {str(p.relative_to(E)) for p in E.rglob('*') if p.is_file()}=={'record.json','stdout','stderr','source/run.py','source/child.py','source/prepare.py','source/execution.py','source/owned_stage.py'}
assert {p.name for p in H.iterdir()}=={'run.py','prepare.py','child.py','inputs.json','launch.json'}
for p in [R/'.work/runtime-installation-controls-08',R/'.work/experiments/runtime-installation-controls-supervisor-08',R/'.work/runtime-installation-controls-launcher-08',R/'.work/runtime-installation-controls-independent-verification-08.json',R/'.work/runtime-installation-controls-verification-execution-08']:
 assert not p.exists() and not p.is_symlink()
B.mkdir();bindings={}
def bind(path,values):
 old=path.read_text();tree=ast.parse(old);lines=old.splitlines(True);found=set()
 for node in tree.body:
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in values:
   name=node.targets[0].id;assert ast.literal_eval(node.value) is None and node.lineno==node.end_lineno
   lines[node.lineno-1]=name+' = '+repr(values[name])+'\n';found.add(name)
 assert found==set(values)
 new=''.join(lines)
 def drop(text):
  tr=ast.parse(text);tr.body=[n for n in tr.body if not(isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values)]
  return ast.dump(tr,include_attributes=False)
 assert drop(old)==drop(new)
 before=B/(path.name+'.unbound.py');before.write_text(old)
 path.write_text(new)
 diff=B/(path.name+'.packet-binding.diff');diff.write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=str(before),tofile=str(path))))
 bindings[str(path)]=dict(before=str(before),before_sha256=sha(before),sha256=sha(path),diff=str(diff),diff_sha256=sha(diff),constants=values,nonbinding_AST_unchanged=True)
launch_script=R/'.work/launch_runtime_installation_controls_08_bounded.py';verify_script=R/'.work/verify_runtime_installation_controls_08.py';audit_script=R/'.work/execute_runtime_installation_controls_audit_08.py'
bind(launch_script,{'EXPECTED':sha(H/'launch.json')})
bind(verify_script,{'EXPECTED_LAUNCH':sha(H/'launch.json'),'EXPECTED_INPUTS':sha(H/'inputs.json'),'EXPECTED_DISPATCHER':sha(launch_script),'EXPECTED_INPUT_BYTES':1952550,'EXPECTED_INPUT_FILES':48})
bind(audit_script,{'EXPECTED':sha(verify_script)})
report=dict(status='prepared-packet-readback-and-source-binding-passed',finished_at=time.time(),actual_preparation=dict(path=str(E/'record.json'),sha256=sha(E/'record.json'),parent_pid=r['parent_pid'],child_pid=r['pid'],returncode=0,admitted_at=r['admitted_at'],finished_at=r['finished_at'],canonical_released_at=r['canonical_released_at']),tool_observation=dict(exit_code=0,chunk_id='b5e4e3',session_id=None),packet=raw,routes=f['routes'],current_files=current,bindings=bindings,controlled_execution=False,provider_calls=0,production_preparation=False,installation=False)
(B/'readback.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(report=str(B/'readback.json'),report_sha256=sha(B/'readback.json'),preparation_sha256=sha(E/'record.json'),bindings=bindings),indent=2))
