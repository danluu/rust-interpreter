"""Source-bound accounting from 80 already completed edited commands."""
import hashlib,json,os,statistics,subprocess,sys
from pathlib import Path
from accounting import analyze
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from suite_reports import validate_report
RUN='jit-preparation-census-01'
ADOPTED='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        frozen={}
        def bind(p,expected=None):
            p=Path(p);h=sha(p)
            if expected is not None:assert h==expected,p
            frozen[str(p.relative_to(ROOT))]=h
            return read(p) if p.suffix=='.json' else h
        closure=bind(ROOT/'results/scratch-memory-values-full-01/closure.json')
        assert closure['status']=='closed' and closure['full_campaign_complete'] and closure['commands']==726
        bind(ROOT/'results/scratch-memory-values-full-01/summary.json',closure['summary_sha256'])
        evidence=bind(ROOT/closure['snapshot']/'evidence.json',closure['evidence_sha256'])
        screen_closure=bind(ROOT/'results/retained-region-values-screen-token-01/closure.json')
        assert screen_closure['status']=='passed' and screen_closure['parked']
        screen_evidence=bind(ROOT/screen_closure['evidence_path'],screen_closure['evidence_sha256'])
        build=bind(ROOT/'results/scratch-memory-values-build-02/summary.json');assert build['tool_key']==ADOPTED
        build_plan=bind(ROOT/build['raw']/'plan.json',build['plan_sha256'])
        for name in ['prepared.rs','suite.rs','jit.rs']:
            path=ROOT/'crates/bytecode/src'/name;relative=str(path.relative_to(ROOT))
            bind(path,build_plan['frozen'][relative])
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md']:bind(p)
        for name in ['workflow_io.py','compare_saved_runtime.py','suite_reports.py']:bind(ROOT/'scripts'/name)
        inputs=[]
        cases=[(name,'scratch-memory-values-edit-'+name+'-01','candidate',15,evidence)
            for name in ['token','folded','pgrust','rg-aot','nushell']]
        cases.append(('token-current','retained-region-values-screen-token-01','baseline',5,screen_evidence))
        for case,run,mode,count,index in cases:
            path=ROOT/'results'/run/'summary.json';s=bind(path,index[str(path.relative_to(ROOT))])
            assert s['status']=='passed' and s['source_restored'] and s['tool_keys'][mode]==ADOPTED
            raw=ROOT/s['raw'];digest=s.get('records_sha256') or s['evidence']['records']
            records=bind(raw/'records.json',digest)
            selected=[r for r in records if r['mode']==mode and r['state'] in range(1,6)]
            assert len(selected)==count and len({(r['cycle'],r['state']) for r in selected})==count
            for r in selected:
                assert r['returncode']==0 and r['launch']['tool_key']==ADOPTED
                assert r['source_sha256']!=r['previous_source_sha256']
                command=r['command'];suite_path=Path(command[command.index('--suite-report')+1])
                suite=bind(suite_path,r['suite_sha256'])
                assert len(suite['tests'])==s['test_count']
                names=[t['name'] for t in suite['tests']]
                assert r['outcomes']==[list(x) for x in sorted(validate_report(suite,names,'prepared',True))]
                inputs.append((case,r,suite))
        assert len(inputs)==80
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        work=ROOT/'.work'/RUN;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,expected_observations=80,
            guest_commands=0,compiler_commands=0,executable_code_publications=0,performance_measurement=False))
        child,out,err=capture([sys.executable,'-m','unittest','test_accounting','-v'],cwd=Path(__file__).parent,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage='accounting controls'))
        (work/'stdout').write_text(out);(work/'stderr').write_text(err)
        write(work/'record.json',dict(pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr')))
        assert child.returncode==0 and 'Ran 3 tests' in err and err.rstrip().endswith('OK'),err
        observations=[]
        for case,r,suite in inputs:
            observations.append(dict(case=case,cycle=r['cycle'],state=r['state'],
                **analyze(suite,r['seconds'],r['launch']['execution_seconds'])))
        groups={}
        for case,*_ in cases:
            rows=[r for r in observations if r['case']==case]
            keys=['command_seconds','execution_seconds','constructor_sum_seconds','compile_sum_seconds',
                'largest_worker_compile_seconds','compile_sum_to_command','largest_worker_compile_to_command',
                'constructor_sum_to_command','constructor_plus_compile_interval_sum_to_command']
            groups[case]=dict(observations=len(rows),medians={k:statistics.median(r[k] for r in rows) for k in keys})
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'observations.json',observations)
        write(result/'summary.json',dict(status='passed',tool_key=ADOPTED,observations=80,controls=3,cases=groups,
            raw=str(work.relative_to(ROOT)),source_revision=revision,plan_sha256=sha(work/'plan.json'),
            record_sha256=sha(work/'record.json'),observations_sha256=sha(result/'observations.json'),
            guest_commands=0,compiler_commands=0,executable_code_publications=0,performance_measurement=False,
            scope='Recorded duration accounting only. Worker intervals overlap; constructor time is an aggregate. No predicted cache saving, causal attribution, or new adoption gate. Private names, paths and output stay in retained raw inputs.'))
        print(json.dumps(groups,indent=2))


def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        result=ROOT/'results'/RUN;summary=read(result/'summary.json');raw=ROOT/summary['raw']
        assert summary['status']=='passed' and summary['observations']==80
        assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'record.json')==summary['record_sha256']
        assert sha(result/'observations.json')==summary['observations_sha256']
        plan=read(raw/'plan.json');bindings={}
        for p,h in plan['frozen'].items():
            assert sha(ROOT/p)==h
            if p.startswith(('.work/','results/')):bindings[p]=dict(kind='retained',sha256=h)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h
                bindings[p]=dict(kind='git',revision=plan['source_revision'],sha256=h)
        record=read(raw/'record.json');assert record['returncode']==0
        for stream in ['stdout','stderr']:assert sha(raw/stream)==record[stream+'_sha256']
        outer=ROOT/'.work/experiments'/RUN;terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT)
        assert sha(outer/'command.log')==terminal['log_sha256']
        assert not (result/'closure.json').exists()
        (result/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(raw/'bindings.json',bindings)
        write(result/'closure.json',dict(status='closed',frozen_inputs=len(bindings),all_hashes_verified=True,
            bindings=str((raw/'bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'bindings.json'),
            summary_sha256=sha(result/'summary.json'),terminal_sha256=sha(result/'terminal.json')))
        print(len(bindings),'input bindings and all controls/observations verified')


if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()
