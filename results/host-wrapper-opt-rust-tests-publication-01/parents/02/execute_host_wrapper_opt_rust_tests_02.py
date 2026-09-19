"""Retain the actual parent/child closure of the native wrapper fixture."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
SOURCE = ROOT/'experiments/host-wrapper-opt-rust-tests-02'
OUT = ROOT/'.work/host-wrapper-opt-rust-tests-execution-02'
EXPECTED = '7d60a8dcf6024195ac8ec7d8a2d715d7754b061d9c33ed40b73f4fa8ea43baef'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(value):
    temporary = OUT/'record.tmp'
    temporary.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    temporary.replace(OUT/'record.json')


assert Path.cwd() == ROOT and not os.path.lexists(OUT)
binding = SOURCE/'binding.json'
assert digest(binding) == EXPECTED
contents = json.loads(binding.read_text())
driver = SOURCE/'run.py'
assert digest(driver) == contents['sources'][str(driver)]
command = ['/opt/homebrew/bin/python3','-B',str(driver),
    '--binding',str(binding),'--binding-sha256',EXPECTED]
OUT.mkdir()
record = dict(status='starting',parent_pid=os.getpid(),parent_parent_pid=os.getppid(),
    started_at=time.time(),source=dict(path=__file__,sha256=digest(__file__)),
    binding=dict(path=str(binding),sha256=EXPECTED),command=command,cwd=str(R),
    canonical_policy='Child acquires canonical; parent holds no lock.',signals=0,retries=0)
save(record)
with (OUT/'stdout').open('xb') as stdout,(OUT/'stderr').open('xb') as stderr:
    child = subprocess.Popen(command,cwd=R,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
    try:
        record.update(child_pid=child.pid,child_may_be_live=True)
        save(record)
    finally:
        code = child.wait()
record.update(status='finished',returncode=code,finished_at=time.time(),child_may_be_live=False,
    stdout_sha256=digest(OUT/'stdout'),stderr_sha256=digest(OUT/'stderr'))
save(record)
assert code == 0
receipt_path = ROOT/'results/host-wrapper-opt-rust-tests-02/record.json'
receipt = json.loads(receipt_path.read_text())
assert receipt['status'] == 'passed' and receipt['pid'] == child.pid
assert receipt['parent_pid'] == os.getpid()
assert record['started_at'] <= receipt['started_at'] <= receipt['finished_at'] <= record['finished_at']
record.update(qualification_verified=True,receipt=dict(path=str(receipt_path),sha256=digest(receipt_path)))
save(record)
print(json.dumps(dict(path=str(OUT/'record.json'),sha256=digest(OUT/'record.json'))))
