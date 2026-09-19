"""Normally wait one exact, source-reviewed partial retirement controller."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

Q = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HANDOFF = X/'.work/runtime-exporter07-cache-executable-retirement-source-handoff-01.json'
OUT = Q/'.work/runtime-exporter07-cache-executable-retirement-execution-01'
RECEIPT = X/'.work/runtime-exporter07-cache-executable-retirement-01/receipt.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ref(path):
    return dict(path=str(path), sha256=sha(path))


def save(record):
    with (OUT/'record.json').open('w') as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write('\n')


assert Path.cwd() == Q and sys.dont_write_bytecode and not sys.flags.optimize
assert sha(HANDOFF) == '54523f05caf5f15de43616269199e477169deca5bb79d30251d7638352f652ac'
h = json.loads(HANDOFF.read_bytes())
assert h['source']['sha256'] == sha(h['source']['path']) == 'd0a9eb194748fa2683b170330f8a2d19ab72463a828f19bee8386deee77c8223'
assert h['plan']['sha256'] == sha(h['plan']['path']) == '6682248c0c6a1f472c8322d69c9dc9920709bf248bc9d0030b705bf39cd868a7'
assert h['command']['argv'] == ['/opt/homebrew/bin/python3', '-B', h['source']['path'], '--plan-sha256', h['plan']['sha256']]
assert h['command']['cwd'] == str(Q)
assert not os.path.lexists(OUT) and not os.path.lexists(RECEIPT.parent)
OUT.mkdir()
r = dict(status='starting', parent_pid=os.getpid(), parent_parent_pid=os.getppid(),
    started_at=time.time(), source=ref(__file__), handoff=ref(HANDOFF), command=h['command'],
    child_may_be_live=True, signals=0, retries=0,
    canonical_policy='Controller owns canonical lock; parent holds none.')
save(r)
with (OUT/'stdout').open('xb') as stdout, (OUT/'stderr').open('xb') as stderr:
    child = subprocess.Popen(h['command']['argv'], cwd=Q, env=h['command']['environment'],
        stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
    try:
        r.update(child_pid=child.pid, child_started_at=time.time())
        save(r)
    finally:
        code = child.wait()
r.update(status='finished', returncode=code, finished_at=time.time(), child_may_be_live=False,
    stdout=ref(OUT/'stdout'), stderr=ref(OUT/'stderr'))
save(r)
assert code == 0
receipt = json.loads(RECEIPT.read_bytes())
assert receipt['status'] == 'passed' and receipt['pid'] == child.pid and receipt['parent_pid'] == os.getpid()
assert receipt['plan_sha256'] == h['plan']['sha256']
assert r['started_at'] <= receipt['started_at'] <= receipt['finished_at'] <= receipt['canonical_parent_lock_closed_at'] <= r['finished_at']
assert receipt['removed_files'] == 274 and receipt['retained_files'] == 9678 and receipt['all_directories_retained'] is True
assert receipt['live_probe_possible'] is False and len(receipt['children']) == 10
r.update(receipt=ref(RECEIPT), retirement_verified=True)
save(r)
print(json.dumps(ref(OUT/'record.json')))
