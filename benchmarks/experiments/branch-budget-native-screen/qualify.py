"""Qualify primary accounting/commands/controller before any acceptance timing."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
from benchmark import validate_protocol
from admission import load
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='branch-budget-native-screen-protocol-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        paths=list(Path(__file__).parent.glob('*.py'))+list(Path(__file__).parent.glob('*.md'))+[Path(focus.__file__)]
        paths += list((ROOT/'scripts').glob('*.py'))
        paths += [ROOT/'benchmarks/experiments/runtime-composition-screen/screen.py']
        builds,proofs=load('token');paths+=proofs
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=3,
            original_project_guest_commands=0,performance_measurement=False))
        records=[]
        for label,count in [('accounting',7),('commands',5),('controller',5)]:
            require_space(ROOT,8)
            command=[sys.executable,'-B','-m','unittest','discover','-s',str(Path(__file__).parent),'-p','test_'+label+'.py','-v']
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
                receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))));write(raw/'records.json',records)
            assert child.returncode==0 and f'Ran {count} tests in ' in err and '\nOK\n' in err,(out+err)[-5000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,count,'passed',flush=True)
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        summary=dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),tests=17,test_counts=dict(accounting=7,commands=5,controller=5),tool_key=builds['candidate']['tool_key'],
            commands=3,reused_commands=0,original_project_guest_commands=0,performance_measurement=False,default_runtime_adoption=False)
        assert validate_protocol(summary,builds['candidate']);write(out/'summary.json',summary)
if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()
