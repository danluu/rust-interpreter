"""Qualify the independent trace reconstruction before replaying real suites."""
import json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='template-miss-parser-model-01'
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        paths=[p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [Path(focus.__file__),ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=1,
            original_project_guest_commands=0,performance_measurement=False))
        write(raw/'records.json',[])
        command=[sys.executable,'-B','-m','unittest','-v','test_model']
        start=time.time();child,out,err=capture(command,cwd=Path(__file__).parent,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=raw/'active.json',receipt=dict(label='model'))
        for stream,value in [('stdout',out),('stderr',err)]:(raw/('model.'+stream)).write_text(value)
        write(raw/'records.json',[dict(label='model',command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
            stdout_sha256=sha(raw/'model.stdout'),stderr_sha256=sha(raw/'model.stderr'))])
        assert child.returncode==0 and 'Ran 7 tests' in err and err.strip().endswith('OK'),(out+err)[-6000:]
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        dest=ROOT/'results'/RUN;dest.mkdir(exist_ok=False)
        write(dest/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=1,tests=7,
            original_project_guest_commands=0,performance_measurement=False))
if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
