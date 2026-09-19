"""Independent finite closed frontend/publication readback. No target imports/probes."""
import hashlib,json,os,re,stat,time,math
from pathlib import Path
Q=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
F=Q/'experiments/host-wrapper-exporter-01';P=F/'packet-01'
OUT=X/'.work/host-wrapper-exporter-frontend-publication-independent-readback-01.json'
checked={};trees={};raws={};stats={};records={};commands={};phase_refs={};began=time.time()
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
 need(r['command']==o['command'][2:] and r['cwd']==str(X),'controller argv transport')
 if name=='build':need(r['environment']==launch['environment'],'build observed environment')
 need(r['inputs_sha256']==checked[str(P/'inputs.json')]['sha256'] and r['sources_sha256']==checked[str(F/'sources.json')]['sha256'] and r['plan_sha256']==checked[str(P/'plan.json')]['sha256'],'source packet pins')
 need(r['runtime_key']==plan['runtime_key'] and r['compiler_builds']==r['VM_builds']==r['guest_executions']==r['signals']==r['retries']==0 and r['performance_measurement'] is False,'phase scope')
 need(s['child_started_at']<=r['started_at']<=r['admitted_at']<=r['finished_at']<=s['finished_at'],'controller chronology')
 need(len(r['commands'])==count==len(schedule),'command count');previous=r['admitted_at'];rows=[]
 for i,(saved,wanted) in enumerate(zip(r['commands'],schedule,strict=True)):
  p=w/'commands'/f'{i:03d}'/'receipt.json';need(saved['path']==str(p) and saved['label']==wanted['label'],'command route')
  c=doc(p,saved['sha256']);need(c['status']=='finished' and c['returncode']==saved['returncode'] and c['returncode'] in wanted['expected'] and c['pid']==saved['pid'],'child closure')
  need(all(c[k]==wanted[k] for k in ('command','environment','cwd')),'exact child recipe '+wanted['label'])
  need(c['supervisor_pid']==r['pid'] and c['parent_pid']==r['parent_pid'] and previous<=c['started_at']<=c['finished_at']<=r['finished_at'],'child chronology/owner');previous=c['finished_at']
  data={st:read(p.parent/st,c[st+'_sha256']) for st in ('stdout','stderr')};raws[str(p)]=data
  if wanted.get('expected_stdout_sha256'):need(c['stdout_sha256']==wanted['expected_stdout_sha256'] and data['stderr']==b'','SDK declaration')
  rows.append((wanted,c,data,str(p)))
 records[name]=r;commands[name]=rows;phase_refs[name]=dict(execution=checked[str(ep/'record.json')],receipt=checked[str(w/'receipt.json')])
 for t in (ep,op,w):tree(t)
 return doc(r['result']['path'],ref=r['result'])

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
prior=doc(X/'.work/host-wrapper-exporter-metadata-build-independent-readback-01.json','fed3686ba4ea03166ac9a4d4269af5d8d735c7afb7681d97f256c6659665fa8b');need(prior['status']=='verified','prior readback')
plan=doc(P/'plan.json',ref=prior['checked_files'][str(P/'plan.json')]);launch=doc(P/'launch.json',ref=prior['checked_files'][str(P/'launch.json')]);inputs=doc(P/'inputs.json',ref=prior['checked_files'][str(P/'inputs.json')])
for name in ('sources.json','build-sources.json'):doc(F/name,ref=prior['checked_files'][str(F/name)])
frontsources=doc(F/'frontend-sources.json','9d8490fd749d92c9dc38c506e9e399fd8bd3073a8496bde4d23204f2d330d0b4')
pubsources=doc(F/'publication-sources.json','94a9faf5250e108dd3bd4014b219c1dd347548bc47f979a71782eb5d5decbb25')
need(len(frontsources['files'])==26 and len(pubsources['files'])==32,'source manifests')
for path,sha in pubsources['files'].items():read(path,sha)
read(F/'execute.py','4255fae6f1173f5ac44d05371b6034328b5d0bc698e28d8ca0e0376c4f3ae55f');read(F/'publication-launch.py','c0512833655a61c56861181d297d76728d6fee003fb9472fbef1697f66a8cfa0')
for row in plan['source_materialization'].values():frozen(row)
binding=plan['binding'];runtime=Path(binding['runtime']['default_sysroot']);B3=Path(binding['build_rustflags'][0].split('=',1)[1]);D=binding['build']['executable']['path'];target=X/'.work/host-wrapper-exporter-target-01';work=X/'.work/host-wrapper-exporter-frontend-01';fixture=work/'fixture';output=work/'outputs';baseenv=plan['launch_environment'];env=baseenv|{'TMPDIR':str(work/'tmp')+'/'}
built=doc(X/'.work/host-wrapper-exporter-build-01/built-tools.json','c2fefcc7f51e56de84b8c7f274b0bd881a7e79e8e617f87d89e116b2e14e20e9')
runplan=doc(work/'run-plan.json','3047b4b460f494e1a8987d7c885b1a91800159273500f3b4b2eb749863870c71')
clang=next(a.split('=',1)[1] for a in binding['build_rustflags'] if a.startswith('-Clinker='));exporter=str(target/'release/rust-interp-mir-export');wrapper=str(target/'release/rust-interp-rustc-wrapper')
def app(name,exe,test=False,sysroot=runtime,profile='native',state='original',error=None,wrap=None):
 a=[exe]+([str(wrap)] if wrap else [])+['--crate-name','role_test' if test else 'role_basic','--edition=2024','--crate-type','lib' if test else 'bin','-Copt-level=0','-Cdebuginfo=0','-Clinker='+clang,'--error-format=json','--emit=metadata']
 if test:a+=['--test','-Zalways-encode-mir=yes']
 if sysroot is not None:a+=['--sysroot',str(sysroot)]
 a += [str(fixture/('test_export.rs' if test else 'basic.rs')),'-o',str(output/(name+'.rmeta'))]
 return dict(name=name,argv=a,profile=profile,state=state,error=error)
