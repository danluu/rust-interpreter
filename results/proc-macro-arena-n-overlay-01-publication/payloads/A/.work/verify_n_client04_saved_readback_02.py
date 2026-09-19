"""Bounded read-only saved N04 qualification; no project imports or child calls."""
from pathlib import Path
import hashlib,json,os,re,stat,time
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
S=R/'experiments/proc-macro-arena-n-client-04';E=R/'results/proc-macro-arena-n-client-04';W=R/'.work/proc-macro-arena-n-client-04'
REPORT=A/'.work/proc-macro-arena-n-client04-independent-readback-01.json'
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
  s=stamp(p.lstat());assert stat.S_ISREG(s['mode']) or stat.S_ISDIR(s['mode']),p
  result[str(p.relative_to(root))]=s
 return result

trees={str(p):tree(p) for p in [S,E,W]}
plan=doc(S/'plan.json');execution=doc(E/'execution.json');result=doc(E/'result.json')
assert file(E/'result.json')['sha256']=='1879638dc56543c6918598cc9bdf2cf0975090efba46ac614dbbfff9bb20deae'
assert file(S/'plan.json')['sha256']==file(E/'plan.json')['sha256']==execution['plan_sha256']=='e7cf786c2ac4ec52890a856edb38ea8d3221a129781f2f3eead8955a57f189e1'
assert file(S/'run_once.py')['sha256']==file(E/'run_once.py')['sha256']=='3739f5c936377069259c9074ecc6a1b0c21247bd78e44596c7d07add69bc0099'
assert result['status']==execution['status']=='passed' and result['execution_sha256']==file(E/'execution.json')['sha256']
assert result['children']==execution['children']==len(execution['command_records'])==len(plan['commands'])==27
assert execution['started_at']<=execution['admitted_at']<=execution['finished_at']<=execution['parent_lock_closed_at']<=execution['canonical_released_at']
assert execution['signals']==[] and execution['retries']==0 and execution['free_bytes_before']>=14*2**30 and execution['free_bytes_after']>=9*2**30
for k in ['compiler_distribution_qualified','runtime_composition_qualified','benchmark']:assert result[k] is False and execution[k] is False
assert result['holdout_qualified'] is False and result['builtin_quote_optimized'] is False and result['compiler_server_unchanged'] is True
assert result['real_N_external_client_integration'] is True and execution['real_N_external_client_integration'] is True
assert result['native_tests_passed']==dict(stock=0,candidate=13) and result['stock_empty_harness_is_smoke_only'] is True
assert result['library_builds']==3 and result['whole_crate_test_builds']==2 and result['caller_cases_per_arm']==9
before=doc(E/'inputs-before.json');after=doc(E/'inputs-after.json');assert before==after and len(before)==execution['input_files']==122 and len(plan['inputs'])==118
assert set(before)==set(plan['inputs'])|{str(S/n) for n in ['plan.json','run_once.py','README.md','source-review.json']}
for name,row in before.items():assert file(name)==row,name
for name,row in plan['inputs'].items():assert row['path']==name and {k:row[k] for k in ['bytes','sha256','identity']}==before[name]
bindings=doc(S/'source-bindings.json');assert len(bindings['copies'])==47
for path,pair in bindings['copies'].items():
 assert pair['copy']['path']==path
 assert before[path]['sha256']==before[pair['origin']['path']]['sha256']==pair['copy']['sha256']==pair['origin']['sha256']
differences=[]
for path in bindings['copies']:
 p=Path(path)
 if p.is_relative_to(S/'source/stock/proc_macro'):
  rel=p.relative_to(S/'source/stock/proc_macro')
  if before[path]['sha256']!=before[str(S/'source/candidate/proc_macro'/rel)]['sha256']:differences.append(str(rel))
assert sorted(differences)==['src/bridge/arena.rs','src/bridge/symbol.rs']==bindings['source_difference_paths']

