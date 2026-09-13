#!/usr/bin/env python3
"""Three conditional range censuses and all three prior CLI controls; no guest execution."""
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--run-id',required=True);args=parser.parse_args()
    assert args.run_id=='disjoint-frame-census-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        build_path=args.build.resolve(strict=True);build=json.loads(build_path.read_text())
        assert build['status']=='passed' and build['tests']=={p:dict(passed=470,ignored=1) for p in ['debug','release']}
        binary=ROOT/build['binary'];assert sha(binary)==build['binary_sha256']
        build_plan=ROOT/build['raw']/'plan.json';assert sha(build_plan)==build['plan_sha256']
        assert all(sha(ROOT/p)==h for p,h in json.loads(build_plan.read_text())['frozen'].items())
        reference_path=ROOT/'results/current-runtime-boundaries-02/summary.json'
        adopted_path=ROOT/'results/operation-map-real-01/summary.json'
        legacy_path=ROOT/'results/address-check-reuse-census-01/summary.json'
        reference,adopted,legacy=[json.loads(p.read_text()) for p in [reference_path,adopted_path,legacy_path]]
        assert all(r['status']=='passed' for r in [reference,adopted,legacy])
        assert adopted['exact_adopted_code'] and adopted['exact_per_pc_profiles']
        paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),build_path,build_plan,binary,reference_path,adopted_path,legacy_path,ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']
        inputs=[]
        for row in reference['profiles']:
            index=row['index'];artifact=ROOT/row['artifact']
            prior,=[r for r in adopted['comparisons'] if r['index']==index]
            profile=ROOT/adopted['raw']/f'{index}-profile.json'
            assert sha(artifact)==row['artifact_sha256'] and sha(profile)==prior['profile_sha256']
            paths += [artifact,profile]
            inputs.append(dict(index=index,artifact=str(artifact.relative_to(ROOT)),profile=str(profile.relative_to(ROOT))))
        # Use the exact saved legacy command's output path, not an inferred name.
        legacy_records=ROOT/legacy['raw']/'records.json'
        assert sha(legacy_records)==legacy['records_sha256']
        first,=[r for r in json.loads(legacy_records.read_text()) if r['label']=='census-0']
        legacy_report=Path(first['command'][2]);assert sha(legacy_report)==legacy['comparisons'][0]['report_sha256']
        paths += [legacy_report,legacy_records]
        region_proof_path=ROOT/'results/region-facts-census-01/summary.json'
        region_proof=json.loads(region_proof_path.read_text());assert region_proof['status']=='passed'
        region_report=ROOT/region_proof['raw']/'0.json'
        assert sha(region_report)==region_proof['comparisons'][0]['report_sha256']
        paths += [region_proof_path,region_report]
        strict_proof_path=ROOT/'results/range-groups-census-01/summary.json'
        strict_proof=json.loads(strict_proof_path.read_text());assert strict_proof['status']=='passed'
        strict_report=ROOT/strict_proof['raw']/'0.json'
        assert sha(strict_report)==strict_proof['comparisons'][0]['report_sha256']
        paths += [strict_proof_path,strict_report]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,inputs=inputs,expected_commands=13,guest_executions=0,performance_measurement=False))
        records=[];reports=[]
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','DYLD_'))}
        def command(label,argv,success):
            require_space(ROOT,8)
            child,out,err=capture([str(binary),*map(str,argv)],cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            records.append(dict(label=label,pid=child.pid,command=[str(binary),*map(str,argv)],returncode=child.returncode,stdout=out,stderr=err,expected_success=success))
            write(work/'records.json',records);assert (child.returncode==0)==success,(label,err)
        for row in inputs:
            report=work/f"{row['index']}.json"
            command('census-'+str(row['index']),['--disjoint-frame',ROOT/row['artifact'],report,ROOT/row['profile']],True)
            data=json.loads(report.read_text())
            assert data['guest_instructions_executed']==0 and data['emitter_changed'] is False
            assert data['artifact_sha256']==frozen[row['artifact']] and data['profile_sha256']==frozen[row['profile']]
            counts=data['counts'];assert counts['fixed_addresses']==counts['local_addresses']+counts['unknown_addresses']
            assert counts['best_group_redundant_checks']<=counts['best_group_addresses']<=counts['all_group_addresses']<=counts['entry_pointer_addresses']<=counts['unknown_addresses']
            assert counts['frame_disjoint_group_addresses']<=counts['best_group_addresses']
            assert counts['frame_disjoint_redundant_checks']<=counts['best_group_redundant_checks']
            assert data['frame_disjoint_assumption']
            assert all(sum(r['counts'][key] for r in data['functions'])==value for key,value in counts.items())
            reports.append(dict(index=row['index'],counts=counts,declined_functions=len(data['declined_functions']),analysis_work=data['analysis_work'],report_sha256=sha(report),top_functions=[r for r in data['functions'] if r['counts']['best_group_addresses']][:8]))
            print(row['index'],json.dumps(counts),'declines',len(data['declined_functions']),flush=True)
        item=inputs[0];artifact=ROOT/item['artifact'];profile=ROOT/item['profile']
        command('legacy-mode',[artifact,work/'legacy.json',profile],True)
        assert (work/'legacy.json').read_bytes()==legacy_report.read_bytes()
        command('region-fact-mode',['--region-facts',artifact,work/'region-facts.json',profile],True)
        assert (work/'region-facts.json').read_bytes()==region_report.read_bytes()
        command('strict-range-mode',['--range-groups',artifact,work/'range-groups.json',profile],True)
        assert (work/'range-groups.json').read_bytes()==strict_report.read_bytes()
        (work/'empty.rbc').write_bytes(b'');(work/'directory').mkdir()
        (work/'symlink.rbc').symlink_to(artifact)
        for name,size in [('oversized.rbc',64*1024**2+1),('oversized-profile.json',256*1024**2+1)]:
            with (work/name).open('xb') as stream:stream.truncate(size)
        cases=[('empty',work/'empty.rbc',profile),('mismatched',artifact,ROOT/inputs[2]['profile']),
            ('oversized-bytecode',work/'oversized.rbc',profile),('oversized-profile',artifact,work/'oversized-profile.json'),
            ('directory',work/'directory',profile),('symlink',work/'symlink.rbc',profile)]
        for label,program,source_profile in cases:
            output=work/(label+'-output.json');command(label,['--disjoint-frame',program,output,source_profile],False)
            assert not output.exists()
        existing=work/'0.json';before=sha(existing)
        command('existing-output',['--disjoint-frame',artifact,existing,profile],False);assert sha(existing)==before
        assert len(records)==13 and all(sha(ROOT/p)==h for p,h in frozen.items())
        destination=ROOT/'results'/args.run_id;destination.mkdir(exist_ok=False)
        result=dict(status='passed',commands=13,guest_executions=0,typed_profile_cases=3,cli_rejection_controls=7,legacy_output_byte_identical=True,region_fact_output_byte_identical=True,strict_range_output_byte_identical=True,comparisons=reports,raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),binary_sha256=sha(binary),performance_measurement=False,emitter_changed=False)
        write(destination/'summary.json',result)

if __name__=='__main__':main()