apps=[dict(name='exporter-capabilities',argv=[exporter,'--rust-interp-capabilities'],profile='native',state='original',error=None),dict(name='wrapper-roles',argv=[wrapper,'--rust-interp-compiler-roles'],profile='native',state='original',error=None),app('basic-native',str(runtime/'bin/rustc')),app('basic-export-explicit-R',exporter,profile='basic'),app('basic-export-default-R',exporter,profile='basic',sysroot=None),app('wrapper-export-R',wrapper,profile='basic',wrap=runtime/'bin/rustc'),app('wrapper-reject-D',wrapper,profile='basic',wrap=D,error='wrong-role'),app('test-native',str(runtime/'bin/rustc'),test=True),app('test-export',exporter,test=True,profile='test'),app('test-discovery',exporter,test=True,profile='list')]
errors=[('type','E0308',b'\nfn uncalled_type_error() -> u32 { "wrong" }\n'),('borrow','E0515',b"\nfn uncalled_borrow_error() -> &'static u32 { let value = 3; &value }\n")]
for state,code,_ in errors:apps += [app('uncalled-'+state+'-native',str(runtime/'bin/rustc'),state=state,error=code),app('uncalled-'+state+'-export',exporter,profile='basic',state=state,error=code)]
apps += [app('restored-native',str(runtime/'bin/rustc')),app('restored-export',exporter,profile='basic'),app('reject-build-sysroot-native',str(runtime/'bin/rustc'),sysroot=B3,error='metadata'),app('reject-build-sysroot-export',exporter,sysroot=B3,profile='basic',error='metadata')]
need(apps==runplan['application_commands'] and len(apps)==18,'complete original18 recipe')
sdk=[r for r in plan['children'] if r['label'].startswith('sdk-') and not r['label'].startswith('sdk-after-')];schedule=[dict(r,environment=env,label='before-'+r['label']) for r in sdk]
for n in ('rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm'):
 binary=plan['adopted_VM']['binary']['path'] if n=='rust-interp-vm' else str(target/'release'/n)
 for flag in ('-L','-l'):schedule.append(dict(label=n+flag,command=['/usr/bin/otool','-arch','arm64',flag,binary],cwd=str(X),environment=env,expected=[0]))
