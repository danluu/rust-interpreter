"""Normally wait the reviewed exporter preparation without holding its lock."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
SOURCE = ROOT/'experiments/host-wrapper-exporter-01'
OUT = ROOT/'.work/host-wrapper-exporter-preparation-execution-01'
EXPECTED = '4e17ba1f0be6548ea3875322a1216c56e5bfb857ca99d57278e18925632cfeb3'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(value):
    temporary = OUT/'record.tmp'
    temporary.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    temporary.replace(OUT/'record.json')


assert Path.cwd() == ROOT and not os.path.lexists(OUT)
binding = SOURCE/'sources.json'
assert digest(binding) == EXPECTED
contents = json.loads(binding.read_text())
driver = SOURCE/'prepare.py'
assert digest(driver) == contents['files'][str(driver)]
command = ['/opt/homebrew/bin/python3','-B',str(driver),
    '--sources-sha256',EXPECTED,
    '--runtime-audit-sha256','878a1f363e6ca5e3acdcb16645c79d8412a260e8721a9fe75eacd7823a481728',
    '--runtime-audit-execution-sha256','1f4d4a70657aa071fb85540f97b8ecbfeed3dcde85e340360b5065e7a3ed7d43']
OUT.mkdir()
record = dict(status='starting',parent_pid=os.getpid(),parent_parent_pid=os.getppid(),
    started_at=time.time(),source=dict(path=__file__,sha256=digest(__file__)),
    binding=dict(path=str(binding),sha256=EXPECTED),command=command,cwd=str(X),
    canonical_policy='Child acquires canonical; parent holds no lock.',signals=0,retries=0)
save(record)
with (OUT/'stdout').open('xb') as stdout,(OUT/'stderr').open('xb') as stderr:
    child = subprocess.Popen(command,cwd=X,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
    try:
        record.update(child_pid=child.pid,child_may_be_live=True)
        save(record)
    finally:
        code = child.wait()
record.update(status='finished',returncode=code,finished_at=time.time(),child_may_be_live=False,
    stdout_sha256=digest(OUT/'stdout'),stderr_sha256=digest(OUT/'stderr'))
save(record)
assert code == 0
receipt_path = X/'.work/host-wrapper-exporter-preparation-01/record.json'
receipt = json.loads(receipt_path.read_text())
assert receipt['status'] == 'passed' and receipt['pid'] == child.pid
assert receipt['parent_pid'] == os.getpid()
assert record['started_at'] <= receipt['started_at'] <= receipt['finished_at'] <= record['finished_at']
record.update(preparation_verified=True,receipt=dict(path=str(receipt_path),sha256=digest(receipt_path)))
save(record)
print(json.dumps(dict(path=str(OUT/'record.json'),sha256=digest(OUT/'record.json'))))
