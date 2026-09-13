from pathlib import Path
import json, os, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import capture,write_json as write
work=ROOT/'.work/checked-addresses-validation-01';work.mkdir(exist_ok=False)
build='results/checked-addresses-build-02/summary.json'
harness_path=ROOT/'results/checked-addresses-python-tests-01/summary.json'
harness=json.loads(harness_path.read_text());assert harness['status']=='passed' and harness['tests']==121 and harness['skipped']==10
harness_inputs=ROOT/harness['raw']/'inputs.json'
assert sha(harness_inputs)==harness['inputs_sha256']
assert all(sha(ROOT/p)==h for p,h in json.loads(harness_inputs.read_text()).items())
stages=[
 ('qualification','benchmarks/experiments/selected-native-sampling/qualify.py',['--checked-addresses-candidate']),
 ('serial','benchmarks/experiments/parallel-suites/compare.py',['--checked-addresses-candidate','--phase','serial','--selection-qualification','results/checked-addresses-qualification-01/summary.json']),
 ('cache','benchmarks/experiments/composed-development/qualify_cache.py',['--checked-addresses-candidate','--automatic-cache']),
 ('profile','benchmarks/experiments/checked-addresses/profile.py',[])]
paths=[ROOT/script for _,script,_ in stages]+list((ROOT/'scripts').glob('*.py'))+[ROOT/'benchmarks/experiments/operation-map/maps.py']+[harness_path,harness_inputs,Path(__file__),ROOT/build,ROOT/'benchmarks/experiments/checked-addresses/PLAN.md']
frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,stages=stages,serialized=True,performance_measurement=False))
rows=[]
for stage,script,flags in stages:
 assert all(sha(ROOT/p)==h for p,h in frozen.items())
 command=[sys.executable,script,*flags,'--build',build,'--run-id','checked-addresses-'+stage+'-01']
 child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage=stage))
 (work/(stage+'.stdout')).write_text(out);(work/(stage+'.stderr')).write_text(err)
 rows.append(dict(stage=stage,command=command,pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/(stage+'.stdout')),stderr_sha256=sha(work/(stage+'.stderr'))))
 write(work/'records.json',rows)
 assert child.returncode==0,err
 result=ROOT/'results'/('checked-addresses-'+stage+'-01')/'summary.json'
 assert json.loads(result.read_text())['status']=='passed'
 rows[-1]['summary_sha256']=sha(result);write(work/'records.json',rows)
 print(stage,'PASS',flush=True)
assert all(sha(ROOT/p)==h for p,h in frozen.items())
destination=ROOT/'results/checked-addresses-validation-01';destination.mkdir(exist_ok=False)
write(destination/'summary.json',dict(status='passed',raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),stages=rows,performance_measurement=False))
