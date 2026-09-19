"""Bounded read-only saved N overlay01 qualification; no project imports or child calls."""
from pathlib import Path
import hashlib,json,os,re,stat,time
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
S=R/'experiments/proc-macro-arena-n-overlay-01';E=R/'results/proc-macro-arena-n-overlay-01';W=R/'.work/proc-macro-arena-n-overlay-01'
REPORT=A/'.work/proc-macro-arena-n-overlay01-independent-readback-01.json'
assert not REPORT.exists()
CHECKED={}
def stamp(s):return {k:getattr(s,'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}
def file(p):
 p=Path(p);before=stamp(p.lstat());assert p.resolve(strict=True)==p and stat.S_ISREG(before['mode']),p
 h=hashlib.sha256();size=0
 with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as f:
  assert stamp(os.fstat(f.fileno()))==before,p
  for block in iter(lambda:f.read(2**20),b''):h.update(block);size+=len(block)
  assert stamp(os.fstat(f.fileno()))==before,p
 assert stamp(p.lstat())==before and size==before['size'],p
 row=dict(bytes=size,sha256=h.hexdigest(),identity=before)
 if str(p) in CHECKED:assert CHECKED[str(p)]==row,p
 CHECKED[str(p)]=row;return row

def raw(p):
 row=file(p);assert row['bytes']<=4*2**20,p
 data=Path(p).read_bytes();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
 assert stamp(Path(p).lstat())==row['identity'];return data

def doc(p):return json.loads(raw(p))
def ref(p):return dict(path=str(p),sha256=file(p)['sha256'])
def tree(root):
 result={'.':stamp(root.lstat())}
 for p in sorted(root.rglob('*')):
  s=stamp(p.lstat());assert stat.S_ISREG(s['mode']) or stat.S_ISDIR(s['mode']) or stat.S_ISLNK(s['mode']),p
  result[str(p.relative_to(root))]=s
 return result

trees={str(p):tree(p) for p in [S,E,W]}
plan=doc(S/'plan.json');execution=doc(E/'execution.json');result=doc(E/'result.json')
assert file(E/'result.json')['sha256']=='129e8818d8a2505139a147fb0f3c2d6593a049c0e8c7cfc9989798caf10a3a42'
assert file(S/'plan.json')['sha256']==file(E/'plan.json')['sha256']==execution['plan_sha256']=='2a47bdd12f42c197438b11a9114e76551ed037875b2e39d773c987c9606b2356'
assert file(S/'run_once.py')['sha256']==file(E/'run_once.py')['sha256']=='ad49eae76dc504915b3320eea66f6f28eadc68a32ffe7cb183b751921e51be8f'
assert result['status']==execution['status']=='passed' and result['execution_sha256']==file(E/'execution.json')['sha256']=='fb525fb1ee530f706e2eef523c9db351db925e40222fd78cd0431981ec012893'
assert result['children']==execution['children']==len(execution['command_records'])==len(plan['commands'])==20
assert execution['started_at']<=execution['admitted_at']<=execution['finished_at']<=execution['parent_lock_closed_at']<=execution['canonical_released_at']
assert execution['signals']==[] and execution['retries']==0 and execution['free_bytes_before']>=16*2**30 and execution['free_bytes_after']>=9*2**30
assert execution['parent_pid']==24718 and execution['overlay_links']==104 and execution['overlay_owned_files']==8
for k in ['compiler_distribution_qualified','runtime_composition_qualified','benchmark']:assert result[k] is False and execution[k] is False
for k in ['holdout_qualified','builtin_quote_optimized']:assert result[k] is False
for k in ['compiler_server_unchanged','default_discovery_qualified','real_N_external_client_integration','inputs_unchanged','complete_N_runtime_unchanged','overlays_unchanged']:assert result[k] is True
assert result['macro_dylib_builds']==2 and result['caller_cases_per_arm']==9
before=doc(E/'inputs-before.json');after=doc(E/'inputs-after.json');assert before==after and len(before)==execution['input_files']==33 and len(plan['inputs'])==28
assert set(before)==set(plan['inputs'])|{str(S/n) for n in ['plan.json','run_once.py','README.md','source-review.json','prerequisite-template.json']}
for name,row in before.items():assert file(name)==row,name
for name,row in plan['inputs'].items():assert row['path']==name and {k:row[k] for k in ['bytes','sha256','identity']}==before[name]
bindings=doc(S/'source-bindings.json');assert len(bindings['copies'])==9
for path,pair in bindings['copies'].items():assert pair['copy']['path']==path and before[path]['sha256']==before[pair['origin']['path']]['sha256']==pair['copy']['sha256']==pair['origin']['sha256']
qualified=doc(E/'prerequisite.json');assert qualified==doc(plan['prerequisite']['path'])
assert qualified['policy']=='reviewed-passed-n-client04-for-default-discovery-v1' and qualified['actual_success'] is True
assert file(plan['prerequisite']['path'])['sha256']==plan['prerequisite']['sha256']==result['prerequisite_sha256']==execution['prerequisite_sha256']=='6a2561c392f07c15d59ec374d931ce348a5635dc52779c47aa8d5e3964f8198d'
proofs={}
for name,reference in qualified['proofs'].items():
 assert set(reference)=={'path','sha256'} and file(reference['path'])['sha256']==reference['sha256']
 if name!='owner-runner':proofs[name]=doc(reference['path'])
assert set(qualified['proofs'])=={'result.json','execution.json','built-artifacts.json','inputs-before.json','inputs-after.json','runtime-before.json','runtime-after.json','owner-plan','owner-runner','independent-readback'}
assert qualified['proofs']['independent-readback']==plan['prerequisite']['independent_readback'] and qualified['proofs']['independent-readback']['sha256']=='8a80fae80394a057e481fd0e6382ad11bc84f1a5a113db91f242e10d219b4465'
prior_review=proofs['independent-readback'];assert prior_review['status']=='verified' and prior_review['command_count']==27 and prior_review['stable_caller_pairs']==9
for key,pname in [('result','result.json'),('execution','execution.json'),('plan','owner-plan'),('runner','owner-runner')]:assert prior_review[key]==qualified['proofs'][pname]
assert proofs['result.json']['status']=='passed' and proofs['result.json']['native_tests_passed']=={'stock':0,'candidate':13}
assert proofs['inputs-before.json']==proofs['inputs-after.json'] and len(proofs['inputs-before.json'])==122
prerequisite_before=doc(E/'prerequisite-before.json');assert prerequisite_before==doc(E/'prerequisite-after.json')
for name,row in prerequisite_before.items():assert file(name)==row,name
for name,row in proofs['inputs-before.json'].items():assert file(name)==row and prerequisite_before[name]==row
selected=qualified['selected_artifacts'];assert len(selected)==6 and set(selected)==set().union(*map(set,plan['overlay']['owned_per_arm'].values()))
for name,row in selected.items():assert file(name)==row==proofs['built-artifacts.json'][name]==prior_review['built_artifacts'][name]
inventory=doc(S/'runtime-inventory.json');rb=doc(E/'runtime-before.json');ra=doc(E/'runtime-after.json');assert rb==ra and rb['full_payload_readback'] is True
TC=Path(inventory['root']);assert str(TC/'bin/rustc')==plan['compiler'] and inventory['file_count']==63 and inventory['link_count']==2
compiled=doc(inventory['compiled']['path']);assert file(inventory['compiled']['path'])['sha256']==inventory['compiled']['sha256'];assert compiled['stage1']==inventory['entries'] and compiled['source_identity']==inventory['source_identity']
observed={};directories={};runtime_bytes=0
for parent,dirs,files in os.walk(TC,followlinks=False):
 p=Path(parent);assert p.resolve(strict=True)==p
 directories[str(p.relative_to(TC))]=stamp(p.lstat())
 for name in dirs+files:
  q=p/name;s=q.lstat();rel=str(q.relative_to(TC))
  if stat.S_ISDIR(s.st_mode):continue
  row=inventory['entries'][rel];ids=dict(zip(['dev','ino','mode','size','mtime_ns','ctime_ns','nlink'],row['stamp']));assert stamp(s)==ids
  if row['kind']=='link':
   assert stat.S_ISLNK(s.st_mode) and os.readlink(q)==row['target'] and str(q.resolve(strict=True))==row['resolved']
   observed[rel]=dict(kind='link',identity=ids,target=row['target'],resolved=row['resolved'])
  else:
   value=file(q);assert row['kind']=='file' and value['sha256']==row['sha256'];observed[rel]=dict(kind='file',**value);runtime_bytes+=value['bytes']
  assert stamp(q.lstat())==ids
assert observed==rb['entries'] and directories==rb['directories']==inventory['directories']
assert len(observed)==65 and sum(v['kind']=='file' for v in observed.values())==63 and runtime_bytes==inventory['logical_file_bytes']

assert rb==proofs['runtime-before.json']==proofs['runtime-after.json']
ob=doc(E/'overlays-before.json');oa=doc(E/'overlays-after.json');assert ob==oa and ob['old_client_and_literal_absent'] is True
specification=plan['overlay'];assert len(specification['aliases'])==52 and len(specification['excluded_original_paths'])==4
owned={};links={};overlay_entries={};overlay_directories={}
for arm in ['stock','candidate']:
 base=W/arm/'sysroot';expected_links={str(base/k):v for k,v in specification['aliases'].items()}
 expected_owned={str(base/'lib/rustlib/aarch64-apple-darwin/lib'/Path(name).name):name for name in specification['owned_per_arm'][arm]};assert len(expected_owned)==4
 found=set();founddirs=set()
 for parent,dirs,files in os.walk(base,followlinks=False):
  directory=Path(parent);relative=str(directory.relative_to(base));founddirs.add(relative);assert directory.resolve(strict=True)==directory
  overlay_directories[str(directory)]=stamp(directory.lstat())
  for leaf in dirs+files:
   p=directory/leaf;s=stamp(p.lstat());name=str(p)
   if stat.S_ISDIR(s['mode']):continue
   found.add(name)
   if name in expected_links:
    declaration=expected_links[name];target=Path(declaration['path']);rel=str(p.relative_to(base));assert target==TC/rel and declaration['record']==inventory['entries'][rel]
    assert stat.S_ISLNK(s['mode']) and os.readlink(p)==str(target) and p.resolve(strict=True)==target
    assert file(target)['sha256']==declaration['record']['sha256']
    value=dict(kind='link',identity=s,target=str(target),resolved=str(target));links[name]=value;overlay_entries[name]=value
   else:
    assert name in expected_owned;origin=expected_owned[name];value=file(p);assert value['sha256']==selected[origin]['sha256'] and value['bytes']==selected[origin]['bytes']
    assert value['identity']['nlink']==1 and value['identity']['ino']!=selected[origin]['identity']['ino'];owned[name]=value;overlay_entries[name]=dict(kind='file',**value)
 assert found==set(expected_links)|set(expected_owned) and founddirs==set(specification['directories'])
 assert all(not os.path.lexists(base/rel) for rel in specification['excluded_original_paths'])
assert len(owned)==8 and len(links)==104 and len(overlay_directories)==14 and len({r['identity']['ino'] for r in owned.values()})==8
assert overlay_entries==ob['entries'] and overlay_directories==ob['directories']
built=doc(E/'built-artifacts.json');built_seen={};cases={c['name']:c for c in plan['cases']};pairs={};children=[];dep_rows={};last_finished=execution['admitted_at'];native={}
for i,(spec,c) in enumerate(zip(plan['commands'],execution['command_records'])):
 label=f'{i:02d}-{spec["arm"]}-{spec.get("case","dylib")}'
 assert doc(E/(label+'-record.json'))==c
 assert c['status']=='closed' and c['may_be_live'] is False and c['observation_errors']==[] and c.get('observation_error_count',0)==0
 assert type(c['returncode']) is int and c['returncode']==spec['expected_returncode']==c['expected_returncode']
 assert c['command']==spec['argv'] and c['cwd']==spec['cwd'] and c['environment']==spec['environment']
 assert c['parent_pid']==execution['parent_pid'] and type(c['pid']) is int and c['pid']>0
 assert c['cpu_seconds']==spec['child_cpu_seconds'] and c['observer_seconds']==spec['child_observer_seconds'] and c['file_bytes']==64*2**20
 assert last_finished<=c['started_at']<=c['spawned_at']<=c['observation_finished_at']<=c['finished_at']<=execution['finished_at'];last_finished=c['finished_at']
 assert all(v['free_bytes']>=9*2**30 and v['work_bytes']<=256*2**20 for v in c['samples'])
 for stream in ['stdout','stderr']:assert file(E/(label+'.'+stream))==c[stream] and c[stream]['bytes']<=2**20
 proof=doc(E/(label+'-verification.json'));assert proof['label']==label
 out=raw(E/(label+'.stdout')).decode();err=raw(E/(label+'.stderr')).decode()
 assert spec['role'] in ['build-macro-dylib','caller']
 if True:
  assert out=='';values=[json.loads(line) for line in err.splitlines()];errors=[];aborts=[]
  for v in values:
   assert v['$message_type']=='diagnostic'
   if v['level']=='error':
    if v['spans']:errors.append(v)
    else:
     m=re.fullmatch(r'aborting due to ([1-9][0-9]*) previous errors?',v['message']);assert m;aborts.append(int(m.group(1)))
   else:assert v['level']=='failure-note'
  expected=list(cases[spec['case']]['errors']) if spec['role']=='caller' else []
  assert len(errors)==len(expected) and aborts==([] if spec['expected_returncode']==0 else [len(errors)])
  normalized=[]
  for errval in errors:
   primary=[s for s in errval['spans'] if s['is_primary']];code=errval['code']['code'] if errval['code'] else None
   matches=[v for v in expected if v['code']==code and v['message']==errval['message'] and any(s['file_name']==cases[spec['case']]['source'] and s['line_start']==v['primary_line'] for s in primary) and ('help' not in v or any(ch['level']=='help' and ch['message']==v['help'] for ch in errval['children']))]
   assert len(matches)==1;expected.remove(matches[0])
   normalized.append(dict(level=errval['level'],code=code,message=errval['message'],primary_spans=[{k:s[k] for k in ['file_name','line_start','line_end','column_start','column_end']} for s in primary],children=[dict(level=v['level'],message=v['message']) for v in errval['children']]))
  normalized.sort(key=lambda v:json.dumps(v,sort_keys=True));assert not expected and proof['diagnostics']==normalized
  if spec['expected_returncode']==0:assert values==[]
  if spec['role']=='caller':pairs.setdefault(spec['case'],{})[spec['arm']]=normalized
  outputs=[spec['output']]+([spec['metadata']] if 'metadata' in spec else [])
  if spec['expected_returncode']!=0:
   assert proof['dependency']==dict(success_outputs_absent=outputs) and all(not os.path.lexists(p) for p in outputs)
  else:
   deps=proof['dependency'];assert set(deps['outputs'])==set(outputs)
   for path in outputs:assert file(path)==deps['outputs'][path]==built[path];built_seen[path]=built[path]
   dep=Path(spec['depinfo']);drow=file(dep);text=raw(dep).decode();assert deps['depinfo']==dict(path=str(dep),**drow);dep_rows[str(dep)]=drow
   assert '/.rustup/toolchains/' not in text and all(arg in text for arg in spec['argv'] if arg.endswith('.rs'))
   if spec['role']!='caller':assert '/libproc_macro-452900db9815e688.' not in text
   assert '/librustc_literal_escaper-f4f532eb55f87a02.' not in text and 'libproc_macro-452900db9815e688.' not in text
   other='stock' if spec['arm']=='candidate' else 'candidate';assert str(W/other/'sysroot') not in text
   discovered={}
   if spec['role']=='build-macro-dylib':
    assert not any(arg.startswith(('proc_macro=','rustc_literal_escaper=','dependency=')) for arg in spec['argv'])
    for name,row in owned.items():
     if Path(name).is_relative_to(W/spec['arm']/'sysroot'):assert name in text and file(name)==row;discovered[name]=row
    assert len(discovered)==4
   else:
    assert spec['role']=='caller';name=str(W/'macro-tests'/spec['arm']/'libarena04_macros.dylib');otherpath=str(W/'macro-tests'/other/'libarena04_macros.dylib')
    assert name in text and otherpath not in text and file(name)==built[name]
   assert deps['default_discovered']==discovered
 children.append(dict(index=i,role=spec['role'],arm=spec['arm'],pid=c['pid'],parent_pid=c['parent_pid'],returncode=c['returncode'],record=ref(E/(label+'-record.json')),verification=ref(E/(label+'-verification.json')),raw={n:ref(E/(label+'.'+n)) for n in ['stdout','stderr']}))
assert built_seen==built and len({c['pid'] for c in children})==20
assert len(pairs)==9 and all(set(v)=={'stock','candidate'} and v['stock']==v['candidate'] for v in pairs.values())
work_files={};work_links={}
for p in sorted(W.rglob('*')):
 if p.is_symlink():
  assert str(p) in links;work_links[str(p)]=links[str(p)]
 elif p.is_file():work_files[str(p)]=file(p)
evidence_files={str(p):file(p) for p in sorted(E.rglob('*')) if p.is_file()}
assert set(work_links)==set(links) and sum(r['bytes'] for r in work_files.values())+sum(r['bytes'] for r in evidence_files.values())+sum(r['identity']['size'] for r in work_links.values())<=256*2**20
for root in [S,E,W]:assert tree(root)==trees[str(root)]
for name,row in CHECKED.items():assert stamp(Path(name).lstat())==row['identity'],name
report=dict(status='verified',scope='actual N overlay01 default-discovery correctness only',finished_at=time.time(),verifier=ref(Path(__file__)),result=ref(E/'result.json'),execution=ref(E/'execution.json'),plan=ref(S/'plan.json'),runner=ref(S/'run_once.py'),prerequisite=ref(plan['prerequisite']['path']),N04_independent_readback=qualified['proofs']['independent-readback'],parent_pid=execution['parent_pid'],canonical_released_at=execution['canonical_released_at'],children=children,command_count=20,source_input_rows=28,full_input_before_after_rows=33,current_inputs_match=True,prerequisite_rows=len(prerequisite_before),stable_caller_pairs=9,stable_diagnostics=pairs,runtime=dict(root=str(TC),files=63,links=2,logical_file_bytes=runtime_bytes,complete_membership=True,full_payload_rehash=True,before=ref(E/'runtime-before.json'),after=ref(E/'runtime-after.json')),overlays=dict(owned_files=8,links=104,directories=14,current_owned=owned,current_links=links,complete_membership=True,old_client_and_literal_absent=True,before=ref(E/'overlays-before.json'),after=ref(E/'overlays-after.json')),built_artifacts=built,depinfo=dep_rows,work_files=work_files,work_links=work_links,evidence_files=evidence_files,checked_files=CHECKED,closed_trees=trees,default_discovery_qualified=True,real_N_external_client_integration=True,compiler_distribution_qualified=False,runtime_composition_qualified=False,holdout_qualified=False,benchmark=False,no_target_imports_or_child_calls=True)
with REPORT.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(dict(path=str(REPORT),sha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(),runtime_bytes=runtime_bytes,built_files=len(built),work_files=len(work_files),work_links=len(work_links),evidence_files=len(evidence_files))))
