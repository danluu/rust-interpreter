"""Finite saved metadata/build readback. Stdlib only; no target imports or probes."""
import hashlib,json,os,re,shlex,stat,time
from pathlib import Path
Q=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
F=Q/'experiments/host-wrapper-exporter-01'; P=F/'packet-01'
OUT=X/'.work/host-wrapper-exporter-metadata-build-independent-readback-01.json'
checked={}; trees={}; raws={}; began=time.time()
def need(x,msg):
 if not x:raise AssertionError(msg)
def ident(s):return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
def read(path,sha=None,ref=None):
 p=Path(path); a=ident(p.lstat());need(p.is_absolute() and p.resolve(strict=True)==p and stat.S_ISREG(a[2]) and a[3]<=8*2**20,'finite regular path '+str(p))
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as f:
  need(ident(os.fstat(f.fileno()))==a,'open identity'); b=f.read(8*2**20+1);need(ident(os.fstat(f.fileno()))==a,'EOF identity')
 need(ident(p.lstat())==a and len(b)==a[3],'read identity');row=dict(path=str(p),bytes=len(b),identity=a,sha256=hashlib.sha256(b).hexdigest())
 if sha:need(row['sha256']==sha,'digest '+str(p))
 if ref:need(row==ref,'reference '+str(p))
 if str(p) in checked:need(checked[str(p)]==row,'changed '+str(p))
 checked[str(p)]=row;return b
def doc(path,sha=None,ref=None):return json.loads(read(path,sha,ref))
def frozen(row):return read(row['path'],ref=row)
def tree(root):
 root=Path(root);members=[]
 for parent,dirs,files in os.walk(root,followlinks=False):
  for n in dirs+files:
   p=Path(parent)/n;s=p.lstat();need(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode),'tree node');members.append((str(p.relative_to(root)),'d' if stat.S_ISDIR(s.st_mode) else 'f'))
 need(len(members)<=400,'closed metadata tree cap');trees[str(root)]=sorted(members)
 return members
plan=doc(P/'plan.json','922663c1d01f2fcf88e5f7b74658ec6e66fc47fb1f5f4bee949d3901da5c32e8')
inputs=doc(P/'inputs.json','de44d4b4bc7685097ba2d0f1e2bcf50fa231a05658092bde87b5d59f17519c8e')
launch=doc(P/'launch.json','450085144d49d9b15442dc848cd48b5784da6c3b21d36710b932727e9f41d591')
need(inputs['plan']==launch['plan']==checked[str(P/'plan.json')] and launch['inputs']==checked[str(P/'inputs.json')],'packet')
sources=doc(F/'sources.json','4e17ba1f0be6548ea3875322a1216c56e5bfb857ca99d57278e18925632cfeb3')
bs=doc(F/'build-sources.json','190a4e56c5083d595f91b3e3bac7ac6e8c8c883bfc32befe49b31473a99e58e1')
need(len(sources['files'])==17 and len(bs['files'])==21 and sources['files']==inputs['files'],'source census')
for p,s in bs['files'].items():read(p,s)
need(all(bs['files'][p]==s for p,s in sources['files'].items()),'source union')
read(F/'execute.py','4255fae6f1173f5ac44d05371b6034328b5d0bc698e28d8ca0e0376c4f3ae55f')
need(len(plan['source_materialization'])==238,'238 source rows')
for rel,row in plan['source_materialization'].items():
 need(row['path']==str(Path(plan['source_root'])/rel) and row==plan['files'][row['path']],'source materialization association');frozen(row)
