"""Qualify the new map reader before using any candidate native map."""
import os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='branch-budget-native-observer-01'

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        paths=[*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__),
            ROOT/'benchmarks/experiments/scratch-memory-values/native_observation.py',
            ROOT/'benchmarks/experiments/scratch-memory-values/test_native_observation.py']
        paths += [ROOT/'scripts'/n for n in ['compare_saved_runtime.py','workflow_io.py','supervise_experiment.py']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=1,
            expected_tests=9,original_project_guest_commands=0,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'};env['PYTHONDONTWRITEBYTECODE']='1'
        command=[sys.executable,'-B','-m','unittest','discover','-s',str(Path(__file__).parent),'-v']
        require_space(ROOT,8);started=time.time()
        child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label='observer'))
        for stream,value in [('stdout',out),('stderr',err)]:(raw/('observer.'+stream)).write_text(value)
        records=[dict(label='observer',command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-started,
            stdout_sha256=sha(raw/'observer.stdout'),stderr_sha256=sha(raw/'observer.stderr'))]
        write(raw/'records.json',records);assert child.returncode==0,(out+err)[-6000:]
        assert 'Ran 9 tests in ' in err and err.rstrip().endswith('OK')
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            commands=1,tests=9,inherited_controls=3,new_controls=6,original_project_guest_commands=0,
            performance_measurement=False,plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json')))
        print('Nine native map observer controls passed',flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
