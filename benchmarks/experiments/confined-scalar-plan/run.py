"""Build and qualify typed access metadata without executing a guest."""
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


def main():
    name='confined-scalar-plan-build-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        directory=Path(__file__).parent
        prior_path=ROOT/'results/confined-leaf-census-01/summary.json';prior=json.loads(prior_path.read_text())
        assert prior['status']=='passed' and prior['controls']==3 and prior['all_frozen_inputs_verified']
        reference_path=ROOT/'results/current-runtime-boundaries-02/summary.json';reference=json.loads(reference_path.read_text())
        assert reference['status']=='passed' and reference['exact_logical_counts_memory_and_entropy']
        one,two=reference['profiles'][:2]
        assert one['artifact']==two['artifact'] and one['artifact_sha256']==two['artifact_sha256']
        artifact=ROOT/one['artifact'];assert sha(artifact)==one['artifact_sha256']
        dependency=[*list((ROOT/'crates/bytecode').rglob('*.rs')),ROOT/'crates/bytecode/Cargo.toml']
        paths=[p for p in directory.iterdir() if p.suffix in ['.rs','.py','.md','.toml','.lock']]
        paths+=dependency+[prior_path,reference_path,artifact,ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/name;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,target=str(target.relative_to(ROOT)),
            same_source_root=True,shared_target_allocated_bytes=allocated,required_free_bytes=needed,
            tests_per_profile=13,oracle_cases_per_profile=6400,guest_commands=0,runtime_changes=0,minimum_child_gib=8))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
             and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records=[]
        def invoke(label,command,building=True):
            if building:assert shutil.disk_usage(ROOT).free>=needed
            require_space(ROOT,8);started=time.time()
            child,out,err=capture(list(map(str,command)),cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,text in [('stdout',out),('stderr',err)]:(work/(label+'.'+stream)).write_text(text)
            records.append(dict(label=label,command=list(map(str,command)),pid=child.pid,returncode=child.returncode,
                started_at=started,finished_at=time.time(),stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records)
            assert child.returncode==0,(out+err)[-5000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            return out
        common=['--locked','--offline','--jobs','2','--manifest-path',directory/'Cargo.toml','--target-dir',target,'--bin','confined-scalar-plan-census']
        for profile,extra in [('debug',[]),('release',['--release'])]:
            out=invoke('test-'+profile,['cargo','+nightly-2026-09-08','test',*extra,*common,'proof::tests::'])
            assert '13 passed; 0 failed' in out and 'path_byte_oracle_checks_both_sides_of_cfg_joins' in out
            print(profile,'13 controls PASS',flush=True)
        invoke('build',['cargo','+nightly-2026-09-08','build','--release',*common])
        binary=work/'confined-scalar-plan-census';shutil.copy2(target/'release/confined-scalar-plan-census',binary)
        digest=sha(binary);invoke('analyze',[binary,artifact,work/'typed.json'],False)
        typed=json.loads((work/'typed.json').read_text());assert typed['status']=='passed' and typed['guest_commands']==typed['runtime_changes']==0
        assert not typed['address_nonescape_proved'] and sha(binary)==digest
        rows=typed['functions'];assert [f['function'] for f in rows]==list(range(len(rows)))
        result=ROOT/'results'/name;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',tests={'debug':13,'release':13},oracle_cases_per_profile=6400,commands=4,
            functions=len(rows),eligible_functions=sum(r['plan']['eligible'] for r in rows),global_work_remaining=typed['global_work_remaining'],
            binary_sha256=digest,setup_seconds=sum(r['finished_at']-r['started_at'] for r in records[:3]),
            analysis_seconds=records[3]['finished_at']-records[3]['started_at'],typed_sha256=sha(work/'typed.json'),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),raw=str(work.relative_to(ROOT)),
            guest_commands=0,runtime_changes=0,performance_measurement=False,address_nonescape_proved=False))
        print('Typed plans PASS',sum(r['plan']['eligible'] for r in rows),flush=True)

if __name__=='__main__':main()