binding=plan['binding'];need(doc(P/'compiler-roles.json')==binding,'role packet')
phase_refs={}; records={}; commands={}
def phase(name,esha,rsha,count,schedule):
 ep=Q/f'.work/host-wrapper-exporter-{name}-execution-01'; e=doc(ep/'record.json',esha);op=Path(e['command'][-1]).parent
 o=doc(op/'plan.json',e['outer_plan_sha256']);s=doc(op/'status.json',e['outer_status_sha256']);read(op/'command.log',s['log_sha256'])
 for st in ('stdout','stderr'):need(read(ep/st,e[st+'_sha256'])==b'','parent stream')
 read(X/'scripts/supervise_experiment.py',o['supervisor_sha256'])
 need(e['status']==s['status']=='finished' and e['returncode']==e['controller_returncode']==s['returncode']==0,'normal closed parent')
 need(e['supervisor_may_be_live'] is False and e['controller_may_be_live'] is False and e['signals']==e['retries']==0,'no possible live child')
 need(e['parent_pid']==s['supervisor_parent_pid'] and e['pid']==s['supervisor_pid'] and e['command']==['/opt/homebrew/bin/python3','-B',str(X/'scripts/supervise_experiment.py'),'--supervise',str(op/'plan.json')],'parent association')
 need(e['environment']==launch['environment'] and e['cwd']==s['cwd']==str(X) and e['launch_sha256']==checked[str(P/'launch.json')]['sha256'],'parent transport')
 need(o['command']==s['command'] and o['owner']==s['owner']==str(X),'outer association')
 need(e['started_at']<=e['child_started_at']<=s['started_at']<=s['child_started_at']<=s['finished_at']<=e['finished_at'],'outer chronology')
 for k,pid,ppid in [('supervisor_identity',e['pid'],e['parent_pid']),('child_identity',s['child_pid'],s['supervisor_pid'])]:need(re.search(r'(?m)^\s*'+str(pid)+r'\s+'+str(ppid)+r'\s',s[k]) is not None,'saved ps parentage')
 w=X/f'.work/host-wrapper-exporter-{name}-01';r=doc(w/'receipt.json',rsha)
 need(r['phase']==name and r['status']=='passed' and r['pid']==s['child_pid'] and r['parent_pid']==s['supervisor_pid'],'controller association')
 need(r['command']==o['command'] and r['environment']==launch['environment'] and r['cwd']==str(X),'controller transport')
 need(r['inputs_sha256']==checked[str(P/'inputs.json')]['sha256'] and r['sources_sha256']==checked[str(F/'sources.json')]['sha256'] and r['plan_sha256']==checked[str(P/'plan.json')]['sha256'],'source packet pins')
 need(r['runtime_key']==plan['runtime_key'] and r['compiler_builds']==r['VM_builds']==r['guest_executions']==r['signals']==r['retries']==0 and r['performance_measurement'] is False,'phase scope')
 need(s['child_started_at']<=r['started_at']<=r['admitted_at']<=r['finished_at']<=s['finished_at'],'controller chronology')
 need(len(r['commands'])==count==len(schedule),'command count');previous=r['admitted_at'];rows=[]
 for i,(saved,wanted) in enumerate(zip(r['commands'],schedule,strict=True)):
  p=w/'commands'/f'{i:03d}'/'receipt.json';need(saved['path']==str(p) and saved['label']==wanted['label'],'command route')
  c=doc(p,saved['sha256']);need(c['status']=='finished' and c['returncode']==saved['returncode']==0 and c['pid']==saved['pid'],'child closure')
  need(all(c[k]==wanted[k] for k in ('command','environment','cwd')),'exact child recipe '+wanted['label'])
  need(c['supervisor_pid']==r['pid'] and c['parent_pid']==r['parent_pid'] and previous<=c['started_at']<=c['finished_at']<=r['finished_at'],'child chronology/owner');previous=c['finished_at']
  data={st:read(p.parent/st,c[st+'_sha256']) for st in ('stdout','stderr')};raws[str(p)]=data
  if wanted.get('expected_stdout_sha256'):need(c['stdout_sha256']==wanted['expected_stdout_sha256'] and data['stderr']==b'','SDK declaration')
  rows.append((wanted,c,data,str(p)))
 records[name]=r;commands[name]=rows;phase_refs[name]=dict(execution=checked[str(ep/'record.json')],receipt=checked[str(w/'receipt.json')])
 for t in (ep,op,w):tree(t)
 return doc(r['result']['path'],ref=r['result'])
