#!/usr/bin/env python3
"""Revalidate all three completed profiles offline; never repeat a guest command."""
import importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
spec=importlib.util.spec_from_file_location('guarded_profile',Path(__file__).with_name('profile.py'))
profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        work=ROOT/'.work/guarded-ranges-profile-repair-01';work.mkdir(exist_ok=False)
        raw=ROOT/'.work/guarded-ranges-profile-01'
        failure_path=ROOT/'results/guarded-ranges-profile-01-failure/summary.json'
        failure=json.loads(failure_path.read_text())
        parent=ROOT/'.work/experiments/guarded-ranges-validation-01'
        assert sha(parent/'status.json')==failure['parent_status_sha256']
        status=json.loads((parent/'status.json').read_text())
        assert status['status']=='finished' and status['returncode']==1
        assert sha(parent/'command.log')==status['log_sha256']
        assert sha(raw/'plan.json')==failure['plan_sha256']
        assert sha(raw/'records.json')==failure['records_sha256']
        old_plan=json.loads((raw/'plan.json').read_text())
        driver_path='benchmarks/experiments/guarded-ranges/profile.py'
        archived=failure_path.with_name('failed-profile-driver.py')
        assert sha(archived)==old_plan['frozen'][driver_path]==failure['driver_sha256']
        for name,digest in old_plan['frozen'].items():
            if name!=driver_path:assert sha(ROOT/name)==digest,name
        records=json.loads((raw/'records.json').read_text())
        assert len(records)==3 and [r['index'] for r in records]==[0,1,2]
        assert all(r['returncode']==0 and r['stdout']=='0\n' for r in records)
        build_path=ROOT/'results/guarded-ranges-build-01/summary.json'
        build=json.loads(build_path.read_text());assert build['status']=='passed'
        vm=ROOT/'.work/interpreter-tools'/build['tool_key']/'rust-interp-vm'
        assert sha(vm)==build['binaries']['rust-interp-vm']
        assert all(r['command'][0]==str(vm) for r in records)
        reference=json.loads((ROOT/'results/current-runtime-boundaries-02/summary.json').read_text())
        wide=json.loads((ROOT/'results/memory-operands-profile-01/summary.json').read_text())
        adopted_path=ROOT/'results/operation-map-real-01/summary.json'
        adopted=json.loads(adopted_path.read_text());assert adopted['exact_adopted_code'] and adopted['exact_per_pc_profiles']
        harness_path=ROOT/'results/guarded-ranges-python-tests-02/summary.json'
        harness=json.loads(harness_path.read_text());assert harness['status']=='passed' and harness['tests']==142 and harness['skipped']==10
        harness_inputs=ROOT/harness['raw']/'inputs.json';assert sha(harness_inputs)==harness['inputs_sha256']
        assert all(sha(ROOT/p)==h for p,h in json.loads(harness_inputs.read_text()).items())
        paths=[Path(__file__),Path(__file__).with_name('profile.py'),failure_path,archived,
            parent/'status.json',parent/'command.log',
            raw/'plan.json',raw/'records.json',build_path,vm,adopted_path,harness_path,harness_inputs,
            Path(__file__).with_name('PROFILE-REPAIR.md')]
        paths += [ROOT/name for name in old_plan['frozen'] if name!=driver_path]
        for index in range(3):
            paths += [raw/f'{index}-profile.json']
            paths += [raw/f'{index}-code'/name for name in ['code.bin','map.json','operations.json']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_commands=0,retained_guest_commands=3,
            only_changed_original_input=driver_path,require_active_profiles=[0,1],allow_inactive_profile=2))
        comparisons=[]
        for item,row in zip(reference['profiles'],records):
            require_space(ROOT,8);index=item['index'];assert row['index']==index
            selection,=[json.loads(line.split(': ',1)[1]) for line in row['stderr'].splitlines()
                if line.startswith('rust-interp-profile-selection: ')]
            assert selection==item['selection']
            stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',row['stderr'])}
            assert all(stats[k]==item['statistics'][k] for k in
                ['instructions','peak_guest_memory','entropy_calls','entropy_bytes','jit_declined_functions'])
            assert stats['jit_declined_functions']==0
            current=json.loads((raw/f'{index}-profile.json').read_text())
            prior_profile=json.loads((ROOT/wide['raw']/f'{index}-profile.json').read_text())
            assert profile.exact_profile_counts(current,prior_profile)
            prior,=[r for r in wide['comparisons'] if r['index']==index]
            attribution=profile.counts(current,stats)
            assert stats['jit_entries']==prior['candidate_jit_entries']
            assert attribution['interpreted_instructions']==prior['candidate_interpreted']
            dump=raw/f'{index}-code';code=(dump/'code.bin').read_bytes()
            regions=json.loads((dump/'map.json').read_text());mapping=json.loads((dump/'operations.json').read_text())
            assert len(code)==stats['jit_bytes']
            profile.validate_operation_map(mapping,regions,code,current,row['pid'])
            checks=profile.verify_range_checks(mapping,code,require_active=index!=2)
            unchanged=False
            if checks['guards']==0:
                control,=[r for r in adopted['comparisons'] if r['index']==index]
                assert sha(dump/'code.bin')==control['code_sha256']
                unchanged=True
            comparisons.append(dict(index=index,name=item['name'],profile_sha256=sha(raw/f'{index}-profile.json'),
                range_checks=checks,inactive_code_byte_identical_to_adopted=unchanged,
                baseline_interpreted=prior['candidate_interpreted'],candidate_interpreted=attribution['interpreted_instructions'],
                baseline_jit_entries=prior['candidate_jit_entries'],candidate_jit_entries=stats['jit_entries'],
                baseline_jit_bytes=prior['candidate_jit_bytes'],candidate_jit_bytes=stats['jit_bytes'],statistics=stats,
                operation_map_sha256=sha(dump/'operations.json'),code_map_sha256=sha(dump/'map.json'),code_sha256=sha(dump/'code.bin')))
            print(index,checks,'unchanged code',unchanged,flush=True)
        assert comparisons[0]['candidate_jit_bytes']<comparisons[0]['baseline_jit_bytes']
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        write(work/'comparisons.json',comparisons)
        out=ROOT/'results/guarded-ranges-profile-01';out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=3,new_guest_commands=0,tool_key=build['tool_key'],vm_sha256=sha(vm),
            exact_logical_counts_memory_and_entropy=True,exact_per_pc_counts=True,exact_operation_map_reconstruction=True,
            comparisons=comparisons,raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            offline_repair=str(work.relative_to(ROOT)),repair_plan_sha256=sha(work/'plan.json'),
            repair_comparisons_sha256=sha(work/'comparisons.json'),performance_measurement=False))

if __name__=='__main__':main()
