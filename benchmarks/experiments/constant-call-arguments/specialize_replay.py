#!/usr/bin/env python3
"""Check saved specialized programs against all original assertions and fixed entropy."""
import argparse,json,os,re,shutil,statistics,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from workflow_io import capture,require_space,write_json as write
from workflow_measurements import child_usage,child_cpu_since
from suite_reports import read_report,validate_report,validate_runtime_limits


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--saved',required=True,type=Path)
    args=parser.parse_args();run=args.run_id
    assert re.fullmatch(r'constant-specialize-replay-\d{2}',run)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,4)
        build_path=ROOT/'results/suite-profiling-build-02/summary.json'
        saved_path=args.saved.resolve(strict=True)
        entropy_path=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json'
        build=json.loads(build_path.read_text());saved=json.loads(saved_path.read_text());entropy=json.loads(entropy_path.read_text())
        assert build['status']==saved['status']==entropy['status']=='passed'
        assert entropy['commands']==17 and entropy['expected_rejections']==10
        tools,key=installed_tools(build['tool_key']);vm=tools/'rust-interp-vm'
        assert sha(vm)==build['binaries']['rust-interp-vm']
        verifier=ROOT/saved['verifier'];assert sha(verifier)==saved['verifier_sha256']
        assert any(c['specialization']['clones'] for c in saved['cases'])
        library=ROOT/entropy['library'];assert sha(library)==entropy['library_sha256']
        paths=[Path(__file__),Path(__file__).with_name('SPECIALIZATION-SAVED.md'),build_path,saved_path,entropy_path,vm,verifier,library]
        paths += [ROOT/'scripts'/name for name in ['compare_saved_runtime.py','interpreter.py','workspace_cache.py','workflow_io.py','workflow_measurements.py','suite_reports.py','native_suite.py']]
        inputs=[]
        for case in saved['cases']:
            original=ROOT/case['artifact'];candidate=ROOT/saved['raw']/(str(case['index'])+'.rbc')
            assert sha(original)==case['artifact_sha256'] and sha(candidate)==case['candidate_artifact_sha256']
            catalog=Path(str(original)+'.entries.json');entries=json.loads(catalog.read_text());names=[e['name'] for e in entries['entries']]
            assert entries['artifact_sha256']==sha(original)
            reference_path=ROOT/'results'/original.parent.name/'summary.json';reference=json.loads(reference_path.read_text());assert reference['status']=='passed'
            records_path=ROOT/reference['raw']/'records.json';assert sha(records_path)==reference['records_sha256']
            prior={r['mode']:r for r in json.loads(records_path.read_text()) if r['state']==6}
            receipts={mode:ROOT/reference['raw']/('6-'+mode+'-suite.json') for mode in ['native','automatic']}
            reports={mode:read_report(path,prior[mode]['suite_sha256'])[0] for mode,path in receipts.items()}
            outcomes=validate_report(reports['native'],names,'native',True)
            assert validate_report(reports['automatic'],names,'prepared',True)==outcomes
            assert prior['automatic']['artifact_sha256']==sha(original) and prior['automatic']['launch']['entry_catalog_sha256']==sha(catalog)
            paths += [original,candidate,catalog,reference_path,records_path,*receipts.values()]
            inputs.append(dict(case=case['case'],artifacts=dict(baseline=str(original),candidate=str(candidate)),catalog=str(catalog),names=names,limits=reports['automatic']['runtime_limits']))
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,inputs=inputs,vm_sha256=sha(vm),minimum_free_gib=4,pairs_per_case=3,
            scope='Saved-program runtime and correctness diagnostic; no changed-source compilation or end-to-end performance gate. One exact recorded entropy stream per case.'))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))};assert not any(k.startswith('DYLD_') for k in env)
        guest_env=dict(env,DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_VM_STATS='1')
        records=[];summaries=[];space=[]
        def execute(command,selected,case,mode,pair):
            space.append(dict(case=case,mode=mode,pair=pair,free_bytes=shutil.disk_usage(ROOT).free,checked_at=time.time()));write(work/'space.json',space);require_space(ROOT,4)
            before=child_usage();started=time.perf_counter()
            child,stdout,stderr=capture(command,cwd=ROOT,env=selected,receipt_path=work/'active.json',receipt=dict(case=case,mode=mode,pair=pair))
            row=dict(case=case,mode=mode,pair=pair,command=command,pid=child.pid,returncode=child.returncode,seconds=time.perf_counter()-started,cpu=child_cpu_since(before),stdout=stdout,stderr=stderr)
            records.append(row);write(work/'records.json',records)
            assert child.returncode==0,stderr
            return row
        for item in inputs:
            case=item['case'];limits=item['limits'];tape=work/(case+'.tape')
            verification=work/(case+'-specialize.json')
            execute([str(verifier),'--verify-specialize',item['artifacts']['baseline'],item['artifacts']['candidate'],str(verification)],env,case,'verify',None)
            verified=json.loads(verification.read_text());assert verified['exact_constant_specialization']
            assert verified['baseline_sha256']==sha(Path(item['artifacts']['baseline'])) and verified['candidate_sha256']==sha(Path(item['artifacts']['candidate']))
            candidate_catalog=json.loads(Path(item['catalog']).read_text());candidate_catalog['artifact_sha256']=verified['candidate_sha256']
            candidate_catalog_path=work/(case+'-candidate-catalog.json');write(candidate_catalog_path,candidate_catalog)
            catalogs=dict(baseline=item['catalog'],candidate=str(candidate_catalog_path));per_artifact={};entropy_counts=None;tape_digest=None;pairs=[]
            order=[(-1,'baseline')]+[(pair,mode) for pair in range(3) for mode in (['baseline','candidate'] if pair%2==0 else ['candidate','baseline'])]
            for pair,mode in order:
                report_path=work/(f'{case}-{pair}-{mode}-suite.json')
                command=[str(vm),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--isolated-batch','prepared',
                    '--suite-report',str(report_path),'--suite-catalog',catalogs[mode],'--instruction-limit',str(limits['instructions']),
                    '--allocation-limit',str(limits['allocations']),item['artifacts'][mode]]
                selected=dict(guest_env,RUST_INTERP_ENTROPY_MODE='record' if pair==-1 else 'replay',RUST_INTERP_ENTROPY_TAPE=str(tape))
                row=execute(command,selected,case,mode,pair);assert row['stdout']=='0\n'
                report,digest=read_report(report_path);validate_report(report,item['names'],'prepared',True)
                validate_runtime_limits(report,limits['instructions'],limits['allocations'],required=True)
                counts={k:int(v) for k,v in re.findall(r'\b(entropy_calls|entropy_bytes)=(\d+)\b',row['stderr'])};assert len(counts)==2
                observed=[{k:t[k] for k in ['name','function','instructions','peak_guest_memory']} for t in report['tests']]
                if pair==-1:entropy_counts=counts;tape_digest=sha(tape)
                assert counts==entropy_counts and sha(tape)==tape_digest
                if mode in per_artifact:assert observed==per_artifact[mode]
                else:per_artifact[mode]=observed
                if len(per_artifact)==2:
                    assert [{k:t[k] for k in ['name','function','peak_guest_memory']} for t in observed]==[{k:t[k] for k in ['name','function','peak_guest_memory']} for t in per_artifact['baseline']]
                row.update(suite_sha256=digest,entropy=counts,tape_sha256=tape_digest,instructions=sum(t['instructions'] for t in observed),jit_declines=sum(t['jit_declined_functions'] for t in report['tests']))
                write(work/'records.json',records);print(case,pair,mode,round(row['seconds'],3),row['instructions'],'instructions',flush=True)
            for pair in range(3):
                r={row['mode']:row for row in records if row['case']==case and row['pair']==pair}
                pairs.append(dict(pair=pair,wall_ratio=r['candidate']['seconds']/r['baseline']['seconds'],cpu_ratio=r['candidate']['cpu']['total_seconds']/r['baseline']['cpu']['total_seconds']))
            summaries.append(dict(case=case,tests=len(item['names']),pairs=pairs,median_runtime_wall_ratio=statistics.median(p['wall_ratio'] for p in pairs),median_runtime_cpu_ratio=statistics.median(p['cpu_ratio'] for p in pairs),
                instructions={mode:sum(t['instructions'] for t in tests) for mode,tests in per_artifact.items()},native_assertion_outcomes_match=True,exact_entropy_replay=True,per_test_peak_memory_equal=True,verification_sha256=sha(verification),candidate_catalog_sha256=sha(candidate_catalog_path)))
            write(work/'cases.json',summaries)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/run;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=len(records),vm_commands=21,verification_commands=3,cases=summaries,vm_sha256=sha(vm),
            complete_workflow_measurement=False,adoption_gate_evaluated=False,saved_artifacts_unchanged=True,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),space_sha256=sha(work/'space.json')))


if __name__=='__main__':main()