metadata=phase('metadata','532e6161fb98c8cfaf9bc1c01972774282cf593a32d000f94bf160c45d0f1bcc','09390382e5426e5ca2fa23ceb620e02e51e5b9908b77bf5bcbd739feed99032d',36,plan['children'])
need(metadata['status']=='metadata-passed-build-unexecuted' and metadata['binding']==binding and metadata['actual_children']==36 and metadata['plan_sha256']==checked[str(P/'plan.json')]['sha256'],'metadata result')
bylabel={w['label']:(c,data,p) for w,c,data,p in commands['metadata']}
cm=bylabel['cargo-metadata'];need(not cm[1]['stderr'],'Cargo metadata diagnostics');cargo=json.loads(cm[1]['stdout']);read(X/'.work/host-wrapper-exporter-metadata-01/cargo-metadata.json',cm[0]['stdout_sha256'])
prior=doc(plan['historical_cargo_metadata']['path'],plan['historical_cargo_metadata']['sha256'])
def semantic(d):return {p['id']:(p['name'],p['version'],p['source']) for p in d['packages']}
newids=semantic(cargo);oldids=semantic(prior);need(set(newids.values())==set(oldids.values()) and len(newids)==30,'30 package graph')
def graph(d,ids):return {ids[n['id']]:(n['features'],sorted((x['name'],ids[x['pkg']],json.dumps(x['dep_kinds'],sort_keys=True)) for x in n['deps'])) for n in d['resolve']['nodes']}
need(graph(cargo,newids)==graph(prior,oldids),'dependency graph/features')
for key in ('workspace_members','workspace_default_members'):need([newids[i] for i in cargo[key]]==[oldids[i] for i in prior[key]],'workspace graph')
need(cargo['workspace_root']==plan['source_root'],'workspace root')
oldp={oldids[p['id']]:p for p in prior['packages']}
for p in cargo['packages']:
 o=oldp[newids[p['id']]];want=o['manifest_path'] if p['source'] else str(Path(plan['source_root'])/Path(o['manifest_path']).relative_to(X));need(p['manifest_path']==want,'package manifest')
 wanted=[]
 for t in o['targets']:
  t=dict(t)
  if not p['source']:t['src_path']=str(Path(plan['source_root'])/Path(t['src_path']).relative_to(X))
  wanted.append(t)
 need(p['targets']==wanted,'package target schema')
need(metadata['dependencies']==dict(packages=cargo['packages'],resolve=cargo['resolve']),'metadata dependencies')
cache={}
for w,c,data,p in commands['metadata']:
 a=w['command']
 if a[:3]==['/usr/bin/otool','-arch','arm64']:
  need(not data['stderr'],'otool diagnostics');cache[(a[-1],a[3])]=(data['stdout'],p,c['stdout_sha256'])
need(metadata['loader_observations']==sorted([dict(path=p,flag=f,receipt=r,stdout_sha256=s) for (p,f),(b,r,s) in cache.items()],key=lambda x:(x['path'],x['flag'])),'loader rows')
def closure(cl,exe,extra=None):
 identity=cl['identity'];state=cl['state'];mapping={'$CARGO':exe};allowed={exe}
 need(identity['policy']=='macos-dyld-closure-v1' and identity['system_assumption']=='system dyld cache bound to uname platform/kernel build','loader policy')
 for lib in identity['libraries']:
  rr=(extra or {}).get(lib['resolved'],plan['files'].get(lib['resolved']));need(rr and lib['bytes']==rr['bytes'] and lib['sha256']==rr['sha256'],'frozen resolved library association')
  mapping[lib['logical']]=lib['resolved'];allowed.add(lib['resolved']);need(state['libraries'][lib['logical']][0]==lib['resolved'],'loader state route')
 for logical,node in identity['nodes'].items():
  exe2=mapping[logical];l=cache[(exe2,'-L')][0].decode();lc=cache[(exe2,'-l')][0].decode()
  deps=[line.strip().split(' (compatibility version ',1)[0] for line in l.splitlines() if line.startswith('\t')]
  rp=[];active=False
  for line in lc.splitlines():
   if line.strip().startswith('cmd '):active=line.strip()=='cmd LC_RPATH'
   m=re.fullmatch(r'\s*path (.+) \(offset \d+\)',line)
   if active and m:rp.append(m[1]);active=False
  need(node==dict(dependencies=deps,rpaths=rp),'otool node reconstruction')
 return allowed