for a in apps:
 e=env|{'RUST_INTERP_COMPILER_ARGV_RECORD_DIR':str(output/(a['name']+'-argv'))}
 if a['profile']!='native':
  e.update(RUST_INTERP_EXPORT_CRATE='role_test' if a['profile'] in ('test','list') else 'role_basic',RUST_INTERP_OUTPUT=str(output/(a['name']+('.json' if a['profile']=='list' else '.rbc'))))
  if a['profile'] in ('test','list'):e['RUST_INTERP_EXPORT_TEST']='1'
  if a['profile']=='list':e['RUST_INTERP_LIST_TESTS']='1'
  else:e['RUST_INTERP_ENTRY']='selected' if a['profile']=='test' else 'changing_value'
 schedule.append(dict(label=a['name'],command=a['argv'],cwd=str(fixture),environment=e,expected=[1,2] if a['error'] else [0]))
schedule += [dict(r,environment=env,label='after-'+r['label']) for r in sdk]
need(runplan==dict(children=schedule,application_commands=apps,diagnostic_pairs=9,direct_frontend_controls=18,fresh_loader_commands=6,sdk_commands=10,capacity=plan['capacity'],binding=binding,source_checkpoint=plan['source_checkpoint']),'full34 declaration')
front=phase('frontend','9b191f71d71a9d2d8b436b0cde5db81c366c52d0972232c27aac9757ab7ae363','a75c9650c711304a28fac3f5c61ec0191503b769ee017f7f71b7d8ce9f0e5586',34,schedule)
fr=records['frontend'];need(fr['source_restored'] is True and fr['source_unchanged'] is True and fr['frontend_qualified'] is True and fr['published'] is False,'frontend terminal')
need(fr['run_plan']==checked[str(work/'run-plan.json')] and fr['build']['result']==prior['checked_files'][str(X/'.work/host-wrapper-exporter-build-01/built-tools.json')],'frontend prior/result pins')
bylabel={w['label']:(c,data,p) for w,c,data,p in commands['frontend']};original={n:read(Path(plan['source_root'])/'tests/fixtures/borrowck-cache'/n) for n in ('basic.rs','test_export.rs')}
for n,b in original.items():need(read(fixture/n)==b,'restored current source')
states={'original':original['basic.rs']}|{n:original['basic.rs']+extra for n,code,extra in errors}
patterns={'scalar-frames':r'functions=(\d+) static_bytes_saved=(\d+) seconds=(\d+\.\d{6})','scalar-promotion':r'slots=(\d+) removed_addresses=(\d+) rewritten=(\d+) seconds=(\d+\.\d{6}) removed_moves=(\d+)','forwarding':r'wrappers=(\d+) calls=(\d+) longest_chain=(\d+) stage=(before-inline|final)','cfg':r'before=(\d+) after=(\d+) seconds=(\d+\.\d{6})','export':r'frontend_ms=(\d+\.\d{3}) lowering_ms=(\d+\.\d{3}) functions=(\d+) ops=(\d+) bytes=(\d+)'}
keys={'scalar-frames':['functions','static_bytes_saved','seconds'],'scalar-promotion':['slots','removed_addresses','rewritten','seconds','removed_moves'],'forwarding':['wrappers','calls','longest_chain','stage'],'cfg':['before','after','seconds'],'export':['frontend_ms','lowering_ms','functions','ops','bytes']}
compilerraw={};artifactraw={};source_rows=[]
need(len(front['children'])==18,'frontend18 outcomes')
for a,item in zip(apps,front['children'],strict=True):
 n=a['name'];c,data,p=bylabel[n];need(item['name']==n and item['receipt']==p and item['receipt_sha256']==checked[p]['sha256'],'frontend outcome association')
 need(frozen(item['source'])==(original['test_export.rs'] if n.startswith('test-') else states[a['state']]),'retained source state')
 source_rows.append(item['source']);raw=data['stderr'];need(b'internal compiler error' not in raw,'ICE');split=item['stderr_separation'];artifact=output/(n+('.json' if a['profile']=='list' else '.rbc'))
 if a['error']=='wrong-role':need(split is None and raw==b"compiler executable does not match the exporter's runtime toolchain\n" and not data['stdout'] and item['artifact'] is None and not artifact.exists(),'plain wrong role');compilerraw[n]=None
 else:
  need(split['raw_sha256']==hashlib.sha256(raw).hexdigest() and split['raw_bytes']==len(raw),'split raw');pos=0;compiler=[];tele=[];diags=[]
  for s in split['segments']:
   b=bytes.fromhex(s['raw_hex']);need(s['start']==pos and s['end']==pos+len(b) and raw[pos:pos+len(b)]==b and b.endswith(b'\n'),'lossless segment');pos+=len(b)
   if s['channel']=='compiler':
    d=json.loads(b);need(d==s['diagnostic'] and d['$message_type']=='diagnostic' and d['level'] in ('error','warning','note','help','failure-note'),'compiler diagnostic');compiler.append(b);diags.append(d)
   else:
    need(s['channel']=='telemetry' and a['profile'] in ('basic','test') and a['error'] is None,'allowed telemetry');text=b[:-1].decode();kind=s['kind'];prefix='rust-interp-'+kind+': ';need(text.startswith(prefix),'telemetry prefix')
    if kind=='aggregate-frames':
     value=json.loads(text[len(prefix):]);need(set(value)=={'capture_seconds','declines','finalize_seconds','functions','initialization_unchanged','static_bytes_saved'} and value['initialization_unchanged'] is True,'aggregate schema')
    else:
     m=re.fullmatch(patterns[kind],text[len(prefix):]);need(m is not None,'telemetry grammar');value={k:(v if k=='stage' else float(v) if k in ('seconds','frontend_ms','lowering_ms') else int(v)) for k,v in zip(keys[kind],m.groups(),strict=True)}
    need(value==s['values'],'telemetry values');tele.append(s)
  need(pos==len(raw) and b''.join(compiler).hex()==split['compiler_stderr_hex'],'complete split');compilerraw[n]=b''.join(compiler)
  if a['error']:
   need(item['artifact'] is None and not artifact.exists() and any(d['level']=='error' for d in diags),'negative diagnostic without artifact')
   if a['error']!='metadata':need(any((d.get('code') or {}).get('code')==a['error'] for d in diags),'required error code')
  elif n=='exporter-capabilities':need(not raw and json.loads(data['stdout'])=={k:v for k,v in built['capabilities'].items() if k!='runtime_wrapper'},'frontend capability')
  elif n=='wrapper-roles':need(not raw and json.loads(data['stdout'])==binding,'frontend wrapper roles')
  elif a['profile']!='native':
   need(item['artifact']['path']==str(artifact),'artifact route');ar=frozen(item['artifact']);artifactraw[n]=ar
   if a['profile']=='list':
    d=json.loads(ar);need(d['kind']=='test-discovery' and d['schema_version']==1 and d['strict_frontend'] is True and d['executed'] is False and d['harness']=='libtest' and d['target']=='aarch64-apple-darwin' and d['count']==1 and len(d['tests'])==1 and d['tests'][0]['name']=='selected' and d['tests'][0]['status']=='classified' and d['tests'][0]['ordinary_test'] is True,'test discovery');need(read(Path(a['argv'][-1]+'.tests.json'))==ar,'test sidecar')
   else:
    kinds=[s['kind'] for s in tele];base=['aggregate-frames','scalar-frames','scalar-promotion'];need(kinds in (base+['cfg','export'],base+['forwarding','cfg','export']) and tele[-1]['values']['bytes']==len(ar),'export telemetry');need(all(s['values']['stage']=='final' for s in tele if s['kind']=='forwarding'),'final forwarding');need(read(Path(a['argv'][-1]+'.rbc'))==ar,'RBC sidecar')
 argvdir=output/(n+'-argv');members=sorted(p.name for p in argvdir.iterdir())
 if a['profile']=='native' or a['error']=='wrong-role':need(item['compiler_argv'] is None and not members,'native/no compiler argv')
 else:
  r=item['compiler_argv'];need(Path(r['path']).parent==argvdir and members==[Path(r['path']).name] and members[0].startswith('exported-'),'argv file route');fields=frozen(r).split(b'\0');need(fields[-1]==b'' and fields[:4]==[b'rust-interp-compiler-argv-v1',b'exported',str(runtime).encode(),str(fixture).encode()],'argv header');argv=[x.decode() for x in fields[4:-1]]
  need(argv[0]==(str(runtime/'bin/rustc') if n=='wrapper-export-R' else exporter),'actual compiler first');roots=[argv[i+1] for i,v in enumerate(argv) if v=='--sysroot']+[v.split('=',1)[1] for v in argv if v.startswith('--sysroot=')];need(roots==[str(B3 if a['error']=='metadata' else runtime)] and str(fixture/('test_export.rs' if n.startswith('test-') else 'basic.rs')) in argv,'actual sysroot/source')
