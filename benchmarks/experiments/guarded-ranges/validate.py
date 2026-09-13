from pathlib import Path
import json, os, sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import capture,write_json as write
work=ROOT/'.work/guarded-ranges-validation-01';work.mkdir(exist_ok=False)
build='results/guarded-ranges-build-01/summary.json'
harness_path=ROOT/'results/guarded-ranges-python-tests-01/summary.json'
harness=json.loads(harness_path.read_text());assert harness['status']=='passed' and harness['tests']==141 and harness['skipped']==10
harness_inputs=ROOT/harness['raw']/'inputs.json'
assert sha(harness_inputs)==harness['inputs_sha256']
assert all(sha(ROOT/p)==h for p,h in json.loads(harness_inputs.read_text()).items())
stages=[
 ('qualification','benchmarks/experiments/selected-native-sampling/qualify.py',['--guarded-ranges-candidate']),
 ('serial','benchmarks/experiments/parallel-suites/compare.py',['--guarded-ranges-candidate','--phase','serial','--selection-qualification','results/guarded-ranges-qualification-01/summary.json']),
 ('cache','benchmarks/experiments/composed-development/qualify_cache.py',['--guarded-ranges-candidate','--automatic-cache']),
 ('profile','benchmarks/experiments/guarded-ranges/profile.py',[])]
paths=[ROOT/script for _,script,_ in stages]+list((ROOT/'scripts').glob('*.py'))+[ROOT/'benchmarks/experiments/operation-map/maps.py']+[harness_path,harness_inputs,Path(__file__),ROOT/build,ROOT/'benchmarks/experiments/guarded-ranges/PLAN.md']
frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,stages=stages,serialized=True,performance_measurement=False))
rows=[]
for stage,script,flags in stages:
 assert all(sha(ROOT/p)==h for p,h in frozen.items())
 command=[sys.executable,script,*flags,'--build',build,'--run-id','guarded-ranges-'+stage+'-01']
 child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage=stage))
 (work/(stage+'.stdout')).write_text(out);(work/(stage+'.stderr')).write_text(err)
 rows.append(dict(stage=stage,command=command,pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/(stage+'.stdout')),stderr_sha256=sha(work/(stage+'.stderr'))))
 write(work/'records.json',rows)
 assert child.returncode==0,err
 result=ROOT/'results'/('guarded-ranges-'+stage+'-01')/'summary.json'
 assert json.loads(result.read_text())['status']=='passed'
 rows[-1]['summary_sha256']=sha(result);write(work/'records.json',rows)
 print(stage,'PASS',flush=True)
assert all(sha(ROOT/p)==h for p,h in frozen.items())
destination=ROOT/'results/guarded-ranges-validation-01';destination.mkdir(exist_ok=False)
write(destination/'summary.json',dict(status='passed',raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),stages=rows,performance_measurement=False))
