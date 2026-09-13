"""Check the bounded continuation and unchanged full protocol without guests."""
import argparse
import json
import os
from pathlib import Path
import sys
from prefix import ROOT,FULL,HARNESS,protocol
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert args.run_id==HARNESS
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        old_path=ROOT/'results/guarded-local-facts-full-protocol-01/summary.json'
        old=json.loads(old_path.read_text());assert old['status']=='passed' and old['tests']==21
        old_inputs=ROOT/old['raw']/'inputs.json';assert sha(old_inputs)==old['inputs_sha256']
        protocol.verify_manifest(json.loads(old_inputs.read_text()))
        directory=Path(__file__).parent
        paths=[p for d in [directory,FULL] for p in d.iterdir() if p.suffix in ['.py','.md']]
        paths+=list((ROOT/'scripts').glob('*.py'))+[old_path,old_inputs]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False);write(work/'inputs.json',frozen)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(FULL))
        child,out,err=capture([sys.executable,'-m','unittest','test_full','test_large',
            'test_full_controller','test_prerequisites','test_prefix','-v'],cwd=directory,env=env,
            receipt_path=work/'active.json',receipt=dict(stage='continuation protocol controls'))
        (work/'stdout').write_text(out);(work/'stderr').write_text(err)
        assert child.returncode==0 and 'Ran 27 tests' in err and err.rstrip().endswith('OK'),err
        protocol.verify_manifest(frozen)
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',tests=27,guest_commands=0,commands=1,
            raw=str(work.relative_to(ROOT)),inputs_sha256=sha(work/'inputs.json'),performance_measurement=False))
        print('PASS:27 full and continuation controls',flush=True)

if __name__=='__main__':main()
