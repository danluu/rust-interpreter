#!/usr/bin/env python3
"""Inspect typed allocation against current, provenance-bound real profiles."""
import json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from profile_vm_transitions import counts as checked_counts
from workflow_io import capture,require_space,write_json as write

def main():
    run='register-lifetimes-census-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        build_path=ROOT/'results/register-lifetimes-build-01/summary.json';build=json.loads(build_path.read_text())
        assert build['status']=='passed' and build['source_commit'].startswith('b352fee')
        assert build['tests']['test-debug']==build['tests']['test-release']==dict(passed=346,ignored=1)
        build_work=ROOT/build['raw'];build_plan=json.loads((build_work/'plan.json').read_text())
        assert sha(build_work/'plan.json')==build['source_manifest_sha256']
        status_path=ROOT/'.work/experiments/register-lifetimes-build-01/status.json';status=json.loads(status_path.read_text())
        assert status['status']=='finished' and status['returncode']==0 and status['owner']==str(ROOT)
        assert sha(status_path.with_name('command.log'))==status['log_sha256']
        assert all(sha(ROOT/p)==h for p,h in build_plan['frozen'].items())
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        binary=work/'rust-interp-lifetime-census';original=Path(build_plan['target'])/'release'/binary.name
        shutil.copy2(original,binary);assert sha(binary)==sha(original)
        reference_path=ROOT/'results/suite-profiling-real-01/summary.json';reference=json.loads(reference_path.read_text())
        assert reference['status']=='passed' and reference['exact_logical_counts_and_entropy']
        frozen_paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),build_path,build_work/'plan.json',build_work/'commands.json',
            status_path,status_path.with_name('command.log'),binary,reference_path,ROOT/'scripts/profile_vm_transitions.py']
        inputs=[]
        for item in reference['profiles']:
            if item['index'] not in [0,1,2,5]:continue
            artifact=ROOT/item['artifact'];catalog=ROOT/item['catalog'];profile=ROOT/reference['raw']/f"{item['index']}-profile.json"
            assert sha(artifact)==item['artifact_sha256'] and sha(catalog)==item['catalog_sha256'] and sha(profile)==item['profile_sha256']
            frozen_paths += [artifact,catalog,profile]
            inputs.append(dict(index=item['index'],case=item['case'],name=item['name'],artifact=str(artifact.relative_to(ROOT)),profile=str(profile.relative_to(ROOT)),
                artifact_sha256=sha(artifact),profile_sha256=sha(profile),statistics=item['statistics']))
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,inputs=inputs,binary_sha256=sha(binary),performance_measurement=False,
            scope='Offline many-to-one lifetime allocation, current token/folded/pgrust profiles; no original artifact mutation or guest execution. All native residency estimates omit transfer/setup/cache costs.'))
        rows=[];reports=[]
        for item in inputs:
            profile=json.loads((ROOT/item['profile']).read_text());checked_counts(profile,item['statistics'])
            output=work/(str(item['index'])+'.json');command=[str(binary),str(ROOT/item['artifact']),str(output),str(ROOT/item['profile'])]
            require_space(ROOT,8)
            child,stdout,stderr=capture(command,cwd=ROOT,env=os.environ.copy(),receipt_path=work/'active.json',receipt=dict(index=item['index']))
            row=dict(index=item['index'],command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr)
            rows.append(row);write(work/'records.json',rows);assert child.returncode==0,stderr
            report=json.loads(output.read_text());assert report['artifact_sha256']==item['artifact_sha256'] and report['profile_sha256']==item['profile_sha256']
            assert len(report['functions'])==len(profile['functions'])
            fields=['old_slots_in_admitted_functions','referenced_slots','allocated_slots','operand_reads','baseline_assigned_reads','allocated_assigned_reads','declined_functions']
            declined_native=0;hot=[]
            for f in report['functions']:
                observed=profile['functions'][f['function']]
                native=sum(hits*(end-pc) for pc,(hits,end) in enumerate(zip(observed['jit_blocks'],observed['jit_block_ends'])) if hits)
                if f['declined']:declined_native+=native;continue
                assert f['allocated_slots']<=f['referenced_slots']<=f['old_slots']
                assert 0<=f['baseline_assigned_reads']<=f['operand_reads'] and 0<=f['allocated_assigned_reads']<=f['operand_reads']
                if native:
                    hot.append(dict(function=f['function'],name_prefix=observed['name'][:160],native_operations=native,
                        old_slots=f['old_slots'],allocated_slots=f['allocated_slots'],extra_assigned_reads=f['allocated_assigned_reads']-f['baseline_assigned_reads']))
            for total,field in [('old_slots_in_admitted_functions','old_slots'),('referenced_slots','referenced_slots'),('allocated_slots','allocated_slots'),
                ('operand_reads','operand_reads'),('baseline_assigned_reads','baseline_assigned_reads'),('allocated_assigned_reads','allocated_assigned_reads')]:
                assert report[total]==sum(f[field] for f in report['functions'] if not f['declined'])
            extra=report['allocated_assigned_reads']-report['baseline_assigned_reads']
            part=dict(index=item['index'],case=item['case'],name=item['name'],**{k:report[k] for k in fields},
                additional_fraction_of_reads_in_admitted_functions=extra/report['operand_reads'],
                native_operation_fraction_declined=declined_native/item['statistics']['jit_instructions'],
                top_hot_functions=sorted(hot,key=lambda r:-r['native_operations'])[:12],
                report_sha256=sha(output),artifact_sha256=item['artifact_sha256'],profile_sha256=item['profile_sha256'])
            reports.append(part);row['report_sha256']=sha(output);write(work/'records.json',rows);write(work/'reports.json',reports)
            print(item['index'],item['case'],'additional assigned-read fraction',part['additional_fraction_of_reads_in_admitted_functions'],flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=len(rows),cases=reports,binary_sha256=sha(binary),
            source_commit=build['source_commit'],performance_measurement=False,original_artifacts_unchanged=True,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))

if __name__=='__main__':main()
