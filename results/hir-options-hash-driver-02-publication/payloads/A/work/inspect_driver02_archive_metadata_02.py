"""Read-only schema census; never imports or executes any archive target source."""
import ast,hashlib,json,stat,time
from pathlib import Path
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913'); A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918');W=R/'.work/hir-options-hash-driver-02';H=R/'experiments/hir-options-hash-driver-stage-03'
P=A/'.work/hash-driver02-lossless-publication-scope-02.json';FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns');seen={}
def enc(v):return json.dumps(v,sort_keys=True,allow_nan=False,separators=(',',':'))
def read(p):
 p=Path(p);s=p.lstat();assert p.resolve()==p and stat.S_ISREG(s.st_mode) and s.st_size<=8*2**20
 b=p.read_bytes();t=p.lstat();assert all(getattr(s,'st_'+k)==getattr(t,'st_'+k) for k in FIELDS)
 seen[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'size':len(b),'identity':{k:getattr(s,'st_'+k) for k in FIELDS}}
 return json.loads(b)
p=read(P);rows={r['path']:r for r in p['files']}
def doc(path):
 d=read(path);got=seen[str(path)];expected=rows[str(path)];assert enc(got)==enc({k:expected[k] for k in got});return d
def digest(path):return rows[str(path)]['sha256']
a=doc(R/'.work/hir-options-hash-driver-independent-verification-02.json');t=doc(W/'receipt.json');r=doc(W/'result.json');launch=doc(H/'launch.json');wire=doc(H/'plan.json');hist=p['history']
assert (a['status'],t['status'],r['status'])==('verified','passed-awaiting-independent-audit','hash-driver-observations-passed-awaiting-independent-audit')
assert a['receipt_sha256']==digest(W/'receipt.json')==hist['receipt_sha256']
assert a['result_sha256']==t['result_sha256']==digest(W/'result.json')==hist['result_sha256']
assert a['launch_sha256']==digest(H/'launch.json')
assert a['inputs_sha256']==t['inputs_sha256']==launch['inputs_sha256']==digest(H/'inputs.json')
assert a['snapshot_plan_sha256']==t['snapshot_plan_sha256']==launch['snapshot_plan_sha256']==digest(H/'snapshot-plan.json')
assert launch['plan_sha256']==digest(H/'plan.json')
for key,hkey,v in [('actual_children','current_qualified_children',3),('compilation_count','compilation_count',1),('driver_process_count','driver_process_count',2),('contexts_per_process','contexts_per_process',8),('stdout_records_per_process','records_per_process',9),('historical_failed_compiler_children','historical_failed_compiler_children',1),('total_actual_hash_children','total_actual_hash_children',4)]:assert type(a[key]) is int and a[key]==hist[hkey]==v
for key in ['hash_driver_qualified','full_frozen_byte_rehash','full_provider_inventories','static_and_actual_loaders_verified']:assert a[key] is True
for key in ['application_qualified','performance_measurement','runtime_installation']:assert a[key] is False
assert enc(a['metadata_plan_reference'])==enc(wire['reference'])
for value in [t,r,wire['remainder']]:
 assert enc(a['continuation_controls'])==enc(value['continuation_controls']);assert enc(a['failed_predecessor']['owner'])==enc(value['failed_driver'])