stats={}
def dyld(saved,raw,pid,allowed,driver,label):
 lines=raw.splitlines(keepends=True);need(len(lines)==len(saved['events']) and saved['pid']==pid and saved['raw_sha256']==hashlib.sha256(raw).hexdigest() and saved['raw_bytes']==len(raw),'dyld stream')
 images={};offset=0
 for i,(line,e) in enumerate(zip(lines,saved['events'],strict=True)):
  need(line.endswith(b'\n') and not line.endswith(b'\r\n') and {k:e[k] for k in ('line','start','end','raw_hex')}==dict(line=i+1,start=offset,end=offset+len(line),raw_hex=line.hex()),'lossless dyld row');offset+=len(line)
  body=line[:-1].decode();m=re.fullmatch(r'dyld\[([0-9]+)\]: <([0-9A-Fa-f-]{36})> (/.+)',body)
  if m:
   need(int(m[1])==pid and m[3] not in images,'dyld new image');path=m[3];system=path.startswith(('/usr/lib/','/System/Library/'));need(system or path in allowed,'allowed image')
   images[path]=dict(path=path,uuid=m[2],state='loaded',system=system,load_event=i)
   need({k:v for k,v in e.items() if k not in ('line','start','end','raw_hex')}==dict(kind='load',path=path,uuid=m[2],state='loaded'),'load event')
  else:
   m=re.fullmatch(r'dyld\[([0-9]+)\]: move (loaded|delayed) to (loaded|delayed): ([^/]+)',body);need(m and int(m[1])==pid and m[2]!=m[3],'dyld transition')
   candidates=[p for p in images if p.rsplit('/',1)[-1]==m[4]];need(len(candidates)==1,'unambiguous prior image');path=candidates[0];need(images[path]['state']==m[2],'prior state');images[path]['state']=m[3]
   need({k:v for k,v in e.items() if k not in ('line','start','end','raw_hex')}==dict(kind='transition',path=path,basename=m[4],before=m[2],after=m[3]),'move event')
 need(saved['images']==list(images.values()) and saved['loaded']==[p for p,v in images.items() if v['state']=='loaded'] and saved['delayed']==[p for p,v in images.items() if v['state']=='delayed'],'dyld final states')
 need(saved['selected_driver']==driver and driver in saved['loaded'] and saved['selected_driver_active'] is True and saved['policy']=='dyld-loaded-delayed-events-v1','active selected driver');stats[label]=dict(events=len(lines),images=len(images),loaded=len(saved['loaded']),delayed=len(saved['delayed']))
for exe,cl in metadata['closures'].items():closure(cl,exe)
for role,info in metadata['actual_roles'].items():
 exe=binding[role]['executable']['path'];need(info['closure']==metadata['closures'][exe],'role closure')
 c,data,p=bylabel[role+'-version'];need(info['version_receipt']==p and data['stdout'].decode()==binding[role]['verbose_version'],'actual compiler version')
 c2,data2,p2=bylabel[role+'-sysroot'];need(info['sysroot_receipt']==p2 and data2['stdout'].decode().strip()==binding[role]['default_sysroot'] and not data2['stderr'],'actual default sysroot')
 dyld(info['loaded'],data['stderr'],c['pid'],closure(info['closure'],exe),info['loaded']['selected_driver'],role)
work=X/'.work/host-wrapper-exporter-build-01';target=X/'.work/host-wrapper-exporter-target-01';env=plan['launch_environment'];future=plan['future_build']
need(future['environment']==plan['build_environment']|{'TMPDIR':str(work/'tmp')+'/'},'build environment')
schedule=[dict(label='cargo-build',command=future['command'],cwd=future['cwd'],environment=future['environment'])]
for name in ('rust-interp-mir-export','rust-interp-rustc-wrapper'):
 for flag in ('-L','-l'):schedule.append(dict(label=name+flag,command=['/usr/bin/otool','-arch','arm64',flag,str(target/'release'/name)],cwd=str(X),environment=env))
