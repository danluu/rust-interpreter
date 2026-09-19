"""Reconstruct adopted captures and verify every changed machine-code edge."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='shared-cold-tail-reconstruction-01'


def read(p):return json.loads(p.read_text())


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed
        frozen={}
        def bind(path,expected=None):
            digest=sha(path)
            if expected is not None:assert digest==expected,path
            frozen[str(path.relative_to(ROOT))]=digest
            return read(path) if path.suffix=='.json' else digest
        focused=ROOT/'results/shared-cold-tail-focused-02'
        fc=bind(focused/'closure.json');fs=bind(focused/'summary.json',fc['summary_sha256'])
        assert fc['status']=='closed' and fc['all_hashes_verified'] and fs['tests']==dict(debug=5,release=5)
        fp=bind(ROOT/fs['raw']/'plan.json',fs['plan_sha256'])
        for path,digest in fp['frozen'].items():
            if path.startswith('crates/') or path in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/path,digest)
        prior=ROOT/'results/adopted-current-runtime-sampling-02'
        closed=bind(prior/'closure.json');summary=bind(prior/'summary.json',closed['summary_sha256'])
        assert closed['status']=='closed' and closed['all_hashes_verified']
        for path,digest in bind(ROOT/closed['evidence'],closed['evidence_sha256']).items():bind(ROOT/path,digest)
        census_path=ROOT/'results/shared-cold-tail-census-01'
        cc=bind(census_path/'closure.json');cs=bind(census_path/'summary.json',cc['summary_sha256'])
        assert cc['status']=='closed' and cs['status']=='passed'
        for path in Path(__file__).parent.iterdir():
            if path.suffix in ['.py','.md']:bind(path)
        for name in ['compare_saved_runtime.py','workflow_io.py']:bind(ROOT/'scripts'/name)
        artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        bind(artifact,artifact.stem)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.argv],target=str(target.relative_to(ROOT)),
            allocated_target_bytes=allocated,required_free_bytes=needed,minimum_child_gib=8,
            expected_commands=3,original_project_guest_commands=0,guest_commands=0,
            executable_code_publications=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','TAIL_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        cargo=['cargo','+nightly-2026-09-08','test','--release','--locked','--offline','--jobs','2',
            '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'-p','rust-interp-bytecode','--lib']
        commands=[('controls',[*cargo,'cold_tail_relocation_'],{},2)]
        for case in summary['cases']:
            label=case['case'];folder=ROOT/'.work'/case['run_id']/'0/jit-code'
            commands.append((label,[*cargo,'jit::code_spans::cold_tails::observe_saved_cold_tails','--','--ignored','--exact'],
                dict(TAIL_ARTIFACT=str(artifact),TAIL_MAP=str(folder/'operations.json'),
                    TAIL_CODE=str(folder/'code.bin'),TAIL_OUTPUT=str(raw/(label+'.json'))),1))
        records=[];cases=[];outputs={}
        for label,command,extra,tests in commands:
            require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed
            start=time.time()
            child,out,err=capture(command,cwd=ROOT,env=env|extra,receipt_path=raw/'active.json',receipt=dict(stage=label))
            for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,extra_env=extra,pid=child.pid,returncode=child.returncode,
                seconds=time.time()-start,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records)
            assert child.returncode==0,(out+err)[-5000:]
            assert f'test result: ok. {tests} passed; 0 failed; 0 ignored;' in out
            if label!='controls':
                report=read(raw/(label+'.json'));expected,=[r for r in cs['cases'] if r['case']==label]
                assert report['status']=='passed' and report['guest_commands']==report['executable_code_publications']==0
                for key in ['exact_adopted_reconstruction','only_fault_tail_and_required_branch_displacements_change','entries_resumes_assertions_and_operations_preserved']:
                    assert report[key]
                assert report['saved_bytes']==expected['saved_bytes'] and report['shared_tails']==expected['replaced_tails']
                assert report['original_bytes']==expected['original_bytes']
                outputs[str((raw/(label+'.json')).relative_to(ROOT))]=sha(raw/(label+'.json'))
                cases.append(dict(case=label,**{k:v for k,v in report.items() if k!='functions'}))
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,'exact cold-tail relocation proof passed',flush=True)
        destination=ROOT/'results'/RUN;destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,commands=len(records),controls=2,cases=cases,
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),outputs=outputs,
            guest_commands=0,executable_code_publications=0,setup_seconds=sum(r['seconds'] for r in records),performance_measurement=False))


if __name__=='__main__':main()
