"""Normally wait the exact ten pure observer regression tests; no compiler work."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
D=ROOT/'experiments/host-wrapper-rbc-driver-03'
OUT=ROOT/'.work/host-wrapper-rbc-observer-tests-execution-01'
MANIFEST='036fc48c643acbaf8dc3ff460e72935b4453d564c7ce755fe42f9c407ac52956'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ref(path):return dict(path=str(path),sha256=sha(path))
def require(ok,message):
    if not ok:raise RuntimeError(message)
def write(value):
    (OUT/'record.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

require(Path.cwd()==R and sys.dont_write_bytecode and not sys.flags.optimize,'fixed R cwd/Python -B')
require(sha(D/'test-sources.json')==MANIFEST,'reviewed test manifest changed')
manifest=json.loads((D/'test-sources.json').read_bytes())
require(len(manifest['tests'])==10 and set(manifest['files'])=={str(D/n) for n in ('support.py','test_footprint.py')},'exact ten-test source scope')
for p,row in manifest['files'].items():require(sha(p)==row['sha256'],'test source changed: '+p)
require(not os.path.lexists(OUT),'fresh test execution directory required')
OUT.mkdir();(OUT/'tmp').mkdir()
env=dict(PATH='/opt/homebrew/bin:/usr/bin:/bin',LANG='C',LC_ALL='C',TZ='UTC',
         PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(OUT/'tmp'))
command=['/opt/homebrew/bin/python3','-B',str(D/'test_footprint.py'),'-v']
record=dict(status='starting',parent_pid=os.getpid(),parent_parent_pid=os.getppid(),
    command=command,cwd=str(R),environment=env,started_at=time.time(),source=ref(__file__),
    test_manifest=ref(D/'test-sources.json'),sources=manifest['files'],expected_tests=manifest['tests'],
    normal_wait_completed=False,child_may_be_live=False,signals=0,retries=0,benchmark=False)
write(record)
with (OUT/'stdout').open('xb') as stdout,(OUT/'stderr').open('xb') as stderr:
    child=subprocess.Popen(command,cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
    try:
        record.update(status='running',pid=child.pid,child_started_at=time.time(),child_may_be_live=True);write(record)
    finally:
        code=child.wait()
record.update(status='closed',returncode=code,normal_wait_completed=True,child_may_be_live=False,
    child_finished_at=time.time(),stdout=ref(OUT/'stdout'),stderr=ref(OUT/'stderr'))
write(record)
try:
    raw=(OUT/'stderr').read_text()
    observed=re.findall(r'^(test_[a-z0-9_]+) \([^\n]+\) \.\.\. ok$',raw,re.M)
    require(code==0 and observed==manifest['tests'] and re.search(r'\nRan 10 tests in [0-9.]+s\n\nOK\n\Z',raw),
            'complete ten-test no-skip/no-failure result required')
    require(not list((OUT/'tmp').iterdir()),'pure-test owned temporary directories were not removed')
    for p,row in manifest['files'].items():require(sha(p)==row['sha256'],'source changed during tests: '+p)
    require(sha(D/'test-sources.json')==MANIFEST,'manifest changed during tests')
    record.update(status='passed',tests_run=10,test_names=observed,inputs_unchanged=True)
except BaseException as error:
    record.update(status='failed',error=str(error));raise
finally:
    record.update(finished_at=time.time());write(record)
print(json.dumps(ref(OUT/'record.json'),sort_keys=True))
