"""Qualify combined native ownership and launcher forwarding without guest timing."""
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='scalar-indirect-observation-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        build_path=ROOT/'results/scalar-indirect-build-01/summary.json';build=read(build_path)
        closure_path=build_path.with_name('closure.json');closed=read(closure_path)
        assert build['status']=='passed' and closed['status']=='closed' and closed['all_hashes_verified']
        assert sha(build_path)==closed['summary_sha256']
        build_plan=ROOT/build['source_manifest'];assert sha(build_plan)==build['source_manifest_sha256']
        paths=[build_path,closure_path,build_plan,ROOT/'tests/test_isolated_launcher.py']
        assert sha(paths[-1])==read(build_plan)['frozen']['tests/test_isolated_launcher.py']
        paths += list(Path(__file__).parent.glob('*.py'))+list(Path(__file__).parent.glob('*.md'))
        paths += list((ROOT/'scripts').glob('*.py'))
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),frozen=frozen,
            expected_commands=2,guest_commands=0,performance_measurement=False))
        records=[]
        for label,cwd,mod,count in [('observation',Path(__file__).parent,'test_native_observation',5),('launcher',ROOT/'tests','test_isolated_launcher',9)]:
            require_space(ROOT,8)
            command=[sys.executable,'-m','unittest',mod,'-v']
            child,out,err=capture(command,cwd=cwd,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
                receipt_path=work/'active.json',receipt=dict(label=label))
            for stream,payload in [('stdout',out),('stderr',err)]: (work/(label+'.'+stream)).write_text(payload)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records)
            assert child.returncode==0 and f'Ran {count} tests' in err and err.rstrip().endswith('OK'),err
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,count,'passed',flush=True)
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=2,tests=dict(observation=5,launcher=9),
            raw=str(work.relative_to(ROOT)),source_revision=read(work/'plan.json')['source_revision'],
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),guest_commands=0,performance_measurement=False))
if __name__=='__main__':main()