assert (a['failed_predecessor']['actual_children'],a['failed_predecessor']['qualified_children'])==(1,0)
o=R/'.work/experiments/hir-options-hash-driver-supervisor-02';l=R/'.work/hash-driver-launch-execution-02';aw=R/'.work/hash-driver-independent-verification-execution-02';outer=doc(o/'status.json');dispatch=doc(l/'record.json');execution=doc(aw/'record.json');handoff=doc(l/'stdout')
assert outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==t['pid'] and outer['supervisor_pid']==t['parent_pid']
assert outer['command']==launch['command'][6:] and outer['cwd']==str(R) and outer['plan_sha256']==digest(o/'plan.json') and outer['log_sha256']==digest(o/'command.log')
assert outer['child_started_at']<=t['started_at']<=t['admitted_at']<=t['finished_at']<=outer['finished_at']
assert dispatch['status']=='terminal-observed' and dispatch['returncode']==dispatch['launcher_returncode']==0
assert dispatch['outer_sha256']==digest(o/'status.json') and dispatch['launch_sha256']==digest(H/'launch.json') and dispatch['launcher_source_path']==str(H/'launch.py') and dispatch['launcher_source_sha256']==digest(H/'launch.py')
assert dispatch['command']==launch['command'] and dispatch['environment']==launch['environment'] and dispatch['cwd']==str(R) and dispatch['controller_pid']==t['pid']
assert dispatch['started_at']<=dispatch['launcher_finished_at']<=dispatch['finished_at'] and outer['finished_at']<=dispatch['terminal_observed_at']<=dispatch['finished_at']
assert enc(handoff)==enc(dispatch['supervisor_handoff']) and handoff['directory']==str(o) and handoff['supervisor_pid']==dispatch['supervisor_pid']==outer['supervisor_pid']
for stream in ['stdout','stderr']:assert dispatch[stream+'_sha256']==digest(l/stream) and execution[stream+'_sha256']==digest(aw/stream)
assert execution['status']=='finished' and execution['returncode']==0 and execution['report_sha256']==digest(R/'.work/hir-options-hash-driver-independent-verification-02.json')
assert execution['source_sha256']==a['verifier_sha256']==digest(H/'verify.py') and execution['finished_at']<=execution['canonical_released_at']
assert execution['verified_output']==doc(aw/'stdout') and execution['actual_closure']=={str(W/'receipt.json'):digest(W/'receipt.json'),str(W/'result.json'):digest(W/'result.json'),str(o/'status.json'):digest(o/'status.json'),str(l/'record.json'):digest(l/'record.json')}
compiled=doc(W/'compile/receipt.json');assert compiled['status']=='finished' and type(compiled['returncode']) is int and compiled['returncode']==0 and compiled['expected']==[0] and digest(W/'compile/receipt.json')==r['compile_receipt_sha256']
assert t['admitted_at']<=compiled['started_at']<=compiled['finished_at']<=t['finished_at']
previous=compiled['finished_at'];kids=[];child_schema={}
for i,name in enumerate(['compile','serial','parallel']):
 c=doc(W/name/'receipt.json');wanted=wire['remainder']['children'][i];kids.append(c['pid'])
 assert c['supervisor_pid']==t['pid'] and c['parent_pid']==t['parent_pid'] and enc(c['command'])==enc(wanted['argv']) and c['cwd']==wanted['cwd'] and enc(c['environment'])==enc(wanted['environment'])
 for stream in ['stdout','stderr']:assert c[stream+'_sha256']==digest(W/name/stream)
 child_schema[name]={'receipt_sha256':digest(W/name/'receipt.json'),'top_keys':sorted(c),'pid':c['pid'],'returncode_location':'returncode' if i==0 else 'wait.returncode'}
 if i==0:continue
 ref=r['processes'][i-1];wait=c['wait'];proof=doc(W/name/'validated-readback.json')
 assert c['status']=='passed' and c['mode']==ref['mode']==name and c['pid']==ref['pid'] and digest(W/name/'receipt.json')==ref['receipt_sha256']
 assert previous<=c['started_at']<=c['controller_finished_at']<=c['child_finished_at']<=t['finished_at']
 assert c['errors']==[] and c['child_may_be_live'] is c['probe_may_be_live'] is c['real_driver_qualification'] is False
 assert wait['status']=='exited' and type(wait['returncode']) is int and wait['returncode']==0 and wait['reason'] is None and wait['errors']==[] and wait['child_may_be_live'] is False
 assert digest(W/name/'validated-readback.json')==ref['readback_sha256'] and enc(proof)==enc(a['processes'][i-1])
 assert proof['mode']==name and proof['pid']==c['pid'] and proof['status']=='validated-process-readback-only'
 assert proof['observations']['contexts']==8 and proof['observations']['mode']==name and proof['observations']['stdout_sha256']==c['stdout_sha256'] and proof['loader']['stderr_sha256']==c['stderr_sha256']
 assert enc(proof['observations']['terminal'])==enc(dict(contexts=8,parallel=name=='parallel',status='passed'));previous=c['child_finished_at']
