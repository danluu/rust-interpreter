#!/usr/bin/env python3
"""Qualify bounded call clones on retained real artifacts before integration."""
import argparse,json,os,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--build',required=True,type=Path)
    parser.add_argument('--minimum-free-gib',type=int,choices=[3,4],default=4)
    args=parser.parse_args();assert re.fullmatch(r'constant-specialize-saved-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,args.minimum_free_gib+(0.5 if args.minimum_free_gib==3 else 0))
        storage=Path(__file__).with_name('OFFLINE-STORAGE.md')
        if args.minimum_free_gib==3:assert 'Offline fixed-size artifact floor: 3 GiB' in storage.read_text()
        build_path=args.build.resolve(strict=True);build=json.loads(build_path.read_text())
        assert build['status']=='passed' and build['tests']['test-debug']==build['tests']['test-release']==dict(passed=386,ignored=1)
        plan_path=ROOT/build['raw']/'plan.json';plan=json.loads(plan_path.read_text())
        assert sha(plan_path)==build['source_manifest_sha256'] and all(sha(ROOT/p)==h for p,h in plan['frozen'].items())
        status_path=ROOT/'.work/experiments'/Path(build['raw']).name/'status.json';status=json.loads(status_path.read_text())
        assert status['status']=='finished' and status['returncode']==0 and status['owner']==str(ROOT)
        assert sha(status_path.with_name('plan.json'))==status['plan_sha256'] and sha(status_path.with_name('command.log'))==status['log_sha256']
        reference_path=ROOT/'results/suite-profiling-real-01/summary.json';reference=json.loads(reference_path.read_text())
        assert reference['status']=='passed' and reference['exact_logical_counts_and_entropy']
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        built=Path(plan['target'])/'release/rust-interp-call-census';binary=work/built.name
        shutil.copy2(built,binary);assert sha(built)==sha(binary)
        paths=[Path(__file__),Path(__file__).with_name('SPECIALIZATION-SAVED.md'),storage,build_path,plan_path,status_path,binary,reference_path,
            ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']
        inputs=[]
        for item in reference['profiles']:
            if item['index'] not in [0,2,5]:continue
            artifact=ROOT/item['artifact'];assert sha(artifact)==item['artifact_sha256'];paths.append(artifact)
            inputs.append(dict(case=item['case'],index=item['index'],artifact=str(artifact.relative_to(ROOT)),artifact_sha256=sha(artifact)))
        assert len(inputs)==3
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,inputs=inputs,minimum_free_gib=args.minimum_free_gib,performance_measurement=False,
            scope='Offline specialization of original real artifacts, without global folding, guest execution or Cargo.'))
        records=[];reports=[]
        for item in inputs:
            output=work/(str(item['index'])+'.rbc');report=work/(str(item['index'])+'.json');check=work/(str(item['index'])+'-checked.json')
            for label,flag,target in [('specialize','--specialize',report),('verify','--verify-specialize',check)]:
                require_space(ROOT,args.minimum_free_gib);command=[str(binary),flag,str(ROOT/item['artifact']),str(output),str(target)]
                before=shutil.disk_usage(ROOT).free
                child,stdout,stderr=capture(command,cwd=ROOT,env=os.environ.copy(),receipt_path=work/'active.json',receipt=dict(index=item['index'],label=label))
                records.append(dict(index=item['index'],label=label,command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr,
                    free_before=before,free_after=shutil.disk_usage(ROOT).free));write(work/'records.json',records)
                assert child.returncode==0,stderr
            r=json.loads(report.read_text());v=json.loads(check.read_text());assert r['exact_constant_specialization'] and v['exact_constant_specialization']
            assert r['baseline_sha256']==v['baseline_sha256']==item['artifact_sha256']
            assert r['candidate_sha256']==v['candidate_sha256']==sha(output) and r['specialization']==v['specialization']
            details=r['specialization'];assert details['fold_work']<=8_000_000 and len(details['clones'])<=64
            assert details['added_operations']<=min(16_384,details['original_operations']//20)
            part=dict(**item,specialization=details,candidate_artifact_sha256=sha(output),report_sha256=sha(report),verification_sha256=sha(check),
                original_bytes=(ROOT/item['artifact']).stat().st_size,candidate_bytes=output.stat().st_size,
                diagnostic_transform_seconds=r['diagnostic_transform_seconds'])
            reports.append(part);print(item['case'],len(details['clones']),'clones',details['rewritten_calls'],'calls',r['diagnostic_transform_seconds'],'seconds',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=len(records),cases=reports,source_commit=build['source_commit'],
            verifier=str(binary.relative_to(ROOT)),verifier_sha256=sha(binary),build=str(build_path.relative_to(ROOT)),
            performance_measurement=False,guest_execution=False,original_artifacts_unchanged=True,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))

if __name__=='__main__':main()
