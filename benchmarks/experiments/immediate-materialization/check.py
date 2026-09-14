"""Qualify the bounded saved-code census, with no guest execution."""
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

def main():
    name='immediate-materialization-controls-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        directory=Path(__file__).parent
        paths=[p for p in directory.iterdir() if p.suffix in ['.py','.md']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/name;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_commands=0))
        child,out,err=capture([sys.executable,'-m','unittest','test_census','-v'],cwd=directory,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage='offline decoder controls'))
        (work/'stdout').write_text(out);(work/'stderr').write_text(err)
        write(work/'record.json',dict(pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr')))
        assert child.returncode==0 and 'Ran 6 tests' in err and err.rstrip().endswith('OK'),err
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/name;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',tests=6,guest_commands=0,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),record_sha256=sha(work/'record.json'),performance_measurement=False))

if __name__=='__main__':main()
