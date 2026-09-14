"""Freeze parser guard controls before running any changed-source command."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='scratch-memory-values-parser-edits-protocol-01'

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        directory=Path(__file__).parent;old=ROOT/'benchmarks/experiments/pgrust-parser-edits'
        paths=[p for p in directory.iterdir() if p.suffix in ['.py','.md']]
        paths += list((ROOT/'scripts').glob('*.py'))+[old/'states.py',old/'test_protocol.py']
        paths += [ROOT/'benchmarks/experiments/scratch-memory-values-full'/n for n in ['prerequisites.py']]
        paths += [ROOT/'benchmarks/experiments/scratch-memory-values/screen.py',ROOT/'benchmarks/experiments/pgrust-parser-probe/probe.py']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        raw=ROOT/'.work'/NAME;raw.mkdir(exist_ok=False);write(raw/'inputs.json',frozen)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(directory)+os.pathsep+str(old))
        child,out,err=capture([sys.executable,'-m','unittest','test_comparison','test_protocol','-v'],cwd=directory,env=env,receipt_path=raw/'active.json',receipt=dict(stage='parser protocol'))
        (raw/'stdout').write_text(out);(raw/'stderr').write_text(err)
        assert child.returncode==0 and 'Ran 16 tests' in err and err.rstrip().endswith('OK'),err
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        dest=ROOT/'results'/NAME;dest.mkdir(exist_ok=False)
        write(dest/'summary.json',dict(status='passed',tests=16,commands=1,guest_commands=0,raw=str(raw.relative_to(ROOT)),inputs_sha256=sha(raw/'inputs.json'),stdout_sha256=sha(raw/'stdout'),stderr_sha256=sha(raw/'stderr'),performance_measurement=False))
        print('PASS: 16 original parser and matched comparison protocol controls',flush=True)
if __name__=='__main__':main()