pairs=[['basic-native','basic-export-explicit-R'],['test-native','test-export'],['uncalled-type-native','uncalled-type-export'],['uncalled-borrow-native','uncalled-borrow-export'],['restored-native','restored-export'],['reject-build-sysroot-native','reject-build-sysroot-export'],['basic-native','basic-export-default-R'],['basic-native','wrapper-export-R'],['test-native','test-discovery']]
need(front['comparison_pairs']==pairs,'nine complete pairs')
for a,b in pairs:need(bylabel[a][1]['stdout']==bylabel[b][1]['stdout'] and compilerraw[a]==compilerraw[b],'raw compiler parity')
for n in ('basic-export-default-R','wrapper-export-R','restored-export'):need(artifactraw[n]==artifactraw['basic-export-explicit-R'],'bytecode parity')
need(bylabel['basic-native'][1]==bylabel['restored-native'][1],'restored raw diagnostics')
need(all(front[k] is True for k in ('raw_compiler_diagnostic_parity','telemetry_losslessly_retained','bytecode_parity','source_restored')) and front['whole_stderr_parity'] is False and front['guest_executions']==0,'correct result scope')
closures=doc(fr['tool_closures']['path'],ref=fr['tool_closures']);cache={}
meta=doc(X/'.work/host-wrapper-exporter-metadata-01/planned.json','0e326abd6b66d2232d9194de7b99732db1a633af2316d33594caf0574dff6fad')
for r in meta['loader_observations']:cache[(r['path'],r['flag'])]=(read(Path(r['receipt']).parent/'stdout',r['stdout_sha256']),r['receipt'],r['stdout_sha256'])
for w,c,data,p in commands['frontend'][5:11]:need(not data['stderr'],'fresh loader diagnostics');cache[(w['command'][-1],w['command'][3])]=(data['stdout'],p,c['stdout_sha256'])
need([c['name'] for c in closures]==['rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm'],'complete3 tool closures')
for item in closures:
 name=item['name'];cl={k:item[k] for k in ('identity','state')};closure(cl,item['binary']['path'])
 if name!='rust-interp-vm':need(cl==built['tool_closures'][name] and item['binary']==built['built_files'][name],'tool immutable closure')
 for flag,p in item['fresh_inspections'].items():need(p==bylabel[name+flag][2],'fresh otool association')