assert kids==a['child_pids']
for name,row in a['artifacts'].items():
 if row['kind']=='file':
  path=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/hash-driver-02')/name;assert digest(path)==row['sha256'] and rows[str(path)]['size']==row['stamp'][3]
for role in ['original','derived']:assert digest(a['driver_source_derivation'][role]['path'])==a['driver_source_derivation'][role]['sha256']
ms={};archive_shapes={}
for role,ref in p['prior_archives'].items():
 m,s,v=[doc(ref[k]['path']) for k in ['manifest','summary','independent_audit']]
 assert s['status']=='passed' and v['status']=='verified' and s['archive']['sha256']==ref['sha256'] and s['archive']['bytes']==ref['size']
 assert s['manifest_sha256']==v['manifest_sha256']==ref['manifest']['sha256'] and v['summary_sha256']==ref['summary']['sha256']
 archive_shapes[role]={k:sorted(x) for k,x in [('summary',s),('audit',v)]}
 if role=='failed_driver01':
  assert v['archive']['sha256']==ref['sha256'] and v['archive']['full_gzip_eof_crc'] is v['archive']['full_member_readback'] is True
  assert m['proposal_sha256']==s['proposal_sha256']==v['proposal_sha256'] and v['original_status']=='failed' and v['hash_driver_qualified'] is False and len(m['members'])==v['selected_files']==168
  q,e,ae=[doc(ref[k]['path']) for k in ['receipt','execution_record','audit_execution_record']]
  assert q['status']=='passed' and e['status']==ae['status']=='finished' and e['returncode']==ae['returncode']==0
  assert q['archive_sha256']==ref['sha256'] and q['summary_sha256']==ref['summary']['sha256'] and v['receipt_sha256']==ref['receipt']['sha256'] and v['execution_record_sha256']==ref['execution_record']['sha256'] and ae['result_sha256']==ref['independent_audit']['sha256']
  assert e['finished_at']<=e['canonical_released_at'] and ae['finished_at']<=ae['canonical_released_at'];ms[role]={row['member']:{'bytes':row['size'],'sha256':row['sha256']} for row in m['members']}
 else:
  assert v['archive_sha256']==ref['sha256'] and v['full_gzip_eof_crc'] is v['full_member_readback'] is True and len(ref['git_blob'])==40;ms[role]=m
m=doc(W/'source-snapshots.json');snap=p['snapshots'];stored={k:v for k,v in m['storage'].items() if v['kind']=='stored'};reused={k:v for k,v in m['storage'].items() if v['kind']=='reused'}
assert len(m['files'])==snap['logical_files']==158 and len(m['blobs'])==snap['physical_blobs']==147 and len(stored)==snap['new_stored_blobs']==54 and len(reused)==snap['reused_blobs']==93
for k,v in stored.items():assert rows[v['path']]['sha256']==m['blobs'][k]['sha256'] and rows[v['path']]['size']==m['blobs'][k]['compressed_bytes']
assert sum(m['blobs'][k]['compressed_bytes'] for k in stored)==snap['new_stored_bytes']==690903
refs=snap['reused_archive_associations'];assert len(refs)==len({x['logical_sha256'] for x in refs})==93
associations=[]
for x in refs:
 k=x['logical_sha256'];src=x['source'];assert k in reused and enc(src)==enc(m['reuse'][k]) and src['path']==reused[k]['path'] and src['blob']['logical_sha256']==k and src['blob']['logical_bytes']==x['logical_bytes'];associations.append((x['recovery'],src['path'],src['blob']['sha256'],src['blob']['compressed_bytes']))
