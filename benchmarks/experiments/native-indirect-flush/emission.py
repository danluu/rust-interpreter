"""Reconstruct retained indirect code and account for every omitted flush byte."""
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);p.add_argument('--build',type=Path,required=True)
    args=p.parse_args();assert re.fullmatch(r'native-indirect-flush-emission-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        build_path=args.build.resolve(strict=True);build=json.loads(build_path.read_text())
        assert build['status']=='passed' and build['tests']=={'test-debug':544,'test-release':544}
        source=ROOT/build['source_manifest'];assert sha(source)==build['source_manifest_sha256']
        frozen=json.loads(source.read_text())['frozen'];assert all(sha(ROOT/p)==h for p,h in frozen.items())
        reference_path=ROOT/'results/native-indirect-profile-01/summary.json';reference=json.loads(reference_path.read_text())
        assert reference['status']=='passed' and reference['commands']==3 and reference['exact_operation_map_reconstruction']
        raw=ROOT/reference['raw'];assert sha(raw/'records.json')==reference['records_sha256']
        artifacts_path=ROOT/'results/current-runtime-boundaries-02/summary.json';artifacts=json.loads(artifacts_path.read_text())
        paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),Path(__file__).with_name('QUALIFICATION.md'),build_path,source,reference_path,raw/'records.json',artifacts_path]
        for case in reference['comparisons']:
            i=case['index'];item,=[r for r in artifacts['profiles'] if r['index']==i]
            artifact=ROOT/item['artifact'];assert sha(artifact)==item['artifact_sha256'];paths.append(artifact)
            for filename,key in [('operations.json','operation_map_sha256'),('code.bin','code_sha256')]:
                path=raw/f'{i}-code'/filename;assert sha(path)==case[key];paths.append(path)
        frozen.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,tool_key=build['tool_key'],expected_commands=3,
            guest_commands=0,executable_code_publications=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','SUCCESSOR_','CARGO_','INDIRECT_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',CARGO_TERM_COLOR='never')
        rows=[];cases=[]
        for c in reference['comparisons']:
            require_space(ROOT,8);i=c['index'];item,=[r for r in artifacts['profiles'] if r['index']==i]
            output=work/f'{i}.json';dump=raw/f'{i}-code'
            command=['cargo','+nightly-2026-09-08','test','--locked','--offline','--jobs','2','--target-dir',str(ROOT/'.work/fixed-frame-clear-combined-build-01/target'),
                '-p','rust-interp-bytecode','--release','--lib','jit::code_spans::indirect_flush::observe_successor_flush_code','--','--exact','--ignored','--nocapture']
            child,out,err=capture(command,cwd=ROOT,env=dict(env,SUCCESSOR_ARTIFACT=str(ROOT/item['artifact']),SUCCESSOR_MAP=str(dump/'operations.json'),
                SUCCESSOR_CODE=str(dump/'code.bin'),SUCCESSOR_OUTPUT=str(output)),receipt_path=work/'active.json',receipt=dict(index=i))
            rows.append(dict(index=i,command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err));write(work/'records.json',rows)
            assert child.returncode==0 and '1 passed; 0 failed' in out,(out+err)[-3000:]
            report=json.loads(output.read_text());assert report['status']=='passed' and report['exact_baseline_reconstruction'] and report['only_flush_word_counts_change']
            assert report['guest_commands']==report['executable_code_publications']==0
            assert report['code_sha256']==c['code_sha256'] and report['baseline_bytes']==c['statistics']['jit_bytes']
            removed=sum(f['removed_flush_bytes'] for f in report['functions'])
            assert report['baseline_bytes']-report['candidate_bytes']==removed
            cases.append(dict(index=i,functions=len(report['functions']),baseline_bytes=report['baseline_bytes'],candidate_bytes=report['candidate_bytes'],
                removed_flush_bytes=removed,report_sha256=sha(output)))
            print(i,'PASS',removed,'flush bytes removed',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',tool_key=build['tool_key'],commands=3,cases=cases,
            exact_indirect_baseline_reconstruction=True,only_dead_flush_words_removed=True,
            guest_commands=0,executable_code_publications=0,performance_measurement=False,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))


if __name__=='__main__':main()