wp=X/'.work/host-wrapper-exporter-publication-01';pp=doc(wp/'publication-plan.json');key=pp['tool_key'];directory=Path(pp['directory']);need(key=='16ad5d9a14ce7711f124a49f09e820eae8cd85b10be0ebf3aeb5eecfdd2602e2' and directory==R/'.work/interpreter-tools'/key,'published route')
pub=phase('publication','a06d0765e6de91448f62eb241a758108735d8ae6b04e253bac3290502b221773','c0a2125c1713634864068582bbf6a6090b671a987bf93f4be50f15d2e5135aac',4,pp['children'])
pr=records['publication'];need(fr['finished_at']<=pr['started_at'] and pr['frontend_receipt_sha256']==phase_refs['frontend']['receipt']['sha256'] and pr['publication'] is True and pr['frontend_qualified'] is True and pr['tool_key']==key,'publication phase order/pins')
need(pr['published_tools_sha256']==checked[str(wp/'published-tools.json')]['sha256'] and pub['tool_key']==key and pub['directory']==str(directory),'published result')
need(len(pp['children'])==4,'four publication calls')
envpub=baseenv|{'TMPDIR':str(wp/'tmp')+'/'}
expected=[dict(label='published-exporter',command=[str(directory/'rust-interp-mir-export'),'--rust-interp-capabilities'],cwd=str(X),environment=envpub|{'DYLD_PRINT_LIBRARIES':'1'},expected=[0]),dict(label='published-wrapper',command=[str(directory/'rust-interp-rustc-wrapper'),'--rust-interp-compiler-roles'],cwd=str(X),environment=envpub,expected=[0]),dict(label='published-host-codegen',command=[str(directory/'rust-interp-rustc-wrapper'),'--rust-interp-host-codegen-capability'],cwd=str(X),environment=envpub,expected=[0]),dict(label='ordinary-installed-reader',command=['/opt/homebrew/bin/python3','-B',str(F/'validate_published.py'),'--publication-sources-sha256',pr['publication_sources_sha256'],'--tool-key',key,'--runtime-compiler-key',plan['runtime_key']],cwd=str(R),environment=envpub,expected=[0])]
need(pp['children']==expected,'publication exact recipe')
need(set(p.name for p in directory.iterdir())=={'rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm','compiler.json','ready.json','capabilities.json'} and stat.S_IMODE(directory.stat().st_mode)==0o555,'installed exact membership')
for name,item in pub['copied'].items():
 src=item['source'];dest=item['destination'];need(ident(Path(src['path']).lstat())==src['identity'] and src['sha256']==dest['sha256']==built['binaries'][name] and src['identity'][:2]!=dest['identity'][:2] and dest['identity'][6]==1,'separate immutable copy');frozen(dest);need(stat.S_IMODE(dest['identity'][2])==0o555,'installed executable mode')
