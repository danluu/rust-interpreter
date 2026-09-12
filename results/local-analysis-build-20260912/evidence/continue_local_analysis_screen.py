from pathlib import Path
import hashlib,json,os,subprocess,time
root=Path(__file__).resolve().parents[2];work=Path(__file__).resolve().parent
original=work/'local-analysis-screen-controller.json';prior=json.loads(original.read_text())
assert len(prior['calls'])==10 and all(r['returncode']==0 for r in prior['calls'])
commands=prior['planned_commands'][10:];assert len(commands)==2
assert commands[0]['label']=='local-analysis-pgrust-20260912-03'
assert not (root/'.work/runs/local-analysis-pgrust-20260912-03').exists()
free=os.statvfs(root).f_bavail*os.statvfs(root).f_frsize;assert free>=3*2**30
receipt=work/'local-analysis-continuation-controller.json'
state={'owner':'build-general-20260912','controller_pid':os.getpid(),'cwd':str(root),'started_at':time.time(),'original_controller_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'free_bytes_at_admission':free,'reason':'Original controller stopped at3GiB admission gate after5 complete verified histories; remaining pgrust history was never started. Continue exact original final commands, no repeats or timing-based selection.','planned_commands':commands,'calls':[]}
with receipt.open('x') as f:json.dump(state,f,indent=2)
for item in commands:
 label,command=item['label'],item['command']
 with (work/(label+'-continuation.log')).open('x') as log:
  child=subprocess.Popen(command,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
  row={'label':label,'command':command,'child_pid':child.pid,'started_at':time.time(),'status':'running'};state['calls'].append(row);receipt.write_text(json.dumps(state,indent=2)+'\n')
  print('START',label,'pid',child.pid,flush=True)
  for line in child.stdout:
   log.write(line);log.flush()
   if not label.endswith('-verify'):print(line,end='',flush=True)
  code=child.wait();row.update(status='complete' if code==0 else 'failed',returncode=code,finished_at=time.time());receipt.write_text(json.dumps(state,indent=2)+'\n');print('END',label,code,flush=True)
  if code:raise SystemExit(code)
state.update(status='complete',finished_at=time.time());receipt.write_text(json.dumps(state,indent=2)+'\n')
