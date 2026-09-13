"""Reconstruct adopted captures and account for native-counter changes and successor-dead flush removal."""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write


def signature(row):
    return (row['region_start'],row['region_end'],row['register'],row['fact'],row['end']-row['offset'],
        row['analysis_available'],row['live_before'],row['live_after'],row['tail_consumed'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--build',type=Path,required=True)
    args=parser.parse_args();assert re.fullmatch(r'native-counter-flush-emission-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        build_path=args.build.resolve(strict=True);build=json.loads(build_path.read_text())
        assert build['status']=='passed' and build['tests']=={'test-debug':532,'test-release':532}
        manifest=ROOT/build['source_manifest'];assert sha(manifest)==build['source_manifest_sha256']
        frozen=json.loads(manifest.read_text())['frozen'];assert all(sha(ROOT/p)==h for p,h in frozen.items())
        old_proof_path=ROOT/'results/consumed-flush-values-census-01/attribution.json'
        old_proof=json.loads(old_proof_path.read_text());assert old_proof['status']=='passed'
        assert all(sha(ROOT/p)==h for p,h in old_proof['evidence'].items())
        frozen.update(old_proof['evidence'])
        for p in [Path(__file__),build_path,manifest,old_proof_path]:frozen[str(p.relative_to(ROOT))]=sha(p)
        artifact=ROOT/'.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        assert sha(artifact)==artifact.stem;frozen[str(artifact.relative_to(ROOT))]=sha(artifact)
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        command=['cargo','+nightly-2026-09-08','test','--release','--locked','--offline','--jobs','2',
            '--target-dir',str(ROOT/'.work/fixed-frame-clear-combined-build-01/target'),'-p','rust-interp-bytecode',
            '--lib','jit::code_spans::native_counter_flush::observe_native_counter_flush_code','--','--ignored','--exact']
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,command=command,tool_key=build['tool_key'],guest_commands=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','NATIVE_COUNTER_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',CARGO_PROFILE_RELEASE_DEBUG='1')
        records=[];comparisons=[]
        for label in ['block','exhaustive']:
            assert all(sha(ROOT/p)==h for p,h in frozen.items());require_space(ROOT,8)
            folder=ROOT/'.work'/('adopted-runtime-sample-'+label+'-01')/'0/jit-code'
            selected=dict(env,NATIVE_COUNTER_ARTIFACT=str(artifact),NATIVE_COUNTER_MAP=str(folder/'operations.json'),
                NATIVE_COUNTER_CODE=str(folder/'code.bin'),NATIVE_COUNTER_OUTPUT=str(work/(label+'.json')))
            child,out,err=capture(command,cwd=ROOT,env=selected,receipt_path=work/'active.json',receipt=dict(label=label))
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err))
            write(work/'records.json',records);assert child.returncode==0,(out+err)[-4000:]
            report=json.loads((work/(label+'.json')).read_text());assert report['status']=='passed'
            assert report['exact_baseline_reconstruction'] and report['counter_words_accounted_by_scope']
            assert report['composition_removes_only_dead_flush_word_counts']
            assert report['guest_commands']==report['executable_code_publications']==0
            old=json.loads((ROOT/'.work/consumed-flush-values-census-01'/(label+'.json')).read_text())
            assert report['code_sha256']==old['code_sha256'] and len(report['functions'])==len(old['functions'])
            old_functions={f['function']:f for f in old['functions']};removed=0;growth=0
            for f in report['functions']:
                prior=old_functions[f['function']];assert f['name']==prior['name']
                expected=[s for s in prior['flush_spans'] if s['analysis_available'] and not s['live_after']]
                assert sorted(map(signature,expected))==sorted(map(signature,f['removed_values']))
                assert f['counter_bytes']-f['candidate_bytes']==f['removed_flush_bytes']==sum(s['end']-s['offset'] for s in expected)
                removed+=f['removed_flush_bytes']
                assert f['counter_bytes']-f['baseline_bytes']==f['counter_delta_bytes']
                growth+=f['counter_delta_bytes']
            assert report['baseline_bytes']+growth-report['candidate_bytes']==removed
            comparisons.append(dict(case=label,functions=len(report['functions']),baseline_bytes=report['baseline_bytes'],
                candidate_bytes=report['candidate_bytes'],removed_flush_bytes=removed,counter_delta_bytes=growth,removed_span_identity_exact=True,
                report_sha256=sha(work/(label+'.json'))))
            print(label,comparisons[-1],flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=2,tool_key=build['tool_key'],comparisons=comparisons,
            exact_adopted_reconstruction=True,only_dead_after_flush_words_removed=True,counter_changes_accounted=True,guest_commands=0,
            executable_code_publications=0,performance_measurement=False,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))


if __name__=='__main__':main()
