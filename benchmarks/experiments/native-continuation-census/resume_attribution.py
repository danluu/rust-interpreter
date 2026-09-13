"""Finish only the failed attribution publication; preserve both completed reconstructions."""
from pathlib import Path
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write


def main():
    old=ROOT/'.work/native-continuation-census-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        terminal_path=ROOT/'.work/experiments/native-continuation-census-01/status.json'
        terminal=json.loads(terminal_path.read_text())
        assert terminal['status']=='finished' and terminal['returncode']==1 and terminal['owner']==str(ROOT)
        prior=json.loads((old/'records.json').read_text())
        assert [(r['label'],r['returncode']) for r in prior]==[('block',0),('exhaustive',0),('attribute',1)]
        assert 'FileNotFoundError' in prior[-1]['stderr'] and '/results/native-continuation-census-01/.attribution.json-' in prior[-1]['stderr']
        frozen=json.loads((old/'plan.json').read_text())['frozen']
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        for label in ['block','exhaustive']:
            p=old/(label+'.json');r=json.loads(p.read_text())
            assert r['status']=='passed' and r['exact_baseline_reconstruction']
            assert r['guest_commands']==r['executable_code_publications']==0
            frozen[str(p.relative_to(ROOT))]=sha(p)
        for p in [old/'records.json',old/'plan.json',terminal_path,Path(__file__)]:frozen[str(p.relative_to(ROOT))]=sha(p)
        work=ROOT/'.work/native-continuation-attribution-02';work.mkdir(exist_ok=False)
        output=ROOT/'results/native-continuation-census-01';output.mkdir(exist_ok=True)
        assert not (output/'attribution.json').exists() and not (output/'summary.json').exists()
        command=[sys.executable,str(Path(__file__).with_name('attribute.py')),'--run-id','native-continuation-census-01']
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,command=command,
            reason='Create missing result directory, then retry failed attribution only',
            retained_reconstructions=2,repeated_reconstruction_commands=0,guest_commands=0))
        child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work/'active.json',receipt=dict(label='attribute'))
        write(work/'records.json',[dict(command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err)])
        assert child.returncode==0,(out+err)[-3500:]
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=json.loads((output/'attribution.json').read_text());assert result['status']=='passed'
        assert all(sha(ROOT/p)==h for p,h in result['evidence'].items())
        write(output/'summary.json',dict(status='passed',raw=str(old.relative_to(ROOT)),
            plan_sha256=sha(old/'plan.json'),records_sha256=sha(old/'records.json'),
            attribution_sha256=sha(output/'attribution.json'),attribution_raw=str(work.relative_to(ROOT)),
            attribution_plan_sha256=sha(work/'plan.json'),attribution_records_sha256=sha(work/'records.json'),
            retained_reconstruction_commands=2,new_reconstruction_commands=0,failed_attribution_attempts=1,
            successful_attribution_commands=1,guest_commands=0,performance_measurement=False))
        print(out,end='');print('Completed attribution; both prior reconstructions retained',flush=True)


if __name__=='__main__':main()
