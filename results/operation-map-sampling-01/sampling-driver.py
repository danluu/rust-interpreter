from pathlib import Path
import json, os, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha, acquire_lock
from workflow_io import capture, require_space, write_json as write
work=ROOT/'.work/operation-map-sampling-01';work.mkdir(exist_ok=False)
proof=ROOT/'results/memory-operands-profile-01/summary.json'
prior=json.loads(proof.read_text());assert prior['status']=='passed' and prior['commands']==3
key='d4a6ff9a73f831178a8c95e835ef5d17afce57e38c590148be8c04438dbc4a44'
artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
catalog=artifact.with_name('490789b82f653196fba00fdb290821edaae0ddc6b152aaf84f93bc815077a794.json')
paths=[Path(__file__),proof,artifact,catalog,ROOT/'benchmarks/experiments/operation-map/QUALIFICATION.md']
paths += [ROOT/'scripts'/n for n in ['sample_owned_vm.py','summarize_owned_sample.py','attribute_generated_sample.py','compare_saved_runtime.py','workflow_io.py','interpreter.py']]
qualification_path=ROOT/'results/operation-map-real-01/summary.json'
qualification=json.loads(qualification_path.read_text());assert qualification['status']=='passed' and qualification['tool_key']==key and qualification['exact_adopted_code']
paths.append(qualification_path)
paths += [p for p in (ROOT/'benchmarks/experiments/operation-map').iterdir() if p.is_file()]
for name,expected in [('operation-map-python-tests-01',103),('operation-map-attribution-tests-01',3)]:
 test_path=ROOT/'results'/name/'summary.json';test=json.loads(test_path.read_text());assert test['status']=='passed' and test['tests']==expected
 inputs=ROOT/test['raw']/'inputs.json';assert sha(inputs)==test['inputs_sha256'];assert all(sha(ROOT/p)==h for p,h in json.loads(inputs.read_text()).items())
 paths += [test_path,inputs]
frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_executions=2,performance_measurement=False,tool_key=key))
assert not any(k.startswith('DYLD_') for k in os.environ)
records=[]
for index,label in enumerate(['block','exhaustive']):
 run='operation-map-sample-'+label+'-01'
 commands=[['scripts/sample_owned_vm.py','--tool-key',key,'--artifact',str(artifact),'--artifact-sha256',sha(artifact),'--run-id',run,'--repetitions','1','--duration','3','--instruction-limit','100000000000','--allocation-limit','150000','--jit-persistent-registers','--jit-resumable-calls','--dump-code','--jit-operation-map','--select-test',prior['comparisons'][index]['name'],'--suite-catalog',str(catalog),'--lock-wait-seconds','45','--minimum-free-bytes',str(8*1024**3)],['scripts/summarize_owned_sample.py','--run-id',run],['benchmarks/experiments/operation-map/attribute.py','--case',label,'--run-id',run]]
 for stage,command in enumerate(commands):
  assert all(sha(ROOT/p)==h for p,h in frozen.items())
  require_space(ROOT,8)
  # The sampler holds the shared lock itself; offline analysis takes it here.
  lock=None
  if stage:
   lock=(ROOT/'.work/benchmark.lock').open('a');acquire_lock(lock,45)
  try:
   child,out,err=capture([sys.executable,*command],cwd=ROOT,env=os.environ.copy(),receipt_path=work/'active.json',receipt=dict(case=label,stage=stage))
   row=dict(case=label,stage=stage,pid=child.pid,command=command,returncode=child.returncode,stdout=out,stderr=err)
   records.append(row);write(work/'records.json',records)
   assert child.returncode==0,err+out
  finally:
   if lock:lock.close()
  print(label,stage,'passed',flush=True)
assert all(sha(ROOT/p)==h for p,h in frozen.items())
write(work/'summary.json',dict(status='passed',guest_executions=2,commands=6,performance_measurement=False))
