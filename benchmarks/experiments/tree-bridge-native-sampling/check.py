from pathlib import Path
import json,os,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,capture,write_json as write
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,12)
    run='tree-bridge-native-sampling-controls-01';work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    paths=list(Path(__file__).parent.glob('*.py'))+[Path(__file__).with_name('PLAN.md')]
    paths += [ROOT/'scripts'/n for n in ['interpreter.py','workflow_io.py','compare_saved_runtime.py']]
    frozen={str(p.relative_to(ROOT)):sha(p) for p in paths};write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_commands=0))
    child,out,err=capture([sys.executable,'-m','unittest','test_contracts','-v'],cwd=Path(__file__).parent,
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage='contracts'))
    write(work/'record.json',dict(pid=child.pid,returncode=child.returncode,stdout=out,stderr=err))
    assert child.returncode==0 and 'Ran 7 tests' in err and err.rstrip().endswith('OK'),out+err
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    result=ROOT/'results'/run;result.mkdir(exist_ok=False)
    write(result/'summary.json',dict(status='passed',tests=7,guest_commands=0,performance_measurement=False,
        raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),record_sha256=sha(work/'record.json')))
    print('PASS seven tree-aware sampler/attribution contracts',flush=True)
