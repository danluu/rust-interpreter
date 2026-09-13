from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='guarded-local-facts-main-protocol-01'
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    folder=ROOT/'benchmarks/experiments/guarded-local-facts-main'
    sys.path.insert(0,str(folder))
    from inputs import CASES,require_complete
    comparison=ROOT/'results/guarded-local-facts-full-continuation-01/summary.json'
    cases=[ROOT/'results'/('guarded-local-facts-edit-'+c+'-01')/'summary.json' for c in CASES]
    require_complete(json.loads(comparison.read_text()),[json.loads(p.read_text()) for p in cases])
    paths=[*folder.glob('*.py'),*folder.glob('*.md'),comparison,*cases,Path(__file__)]
    frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
    work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
    command=[sys.executable,'-m','unittest','discover','-s',str(folder),'-p','test_*.py','-v']
    write(work/'plan.json',dict(owner=str(ROOT),command=command,frozen=frozen,guest_commands=0))
    child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(label='controller-tests'))
    (work/'stdout').write_text(out);(work/'stderr').write_text(err)
    write(work/'record.json',dict(pid=child.pid,command=command,returncode=child.returncode,stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr')))
    assert child.returncode==0 and 'Ran 5 tests in ' in err and err.rstrip().endswith('OK'),err
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    dest=ROOT/'results'/NAME;dest.mkdir(exist_ok=False)
    write(dest/'summary.json',dict(status='passed',tests=5,guest_commands=0,compiler_build_commands=0,actual_completed_comparison_validated=True,
        raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),record_sha256=sha(work/'record.json'),frozen_inputs=len(frozen),performance_measurement=False))
    print('PASS: five integration boundary checks and actual completed comparison',flush=True)
