"""Compile and check the test-only eviction-loss observer in both profiles."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    run = 'local-value-transfer-build-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45); require_space(ROOT,12)
        paths = [ROOT/n for n in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']]
        paths += [p for p in (ROOT/'crates/bytecode').rglob('*') if p.is_file() and (p.suffix=='.rs' or p.name=='Cargo.toml')]
        paths += [Path(__file__),Path(__file__).with_name('PLAN.md'),Path(__file__).with_name('DESIGN.md')]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        commands=[(label,['cargo','+nightly-2026-09-08','test',*profile,'--locked','--offline',
            '--jobs','2','--target-dir',str(target),'-p','rust-interp-bytecode'])
            for label,profile in [('debug',[]),('release',['--release'])]]
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,commands=commands,
            source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            expected_passed_per_profile=411,expected_ignored_per_profile=6,
            observer_enabled_only_by_explicit_ignored_census=True,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_'))
             and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER',
                           'CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0',CARGO_PROFILE_RELEASE_DEBUG='1',PYTHONDONTWRITEBYTECODE='1')
        rows=[];totals={}
        for label,command in commands:
            require_space(ROOT,8)
            child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            (work/(label+'.stdout')).write_text(out);(work/(label+'.stderr')).write_text(err)
            rows.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',rows)
            assert child.returncode==0,(out+err)[-3000:]
            counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
            assert counts and all(int(f)==0 for _,f,_ in counts)
            totals[label]=dict(passed=sum(int(n) for n,_,_ in counts),ignored=sum(int(n) for _,_,n in counts))
            assert totals[label]==dict(passed=411,ignored=6),totals[label]
            assert len(re.findall(r'^test jit::local_memory::transfer_tests::.* \.\.\. ok$',out,re.M))==8
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,totals[label],'passed',flush=True)
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=2,tests=totals,transfer_tests=8,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            production_transfer_enabled=False,performance_measurement=False))


if __name__=='__main__':main()
