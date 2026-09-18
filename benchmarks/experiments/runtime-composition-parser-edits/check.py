"""Freeze parser guard controls before running any changed-source command."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='runtime-composition-parser-edits-protocol-01'

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        directory=Path(__file__).parent;old=ROOT/'benchmarks/experiments/pgrust-parser-edits'
        paths=[p for p in directory.iterdir() if p.suffix in ['.py','.md']]
        paths += list((ROOT/'scripts').glob('*.py'))+[old/'states.py',old/'test_protocol.py']
        paths += [ROOT/'benchmarks/experiments/runtime-composition-full'/n for n in ['prerequisites.py']]
        paths += [ROOT/'benchmarks/experiments/runtime-composition-screen/screen.py',ROOT/'benchmarks/experiments/pgrust-parser-probe/probe.py']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        raw=ROOT/'.work'/NAME;raw.mkdir(exist_ok=False);write(raw/'inputs.json',frozen)
        records=[]
        for label,cwd,module,count in [('matched',directory,'test_comparison',6),('original',old,'test_protocol',10)]:
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(cwd))
            child,out,err=capture([sys.executable,'-m','unittest',module,'-v'],cwd=cwd,env=env,receipt_path=raw/'active.json',receipt=dict(stage=label+' parser protocol'))
            (raw/(label+'.stdout')).write_text(out);(raw/(label+'.stderr')).write_text(err)
            record=dict(label=label,returncode=child.returncode,pid=child.pid,tests=count,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')))
            records.append(record);write(raw/'records.json',records)
            assert child.returncode==0 and ('Ran '+str(count)+' tests') in err and err.rstrip().endswith('OK'),err
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        dest=ROOT/'results'/NAME;dest.mkdir(exist_ok=False)
        write(dest/'summary.json',dict(status='passed',tests=16,commands=2,guest_commands=0,raw=str(raw.relative_to(ROOT)),inputs_sha256=sha(raw/'inputs.json'),records_sha256=sha(raw/'records.json'),performance_measurement=False))
        print('PASS: 16 original parser and matched comparison protocol controls',flush=True)
if __name__=='__main__':main()
