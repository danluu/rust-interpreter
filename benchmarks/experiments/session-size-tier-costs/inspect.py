"""Read closed primary stage intervals without executing any guest or compiler."""
import json,statistics,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-screen'))
from accounting import SESSION_MODES,account
RUN='session-size-tier-primary-costs-01'
PRIMARY='cross-program-template-parser-screen-incremental-03'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12);frozen={}
        def bind(path,expected=None):
            h=sha(path)
            if expected is not None:assert h==expected,path
            frozen[str(path.relative_to(ROOT))]=h;return read(path) if path.suffix=='.json' else h
        result=ROOT/'results'/PRIMARY;c=bind(result/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
        s=bind(result/'summary.json',c['summary_sha256']);assert s['measurement']['verdict']=='unmeasurable' and not s['measurement']['gate_passed']
        bind(result/'terminal.json',c['terminal_sha256']);evidence=bind(ROOT/c['evidence'],c['evidence_sha256'])
        old=ROOT/s['raw'];records=bind(old/'records.json',s['records_sha256']);sessions=bind(old/'sessions.json',s['sessions_sha256'])
        rows,_=account(records,sessions);observed=[]
        for row in rows:
            if row['state']<=0 or row['mode']=='native':continue
            report_path=old/f"{row['index']}-suite.json";report=bind(report_path,evidence[str(report_path.relative_to(ROOT))]);launch=row['launch']
            value=dict(index=row['index'],state=row['state'],mode=row['mode'],wall_ms=row['accounted_wall_seconds']*1000,
                cpu_ms=row['accounted_cpu_seconds']*1000,build_to_ready_ms=launch['build_to_ready_seconds']*1000,
                execution_ms=launch['execution_seconds']*1000,
                launcher_after_execution_ms=(launch['launcher_seconds']-launch['build_to_ready_seconds']-launch['execution_seconds'])*1000,
                report_interval_ms=report['seconds_before_report_write']*1000,
                test_compile_sum_ms=sum(t.get('jit_compile_ns',0) for t in report['tests'])/1e6)
            assert value['launcher_after_execution_ms']>=0
            if row['mode'] in SESSION_MODES:
                request=launch['template_session']['response']['request_seconds']*1000
                value.update(server_request_ms=request,client_outside_server_request_ms=value['execution_ms']-request,
                    server_outside_worker_interval_ms=request-value['report_interval_ms'],
                    preparation_sum_ms=sum(w['preparation_ns'] for w in report['worker_records'])/1e6,
                    history_hits=sum((w['templates'] or {}).get('hits',0) for w in report['worker_records']),
                    history_lookups=sum((w['templates'] or {}).get('lookups',0) for w in report['worker_records']),
                    history_evictions=sum((w['storage'] or {}).get('evictions',0) for w in report['worker_records']))
                assert value['client_outside_server_request_ms']>=0 and value['server_outside_worker_interval_ms']>=0
            else:value['preparation_sum_ms']=report['preparation_ns']/1e6
            observed.append(value)
        assert len(observed)==20
        medians={}
        for mode in ['baseline','duplicate','session-fresh','candidate']:
            selected=[r for r in observed if r['mode']==mode];assert len(selected)==5
            fields=set(selected[0])-{'index','state','mode'}
            medians[mode]={key:statistics.median(r[key] for r in selected) for key in sorted(fields)}
        for p in [Path(__file__),ROOT/'benchmarks/experiments/cross-program-template-screen/accounting.py',Path(focus.__file__),
                ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=0,original_project_guest_commands=0,
            read_only_closed_evidence=True,performance_measurement=False))
        write(raw/'records.json',[]);write(raw/'rows.json',observed)
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=0,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),outputs={str((raw/'rows.json').relative_to(ROOT)):sha(raw/'rows.json')},
            rows=20,medians_ms=medians,original_project_guest_commands=0,performance_measurement=False,
            scope='Derived intervals from a closed end-to-end primary. Worker/compile duration sums can overlap; not CPU or independent runs. Baseline report interval includes catalog checks; session interval starts after decode/validation/report reservation. Outside-worker interval combines pre-worker input work and post-worker report serialization/write/flush.'))
        print(json.dumps(medians,indent=2),flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
