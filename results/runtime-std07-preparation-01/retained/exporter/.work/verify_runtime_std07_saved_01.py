"""Finite readback of closed ordinary std07 evidence; no imports/probes/workloads."""
import hashlib,json,os,stat,time
from pathlib import Path
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H=ROOT/'experiments/runtime-std-after-installation07-01'
L=R/'.work/hir-options-hash-runtime-std-launch-execution-07-01'
O=R/'.work/experiments/hir-options-hash-runtime-std-supervisor-07-01'
W=R/'.work/hir-options-hash-runtime-std-supervision-07-01'
RUN=R/'.work/hir-options-hash-runtime-std-07-01'
OUT=X/'.work/runtime-std07-independent-readback-01.json'
CHECKED={}
def stamp(p):
 s=p.lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
def raw(p,expected=None,remember=True):
 p=Path(p);before=stamp(p)
 assert p.resolve(strict=True)==p and stat.S_ISREG(before[2]) and before[3]<=128*2**20
 with p.open('rb') as f:b=f.read()
 assert stamp(p)==before and len(b)==before[3]
 row=dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),identity=before)
 if expected:assert row['sha256']==expected,str(p)
 if remember:
  assert str(p) not in CHECKED or CHECKED[str(p)]==row
  CHECKED[str(p)]=row
 return b,row
def read(p,expected=None):return json.loads(raw(p,expected)[0])
def sha(p):return raw(p)[1]['sha256']
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def tree(root,files,stamps):
 assert len(stamps)<=10000 and '.' in stamps and sum(s[3] for s in stamps.values() if stat.S_ISREG(s[2]))<=384*2**20
 children={n:set() for n,s in stamps.items() if stat.S_ISDIR(s[2])}
 for n in stamps:
  if n!='.':children[str(Path(n).parent)].add(Path(n).name)
 count=total=0
 for n,s in stamps.items():
  p=root/n;current=stamp(p);assert current[:6]==s and not s[2]&0o222
  if stat.S_ISDIR(s[2]):assert set(os.listdir(p))==children[n]
  else:
   assert stat.S_ISREG(s[2]) and current[6]==1 and n in files
   b,_=raw(p,files[n],remember=False);count+=1;total+=len(b)
 assert count==len(files)
 for n,s in stamps.items():assert stamp(root/n)[:6]==s
 return dict(files=count,bytes=total,entries=len(stamps),exact_membership=True,immutable=True,full_sha_readback=True,stamps_sha256=digest(stamps))
def span_text(span,b):
 assert not b.startswith(b'\xef\xbb\xbf') and b'\r' not in b
 lines=b.decode('utf-8').split('\n')
 assert 1<=span['line_start']<=span['line_end']<=len(lines)
 for end in ['start','end']:
  line,column=span['line_'+end],span['column_'+end];assert 1<=column<=len(lines[line-1])+1
  offset=sum(len(s.encode())+1 for s in lines[:line-1])+len(lines[line-1][:column-1].encode())
  assert span['byte_'+end]==offset
 assert span['byte_start']<=span['byte_end']
 return [dict(text=lines[n-1],highlight_start=span['column_start'] if n==span['line_start'] else 1,highlight_end=span['column_end'] if n==span['line_end'] else len(lines[n-1])+1) for n in range(span['line_start'],span['line_end']+1)]