schedule.extend([dict(label='exporter-capabilities',command=[str(target/'release/rust-interp-mir-export'),'--rust-interp-capabilities'],cwd=str(X),environment=env|{'DYLD_PRINT_LIBRARIES':'1'}),dict(label='wrapper-roles',command=[str(target/'release/rust-interp-rustc-wrapper'),'--rust-interp-compiler-roles'],cwd=str(X),environment=env)])
built=phase('build','9b21a3acb87e2c7f37d379ca85d30ad474a9f4d950d4eb4bc1a164f15738c090','b4e7c71d32691a7c46435fbd9d42a5ba7f325ab47c85fe2003db8ba838d73ef7',7,schedule)
need(records['metadata']['finished_at']<=records['build']['started_at'] and records['build']['exporter_builds']==1 and records['metadata']['exporter_builds']==0,'phase order/scope')
need(built['metadata']==records['build']['metadata'] and built['metadata']['receipt']==phase_refs['metadata']['receipt'] and built['metadata']['result']==records['metadata']['result'],'build metadata association')
need(records['build']['metadata_receipt_sha256']==phase_refs['metadata']['receipt']['sha256'] and records['build']['build_sources_sha256']==checked[str(F/'build-sources.json')]['sha256'],'build pins')
need(built['compiler_roles']==binding and built['runtime_key']==plan['runtime_key'] and built['status']=='build-passed-frontend-unexecuted' and built['VM']==plan['adopted_VM'],'build result')
for k in ('frontend_qualified','application_qualified','published','performance_measurement'):need(built[k] is False,'historical build capture scope')
evidence=doc(built['evidence']['path'],ref=built['evidence']);cdata=commands['build'][0][2]
need(evidence['cargo_receipt']==checked[commands['build'][0][3]],'Cargo receipt association')
parsed=evidence['parsed'];need(''.join(r['raw'] for r in parsed['rows']).encode()==cdata['stdout'],'Cargo raw lossless')
messages=[];forwarded=[];labels={f"[{p['name']} {p['version']}] ":p['id'] for p in cargo['packages']}
for i,(raw,row) in enumerate(zip(cdata['stdout'].decode().splitlines(keepends=True),parsed['rows'],strict=True),1):
 need(row['line']==i and row['raw']==raw,'Cargo row index')
 if raw.startswith('{'):
  d=json.loads(raw);need(row==dict(line=i,kind='cargo-json',raw=raw,message=d) and d['reason'] in ('compiler-artifact','build-script-executed','compiler-message','build-finished','future-incompat-report'),'Cargo JSON schema');messages.append(d)
 else:
  pref=[p for p in labels if raw.startswith(p)];need(len(pref)==1 and row==dict(line=i,kind='build-script-stdout',raw=raw,package_id=labels[pref[0]],prefix=pref[0]),'forwarded build script');forwarded.append(row)
need(messages==parsed['messages'] and forwarded==parsed['forwarded'] and messages[-1]['reason']=='build-finished' and messages[-1]['success'] is True,'Cargo terminal')
need({r['package_id'] for r in forwarded}<={r['package_id'] for r in messages if r['reason']=='build-script-executed'},'forwarded script closure')
actual=[];d=binding['build']['executable']['path']
for line in cdata['stderr'].decode().splitlines():
 m=re.fullmatch(r'\s*Running `(.*)`',line)
 if not m:continue
 argv=shlex.split(m[1])
 if '--crate-name' not in argv:continue
 need(argv.count(d)==1,'exact D2 executable');i=argv.index(d);cmd=argv[i:];prefix=argv[:i];eprefix=prefix[1:] if prefix[:1]==['env'] else prefix
 need(all('=' in a for a in eprefix) and all(flag in cmd for flag in binding['build_rustflags']) and sum(a.startswith('--sysroot') for a in cmd)==1,'actual compiler flags')
 need(not any('RUSTC_FORCE_RUSTC_VERSION=' in a or 'RUSTC_OVERRIDE_VERSION_STRING=' in a for a in argv),'no fake compiler identity')
 rs=[a for a in cmd if a.endswith('.rs')];need(len(rs)==1,'one source');src=Path(rs[0]);src=src if src.is_absolute() else Path(plan['source_root'])/src;src=str(src)
 need(src in plan['files'],'frozen compiler source');actual.append(dict(command=cmd,environment_assignments=prefix,source=src))
