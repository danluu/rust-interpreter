"""Check scheduling against independent previous-report priorities; describe worker tails."""
import json,math,statistics,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='session-duration-order-evidence-01'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12);frozen={}
        def bind(p,h=None):
            actual=sha(p)
            if h is not None:assert actual==h,p
            frozen[str(p.relative_to(ROOT))]=actual
            return read(p) if p.suffix=='.json' else actual
        def closed(name):
            folder=ROOT/'results'/name;c=bind(folder/'closure.json')
            assert c['status']=='closed' and c['all_hashes_verified']
            s=bind(folder/'summary.json',c['summary_sha256']);t=bind(folder/'terminal.json',c['terminal_sha256'])
            assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0 and t['owner']==str(ROOT)
            return s
        replay=closed('session-duration-order-parser-client-01')
        assert replay['test_invocations']==1824 and replay['verified_cache_hits']>0 and replay['duration_order'] is True
        observations=[];conformity=[];cases=[0,-1,1,2,3,4,5,0]
        for variant,run in [('parent','parameterized-literals-phases-parser-01'),('duration','session-duration-order-phases-parser-01')]:
            s=closed(run);assert s['test_invocations']==1824 and s['parameterized_literals'] is True
            if variant=='duration':assert s['duration_order'] is True and s['shared_literal_keys'] is False
            old=ROOT/s['raw'];outputs=s['outputs']
            for mode in ['fresh','cached']:
                previous={}
                for ordinal,state in enumerate(cases):
                    p=old/mode/(str(ordinal)+'.report.json');report=bind(p,outputs[str(p.relative_to(ROOT))])
                    assert report['selected']==report['completed']==114 and report['workers']==2 and report['poisoned'] is False
                    tests=report['tests'];assert [t['index'] for t in tests]==list(range(114))
                    assert len({t['name'] for t in tests})==114
                    order=sorted(range(114),key=lambda i:(-previous.get(tests[i]['name'],0),i))
                    ranks={index:rank for rank,index in enumerate(order)}
                    workers=report['worker_records'];assert len(workers)==2 and {w['worker'] for w in workers}=={0,1}
                    complete=[];groups=[];current={}
                    for w in workers:
                        assert w['status']=='completed' and w['poisoned'] is False
                        assert type(w['preparation_ns']) is int and w['preparation_ns']>=0
                        elapsed=0;group=[];worker_ranks=[]
                        for offset,test in enumerate(w['tests']):
                            index=test['index'];assert type(index) is int and 0<=index<114
                            assert test['name']==tests[index]['name'] and test['status']==tests[index]['status']
                            assert test['status'] in ['passed','failed']
                            seconds=test['seconds'];assert type(seconds) in [int,float] and math.isfinite(seconds) and seconds>=0
                            nanos=seconds*1e9;assert math.isfinite(nanos) and nanos<2**64
                            current[test['name']]=int(nanos);worker_ranks.append(ranks[index])
                            group.append(dict(worker=w['worker'],index=index,name=test['name'],ordinal=offset,
                                tests_on_worker=len(w['tests']),milliseconds=seconds*1000,prior_tests_ms=elapsed*1000))
                            elapsed+=seconds;complete.append(index)
                        if variant=='duration':assert worker_ranks==sorted(set(worker_ranks)),(mode,ordinal,w['worker'],worker_ranks)
                        assert elapsed+w['preparation_ns']/1e9<=report['seconds_before_report_write']+1e-6
                        groups.append(dict(worker=w['worker'],tests=len(group),test_sum_ms=elapsed*1000,
                            preparation_ms=w['preparation_ns']/1e6,priority_ranks=worker_ranks,ordered_tests=group))
                    assert sorted(complete)==list(range(114)) and len(current)==114
                    if variant=='duration':
                        conformity.append(dict(mode=mode,ordinal=ordinal,state=state,request_id=report['request_id'],
                            prior_duration_entries=len(previous),expected_order=order,worker_priority_ranks=[g['priority_ranks'] for g in groups]))
                    previous=current
                    if state<=0:continue
                    assert report['passed']==114 and report['failed']==0
                    heaviest=max((test for group in groups for test in group['ordered_tests']),key=lambda test:test['milliseconds'])
                    same=next(g for g in groups if g['worker']==heaviest['worker']);peer=next(g for g in groups if g['worker']!=heaviest['worker'])
                    observations.append(dict(variant=variant,mode=mode,state=state,ordinal=ordinal,
                        worker_interval_ms=report['seconds_before_report_write']*1000,heaviest=heaviest,
                        heaviest_is_first=heaviest['ordinal']==0,heaviest_is_last=heaviest['ordinal']==heaviest['tests_on_worker']-1,
                        prior_tests_ms=heaviest['prior_tests_ms'],heaviest_ms=heaviest['milliseconds'],
                        worker_test_sum_ms=same['test_sum_ms'],peer_test_sum_ms=peer['test_sum_ms'],groups=groups))
        assert len(observations)==20 and len(conformity)==16
        comparisons={}
        for variant in ['parent','duration']:
            comparisons[variant]={}
            for mode in ['fresh','cached']:
                selected=[o for o in observations if o['variant']==variant and o['mode']==mode];assert len(selected)==5
                comparisons[variant][mode]=dict(reports=5,heaviest_first=sum(o['heaviest_is_first'] for o in selected),
                    heaviest_last=sum(o['heaviest_is_last'] for o in selected),
                    heaviest_names=sorted({o['heaviest']['name'] for o in selected}),
                    medians_ms={field:statistics.median(o[field] for o in selected) for field in
                        ['worker_interval_ms','prior_tests_ms','heaviest_ms','worker_test_sum_ms','peer_test_sum_ms']})
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__),
                ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=0,
            original_project_guest_commands=0,read_only_closed_evidence=True,performance_measurement=False))
        write(raw/'records.json',[]);write(raw/'observations.json',observations);write(raw/'conformity.json',conformity)
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=0,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),valid_reports=20,test_intervals=2280,
            priority_conformity_reports=16,priority_conformity_invocations=1824,comparisons=comparisons,
            outputs={str((raw/name).relative_to(ROOT)):sha(raw/name) for name in ['observations.json','conformity.json']},
            original_project_guest_commands=0,performance_measurement=False,default_runtime_adoption=False,
            scope='Independent priority reconstruction and actual ordered elapsed test intervals from separate instrumented runs. No end-to-end speedup or ideal scheduling prediction.'))
        print(json.dumps(comparisons,indent=2),flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
