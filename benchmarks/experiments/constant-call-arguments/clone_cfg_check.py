#!/usr/bin/env python3
"""Focused clone CFG-ordering regression; no tool publication or guest benchmark."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--expect',choices=['failure','success'],required=True)
    args=parser.parse_args();assert args.run_id.startswith('constant-clone-cfg-') and Path(args.run_id).name==args.run_id
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,4)
        assert not subprocess.check_output(['git','diff','HEAD','--name-only'],cwd=ROOT,text=True).strip()
        source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        previous=ROOT/'.work/constant-specialize-build-03/plan.json';assert json.loads(previous.read_text())['target']==str(target)
        terminal=ROOT/'.work/experiments/constant-specialize-build-03/status.json';status=json.loads(terminal.read_text());assert status['status']=='finished' and status['returncode']==0
        files=[ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'rust-toolchain.toml',Path(__file__),Path(__file__).with_name('CLONE-CFG.md'),previous,terminal]
        files+=list((ROOT/'crates').rglob('*.rs'))+list((ROOT/'crates').rglob('Cargo.toml'))
        frozen={str(p.relative_to(ROOT)):sha(p) for p in files}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False);temporary=work/'tmp';temporary.mkdir()
        write(work/'plan.json',dict(owner=str(ROOT),source_commit=source,frozen=frozen,target=str(target),minimum_free_gib=4,expected=args.expect,scope='regression',tool_publication=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',CARGO_PROFILE_RELEASE_DEBUG='1',TMPDIR=str(temporary))
        rows=[]
        selected_tests=[('jit::constant_specialize::tests::unreachable_branch_reads_do_not_reject_an_otherwise_proven_clone',[],['--','--exact'],1)]
        for selected,profile,tail,count in selected_tests:
            require_space(ROOT,4)
            command=['cargo','+nightly-2026-09-08','test',*profile,'--locked','--offline','--jobs','2','--target-dir',str(target),'-p','rust-interp-bytecode','--lib',selected,*tail]
            free=shutil.disk_usage(ROOT).free
            child,stdout,stderr=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(test=selected))
            row=dict(test=selected,profile='release' if profile else 'debug',tests=count,command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr,free_before=free,free_after=shutil.disk_usage(ROOT).free);rows.append(row);write(work/'records.json',rows)
            assert child.returncode==(101 if args.expect=='failure' else 0),stderr
            assert f'running {count} test' in stdout and ('1 failed;' if args.expect=='failure' else f'{count} passed;') in stdout
            if args.expect=='failure':assert 'panicked at' in stdout and ('assertion' in stdout or 'original Err' in stdout)
            print(selected,'observed',args.expect,flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='expected-regression-failures' if args.expect=='failure' else 'passed',commands=len(rows),tests=[dict(profile=r['profile'],selected=r['tests']) for r in rows],scope='regression',source_commit=source,minimum_free_gib=4,tool_publication=False,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))


if __name__=='__main__':main()
