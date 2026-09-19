"""Audit actual ordered per-worker test intervals in a closed edited-source primary."""
import json,math,statistics,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='session-worker-tail-census-01'
PRIMARY='cross-program-template-parser-screen-incremental-05'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12);frozen={}
        def bind(p,h=None):
            actual=sha(p)
            if h is not None:assert actual==h,p
            frozen[str(p.relative_to(ROOT))]=actual
            return read(p) if p.suffix=='.json' else actual
        prior=ROOT/'results'/PRIMARY;c=bind(prior/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified']
        s=bind(prior/'summary.json',c['summary_sha256']);t=bind(prior/'terminal.json',c['terminal_sha256'])
        assert s['status']=='passed' and s['commands']==40 and s['source_restored']
        assert s['measurement']['verdict']=='failed' and not s['measurement']['gate_passed']
        assert t['status']=='finished' and t['returncode']==0 and t['owner']==str(ROOT)
        evidence=bind(ROOT/c['evidence'],c['evidence_sha256'])
        old=ROOT/s['raw'];records=bind(old/'records.json',s['records_sha256']);observations=[]
        for row in records:
            if row['state']<=0 or row['mode'] not in ['candidate','session-fresh']:continue
            p=old/f"{row['index']}-suite.json";report=bind(p,evidence[str(p.relative_to(ROOT))])
            assert report['selected']==report['completed']==report['passed']==114 and report['failed']==0
            assert report['poisoned'] is False and report['workers']==2
            workers=report['worker_records'];assert len(workers)==2 and {w['worker'] for w in workers}=={0,1}
            complete=[];groups=[]
            for w in workers:
                assert w['status']=='completed' and w['poisoned'] is False
                assert type(w['preparation_ns']) is int and w['preparation_ns']>=0
                tests=w['tests'];elapsed=0;group=[]
                for ordinal,test in enumerate(tests):
                    assert type(test['index']) is int and 0<=test['index']<114
                    assert test['status']=='passed' and test['name']==report['tests'][test['index']]['name']
                    seconds=test['seconds'];assert type(seconds) in [int,float] and math.isfinite(seconds) and seconds>=0
                    group.append(dict(worker=w['worker'],index=test['index'],name=test['name'],ordinal=ordinal,
                        tests_on_worker=len(tests),milliseconds=seconds*1000,prior_tests_ms=elapsed*1000))
                    elapsed+=seconds;complete.append(test['index'])
                assert elapsed+w['preparation_ns']/1e9<=report['seconds_before_report_write']+1e-6
                groups.append(dict(worker=w['worker'],tests=len(tests),test_sum_ms=elapsed*1000,
                    preparation_ms=w['preparation_ns']/1e6,ordered_tests=group))
            assert sorted(complete)==list(range(114))
            heaviest=max((test for group in groups for test in group['ordered_tests']),key=lambda test:test['milliseconds'])
            same=next(group for group in groups if group['worker']==heaviest['worker'])
            peer=next(group for group in groups if group['worker']!=heaviest['worker'])
            observations.append(dict(mode=row['mode'],state=row['state'],index=row['index'],
                worker_interval_ms=report['seconds_before_report_write']*1000,
                heaviest=heaviest,heaviest_is_last=heaviest['ordinal']==heaviest['tests_on_worker']-1,
                prior_tests_ms=heaviest['prior_tests_ms'],heaviest_ms=heaviest['milliseconds'],
                worker_test_sum_ms=same['test_sum_ms'],peer_test_sum_ms=peer['test_sum_ms'],groups=groups))
        assert len(observations)==10
        modes={}
        for mode in ['session-fresh','candidate']:
            selected=[o for o in observations if o['mode']==mode];assert len(selected)==5
            modes[mode]=dict(reports=5,heaviest_last=sum(o['heaviest_is_last'] for o in selected),
                heaviest_names=sorted({o['heaviest']['name'] for o in selected}),
                medians_ms={field:statistics.median(o[field] for o in selected) for field in
                    ['worker_interval_ms','prior_tests_ms','heaviest_ms','worker_test_sum_ms','peer_test_sum_ms']},
                prior_test_range_ms=[min(o['prior_tests_ms'] for o in selected),max(o['prior_tests_ms'] for o in selected)])
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__),
                ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=0,
            original_project_guest_commands=0,read_only_closed_evidence=True,performance_measurement=False))
        write(raw/'records.json',[]);write(raw/'observations.json',observations)
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=0,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),reports=10,test_intervals=1140,modes=modes,
            outputs={str((raw/'observations.json').relative_to(ROOT)):sha(raw/'observations.json')},
            original_project_guest_commands=0,performance_measurement=False,default_runtime_adoption=False,
            scope='Actual ordered elapsed test intervals, not an ideal scheduling prediction. Cache warmth, compilation, contention and test durations can change with scheduling. Prior intervals exclude worker setup and loop/report overhead. No test is renamed, skipped or changed.'))
        print(json.dumps(modes,indent=2),flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
