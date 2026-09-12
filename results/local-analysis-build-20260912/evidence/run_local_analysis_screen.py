from pathlib import Path
import hashlib,json,os,subprocess,sys,time
root=Path(__file__).resolve().parents[2]
work=Path(__file__).resolve().parent
baseline=json.loads((work/'current-baseline-tools.json').read_text())['tool_key']
candidate=json.loads((work/'local-analysis-tools.json').read_text())['tool_key']
common=['--cycles','1','--jobs','18','--native-jobs','18','--native-profile','repository','--native-test-threads','1','--check-floor','--minimum-free-gib','1','--lock-wait-seconds','300','--baseline-tool-key',baseline,'--candidate-tool-key',candidate,'--comparison-engine','jit','--baseline-jit-resumable-calls','--baseline-jit-persistent-registers','--candidate-jit-resumable-calls','--candidate-jit-persistent-registers','--batch','--inline-leaves','--baseline-inline-leaves','--trap-unsupported-calls','--run-try-callbacks','--std-mir','--instruction-limit','100000000000','--allocation-limit','150000','--guest-mir-opt-level','3','--guest-mir-inline-scale','8','--build-tool-opt-level','0','--expect-identical-bytecode','--build-metrics','--verify-restoration']
orders=['native,baseline,candidate','baseline,candidate,native','candidate,native,baseline']
commands=[]
for i,order in enumerate(orders,1):
 for label,project,workflow in [('token','fre',['--workflow','token-phrase-allocation']),('pgrust','pgrust',[])]:
  name=f'local-analysis-{label}-20260912-{i:02}'
  commands.append((name,[sys.executable,'scripts/bench_e2e_workflow.py','--run-id',name,'--project',project,*workflow,'--initial-mode-order',order,*common]))
  commands.append((name+'-verify',[sys.executable,'scripts/verify_repeated_workflow.py',f'results/{name}/summary.json','--wait-for-lock','300']))
receipt=work/'local-analysis-screen-controller.json'
state={'owner':'build-general-20260912','controller_pid':os.getpid(),'controller_ppid':os.getppid(),'cwd':str(root),'started_at':time.time(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'planned_commands':[{'label':n,'command':c} for n,c in commands],'calls':[]}
with receipt.open('x') as f:json.dump(state,f,indent=2)
for label,command in commands:
 if not label.endswith('-verify'):
  assert os.statvfs(root).f_bavail*os.statvfs(root).f_frsize >= 3*2**30, 'history admission requires3GiB'
 with (work/(label+'-controller.log')).open('x') as log:
  child=subprocess.Popen(command,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
  row={'label':label,'command':command,'child_pid':child.pid,'started_at':time.time(),'status':'running'};state['calls'].append(row)
  receipt.write_text(json.dumps(state,indent=2)+'\n');print('START',label,'pid',child.pid,flush=True)
  for line in child.stdout:
   log.write(line);log.flush()
   if not label.endswith('-verify'):print(line,end='',flush=True)
  code=child.wait();row.update(returncode=code,finished_at=time.time(),status='complete' if code==0 else 'failed')
  receipt.write_text(json.dumps(state,indent=2)+'\n');print('END',label,code,flush=True)
  if code:sys.exit(code)
state['finished_at']=time.time();state['status']='complete';receipt.write_text(json.dumps(state,indent=2)+'\n')
