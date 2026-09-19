"""Deploy four reviewed source files exclusively; run only two help commands."""
from pathlib import Path
import hashlib, json, os, stat, subprocess, time

HERE=Path(__file__).resolve().parent
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE=ROOT/'experiments/workflow-runtime-arms-standalone-01'
OWNER=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
DEST=OWNER/'experiments/workflow-runtime-arms-01'
PYTHON='/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14'
EXPECTED={
 'bench_e2e_workflow.py':'52cb0fc1757293426b660698042ca4e9a19d3066a38444c815e9a67354425cf6',
 'verify_repeated_workflow.py':'b0cedd66c9579c8acb0a1387aa827466b1ab675df8fc510dcd4662f20bd633f7',
 'workflow_runtime_arms.py':'57c7b2e1d5127a90d39599a9910bbac18c51c679a57656eff16556c621758822',
 'workflow_placement.py':'aaa2da72e61d73d6d8a061395502986e4473bc9941298953512e145c978c6678',
}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def identity(path):
 s=path.lstat()
 return dict(dev=s.st_dev,ino=s.st_ino,mode=s.st_mode,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,nlink=s.st_nlink)
def source(path):
 before=identity(path);assert stat.S_ISREG(before['mode']) and not path.is_symlink()
 payload=path.read_bytes();assert identity(path)==before
 return dict(path=str(path),sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),identity=before),payload
def write(name,value):
 with (HERE/name).open('x') as output:json.dump(value,output,indent=2,sort_keys=True);output.write('\n')
assert sha(Path(PYTHON))=='87d4df53fd91304be5bac391fb204643c36b7df2023c04a0953bcbc7d4fdf634'
help_proof=json.loads((SOURCE/'help-source-inspection.json').read_text())
assert sha(SOURCE/'help-source-inspection.json')=='c5daf951f1e3f8d07d147a98c476881b01007152061440fc5c31adabda971e1f'
base=json.loads((ROOT/'experiments/workflow-runtime-arms-01/base-sources.json').read_text())['sources']
originals={Path(p):row['sha256'] for p,row in base.items()}
originals.update({Path(row['source']['path']):row['source']['sha256'] for row in help_proof['source_graph'].values()})
original_rows={str(p):source(p)[0] for p in originals}
assert all(row['sha256']==originals[Path(p)] for p,row in original_rows.items())
selected={name:source(SOURCE/'proposed'/name) for name in EXPECTED}
assert all(row['sha256']==EXPECTED[name] for name,(row,payload) in selected.items())
assert not DEST.exists() and not DEST.is_symlink()
DEST.mkdir()
copied={}
for name,(row,payload) in selected.items():
 with (DEST/name).open('xb') as output:output.write(payload)
 copied[name]=source(DEST/name)[0]
 assert copied[name]['sha256']==row['sha256'] and copied[name]['bytes']==row['bytes']
 assert copied[name]['identity']['ino']!=row['identity']['ino'] and copied[name]['identity']['nlink']==1
 assert source(SOURCE/'proposed'/name)[0]==row
assert set(p.name for p in DEST.iterdir())==set(EXPECTED)
write('deployment.json',dict(status='deployed',destination=str(DEST),source={name:row for name,(row,payload) in selected.items()},files=copied,
 parent_pid=os.getpid(),parent_parent_pid=os.getppid(),finished_at=time.time(),original_R_sources=original_rows))
commands=help_proof['commands']
assert commands==[[PYTHON,'-E','-s','-B',str(DEST/name),'--help'] for name in ['bench_e2e_workflow.py','verify_repeated_workflow.py']]
environment=dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C')
completed=[]
for index,command in enumerate(commands):
 label='benchmark' if index==0 else 'verifier'
 for p,row in original_rows.items():assert source(Path(p))[0]==row
 for name,row in copied.items():assert source(DEST/name)[0]==row
 record=dict(status='starting',command=command,cwd=str(OWNER),environment=environment,parent_pid=os.getpid(),
 parent_parent_pid=os.getppid(),started_at=time.time(),sources_before=copied,originals_before=original_rows,
 runner_sha256=sha(Path(__file__)),deployment_sha256=sha(HERE/'deployment.json'))
 with (HERE/(label+'.stdout')).open('xb') as stdout,(HERE/(label+'.stderr')).open('xb') as stderr:
  child=subprocess.Popen(command,cwd=OWNER,env=environment,stdout=stdout,stderr=stderr)
  record.update(pid=child.pid,spawned_at=time.time());write(label+'-started.json',record)
  try:record['returncode']=child.wait(timeout=60)
  except subprocess.TimeoutExpired:
   record.update(status='wait-timeout-unclosed',observed_at=time.time());write(label+'-record.json',record);raise
 record.update(status='closed',finished_at=time.time(),stdout_sha256=sha(HERE/(label+'.stdout')),stderr_sha256=sha(HERE/(label+'.stderr')))
 record['sources_after']={name:source(DEST/name)[0] for name in EXPECTED}
 record['originals_after']={p:source(Path(p))[0] for p in original_rows}
 write(label+'-record.json',record)
 assert record['returncode']==0 and (HERE/(label+'.stderr')).stat().st_size==0
 output=(HERE/(label+'.stdout')).read_text();assert output.startswith('usage: ') and len(output.encode())<=262144
 if index==0:assert all(flag in output for flag in ['--baseline-runtime-compiler-key','--candidate-runtime-compiler-key','--baseline-std-mir-key','--candidate-std-mir-key'])
 assert record['sources_before']==record['sources_after'] and record['originals_before']==record['originals_after']
 assert set(p.name for p in DEST.iterdir())==set(EXPECTED)
 completed.append(dict(label=label,command=command,pid=child.pid,returncode=record['returncode'],record_sha256=sha(HERE/(label+'-record.json'))))
write('result.json',dict(status='passed',deployment_sha256=sha(HERE/'deployment.json'),commands=completed,
 sources_unchanged=True,original_R_sources_unchanged=True,only_help_executed=True,
 provider_or_benchmark_execution=False,finished_at=time.time()))
print(json.dumps(dict(status='passed',result_sha256=sha(HERE/'result.json'),deployment_sha256=sha(HERE/'deployment.json'),commands=completed)))