inventory=doc(S/'runtime-inventory.json');rb=doc(E/'runtime-before.json');ra=doc(E/'runtime-after.json');assert rb==ra and rb['full_payload_readback'] is True
TC=Path(inventory['root']);assert str(TC)==plan['sysroot'] and inventory['file_count']==63 and inventory['link_count']==2
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
 if spec['role']=='run-whole-crate-tests':
  assert err=='';lines=[v for v in out.splitlines() if v];names=spec['tests'];assert names==plan['whole_crate_test_names'][spec['arm']]
  assert len(lines)==len(names)+2 and lines[0]==f'running {len(names)} tests' and lines[1:-1]==[f'test {name} ... ok' for name in names]
  assert re.fullmatch(r'test result: ok\. '+str(len(names))+r' passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in [0-9]+\.[0-9]+s',lines[-1])
  expect=dict(tests=names,passed=len(names),stock_empty_harness_is_smoke_only=spec['arm']=='stock');assert proof['native_tests']==expect;native[spec['arm']]=expect
 else:
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
   if spec['role'] in ['build-stock-client','build-candidate-client','build-whole-crate-tests','build-macro-dylib']:
    meta=spec['role'] in ['build-stock-client','build-candidate-client'];direct=spec['role']!='build-macro-dylib';supplied={}
    for suffix in ['rlib','rmeta']:
     name=str(W/'dependency'/('librustc_literal_escaper-arena04_n_dep01.'+suffix));assert file(name)==built[name]
     if direct:assert any(spec['argv'][j:j+2]==['--extern','rustc_literal_escaper='+name] for j in range(len(spec['argv'])-1))
     else:assert not any(arg.startswith('rustc_literal_escaper=') for arg in spec['argv'])
     if suffix=='rmeta' or not meta:assert name in text
     supplied[suffix]=dict(path=name,**built[name])
    assert deps['normal_literal_dependency']==dict(metadata_only_rlib_build=meta,supplied=supplied,direct_extern_required=direct,dependency_route='direct' if direct else 'transitive-through-matched-proc-macro',required_depinfo_flavors=['rmeta'] if meta else ['rlib','rmeta'],code_archive_linkage_required=not meta,code_archive_present_in_depinfo=supplied['rlib']['path'] in text)
    assert '/librustc_literal_escaper-f4f532eb55f87a02.' not in text
   if spec['role']=='build-macro-dylib':
    for suffix in ['rlib','rmeta']:
     name=str(W/spec['arm']/(f'libproc_macro-arena04_n_{spec["arm"]}01.'+suffix));assert name in text and file(name)==built[name]
    assert str(W/('stock' if spec['arm']=='candidate' else 'candidate')) not in text
   if spec['role']=='caller':
    name=str(W/'macro-tests'/spec['arm']/'libarena04_macros.dylib');other=str(W/'macro-tests'/('stock' if spec['arm']=='candidate' else 'candidate')/'libarena04_macros.dylib');assert name in text and other not in text and file(name)==built[name]
 children.append(dict(index=i,role=spec['role'],arm=spec['arm'],pid=c['pid'],parent_pid=c['parent_pid'],returncode=c['returncode'],record=ref(E/(label+'-record.json')),verification=ref(E/(label+'-verification.json')),raw={n:ref(E/(label+'.'+n)) for n in ['stdout','stderr']}))
assert built_seen==built and len({c['pid'] for c in children})==27
assert len(pairs)==9 and all(set(v)=={'stock','candidate'} and v['stock']==v['candidate'] for v in pairs.values())
assert native['stock']['passed']==0 and native['candidate']['passed']==13
work_files={str(p):file(p) for p in sorted(W.rglob('*')) if p.is_file()};evidence_files={str(p):file(p) for p in sorted(E.rglob('*')) if p.is_file()}
assert sum(r['bytes'] for r in work_files.values())+sum(r['bytes'] for r in evidence_files.values())<=256*2**20
for root in [S,E,W]:assert tree(root)==trees[str(root)]
for name,row in CHECKED.items():assert stamp(Path(name).lstat())==row['identity'],name
report=dict(status='verified',scope='actual N04 external proc-macro clients and finite correctness controls only',finished_at=time.time(),verifier=ref(Path(__file__)),result=ref(E/'result.json'),execution=ref(E/'execution.json'),plan=ref(S/'plan.json'),runner=ref(S/'run_once.py'),parent_pid=execution['parent_pid'],canonical_released_at=execution['canonical_released_at'],children=children,command_count=27,source_input_rows=118,full_input_before_after_rows=122,current_inputs_match=True,source_difference_paths=sorted(differences),native_tests=native,stable_caller_pairs=9,stable_diagnostics=pairs,runtime=dict(root=str(TC),files=63,links=2,logical_file_bytes=runtime_bytes,complete_membership=True,full_payload_rehash=True,before=ref(E/'runtime-before.json'),after=ref(E/'runtime-after.json')),built_artifacts=built,depinfo=dep_rows,work_files=work_files,evidence_files=evidence_files,checked_files=CHECKED,closed_trees=trees,real_N_external_client_integration=True,compiler_distribution_qualified=False,runtime_composition_qualified=False,holdout_qualified=False,benchmark=False,no_target_imports_or_child_calls=True)
with REPORT.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(dict(path=str(REPORT),sha256=hashlib.sha256(REPORT.read_bytes()).hexdigest(),runtime_bytes=runtime_bytes,built_files=len(built),work_files=len(work_files),evidence_files=len(evidence_files),checked_files=len(CHECKED))))