def main():
 start=time.time();plan=read(H/'plan.json','5ff7bd5e9ef6365d0f2e9083338bf688ebcf49dde51753be007be8ddceb39354');frozen=read(H/'inputs.json','9e7194aa46b2eb895b6340c64750ed99fbefba1020cc4b334c5d0c93464304e8');launch=read(H/'launch.json','91313c000f00a68929e0ef137286d707a7e2c4d5dddc84c64cb52d9374a29157')
 entry=read(L/'record.json','21586fa1fc3dca5e3c2ca5f8a9fe1afec18cbfc8e881682a9ed1e50f05e52200');outer=read(O/'status.json',entry['outer_sha256']);record=read(W/'receipt.json',entry['controller_receipt']['sha256']);child=read(W/'command/receipt.json',record['child']['sha256'])
 assert entry['status']=='terminal-observed' and outer['status']==child['status']=='finished' and record['status']=='passed'
 assert entry['launcher_returncode']==entry['returncode']==outer['returncode']==child['returncode']==0 and 'observation_error' not in entry
 assert entry['wrapper_may_be_live'] is False and entry['controller_may_be_live'] is False and entry['detached_supervisor_os_closure_observed'] is False
 assert entry['command']==launch['command'] and outer['command']==launch['command'][6:] and entry['environment']==launch['environment']==record['environment']==child['environment']==plan['environment']
 expected_cli=list(plan['command']);assert expected_cli[4]=={'source_freeze_sha256':True};expected_cli[4]=sha(H/'inputs.json')
 assert child['command']==record['command']==expected_cli and child['cwd']==entry['cwd']==outer['cwd']==str(R)
 assert entry['supervisor_pid']==outer['supervisor_pid']==record['parent_pid']==child['parent_pid']==24837
 assert entry['controller_pid']==outer['child_pid']==record['pid']==child['supervisor_pid']==24840
 assert child['pid']==24842 and entry['pid']==24836 and entry['launcher_pid']==24115
 times=[entry['started_at'],outer['started_at'],record['started_at'],child['started_at'],child['finished_at'],record['finished_at'],outer['finished_at'],entry['terminal_observed_at']];assert times==sorted(times)
 assert sha(O/'plan.json')==outer['plan_sha256'] and sha(O/'command.log')==outer['log_sha256']
 for name,row in entry['supervisor_evidence'].items():
  assert sha(row['path'])==row['sha256']==sha(row['retained_path'])
 for name in ['stdout','stderr']:
  assert sha(L/name)==entry[name+'_sha256'] and sha(W/'command'/name)==child[name+'_sha256']
 assert raw(L/'stderr')[0]==raw(W/'command/stderr')[0]==b''
 total=0
 for p,h in frozen['files'].items():
  b,_=raw(p,h);assert len(b)<=32*2**20;total+=len(b);raw(W/'inputs'/p.lstrip('/'),h)
 assert len(frozen['files'])==138 and total==frozen['input_bytes']==record['retained_input_bytes']==53444566
 ready=read(record['ready']['path'],record['ready']['sha256']);result=read(record['result']['path'],record['result']['sha256']);work=Path(record['sysroot']).parent;identity=ready['identity']
 assert result['status']=='passed' and result['commands']==7 and result['key']==record['std_key']==ready['key']==work.name==digest(identity)
 assert ready['owner']==str(R) and identity['compiler_key']==plan['runtime_key'] and identity['namespace']==plan['namespace'] and identity['recipe']==plan['cargo_recipe']
 assert read(work/'owner.json')==dict(owner=str(R),identity=identity,run_id=ready['run_id'])
 assert ready['probes']==['native','prepared'] and ready['full_presentation_qualified'] is False and result['full_presentation_qualified'] is False and result['strict_integration_required'] is True
 runtime=Path(identity['compiler_sysroot']);source_prefix='lib/rustlib/src/rust/library/'
 rready=read(record['runtime_prerequisite']['ready']['path'],record['runtime_prerequisite']['ready']['sha256'])
 assert identity['source_files']=={p[len(source_prefix):]:h for p,h in rready['identity']['files'].items() if p.startswith(source_prefix)}
 assert identity['source_sha256']==rready['identity']['source_sha256'] and identity['compiler_source_commit']==plan['compiler_source_commit']
 runenv=dict(plan['environment']);runenv.update(RUSTC_WRAPPER='',RUSTC_WORKSPACE_WRAPPER='',CARGO_TERM_COLOR='never')
 buildenv=dict(runenv);buildenv.update(PATH=str(runtime/'bin')+os.pathsep+runenv['PATH'],RUSTC=str(runtime/'bin/rustc'))
 if (runtime/'bin/rustdoc').exists():buildenv['RUSTDOC']=str(runtime/'bin/rustdoc')
 buildenv.update(ready['environment']);probeenv={k:v for k,v in buildenv.items() if k not in ['RUSTFLAGS','__CARGO_RUSTC_BOOTSTRAP_WS_REMAP']}
 assert digest(buildenv)==identity['build_environment_sha256']
 cargo=plan['cargo_executable'];expected=[['rustup','which','--toolchain','nightly-2026-09-08','cargo'],[cargo,'-Vv'],['/usr/bin/otool','-arch','arm64','-L',cargo],['/usr/bin/otool','-arch','arm64','-l',cargo]]
 for label,sysroot in [('native',runtime),('prepared',work/'sysroot')]:
  d=RUN/('probe-'+label);argv=[str(runtime/'bin/rustc'),str(d/'source.rs'),'--crate-type=lib','--edition=2024','--emit=metadata','--error-format=json','--sysroot',str(sysroot),'-o',str(d/'probe.rmeta')]
  if label=='prepared':expected.append(ready['command'])
  expected.append(argv)
 expanded=[cargo]
 for item in identity['recipe']:
  expanded.append(item if isinstance(item,str) else identity['target'] if item=={'compiler_host':True} else '-Zroot-dir='+str(work) if item=={'std_root':True} else str(work/item['std_work']))
 assert ready['command']==expanded and ready['sysroot_files']==ready['metadata']|{source_prefix+p:h for p,h in identity['source_files'].items()}
 assert len(ready['metadata'])==26 and all(p.endswith('.rmeta') for p in ready['metadata'])
 for crate in ['core','alloc','std','test','proc_macro']:assert sum(Path(p).name.startswith('lib'+crate+'-') for p in ready['metadata'])==1
 rows=read(RUN/'commands.json');assert len(rows)==7;previous=child['started_at'];pids=set();proofs=[];probe_observations={}
 for i,(row,declared,argv) in enumerate(zip(rows,plan['expected_outer_cli_children'],expected,strict=True)):
  label=declared['label'];proc=read(RUN/(label+'-process.json'));assert row==read(RUN/(label+'.json'))
  assert row['label']==proc['label']==label and row['command']==proc['command']==argv and row['returncode']==proc['returncode']==declared['returncode'] and proc['status']=='finished'
  assert proc['pid'] not in pids and proc['parent_pid']==child['pid'];pids.add(proc['pid']);assert previous<=proc['started_at']<=proc['finished_at']<=child['finished_at'];previous=proc['finished_at']
  assert proc['cwd']==str(work if label=='metadata' else RUN/label if label.startswith('probe-') else RUN)
  env=runenv if i<4 else buildenv if label=='metadata' else probeenv;assert row['environment_sha256']==proc['environment_sha256']==digest(env)
  assert b'internal compiler error' not in row['stderr'].encode()
  proofs.append(dict(label=label,pid=proc['pid'],returncode=proc['returncode'],process_sha256=sha(RUN/(label+'-process.json')),raw_sha256={s:hashlib.sha256(row[s].encode()).hexdigest() for s in ['stdout','stderr']}))
  if label.startswith('probe-'):
   assert not row['stdout'] and list((RUN/label).iterdir())==[RUN/label/'source.rs'];ds=[json.loads(line) for line in row['stderr'].splitlines()]
   assert any(d.get('level')=='error' and (d.get('code') or {}).get('code')=='E0080' for d in ds)
   source=(runtime if label=='probe-native' else work/'sysroot')/source_prefix;seen=set();pending=[ds]
   while pending:
    val=pending.pop()
    if isinstance(val,list):pending.extend(val)
    elif isinstance(val,dict):
     if 'file_name' in val:
      p=Path(val['file_name'])
      if p.is_absolute() and p.is_relative_to(source):
       rel=str(p.relative_to(source));assert rel in identity['source_files'];payload,_=raw(p,identity['source_files'][rel]);assert val['text'] and val['text']==span_text(val,payload);seen.add(rel)
      else:assert not str(p).startswith(('/rustc/','library/','core/','std/'))
     pending.extend(val.values())
   assert {'core/src/panic.rs','std/src/macros.rs'}<=seen;probe_observations[label]=sorted(seen)
 trees={'library':tree(work/'library',identity['source_files'],ready['snapshot_stamps']),'sysroot':tree(work/'sysroot',ready['sysroot_files'],ready['sysroot_stamps']),'evidence':tree(work/'evidence',ready['evidence_files'],ready['evidence_stamps'])}
 for p,h in ready['evidence_files'].items():raw(RUN/p,h)
 assert set(p.name for p in work.iterdir())=={'evidence','owner.json','target','library','ready.json','sysroot'}
 assert not (work/'ready.json').stat().st_mode&0o222
 for p,row in CHECKED.items():assert stamp(Path(p))==row['identity']
 report=dict(status='verified',owner='/root/workspace_capacity',started_at=start,finished_at=time.time(),reader_sha256=sha(Path(__file__)),runtime_key=plan['runtime_key'],std_key=ready['key'],sysroot=str(work/'sysroot'),ready=dict(path=record['ready']['path'],sha256=record['ready']['sha256']),receipt_sha256=sha(W/'receipt.json'),result_sha256=sha(RUN/'result.json'),launch_execution_sha256=sha(L/'record.json'),actual_commands=proofs,trees=trees,probe_source_observations=probe_observations,frozen_and_retained_files=138,frozen_bytes=total,all_raw_preserved=True,source_and_output_unchanged=True,full_presentation_qualified=False,application_qualified=False,benchmark=False,reexecuted_commands=0,target_imports=0,provider_tree_walk=False,detached_supervisor_os_reaped=False,closure_scope=entry['closure_scope'],checked_files=CHECKED)
 with OUT.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps(dict(status='verified',report=str(OUT),sha256=sha(OUT),std_key=ready['key'],runtime_key=plan['runtime_key'],trees=trees),sort_keys=True))
if __name__=='__main__':main()
