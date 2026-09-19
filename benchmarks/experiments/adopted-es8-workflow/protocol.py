import os
import sys
from common import ROOT,HERE,PROTOCOL,inputs,revision,focus,read,sha,write,capture,acquire_lock,require_space


def main():
    frozen,original,owner=inputs();source=revision()
    raw=ROOT/'.work'/PROTOCOL;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
    write(raw/'plan.json',dict(owner=str(ROOT),source_revision=source,frozen=frozen,
        controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=1,
        original_project_guest_commands=0,performance_measurement=False))
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        command=[sys.executable,'-B','-m','unittest','discover','-s',str(HERE),'-p','test_model.py','-v']
        child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=raw/'active.json',receipt=dict(label='protocol'))
        for stream,value in [('stdout',out),('stderr',err)]:(raw/('protocol.'+stream)).write_text(value)
        write(raw/'records.json',[dict(label='protocol',command=command,pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/'protocol.stdout'),stderr_sha256=sha(raw/'protocol.stderr'))])
        assert child.returncode==0 and 'Ran 6 tests' in err and err.rstrip().endswith('OK'),err
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        output=ROOT/'results'/PROTOCOL;output.mkdir(exist_ok=False)
        write(output/'summary.json',dict(status='passed',source_revision=source,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=1,controls=6,
            original_project_guest_commands=0,performance_measurement=False))


if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=PROTOCOL;focus.close()
    else:assert len(sys.argv)==1;main()
