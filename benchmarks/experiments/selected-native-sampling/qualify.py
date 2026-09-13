#!/usr/bin/env python3
"""Check uninstrumented selection against all seven exact real profile receipts."""
import argparse,json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from workflow_io import capture,require_space,write_json as write

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',type=Path,required=True);parser.add_argument('--run-id',required=True)
    kinds=parser.add_mutually_exclusive_group()
    kinds.add_argument('--parallel-suite-candidate',action='store_true',help='qualify the 365-test parallel runner against the same serial reference inputs')
    kinds.add_argument('--composed-candidate',action='store_true',help='qualify the 393-test corrected composed runtime against the same serial reference inputs')
    kinds.add_argument('--call-protocol-candidate',action='store_true',help='qualify the 395-test call-protocol runtime')
    kinds.add_argument('--guarded-indirect-candidate', action='store_true', help='qualify the 424-test guarded indirect-call runtime')
    kinds.add_argument('--wide-bitwise-candidate', action='store_true', help='qualify the 419-test wide integer emitter')
    kinds.add_argument('--capacity-credit-candidate', action='store_true', help='qualify the 422-test capacity-credit runtime')
    kinds.add_argument('--main-integration-candidate',action='store_true',help='qualify the 418-test compiler/runtime integration')
    args=parser.parse_args();assert re.fullmatch(r'(guarded-indirect|wide-bitwise|call-capacity-credit|call-protocol-main|resumable-call-protocol|composed-development|parallel-suites|selected-native)-qualification-\d{2}',args.run_id)
    assert args.run_id.startswith('guarded-indirect')==args.guarded_indirect_candidate
    assert args.run_id.startswith('wide-bitwise')==args.wide_bitwise_candidate
    assert args.run_id.startswith('call-capacity-credit')==args.capacity_credit_candidate
    assert args.run_id.startswith('call-protocol-main')==args.main_integration_candidate
    assert args.run_id.startswith('resumable-call-protocol')==args.call_protocol_candidate
    assert args.run_id.startswith('parallel-suites')==args.parallel_suite_candidate
    assert args.run_id.startswith('composed-development')==args.composed_candidate
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,3.5)
        build_path=args.build.resolve(strict=True);build=json.loads(build_path.read_text())
        expected_tests=424 if args.guarded_indirect_candidate else 419 if args.wide_bitwise_candidate else 422 if args.capacity_credit_candidate else 418 if args.main_integration_candidate else 395 if args.call_protocol_candidate else 393 if args.composed_candidate else 365 if args.parallel_suite_candidate else 360
        assert build['status']=='passed' and build['tests']['test-debug']==build['tests']['test-release']==dict(passed=expected_tests,ignored=1)
        tools,key=installed_tools(build['tool_key']);vm=tools/'rust-interp-vm';assert sha(vm)==build['binaries']['rust-interp-vm']
        reference_path=ROOT/'results/suite-profiling-real-01/summary.json';reference=json.loads(reference_path.read_text());assert reference['status']=='passed' and reference['exact_logical_counts_and_entropy']
        old=ROOT/'.work/suite-profiling-real-01';old_records=json.loads((old/'records.json').read_text());assert sha(old/'records.json')==reference['records_sha256']
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json';entropy=json.loads(entropy_path.read_text());assert entropy['status']=='passed'
        library=ROOT/entropy['library'];assert sha(library)==entropy['library_sha256']
        inputs=[];paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),build_path,reference_path,old/'records.json',vm,entropy_path,library,
            ROOT/'scripts/workflow_io.py',ROOT/'scripts/interpreter.py',ROOT/'scripts/workspace_cache.py',ROOT/'scripts/compare_saved_runtime.py']
        if args.parallel_suite_candidate:paths.append(ROOT/'benchmarks/experiments/parallel-suites/PLAN.md')
        if args.guarded_indirect_candidate:paths.append(ROOT/'benchmarks/experiments/guarded-indirect/PLAN.md')
        if args.wide_bitwise_candidate:paths.append(ROOT/'benchmarks/experiments/wide-bitwise/PLAN.md')
        if args.capacity_credit_candidate:paths.append(ROOT/'benchmarks/experiments/call-capacity-credit/PLAN.md')
        if args.main_integration_candidate:paths.append(ROOT/'benchmarks/experiments/call-protocol-main/PLAN.md')
        if args.call_protocol_candidate:paths.append(ROOT/'benchmarks/experiments/resumable-call-protocol/PLAN.md')
        if args.composed_candidate:paths.append(ROOT/'benchmarks/experiments/composed-development/PLAN.md')
        for case in reference['profiles']:
            artifact=ROOT/case['artifact'];catalog=ROOT/case['catalog'];tape=old/(str(case['index'])+'.tape');profile=old/(str(case['index'])+'-profile.json')
            assert sha(artifact)==case['artifact_sha256'] and sha(catalog)==case['catalog_sha256'] and sha(profile)==case['profile_sha256']
            prior=next(r for r in old_records if r['index']==case['index'] and r['mode']=='profile');assert sha(tape)==prior['tape_sha256']
            inputs.append(dict(case=case,artifact=str(artifact),catalog=str(catalog),tape=str(tape),tape_sha256=sha(tape)))
            paths += [artifact,catalog,tape,profile]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths};work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,inputs=inputs,vm_sha256=sha(vm),minimum_free_gib=3,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))};assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE='replay',RUST_INTERP_VM_STATS='1')
        rows=[]
        for item in inputs:
            require_space(ROOT,3);case=item['case'];selected=dict(env,RUST_INTERP_ENTROPY_TAPE=item['tape'])
            command=[str(vm),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--select-test',case['name'],'--suite-catalog',item['catalog'],
                '--instruction-limit',str(case['limits']['instructions']),'--allocation-limit',str(case['limits']['allocations']),item['artifact']]
            child,stdout,stderr=capture(command,cwd=ROOT,env=selected,receipt_path=work/'active.json',receipt=dict(index=case['index']))
            row=dict(index=case['index'],command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr);rows.append(row);write(work/'records.json',rows)
            assert child.returncode==0 and stdout=='0\n',stderr
            selection=[json.loads(line.split(': ',1)[1]) for line in stderr.splitlines() if line.startswith('rust-interp-test-selection: ')]
            assert len(selection)==1 and selection[0]==case['selection']
            stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',stderr)}
            expected={k:case['statistics'][k] for k in ['instructions','peak_guest_memory','jit_declined_functions','entropy_calls','entropy_bytes']}
            assert {k:stats[k] for k in expected}==expected and sha(Path(item['tape']))==item['tape_sha256']
            row.update(selection=selection[0],statistics=stats,exact_reference_statistics=expected);write(work/'records.json',rows);print(case['index'],case['name'],'passed',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items());out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=len(rows),selected_tests=len(rows),tool_key=key,vm_sha256=sha(vm),
            original_assertions_match=True,exact_instructions_memory_and_entropy=True,bytecode_and_catalogs_unchanged=True,performance_measurement=False,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))

if __name__=='__main__':main()
