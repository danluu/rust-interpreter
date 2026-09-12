#!/usr/bin/env python3
"""Transform three immutable current artifacts, without executing guest code."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

def main():
    run='constant-fold-saved-02'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,7)
        composition_path=ROOT/'results/constant-fold-compose-02/summary.json';composition=json.loads(composition_path.read_text())
        assert composition['status']=='composed' and composition['build']=='results/constant-fold-build-08/summary.json'
        binary=ROOT/composition['verifier'];assert sha(binary)==composition['verifier_sha256']
        reference_path=ROOT/'results/suite-profiling-real-01/summary.json';reference=json.loads(reference_path.read_text())
        assert reference['status']=='passed' and reference['exact_logical_counts_and_entropy']
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        frozen_paths=[Path(__file__),Path(__file__).with_name('PROTOTYPE.md'),composition_path,binary,reference_path,
            ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']
        inputs=[]
        for item in reference['profiles']:
            if item['index'] not in [0,2,5]:continue
            artifact=ROOT/item['artifact'];assert sha(artifact)==item['artifact_sha256'];frozen_paths.append(artifact)
            inputs.append(dict(case=item['case'],index=item['index'],artifact=str(artifact.relative_to(ROOT)),artifact_sha256=sha(artifact)))
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,inputs=inputs,minimum_free_gib=7,performance_measurement=False,
            scope='Host-only offline transformation and whole-artifact verification. No guest execution/build or lowered real-project benchmark admission.'))
        records=[];reports=[]
        for item in inputs:
            output=work/(str(item['index'])+'.rbc');report=work/(str(item['index'])+'.json');check=work/(str(item['index'])+'-checked.json')
            for label,command in [('fold',[str(binary),'--fold',str(ROOT/item['artifact']),str(output),str(report)]),
                                  ('verify',[str(binary),'--verify-fold',str(ROOT/item['artifact']),str(output),str(check)])]:
                require_space(ROOT,7)
                child,stdout,stderr=capture(command,cwd=ROOT,env=os.environ.copy(),receipt_path=work/'active.json',receipt=dict(index=item['index'],label=label))
                records.append(dict(index=item['index'],label=label,command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr));write(work/'records.json',records)
                assert child.returncode==0,stderr
            r=json.loads(report.read_text());v=json.loads(check.read_text());assert r['exact_constant_fold'] and v['exact_constant_fold']
            assert r['baseline_sha256']==v['baseline_sha256']==item['artifact_sha256']
            assert r['candidate_sha256']==v['candidate_sha256']==sha(output)
            parts=r['fold']['functions'];totals={field:sum(f[field] for f in parts) for field in ['old_operations','new_operations','folded_values','folded_switches','dead_definitions','solver_work']}
            assert totals['solver_work']==r['fold']['solver_work']<=32_000_000
            part=dict(**item,**totals,declined_functions=sum(f['declined'] for f in parts),functions=len(parts),
                final_operations=r['control_flow']['new_operations'],folded_artifact_sha256=sha(output),report_sha256=sha(report),verification_sha256=sha(check),
                diagnostic_transform_seconds=r['diagnostic_transform_seconds'])
            reports.append(part);print(item['case'],part,flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=len(records),cases=reports,source_commit=composition['source_commit'],
            performance_measurement=False,guest_execution=False,original_artifacts_unchanged=True,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))

if __name__=='__main__':main()
