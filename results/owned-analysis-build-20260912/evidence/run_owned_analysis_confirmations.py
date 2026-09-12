from pathlib import Path
import fcntl,hashlib,json,os,shutil,stat,subprocess,sys,time

root=Path(__file__).resolve().parents[2]
work=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
plan_path=work/'owned-analysis-public-confirmation-plan.json'
plan=json.loads(plan_path.read_text())
screen_path=work/'owned-analysis-screen-assessment.json'
assert json.loads(screen_path.read_text())['screen_pass']
for name,digest in plan['proofs'].items():assert sha(Path(name))==digest,name
for mode in ['baseline','candidate']:
 for name,digest in plan[mode]['binaries'].items():
  assert sha(Path(plan[mode]['directory'])/name)==digest,name
sources=json.loads((work/'owned-analysis-confirm-sources.json').read_text())
for name,details in sources['sources'].items():
 source=root/'.work/sources'/name
 assert source.resolve()==source and not source.is_symlink()
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==details['revision']
 assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=source,text=True)
 for filename,digest in details['files'].items():assert sha(source/filename)==digest
commands=plan['commands']
assert len(commands)==4
bound=[plan_path,work/'owned-analysis-public-confirmation-plan.md',screen_path,
       work/'owned-analysis-pre-screen-qualification.json',work/'owned-analysis-confirm-sources.json',
       Path(__file__),work/'assess_owned_analysis_confirmations.py']
state={'owner':'build-general-20260912','controller_pid':os.getpid(),'controller_ppid':os.getppid(),
       'cwd':str(root),'started_at':time.time(),'planned_commands':commands,'calls':[],
       'proofs':{str(p.relative_to(root)):sha(p) for p in bound},'admissions':[]}
receipt=work/'owned-analysis-confirmation-controller.json'
with receipt.open('x') as f:json.dump(state,f,indent=2)
def save():receipt.write_text(json.dumps(state,indent=2)+'\n')
def admit(label):
 lock=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock').open('r+b')
 started=time.time();deadline=time.monotonic()+300
 try:
  while True:
   try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
   except BlockingIOError:
    if time.monotonic()>=deadline:raise RuntimeError('confirmation admission lock unavailable')
    time.sleep(1)
  held=os.fstat(lock.fileno());named=os.stat(lock.name)
  assert stat.S_ISREG(held.st_mode) and (held.st_dev,held.st_ino)==(named.st_dev,named.st_ino)
  minimum_gib=7.34 if label=='owned-analysis-confirm-ruff-20260912-01' else 21.74
  free=shutil.disk_usage(root).free
  state['admissions'].append({'label':label,'free_bytes':free,'minimum_gib':minimum_gib,
                             'lock_wait_started':started,'time':time.time(),'lock_identity':[held.st_dev,held.st_ino]});save()
  if free < minimum_gib*2**30:raise RuntimeError('confirmation admission capacity unavailable: '+label)
  assert not (root/'.work/runs'/label).exists() and not (root/'results'/label).exists(),'confirmation must be fresh'
  return lock
 except BaseException:
  lock.close();raise
try:
 for item in commands:
  label,command=item['label'],item['command']
  with (work/(label+'-controller.log')).open('x') as log:
   admission=None if label.endswith('-verify') else admit(label)
   try:
    child=subprocess.Popen(command,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
   finally:
    # Release immediately after spawning, before waiting for any child output.
    # The child independently acquires the same lock and retains its 1-GiB floor.
    if admission is not None:
     admission.close();state['admissions'][-1]['lock_released_at']=time.time()
   row={'label':label,'command':command,'child_pid':child.pid,'started_at':time.time(),'status':'running'}
   state['calls'].append(row);save();print('START',label,'pid',child.pid,flush=True)
   for line in child.stdout:
    log.write(line);log.flush()
    if not label.endswith('-verify'):print(line,end='',flush=True)
   code=child.wait();row.update(returncode=code,finished_at=time.time(),status='complete' if code==0 else 'failed');save()
   print('END',label,code,flush=True)
   if code:raise RuntimeError('confirmation command failed: '+label)
 state.update(status='complete',finished_at=time.time());save()
except BaseException as error:
 state.update(status='stopped',error=repr(error),finished_at=time.time());save();raise
