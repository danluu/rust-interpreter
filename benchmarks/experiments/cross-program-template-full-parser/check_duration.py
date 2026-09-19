"""Qualify complete session CPU accounting before any primary measurements."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='cross-program-template-parser-full-protocol-02'

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        paths=[p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [ROOT/'benchmarks/experiments/cross-program-template-screen/session_owner.py']
        paths += [Path(focus.__file__),ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=1,
            original_project_guest_commands=0,performance_measurement=False))
        write(raw/'records.json',[]);command=[sys.executable,'-B','-m','unittest','discover','-s',str(Path(__file__).parent),'-p','test_accounting.py','-v']
        start=time.time();child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=raw/'active.json',receipt=dict(label='accounting'))
        for stream,value in [('stdout',out),('stderr',err)]:(raw/('accounting.'+stream)).write_text(value)
        records=[dict(label='accounting',command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
            stdout_sha256=sha(raw/'accounting.stdout'),stderr_sha256=sha(raw/'accounting.stderr'))];write(raw/'records.json',records)
        assert child.returncode==0 and 'Ran 8 tests in ' in err and '\nOK\n' in err,(out+err)[-4096:]
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=1,tests=8,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),original_project_guest_commands=0,performance_measurement=False))

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()