need(actual==evidence['compilers'] and len(actual)==44,'44 exact actual compiler rows')
need(not any(v in cdata['stderr'] for v in (b'stripping debug info',b'SIGABRT',b'Library not loaded:',b'internal compiler error')) and evidence['strip_failures']==0,'Cargo diagnostics')
need(evidence['build_script_compiler_identity_probes']==records['build']['expected_build_script_compiler_identity_probes']==4,'nested identity probe scope')
for name,row in built['built_files'].items():frozen(row);need(row['sha256']==built['binaries'][name],'built digest')
arts=[r for r in messages if r['reason']=='compiler-artifact' and 'bin' in r.get('target',{}).get('kind',[]) and r.get('executable')]
need({r['executable'] for r in arts}=={r['path'] for r in built['built_files'].values()} and len(arts)==2 and all(r['fresh'] is False for r in arts),'fresh binary outputs')
need(evidence['generated']==built['generated'] and len(built['generated'])==1,'generated roles')
gen=frozen(built['generated'][0]).decode();first=gen.splitlines()[0];m=re.fullmatch(r'pub const BINDING_JSON: Option<&str> = Some\((.*)\);',first);need(m and json.loads(json.loads(m[1]))==binding,'generated typed role equality')
for w,c,data,p in commands['build'][1:5]:need(not data['stderr'],'tool loader diagnostics');cache[(w['command'][-1],w['command'][3])]=(data['stdout'],p,c['stdout_sha256'])
for name,cl in built['tool_closures'].items():closure(cl,built['built_files'][name]['path'])
cap=commands['build'][5];wrap=commands['build'][6];rawcap=json.loads(cap[2]['stdout']);roles=json.loads(wrap[2]['stdout']);need(not wrap[2]['stderr'] and roles==binding==rawcap['compiler_roles'],'actual wrapper/exporter roles')
need(rawcap['schema_version']==1 and rawcap['bytecode_version']==5 and rawcap['compiler_sysroot']==binding['runtime']['default_sysroot'],'capability runtime')
need(built['capabilities']==rawcap|{'runtime_wrapper':dict(sha256=built['binaries']['rust-interp-rustc-wrapper'],compiler_roles=binding)},'ordinary recorded wrapper augmentation')
need(rawcap['host_codegen_opt']==dict(schema_version=1,policy='host-codegen-opt-v1',roles=['proc-macro','lib','rlib'],opt_level=3,mir_opt_level=1,lto='off',preserve_checks=True) and 'host-codegen-opt-v1' in rawcap['export_options'],'new capability association')
need(built['exporter_probe']==checked[cap[3]] and built['wrapper_probe']==checked[wrap[3]],'probe refs')
dyld(built['exporter_loader'],cap[2]['stderr'],cap[1]['pid'],closure(built['tool_closures']['rust-interp-mir-export'],built['built_files']['rust-interp-mir-export']['path']),binding['runtime_driver']['path'],'exporter')
read(Path(__file__).absolute())
for p,row in list(checked.items()):need(ident(Path(p).lstat())==row['identity'],'final unchanged identity '+p)
result=dict(status='verified',reviewer='X independent saved evidence',pid=os.getpid(),parent_pid=os.getppid(),started_at=began,finished_at=time.time(),metadata_children=36,build_children=7,cargo_compiles=44,source_files_rehashed=238,phase_refs=phase_refs,built_files=built['built_files'],generated=built['generated'],dyld=stats,checked_files=checked,closed_trees=trees,compiler_calls=0,provider_probes=0,provider_payloads_rehashed=False,application_qualified=False,frontend_qualified=False,performance_qualified=False,limitations=['Saved source/argv/raw/closed wait verification only; no provider payload rehash or current loader resolution probe.','Four build-script role probes are source, Cargo and generated-output evidence, not four separately supervised child receipts.','Short-lived command identity records may lack successful cwd observation; exact saved spawn cwd and parent/child receipts are retained.','Build result captures frontend/publication unexecuted at its own closure, not a claim about later phases.'])
need(not OUT.exists(),'fresh report');OUT.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(report=str(OUT),sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),files=len(checked),dyld=stats)))
