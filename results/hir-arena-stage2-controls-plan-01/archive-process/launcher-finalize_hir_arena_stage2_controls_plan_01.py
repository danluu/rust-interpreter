from pathlib import Path
import hashlib, json, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/stable-cgu"))
from owned_stage import CANONICAL_LOCK, workload_lock, disk
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/hir-arena-stage2-controls-plan-01'
WORK=ROOT/'.work/hir-arena-stage2-controls-plan-archive-01'
SUP=ROOT/'.work/experiments/hir-arena-stage2-controls-plan-archive-supervisor-01'
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
with workload_lock(CANONICAL_LOCK, 600):
    disk(ROOT)
    record=json.loads((WORK/'summary.json').read_bytes())
    status=json.loads((SUP/'status.json').read_bytes())
    summary=json.loads((OUT/'summary.json').read_bytes())
    assert record['status']=='passed' and status['status']=='finished' and status['returncode']==0
    assert status['child_pid']==record['pid']
    assert sha(SUP/'plan.json')==status['plan_sha256'] and sha(SUP/'command.log')==status['log_sha256']
    assert sha(OUT/'summary.json')==record['summary_sha256']
    assert sha(OUT/'evidence.tar.gz')==summary['archive']['sha256'] and summary['archive']['all_member_hashes_verified']
    target=OUT/'archive-process';target.mkdir(exist_ok=False)
    manifest={}
    for src in [WORK/'summary.json',*(SUP/n for n in ['status.json','plan.json','command.log','supervisor.log']), ROOT/'.work/hir-arena-stage2-controls-plan-archive-launch-01.json', Path(__file__).resolve()]:
     data=src.read_bytes();name=('archive-' if src.parent==WORK else 'supervisor-' if src.parent==SUP else 'launcher-')+src.name
     (target/name).write_bytes(data)
     assert (target/name).read_bytes()==src.read_bytes()
     manifest[name]=dict(source=str(src),sha256=sha(src),bytes=len(data))
    (target/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(status='passed',archive_sha256=summary['archive']['sha256'],members=summary['archive']['members'],
     archive_bytes=summary['archive']['bytes'],summary_sha256=sha(OUT/'summary.json'),archive_pid=record['pid'],supervisor_pid=status['supervisor_pid'],
     completed_at=record['finished_at']),sort_keys=True))
