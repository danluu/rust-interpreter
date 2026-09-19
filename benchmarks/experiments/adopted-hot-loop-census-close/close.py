"""Close already completed census after resolving the Python executable alias."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent/'adopted-hot-loop-census-v2'))
from run import *
def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        out=ROOT/'results'/RUN;s=read(out/'summary.json');raw=ROOT/s['raw']
        assert s['status']=='passed' and s['controls']==CONTROLS
        for key in ['plan','records']:assert sha(raw/(key+'.json'))==s[key+'_sha256']
        plan=read(raw/'plan.json');assert plan['frozen']==inputs()
        assert plan['source_revision']==s['source_revision']
        bindings={}
        for p,h in plan['frozen'].items():
            if p.startswith(('.work/','results/')):bindings[p]=dict(kind='retained',sha256=h)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h
                bindings[p]=dict(kind='git',revision=plan['source_revision'],sha256=h)
        records=read(raw/'records.json');assert len(records)==1
        record=records[0];assert record['returncode']==0
        for stream in ['stdout','stderr']:assert sha(raw/('controls.'+stream))==record[stream+'_sha256']
        stderr=(raw/'controls.stderr').read_text()
        assert f'Ran {CONTROLS} tests' in stderr and stderr.rstrip().endswith('OK')
        for index,label in enumerate(['block','exhaustive']):
            assert sha(raw/(label+'-details.json'))==s['details_sha256'][label]
            summary,details=case(index,label)
            assert summary==s['cases'][index] and details==read(raw/(label+'-details.json'))
            del details;gc.collect()
        outer=ROOT/'.work/experiments'/RUN;t=read(outer/'status.json')
        assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
        assert Path(t['command'][0]).resolve()==Path(sys.executable).resolve()
        assert t['command'][1:]==[str(HERE/'run.py')]
        assert sha(outer/'command.log')==t['log_sha256'] and sha(outer/'plan.json')==t['plan_sha256']
        failed_outer=ROOT/'.work/experiments/adopted-hot-loop-census-02-closure'
        failed=read(failed_outer/'status.json')
        assert failed['status']=='finished' and failed['returncode']==1
        assert failed['owner']==failed['cwd']==str(ROOT)
        assert failed['command']==t['command']+['--close']
        assert sha(failed_outer/'plan.json')==failed['plan_sha256']
        assert sha(failed_outer/'command.log')==failed['log_sha256']
        assert "assert t['command']==[str(Path(sys.executable)),str(HERE/'run.py')]" in (failed_outer/'command.log').read_text()
        assert (failed_outer/'command.log').read_text().rstrip().endswith('AssertionError')
        closure_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        closure_sources={}
        for source in Path(__file__).parent.iterdir():
            if source.suffix not in ['.py','.md']:continue
            p=relative(source);h=sha(source)
            assert hashlib.sha256(subprocess.check_output(['git','show',closure_revision+':'+p],cwd=ROOT)).hexdigest()==h
            closure_sources[p]=dict(kind='git',revision=closure_revision,sha256=h)
        assert not (out/'closure.json').exists()
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(raw/'bindings.json',bindings)
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,all_derivations_recomputed=True,
            frozen_inputs=len(bindings),source_revision=plan['source_revision'],bindings=relative(raw/'bindings.json'),
            closure_sources=closure_sources, prior_failed_closure=str(failed_outer.relative_to(ROOT)),
            prior_failed_closure_status_sha256=sha(failed_outer/'status.json'),
            prior_failed_closure_log_sha256=sha(failed_outer/'command.log'),
            bindings_sha256=sha(raw/'bindings.json'),summary_sha256=sha(out/'summary.json'),
            terminal_sha256=sha(out/'terminal.json'),guest_commands=0,performance_measurement=False))
        print('CLOSED',len(bindings),'bindings; both full derivations recomputed',flush=True)

if __name__=="__main__":close()
