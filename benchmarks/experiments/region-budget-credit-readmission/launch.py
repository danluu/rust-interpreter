"""Admit unchanged model only after the previous admission failure is closed."""
import fcntl
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import write_json as write, require_space
failed=ROOT/'results/region-budget-credit-01'
c=json.loads((failed/'closure.json').read_text())
assert c['status']=='closed' and c['admission_failure_only'] and c['controls']==c['cases']==0
for stem in ['summary','terminal']:
    assert sha(failed/(stem+'.json'))==c[stem+'_sha256']
assert sha(failed/'command.log')==c['log_sha256']
s=json.loads((failed/'summary.json').read_text())
for path,digest in s['source_bindings'].items(): assert sha(ROOT/path)==digest
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        print('DEFERRED: shared lock occupied; no new attempt started')
        raise SystemExit(0)
    require_space(ROOT,12)
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    run='region-budget-credit-02'
    raw=ROOT/'.work/region-budget-credit-readmission-02'
    raw.mkdir(exist_ok=False)
    write(raw/'admission.json',dict(previous_closure=str((failed/'closure.json').relative_to(ROOT)),
        previous_closure_sha256=sha(failed/'closure.json'),unchanged_model=s['source_bindings'],
        source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        next_run=run,lock_was_available=True,performance_measurement=False))
# The supervisor's controller independently acquires the lock with its normal
# 45-second admission. Release this readmission lock before starting that child.
subprocess.run([sys.executable,str(ROOT/'scripts/supervise_experiment.py'),'--run-id',run,'--',
    '/opt/homebrew/bin/python3',str(ROOT/'benchmarks/experiments/region-budget-credit/analyze.py'),
    '--run-id',run],cwd=ROOT,check=True)
