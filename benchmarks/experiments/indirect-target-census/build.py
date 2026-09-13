"""Qualify and freeze a explicit-feature indirect-target observer; install no production VM."""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
TARGET=ROOT/'.work/fixed-frame-clear-combined-build-01/target'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert re.fullmatch(r'indirect-target-build-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        paths=[p for p in (ROOT/'crates').rglob('*') if p.is_file() and p.suffix in ['.rs','.toml']]
        paths+=[ROOT/p for p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml','scripts/compare_saved_runtime.py','scripts/workflow_io.py']]
        paths+=[Path(__file__),Path(__file__).with_name('PLAN.md')]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        rust={p:h for p,h in frozen.items() if p.startswith('crates/') or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        common=['cargo','+nightly-2026-09-08','test','--locked','--offline','--jobs','2','--target-dir',str(TARGET),'-p','rust-interp-bytecode']
        commands=[('debug',common),('release',common+['--release']),
            ('observer',['cargo','+nightly-2026-09-08','build','--locked','--offline','--jobs','2','--target-dir',str(TARGET),'-p','rust-interp-bytecode','--release','--features','indirect-target-observer','--bin','rust-interp-indirect-observer','--message-format=json'])]
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,rust_inputs=rust,commands=commands,guest_benchmark_commands=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','INDIRECT_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',CARGO_PROFILE_RELEASE_DEBUG='1',PYTHONDONTWRITEBYTECODE='1')
        records=[];tests={};observer=None
        for label,command in commands:
            require_space(ROOT,8);assert all(sha(ROOT/p)==h for p,h in frozen.items())
            child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err))
            write(work/'records.json',records);assert child.returncode==0,(out+err)[-4000:]
            if label!='observer':
                tests[label]=sum(map(int,re.findall(r'test result: ok\. (\d+) passed;',out)))
                assert tests[label]==417,tests
                assert sum(map(int,re.findall(r'test result: ok\. \d+ passed; \d+ failed; (\d+) ignored;',out)))==10
                for name in ['indirect_trace_records_validated_targets_and_native_readiness','indirect_trace_does_not_observe_invalid_handles_or_signatures','indirect_trace_is_bounded_and_scope_cleanup_preserves_execution']:
                    assert '::'+name+' ... ok' in out
            else:
                entries=[json.loads(line) for line in out.splitlines() if line.startswith('{')]
                executable,=[Path(e['executable']).resolve(strict=True) for e in entries if e.get('reason')=='compiler-artifact' and e.get('executable') and e['target']['name']=='rust-interp-indirect-observer' and e['target']['kind']==['bin']]
                assert executable.is_relative_to(TARGET)
                observer=work/'observer';shutil.copy2(executable,observer);assert sha(observer)==sha(executable)
            print(label,'passed',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',tests=tests,rust_inputs=rust,
            observer=str(observer.relative_to(ROOT)),observer_sha256=sha(observer),observer_only=True,observer_main_thread=True,explicit_feature="indirect-target-observer",
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            guest_benchmark_commands=0,performance_measurement=False))


if __name__=='__main__':main()
