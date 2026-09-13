"""Qualify launcher routing and exact profile reconciliation before replay."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);args=p.parse_args()
    assert re.fullmatch(r'tree-bridge-controls-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        paths=list((ROOT/'scripts').glob('*.py'))+list((ROOT/'tests').glob('*.py'))+list(Path(__file__).parent.glob('*.py'))
        paths += [Path(__file__).with_name(name) for name in ['PLAN.md','QUALIFICATION.md']]
        frozen={str(path.relative_to(ROOT)):sha(path) for path in paths}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False);write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_commands=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        env['PYTHONDONTWRITEBYTECODE']='1';assert not any(k.startswith('DYLD_') for k in env)
        commands=[('profile',[sys.executable,'-m','unittest','test_profile','-v'],Path(__file__).parent,6,0),
            ('launcher',[sys.executable,'-m','unittest','discover','-s','tests','-v'],ROOT,386,16)]
        records=[]
        for label,command,cwd,expected,skips in commands:
            require_space(ROOT,8)
            child,out,err=capture(command,cwd=cwd,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            records.append(dict(label=label,command=command,cwd=str(cwd),pid=child.pid,returncode=child.returncode,stdout=out,stderr=err));write(work/'records.json',records)
            assert child.returncode==0,(out+err)[-5000:]
            assert f'Ran {expected} tests' in err
            assert err.rstrip().endswith(f'OK (skipped={skips})' if skips else 'OK')
            print(label,'PASS',expected,'tests',flush=True)
        assert all(sha(ROOT/path)==h for path,h in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',profile_controls=6,launcher_tests=386,launcher_skipped=16,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            guest_commands=0,performance_measurement=False))

if __name__=='__main__':main()