ready=doc(directory/'ready.json');caps=doc(directory/'capabilities.json');composition=doc(directory/'compiler.json')
for name in ('ready.json','capabilities.json','compiler.json'):need(stat.S_IMODE(checked[str(directory/name)]['identity'][2])==0o444,'installed metadata mode')
need(ready==built['binaries'] and caps==pub['capabilities'] and composition==pub['composition']==pp['composition'],'installed typed metadata')
need(hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()==key,'composition key')
need(composition['compiler_key']==plan['runtime_key'] and composition['compiler_roles']==binding and composition['source']['files']=={r['path']:r['sha256'] for r in plan['source_materialization'].values()} and composition['source']['overlay']==plan['source_overlay'] and composition['actual_build']['tools']==prior['checked_files'][str(X/'.work/host-wrapper-exporter-build-01/built-tools.json')],'composition exact source/build')
need(composition['direct_frontend']==pr['frontend'] and composition['direct_frontend']['receipt']==phase_refs['frontend']['receipt'],'frontend composed refs')
for k in ('benchmark','host_codegen_application_qualified'):need(pub[k] is False and composition[k] is False,'no application/performance claim')
need(pub['guest_execution'] is False and pub['frontend_host_codegen_mode']==composition['frontend_host_codegen_mode']=='off','frontend old mode scope')
p0,p1,p2,p3=commands['publication'];rawcap=json.loads(p0[2]['stdout']);need(rawcap=={k:v for k,v in built['capabilities'].items() if k!='runtime_wrapper'},'published raw caps');need(json.loads(p1[2]['stdout'])==binding and not p1[2]['stderr'],'wrapper roles')
lines=p2[2]['stdout'].decode().splitlines();need(not p2[2]['stderr'] and len(lines)==3 and json.loads(lines[0])==rawcap['host_codegen_opt'] and lines[1]==str(runtime) and json.loads(lines[2])==binding,'actual3line host capability')
expectedcaps=built['capabilities']|dict(tool_key=key,exporter_sha256=built['binaries']['rust-interp-mir-export'],host_codegen_wrapper=dict(sha256=built['binaries']['rust-interp-rustc-wrapper'],capability=rawcap['host_codegen_opt'],compiler_sysroot=str(runtime),compiler_roles=binding))
need(caps==expectedcaps,'exact capability augmentation')
need(not p3[2]['stderr'] and json.loads(p3[2]['stdout'])==dict(status='passed',tool_key=key,runtime_key=plan['runtime_key'],directory=str(directory)),'ordinary installed reader passed')
for field,row in [('actual_exporter_probe',p0),('actual_wrapper_probe',p1),('actual_host_codegen_probe',p2),('installed_validation',p3)]:need(pub[field]==row[3],'publication probe association')
allowed={str(directory/'rust-interp-mir-export')}|{r['resolved'] for r in closures[0]['identity']['libraries']}
dyld(pub['loaded_images'],p0[2]['stderr'],p0[1]['pid'],allowed,binding['runtime_driver']['path'],'published-exporter')
for root in (work,wp):
 for rel,kind in trees[str(root)]:
  if kind=='f':read(root/rel)
