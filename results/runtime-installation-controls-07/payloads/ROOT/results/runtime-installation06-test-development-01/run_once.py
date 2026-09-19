"""One ordinary isolated development unittest pass; no runtime/provider work."""
from pathlib import Path
import hashlib, json, os, resource, subprocess, time
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = Path(__file__).resolve().parent
SOURCE = ROOT/'experiments/runtime-installation-after-preflight05-02'
STARTUP = ROOT/'experiments/runtime04-environment-adapter-01'
PYTHON = '/opt/homebrew/bin/python3'
PATHS = [SOURCE/n for n in ['entry.py','controller.py','audit_owner.py','routes.json','prepare.py','prepare_once.py','launch.py','test_installation.py']]
PATHS += [STARTUP/'environment.py',ROOT/'experiments/runtime-preflight-retry-05/routes.json',HERE/'child.py',Path(__file__),Path(PYTHON).resolve(strict=True)]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows():
 result={}
 for p in PATHS:
  before=p.stat();data=p.read_bytes();after=p.stat()
  keys=['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']
  assert all(getattr(before,'st_'+k)==getattr(after,'st_'+k) for k in keys)
  result[str(p)]=dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),identity={k:getattr(after,'st_'+k) for k in keys})
 return result
def write(n,v):
 with (HERE/n).open('x') as f: json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(60,60))
 resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024,256*1024))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
EXPECTED={'/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/audit_owner.py': '4ce531a592d99046f0936a43d2b31c6a1f3ecbca7da809b70da79b20f45a97b8', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/controller.py': 'cf44c7b7fae1964af472d6f3cffe6f5c9d2d1d782d83dc123f65dbd64de259c8', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/entry.py': '6e98a34a72b756fd38c48e8f98dbdd535321d555d4332f66cacc876e0d487467', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/launch.py': '27734a6ae2fa8f13ca62afdccfa3fe400f1b5e42666629fa81c9fce5dc1e8fdc', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/prepare.py': '9414b82645bbd96e491f2d348439bdfafd0fe54430ca427c3808bc8d8a68e855', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/prepare_once.py': 'b5210818a1321d802987ed5e234d0d4f1b65fc2dee823974f0bfbbe6f7429a43', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/routes.json': 'ef75ddf2057ebd395a159623d387b01051ee1479363bf9c878f7641b99ec0dd2', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/test_installation.py': 'cee84852f61d4ecbb9c16c96521dc205b7090a2783333bb076fe08475630361d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01/environment.py': 'fbc563accfeebe2650902263ed9972031d37c84bc8c21986a3545ae4020d314d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/routes.json': '893d6102741b5206a829e2f5e130614667140b1eacc09d0c55616f7311f82e6a'}
before=rows();assert all(before[p]['sha256']==digest for p,digest in EXPECTED.items()), 'reviewed source differs'
write('source-before.json',before)
command=[PYTHON,'-B',str(HERE/'child.py')]
environment={'PATH':'/usr/bin:/bin:/opt/homebrew/bin','LANG':'C','LC_ALL':'C',
 'TMPDIR':str(HERE/'tmp'),'PYTHONPATH':str(STARTUP),'PYTHONDONTWRITEBYTECODE':'1'}
record=dict(command=command,cwd=str(SOURCE),environment=environment,parent_pid=os.getpid(),
 parent_parent_pid=os.getppid(),started_at=time.time(),cpu_seconds=60,file_bytes=256*1024,
 canonical_lock_access=False,compiler_calls=0,provider_calls=0,network=False)
with (HERE/'stdout').open('xb') as out,(HERE/'stderr').open('xb') as err:
 child=subprocess.Popen(command,cwd=SOURCE,env=environment,stdout=out,stderr=err,preexec_fn=limits)
 record.update(pid=child.pid,spawned_at=time.time());write('started.json',record)
 record['returncode']=child.wait()
record.update(status='closed',finished_at=time.time(),stdout_sha256=sha(HERE/'stdout'),stderr_sha256=sha(HERE/'stderr'))
write('record.json',record)
after=rows();write('source-after.json',after)
raw=(HERE/'stderr').read_text();passed=record['returncode']==0 and 'Ran 25 tests' in raw and raw.rstrip().endswith('OK') and before==after
result=dict(status='passed' if passed else 'failed',actual_tests=25 if passed else None,
 sources_unchanged=before==after,returncode=record['returncode'],record_sha256=sha(HERE/'record.json'),
 controlled_qualification=False,scope='ordinary pure installation06 route/phase/prerequisite and fixed prefix budget controls only')
write('result.json',result)
write('manifest.json',{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(HERE.iterdir()) if p.is_file()})
print(json.dumps(dict(status=result['status'],result_sha256=sha(HERE/'result.json'))))
raise SystemExit(0 if passed else 1)
