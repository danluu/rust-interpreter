"""Qualify native indirect transitions and exact metadata before broader checks."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);args=p.parse_args()
    assert re.fullmatch(r'native-indirect-focus-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,16)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        paths=[p for p in (ROOT/'crates').rglob('*') if p.is_file() and p.suffix in ['.rs','.toml']]
        paths += [Path(__file__),Path(__file__).with_name('PLAN.md')]
        paths += [ROOT/p for p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml','scripts/workflow_io.py','scripts/compare_saved_runtime.py','scripts/interpreter.py','benchmarks/experiments/operation-map/maps.py']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        common=['cargo','+nightly-2026-09-08','test','--locked','--offline','--jobs','2','--target-dir',str(ROOT/'.work/fixed-frame-clear-combined-build-01/target'),'-p','rust-interp-bytecode']
        commands=[('transitions',common+['--test','native_indirect'],8),('metadata',common+['--lib','jit::indirect::tests'],3)]
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,commands=commands,performance_measurement=False,guest_benchmark_commands=0))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','INDIRECT_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',PYTHONDONTWRITEBYTECODE='1')
        records=[]
        for label,command,expected in commands:
            require_space(ROOT,8);assert all(sha(ROOT/k)==v for k,v in frozen.items())
            child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err));write(work/'records.json',records)
            assert child.returncode==0,(out+err)[-6000:]
            assert sum(map(int,re.findall(r'test result: ok\. (\d+) passed;',out)))==expected
            print(label,'PASS',expected,flush=True)
        assert all(sha(ROOT/k)==v for k,v in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',tests=11,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),guest_benchmark_commands=0,performance_measurement=False))


if __name__=='__main__':main()