read(Path(__file__).absolute())
for p,row in list(checked.items()):need(ident(Path(p).lstat())==row['identity'],'unchanged final ref '+p)
result=dict(status='verified',reviewer='X saved-only independent frontend/publication',pid=os.getpid(),parent_pid=os.getppid(),started_at=began,finished_at=time.time(),checked_files=checked,closed_trees=trees,phase_refs=phase_refs,frontend_children=34,frontend_controls=18,diagnostic_pairs=9,frontend_successes=sum(c['returncode']==0 for w,c,d,p in commands['frontend']),frontend_expected_failures=sum(c['returncode']!=0 for w,c,d,p in commands['frontend']),lossless_stderr_separations=17,plain_wrong_role_refusal=1,raw_compiler_parity=True,whole_stderr_parity=False,bytecode_parity=True,source_restored=True,publication_children=4,published_members=6,tool_key=key,directory=str(directory),separate_binary_copies=True,ordinary_installed_reader_passed=True,host_codegen_capability_bound=True,frontend_host_codegen_mode='off',host_codegen_application_qualified=False,application_qualified=False,performance_qualified=False,compiler_calls=0,provider_probes=0,provider_payloads_rehashed=False,dyld=stats,limitations=['No compiler/provider probes or workload replay; actual recorded target binaries were not executed by this reader.','Three installed binary copies were fully EOF/SHA verified; original adopted VM was checked by its exact current seven-field stamp and frozen digest association.','Frontend full18 runs with combined host policy off. Publication capability binding is not host-on application correctness or a timing claim.'])
need(not OUT.exists(),'fresh report');OUT.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(report=str(OUT),sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),checked=len(checked),tool_key=key)))
