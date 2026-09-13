"""Build bounded proof controls and analyze a saved artifact without guest execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-id', required=True)
    args = p.parse_args()
    assert re.fullmatch(r'local-overwrite-census-build-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 16)
        directory = Path(__file__).parent
        reference_path = ROOT / 'results/current-runtime-boundaries-02/summary.json'
        reference = json.loads(reference_path.read_text())
        assert reference['status'] == 'passed' and reference['exact_logical_counts_memory_and_entropy']
        a, b = reference['profiles'][:2]
        assert a['artifact'] == b['artifact'] and a['artifact_sha256'] == b['artifact_sha256']
        artifact = ROOT / a['artifact']; assert sha(artifact) == a['artifact_sha256']
        qualification_path = ROOT / 'results/native-indirect-flush-build-01/summary.json'
        qualification = json.loads(qualification_path.read_text())
        source_manifest = ROOT / qualification['source_manifest']
        assert qualification['status'] == 'passed' and qualification['tests'] == {'test-debug':544,'test-release':544}
        assert sha(source_manifest) == qualification['source_manifest_sha256']
        old_frozen = json.loads(source_manifest.read_text())['frozen']
        dependency = [*list((ROOT / 'crates/bytecode').rglob('*.rs')), ROOT / 'crates/bytecode/Cargo.toml']
        assert all(sha(p) == old_frozen[str(p.relative_to(ROOT))] for p in dependency)
        paths = [p for p in directory.iterdir() if p.suffix in ['.rs','.py','.md','.toml','.lock']]
        paths += dependency + [artifact, reference_path, qualification_path, source_manifest,
            ROOT / 'scripts/workflow_io.py', ROOT / 'scripts/compare_saved_runtime.py',
            ROOT / 'results/memory-operation-parts-census-01/closure.json']
        maps=[]
        for label in ['block','exhaustive']:
            folder=ROOT/'.work'/('adopted-runtime-sample-'+label+'-01')/'0'
            maps.append(folder/'jit-code/operations.json')
            paths += [maps[-1],folder/'jit-code/code.bin']
            mapping=json.loads(maps[-1].read_text())
            assert mapping['code_sha256']==sha(paths[-1]) and mapping['reconstructed_bytes_match']
        closure=json.loads((ROOT/'results/memory-operation-parts-census-01/closure.json').read_text())
        assert closure['status']=='passed'
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        bindings = []
        for name, digest in frozen.items():
            if name.startswith(('benchmarks/', 'scripts/', 'crates/', 'results/')):
                spec = revision + ':' + name
                assert hashlib.sha256(subprocess.check_output(['git','show',spec],cwd=ROOT)).hexdigest() == digest
                bindings.append(dict(path=name,sha256=digest,git_source=spec))
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        write(work / 'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            target=str(target.relative_to(ROOT)),rust_dependency_qualification=qualification['tool_key'],
            expected_controls_per_profile=6,oracle_cases_per_profile=10000,guest_commands=0,
            runtime_changes=0,initial_gib=16,minimum_child_gib=8,performance_measurement=False))
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',CARGO_TERM_COLOR='never')
        records = []
        def invoke(label, command):
            require_space(ROOT,8)
            started=time.time()
            child,out,err=capture(list(map(str,command)),cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            for suffix,value in [('stdout',out),('stderr',err)]: (work/(label+'.'+suffix)).write_text(value)
            records.append(dict(label=label,command=list(map(str,command)),pid=child.pid,returncode=child.returncode,
                started_at=started,finished_at=time.time(),stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records)
            assert child.returncode==0,(label,(out+err)[-4000:])
            assert all(sha(ROOT/name)==digest for name,digest in frozen.items())
            return out,err
        common=['--locked','--offline','--jobs','2','--manifest-path',directory/'Cargo.toml','--target-dir',target]
        for profile, extra in [('debug',[]),('release',['--release'])]:
            out,err=invoke('test-'+profile,['cargo','+nightly-2026-09-08','test',*extra,*common,'--bin','local-overwrite-census','proof::tests::'])
            assert '6 passed; 0 failed' in out,out
            assert 'independent_byte_oracle_checks_10000_four_event_histories' in out
            print(profile,'PASS 6 controls including 10000 oracle cases',flush=True)
        invoke('build',['cargo','+nightly-2026-09-08','build','--release',*common,'--bin','local-overwrite-census'])
        binary=work/'local-overwrite-census';shutil.copy2(target/'release/local-overwrite-census-census',binary)
        binary_sha=sha(binary);cases=[]
        for label,mapping in zip(['block','exhaustive'],maps):
            started=time.time();typed_path=work/(label+'.json')
            invoke('analyze-'+label,[binary,artifact,mapping,typed_path])
            assert sha(binary)==binary_sha
            typed=json.loads(typed_path.read_text());assert typed['status']=='passed' and typed['guest_commands']==typed['runtime_changes']==0
            regions=[r for f in typed['functions'] for r in f['regions']]
            cases.append(dict(case=label,functions=len(typed['functions']),regions=len(regions),
                writes=sum(r['proof']['writes'] for r in regions),candidates=sum(len(r['proof']['candidates']) for r in regions),
                declined_regions=sum(r['proof']['decline'] is not None for r in regions),
                global_work_remaining=typed['global_work_remaining'],analysis_seconds=time.time()-started,
                typed_sha256=sha(typed_path)))
            print(label,json.dumps(cases[-1]),flush=True)
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'source-bindings.json',dict(source_revision=revision,files=bindings))
        write(result/'summary.json',dict(status='passed',tests={'debug':6,'release':6},oracle_cases_per_profile=10000,commands=5,
            cases=cases,binary_sha256=binary_sha,
            setup_seconds=sum(r['finished_at']-r['started_at'] for r in records[:3]),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            source_bindings_sha256=sha(result/'source-bindings.json'),unique_frozen_inputs=len(frozen),git_bindings=len(bindings),
            raw=str(work.relative_to(ROOT)),guest_commands=0,runtime_changes=0,performance_measurement=False))
        print('PASS exact-region local overwrite census',flush=True)



if __name__=='__main__':main()
