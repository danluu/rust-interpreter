#!/usr/bin/env python3
"""One authorized pure dyld-parser suite; no provider/compiler calls or locks."""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
CWD=ROOT/'experiments/runtime-exporter-after-installation07-02'
OUT=ROOT/'results/runtime-exporter-dyld-parser-test-01'
PINS={str(CWD/'dyld_parser.py'):'96cc2eac6665f8befc03bdebc04d1a12409f60659944a7a64fdd60bfca774fe0',
      str(CWD/'test_dyld_parser.py'):'7b2d5e99f8a89ad98737e7cfe80aceff98cb40d7e7544b6fa4a5428b47f778a6'}
BASE=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-exporter-metadata-01/commands')
PINS.update({str(BASE/'025/stderr'):'38d246a87b22ed9f64efc9a52dd1cc90bf8238bcefe7355287b2fe71d01b91c8',
 str(BASE/'025/receipt.json'):'fede29331aa274c15ac9c275c46820d36c7457af0c1603e0b4926467003a96a1',
 str(BASE/'027/stderr'):'845591447242c62e2641508f5d19e1ef6808459bfd3d0b331277448dbcc96d13',
 str(BASE/'027/receipt.json'):'6494cf8a01a4bf0f78132918049819fbaf353164a86c557eca018d0ad90793d7'})

def write(name,data):
 with (OUT/name).open('x') as f:
  json.dump(data,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())

def row(path):
 path=Path(path);assert path.resolve(strict=True)==path and path.is_file() and not path.is_symlink()
 a=path.stat();data=path.read_bytes();b=path.stat();assert a==b
 return dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),identity=[a.st_dev,a.st_ino,a.st_mode,a.st_size,a.st_mtime_ns,a.st_ctime_ns,a.st_nlink])

def capture():
 result={p:row(p) for p in PINS}
 assert all(result[p]['sha256']==h for p,h in PINS.items())
 return result

def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(60,60))
 resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024,256*1024))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))

assert Path.cwd()==CWD
before=capture();write('inputs-before.json',before)
(OUT/'tmp').mkdir()
env=dict(PATH='/opt/homebrew/bin:/usr/bin:/bin',LANG='C',LC_ALL='C',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(OUT/'tmp')+'/')
command=['/opt/homebrew/bin/python3','-B','test_dyld_parser.py']
record=dict(status='starting',parent_pid=os.getpid(),parent_parent_pid=os.getppid(),started_at=time.time(),command=command,cwd=str(CWD),environment=env,canonical_lock=False,signals=0,retries=0,provider_probes=0)
write('invocation.json',record)
with (OUT/'stdout').open('xb') as stdout,(OUT/'stderr').open('xb') as stderr:
 child=subprocess.Popen(command,cwd=CWD,env=env,stdout=stdout,stderr=stderr,preexec_fn=limits)
 record.update(status='running',pid=child.pid,child_started_at=time.time());write('started.json',record)
 returncode=child.wait()
record.update(status='finished',returncode=returncode,finished_at=time.time(),waited=True,may_be_live=False)
for stream in ('stdout','stderr'):record[stream]=row(OUT/stream)
write('record.json',record)
after=capture();write('inputs-after.json',after)
raw=(OUT/'stderr').read_text();passed=returncode==0 and before==after and re.search(r'\nRan 24 tests in [0-9.]+s\n\nOK\n\Z',raw) is not None
write('result.json',dict(status='passed' if passed else 'failed',tests=24 if passed else None,returncode=returncode,record_sha256=row(OUT/'record.json')['sha256'],source_and_fixtures_unchanged=before==after,provider_probes=0,canonical_lock=False,frontend_qualified=False,metadata_qualified=False))
print(json.dumps(dict(status='passed' if passed else 'failed',tests=24 if passed else None,parent_pid=record['parent_pid'],pid=child.pid,returncode=returncode)))
raise SystemExit(0 if passed else 1)
