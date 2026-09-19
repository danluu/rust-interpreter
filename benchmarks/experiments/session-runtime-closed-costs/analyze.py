import hashlib,importlib.util,math,statistics,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
import json
RUN='session-runtime-closed-costs-01'
CASES={'token':'session-runtime-composition-edit-token-01','folded':'session-runtime-composition-edit-folded-01',
    'pgrust':'session-runtime-composition-edit-pgrust-02','rg-aot':'session-runtime-composition-edit-rg-aot-01'}
MODES=['baseline','duplicate','candidate','session-fresh']
def read(p):return json.loads(p.read_text())
def median(xs):
    assert xs and all(type(x) in [int,float] and math.isfinite(x) and x>=0 for x in xs)
    return statistics.median(xs)
def accounting(case):
    folder='session-runtime-composition-large-guards' if case=='rg-aot' else 'session-runtime-composition-guards'
    p=ROOT/'benchmarks/experiments'/folder/'accounting.py'
    spec=importlib.util.spec_from_file_location('closed_costs_accounting_'+case,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m,p
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);frozen={};derived={}
        def bind(p,h=None):
            digest=sha(p)
            if h is not None:assert digest==h,p
            frozen[str(p.relative_to(ROOT))]=digest;return read(p)
        for case,name in CASES.items():
            out=ROOT/'results'/name;c=bind(out/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            s=bind(out/'summary.json',c['summary_sha256']);t=bind(out/'terminal.json',c['terminal_sha256'])
            assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
            stage=ROOT/s['raw'];assert stage==ROOT/'.work'/name
            rows=bind(stage/'records.json',s['records_sha256']);sessions=bind(stage/'sessions.json',s['sessions_sha256'])
            module,path=accounting(case);frozen[str(path.relative_to(ROOT))]=sha(path)
            assert module.ratios(rows,sessions,case)==s['measurement']
            charged,overheads=module.account(rows,sessions);observed=[]
            for r in charged:
                if r['state']<=0 or r['mode'] not in MODES:continue
                j=bind(stage/(str(r['index'])+'-suite.json'),r['suite_sha256'])
                tests=j['tests'];assert len(tests)==s['original_tests'] and all(t['status']=='passed' for t in tests)
                assert j['failed']==0 and j['passed']==len(tests)
                values=dict(command_wall_seconds=r['accounted_wall_seconds'],command_cpu_seconds=r['accounted_cpu_seconds'],
                    build_to_ready_seconds=r['launch']['build_to_ready_seconds'],execution_seconds=r['launch']['execution_seconds'],
                    report_elapsed_seconds=j['seconds_before_report_write'],guest_test_work_seconds=sum(t['seconds'] for t in tests),
                    longest_guest_test_seconds=max(t['seconds'] for t in tests),jit_compile_work_seconds=sum(t['jit_compile_ns'] for t in tests)/1e9)
                if r['mode'] in ['candidate','session-fresh']:
                    values['preparation_work_seconds']=sum(w['preparation_ns'] for w in j['worker_records'])/1e9
                    values['template_hits']=sum((w['templates'] or {}).get('hits',0) for w in j['worker_records'])
                    values['template_lookups']=sum((w['templates'] or {}).get('lookups',0) for w in j['worker_records'])
                observed.append(dict(cycle=r['cycle'],state=r['state'],mode=r['mode'],values=values))
            assert len(observed)==60
            medians={mode:{key:median([r['values'][key] for r in observed if r['mode']==mode]) for key in next(r['values'] for r in observed if r['mode']==mode)} for mode in MODES}
            pairs=[]
            for cycle in range(3):
                for state in range(1,6):
                    arm={r['mode']:r['values'] for r in observed if r['cycle']==cycle and r['state']==state};assert set(arm)==set(MODES)
                    pairs.append(dict(cycle=cycle,state=state,ratios={base:{k:arm['candidate'][k]/v for k,v in arm[base].items() if v>0 and k in arm['candidate']} for base in ['baseline','session-fresh']},
                        differences={base:{k:arm['candidate'][k]-v for k,v in arm[base].items() if k in arm['candidate']} for base in ['baseline','session-fresh']}))
            derived[case]=dict(valid_edits=15,original_tests=s['original_tests'],medians=medians,paired_observations=pairs,
                interpretation='Descriptive intervals and work counters; stages overlap and separate medians are not additive.',
                full_history_gate_unchanged=s['measurement']['verdict'],public_names_disclosed=False)
            print(case,':15 edits/four arms, original verdict reproduced',flush=True)
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        write(raw/'derived.json',derived);write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],new_compiler_or_guest_commands=0,new_timing_samples=0))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            cases={case:{k:v for k,v in values.items() if k!='paired_observations'} for case,values in derived.items()},
            original_verdicts_reproduced=4,suite_reports=240,new_compiler_or_guest_commands=0,new_timing_samples=0,
            plan_sha256=sha(raw/'plan.json'),derived_sha256=sha(raw/'derived.json')))
if __name__=='__main__':main()
