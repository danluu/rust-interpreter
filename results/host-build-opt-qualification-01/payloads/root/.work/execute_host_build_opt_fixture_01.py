"""Normally wait for the source-reviewed host-profile fixture qualification."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

Q = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
H = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/host-build-opt-fixture-source-handoff-03.json')
OUT = Q/'.work/host-build-opt-fixture-execution-01'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(record):
    (OUT/'record.json').write_text(json.dumps(record, indent=2, sort_keys=True)+'\n')

assert Path.cwd() == Q
assert digest(H) == '16f2e8bc8c9c2b959e162cd8c3a0e45a55e174c9cbdcc23aa914201b6961a347'
h = json.loads(H.read_bytes())
assert digest(h['driver']['path']) == h['driver']['sha256'] == '6bc127ffab0ca3fc65f87c38bd54fa3642e0c536470fd8795fe0ede37379f7aa'
assert digest(h['source_manifest']['path']) == h['source_manifest']['sha256'] == '033c5477820247f9c43791269151aa43e2102c841914ec5b42b6dc930859ceae'
assert h['argv'] == ['/opt/homebrew/bin/python3', '-B', h['driver']['path'], '--sources-sha256', h['source_manifest']['sha256']]
assert h['cwd'] == '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918'
assert not os.path.lexists(OUT)
OUT.mkdir()
r = dict(status='starting', parent_pid=os.getpid(), parent_parent_pid=os.getppid(),
         started_at=time.time(), handoff=dict(path=str(H),sha256=digest(H)),
         source=dict(path=__file__,sha256=digest(__file__)), command=h['argv'],cwd=h['cwd'],
         canonical_policy='Child acquires canonical; parent holds no lock.',signals=0,retries=0)
save(r)
with (OUT/'stdout').open('xb') as stdout, (OUT/'stderr').open('xb') as stderr:
    child = subprocess.Popen(h['argv'], cwd=h['cwd'], stdin=subprocess.DEVNULL,
                             stdout=stdout, stderr=stderr)
    try:
        r.update(child_pid=child.pid, child_may_be_live=True)
        save(r)
    finally:
        code = child.wait()
r.update(status='finished', returncode=code, finished_at=time.time(), child_may_be_live=False,
         stdout_sha256=digest(OUT/'stdout'), stderr_sha256=digest(OUT/'stderr'))
save(r)
assert code == 0
receipt_path = Q/'results/host-build-opt-fixture-01/record.json'
receipt = json.loads(receipt_path.read_bytes())
assert receipt['status'] == 'passed' and receipt['pid'] == child.pid and receipt['parent_pid'] == os.getpid()
assert r['started_at'] <= receipt['started_at'] <= receipt['finished_at'] <= r['finished_at']
r.update(qualification_verified=True,receipt=dict(path=str(receipt_path),sha256=digest(receipt_path)))
save(r)
print(json.dumps(dict(path=str(OUT/'record.json'),sha256=digest(OUT/'record.json'))))
