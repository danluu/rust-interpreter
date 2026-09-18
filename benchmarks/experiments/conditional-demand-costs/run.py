"""Audit retained parser launch stages and both prepared workers; run no guest."""
import hashlib,json,statistics,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from suite_reports import read_report,validate_report
NAME='conditional-demand-costs-01'
SCREEN='conditional-demand-parser-screen-incremental-01'
MODES=['baseline','duplicate','candidate','anchor']
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        folder=ROOT/'results'/SCREEN;summary=read(folder/'summary.json');closed=read(folder/'closure.json')
        assert summary['status']=='passed' and summary['commands']==40 and summary['original_tests']==114
        assert closed['status']=='closed' and closed['all_hashes_verified'] and closed['verdict']=='failed'
        assert sha(folder/'summary.json')==closed['summary_sha256'] and sha(folder/'terminal.json')==closed['terminal_sha256']
        raw=ROOT/summary['raw'];paths=[folder/n for n in ['summary.json','closure.json','terminal.json']]
        for name in ['plan','records','space']:
            assert sha(raw/(name+'.json'))==summary[name+'_sha256'];paths.append(raw/(name+'.json'))
        evidence=ROOT/closed['evidence'];assert sha(evidence)==closed['evidence_sha256'];paths.append(evidence)
        for path,digest in read(evidence).items():assert sha(ROOT/path)==digest
        records=read(raw/'records.json');plan=read(raw/'plan.json')
        names=[plan['custom_template'][i+1] for i,x in enumerate(plan['custom_template']) if x=='--entry']
        assert len(names)==len(set(names))==114
        selected=[r for r in records if r['state']>0 and r['mode'] in MODES]
        assert len(selected)==20 and {(r['state'],r['mode']) for r in selected}=={(s,m) for s in range(1,6) for m in MODES}
        paths += [raw/(str(r['index'])+'-suite.json') for r in selected]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [ROOT/'scripts'/n for n in ['compare_saved_runtime.py','workflow_io.py','suite_reports.py']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,guest_commands=0,source_edits=0,minimum_free_gib=8,performance_measurement=False))
        rows=[]
        for record in selected:
            report,_=read_report(raw/(str(record['index'])+'-suite.json'),record['suite_sha256'])
            validate_report(report,names,'prepared',True);assert report['workers']==report['requested_workers']==2
            workers=[]
            for worker in range(2):
                tests=[t for t in report['tests'] if t['worker']==worker];assert tests
                last=tests[-1]
                assert all(a['jit_bytes']<=b['jit_bytes'] for a,b in zip(tests,tests[1:]))
                assert 0<last['jit_bytes']<=16*1024**2
                native=sum(t['jit_instructions'] for t in tests);total=sum(t['instructions'] for t in tests)
                assert all(0<=t['jit_instructions']<=t['instructions'] for t in tests)
                data=dict(worker=worker,tests=len(tests),test_seconds=sum(t['seconds'] for t in tests),
                    compile_seconds=sum(t['jit_compile_ns'] for t in tests)/1e9,
                    final_code_bytes=last['jit_bytes'],compiled_functions=last['jit_compiled_functions'],
                    declined_functions=last['jit_declined_functions'],instructions=total,native=native,interpreted=total-native,
                    entries=sum(t['jit_entries'] for t in tests))
                if record['mode']=='candidate':
                    data['demand']=last['jit_demand']
                    for field in ['published_regions','declined_regions','eager_fallbacks','plan_bytes','metadata_bytes']:
                        assert all(a['jit_demand'][field]<=b['jit_demand'][field] for a,b in zip(tests,tests[1:]))
                    for field in ['plan_bytes','metadata_bytes']:assert 0<data['demand'][field]<=16*1024**2
                workers.append(data)
            reference,=[t for t in report['tests'] if t['name']=='tests_dump::c_reference_vectors']
            launch=record['launch']
            rows.append(dict(state=record['state'],mode=record['mode'],wall_seconds=record['wall_seconds'],cpu_seconds=record['cpu_seconds'],
                cargo_seconds=launch['cargo_seconds'],ready_seconds=launch['build_to_ready_seconds'],execution_seconds=launch['execution_seconds'],
                suite_seconds=report['seconds_before_report_write'],constructor_sum_seconds=report['preparation_ns']/1e9,
                compile_sum_seconds=sum(w['compile_seconds'] for w in workers),compile_max_worker_seconds=max(w['compile_seconds'] for w in workers),
                interpreted=sum(w['interpreted'] for w in workers),native=sum(w['native'] for w in workers),
                final_code_sum=sum(w['final_code_bytes'] for w in workers),workers=workers,
                reference_vectors={k:reference[k] for k in ['worker','seconds','instructions','jit_instructions','jit_compile_ns','jit_bytes','jit_entries']}))
        metrics=['wall_seconds','cpu_seconds','cargo_seconds','ready_seconds','execution_seconds','suite_seconds',
            'constructor_sum_seconds','compile_sum_seconds','compile_max_worker_seconds','interpreted','native','final_code_sum']
        medians={mode:{key:statistics.median(r[key] for r in rows if r['mode']==mode) for key in metrics} for mode in MODES}
        paired={}
        for key in metrics:
            ratios=[]
            for state in range(1,6):
                pair={r['mode']:r for r in rows if r['state']==state}
                assert pair['baseline'][key]>0;ratios.append(pair['candidate'][key]/pair['baseline'][key])
            paired[key]=statistics.median(ratios)
        assert all(sha(ROOT/path)==digest for path,digest in frozen.items())
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',retained_commands=20,new_guest_commands=0,source_edits=0,
            rows=rows,medians=medians,paired_median_ratios=paired,raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),
            exact_cross_run_logical_counts=False,ordinary_os_entropy=True,performance_measurement=False,
            limitations='Retained stages are descriptive and overlap; constructor/compile sums are not command critical paths. OS entropy and dynamic worker scheduling differ. No new timing or causal subtraction.'))
        print(json.dumps(dict(paired_median_ratios=paired,medians=medians)),flush=True)
if __name__=='__main__':main()
