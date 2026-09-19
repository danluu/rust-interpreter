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
SOURCE=ROOT/'experiments/runtime-native-loader-probes-01'
ALLOWED={'/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/test_native_loader.py', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/runtime_compiler.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/runtime-native-loader-development-01/child.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/runtime_compiler.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/producer_recipe.py', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/custom_compiler.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/installation-plan-01/specification.json', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/audit_recipe.py', '/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/hir-options-hash/runtime-installation-01/recipe.py'}
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
    if event in {'os.mkdir','os.remove','os.rename','os.rmdir','os.chmod','os.link','os.symlink','os.truncate','os.chown','os.utime'}:
        raise RuntimeError('pure development controls refuse filesystem mutation')
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
suite=unittest.defaultTestLoader.loadTestsFromName('test_native_loader')
assert suite.countTestCases()==18
result=unittest.TextTestRunner(verbosity=2).run(suite)
signal.alarm(0)
raise SystemExit(0 if result.wasSuccessful() and result.testsRun==18 and not result.skipped else 1)
