"""Exact pure development suite; reject workload and unrelated workspace access."""
import os
import hashlib
import json
from importlib.util import cache_from_source
from pathlib import Path
import signal
import sys
import unittest
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE=ROOT/'experiments/runtime-installation-after-preflight05-02'
ALLOWED={str(SOURCE/name) for name in ['entry.py','controller.py','audit_owner.py','routes.json','test_installation.py']}
ALLOWED.update([str(ROOT/'experiments/runtime04-environment-adapter-01/environment.py'),str(ROOT/'experiments/runtime-preflight-retry-05/routes.json'),str(Path(__file__).resolve())])
CACHE_ALIASES={cache_from_source(path) for path in ALLOWED if path.endswith('.py')}
# Authenticate every allowed project source against the parent observation before imports.
observed=json.loads(Path(__file__).with_name('source-before.json').read_bytes())
for name in ALLOWED:
 data=Path(name).read_bytes()
 assert hashlib.sha256(data).hexdigest()==observed[name]['sha256']
 assert {key:getattr(Path(name).stat(),'st_'+key) for key in observed[name]['identity']}==observed[name]['identity']

assert all(not os.path.lexists(path) for path in CACHE_ALIASES), 'cached target bytecode is not admitted'
def audit(event,args):
    if event.startswith(('subprocess.','os.exec','os.posix_spawn','socket.')) or event in ('os.system','os.kill','os.killpg'):
        raise RuntimeError('pure development controls refuse process/network/signal calls')
    if event=='open':
        name,mode,flags=args
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            raise RuntimeError('pure development fixtures cannot write files')
        if isinstance(name,(str,bytes)):
            path=str(Path(os.fsdecode(name)).absolute())
            if path in CACHE_ALIASES:
                if os.path.lexists(path):raise RuntimeError('cached target bytecode appeared')
                return  # Only an absent interpreter cache lookup; normal source read follows.
            if path.startswith('/Users/danluu/dev/') and path not in ALLOWED:
                raise RuntimeError('unrelated workspace or provider read refused: '+path)
sys.addaudithook(audit)
signal.alarm(120)
sys.path.insert(0,str(SOURCE))
suite=unittest.defaultTestLoader.loadTestsFromName('test_installation')
assert suite.countTestCases()==25
result=unittest.TextTestRunner(verbosity=2).run(suite)
signal.alarm(0)
raise SystemExit(0 if result.wasSuccessful() and result.testsRun==25 and not result.skipped else 1)