compact=doc(H/'inputs.json');base=snap['compact_base_archive_association'];assert enc(compact['file_table_base'])==enc(base['reference']);associations.append((base['archived'],base['reference']['path'],base['reference']['sha256'],compact['files'][base['reference']['path']]['size']))
for ref,path,dig,size in associations:
 assert ref['logical_member']==str(path).lstrip('/') and ref['sha256']==dig and ref['size']==size and ref['archive_sha256']==p['prior_archives'][ref['archive']]['sha256']
 member=ref['logical_member'];chain=[]
 while True:
  assert member not in chain and len(chain)<256;chain.append(member);row=ms[ref['archive']][member];assert row['sha256']==dig and row['bytes']==size
  if 'linkname' not in row:break
  member=row['linkname']
 assert chain==ref['alias_chain'] and member==ref['physical_member']
logical=[dict(source=path,sha256=row['sha256'],size=row['size'],physical_blob=row['path'],storage=m['storage'][row['sha256']]['kind']) for path,row in sorted(m['files'].items())];assert enc(logical)==enc(snap['logical_alias_map'])
ext=snap['external_metadata_plan_recovery'];assert enc(wire['reference'])==enc(ext['reference']) and len(ext['steps'])==2
first,last=ext['steps'];match=[x for x in refs if x['logical_sha256']==ext['reference']['sha256']];assert len(match)==1
assert first['archive']==match[0]['recovery']['archive']=='failed_driver01' and first['member']==first['physical_member']==match[0]['recovery']['physical_member'] and first['sha256']==match[0]['source']['blob']['sha256'] and first['bytes']==match[0]['source']['blob']['compressed_bytes']
assert last==dict(operation='bounded-gzip-full-eof-crc-and-sha256',logical_sha256=ext['reference']['sha256'],logical_bytes=ext['logical_bytes']) and last['logical_bytes']==match[0]['logical_bytes']
assert not p['missing_recovery_references'] and not p['forthcoming_archives']
engine=R/'experiments/hash-driver-success-evidence-02/archive.py';wrapper=engine.with_name('execute.py');old=R/'experiments/hash-driver-success-evidence-01/archive.py'
for source in [engine,wrapper]:ast.parse(source.read_bytes())
olddefs={x.name:ast.dump(x,include_attributes=False) for x in ast.parse(old.read_bytes()).body if isinstance(x,(ast.FunctionDef,ast.ClassDef))};newdefs={x.name:ast.dump(x,include_attributes=False) for x in ast.parse(engine.read_bytes()).body if isinstance(x,(ast.FunctionDef,ast.ClassDef))};changed=[k for k in olddefs if olddefs[k]!=newdefs[k]];assert changed==['validate_history','main'];assert set(newdefs)-set(olddefs)=={'previous_attempt'}
report=dict(status='read-only-saved-metadata-schema-census-passed',scope_sha256=seen[str(P)]['sha256'],engine_sha256=hashlib.sha256(engine.read_bytes()).hexdigest(),wrapper_sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest(),original_engine_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),changed_functions=changed,new_functions=['previous_attempt'],child_receipt_schemas=child_schema,prior_archive_shapes=archive_shapes,read_metadata=seen,physical_reference_equations=93,base_reference_equations=1,external_metadata_inner_gzip_route=True,all_logical_aliases=158,original_archive_attempt_status='failed-before-output',target_imports=0,target_function_calls=0,archive_payload_reads=0,provider_payload_reads=0,interpretation='Independent metadata expressions only; this does not execute or qualify the archive engine, compress data, or substitute for the eventual full archive audit.',finished_at=time.time())
out=A/'.work/hash-driver-success-archive02-schema-census-01.json'
with out.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(report=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),metadata_files=len(seen),metadata_bytes=sum(v['size'] for v in seen.values()),changed_functions=changed)))
