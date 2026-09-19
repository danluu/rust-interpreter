"""One ordinary isolated development unittest pass; no runtime/provider work."""
from pathlib import Path
import hashlib, json, os, resource, subprocess, time
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = Path(__file__).resolve().parent
SOURCE = ROOT/'experiments/runtime-installation-after-preflight05-03'
STARTUP = ROOT/'experiments/runtime04-environment-adapter-01'
PYTHON = '/opt/homebrew/bin/python3'
PATHS = [Path(p) for p in ['/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/entry.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/controller.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/audit_owner.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/routes.json', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/prepare.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/prepare_once.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/launch.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/imports.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/test_installation.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/test_imports.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01/environment.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/routes.json']]
PATHS += [HERE/'child.py',Path(__file__),Path(PYTHON).resolve(strict=True)]
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
EXPECTED={'/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/entry.py': '31bfb9cfd59bbbc45648ce7d6b5e72ddf5efdee62991df1e9414ae3d9ffdf736', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/controller.py': 'ba41563fed996c39c4f082e157c10845ddfca8bbde627ac22a22920c3f0ef642', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/audit_owner.py': '7a5fb8804372a42cc01e7890ec1be4e4a24cceb5dbe800a7dad67940efc212d5', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/routes.json': 'd339e74a11edb948f3cf4bcc0afbbba76887cc61aed125c8bb8bf62b1633723a', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/prepare.py': '8ca8b3371176b34c18b8e086e719f832ff86c4edbc1e2eab38c6a8ec04209722', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/prepare_once.py': 'ab0609d297302262feb418a240d0ec4a0c88d511f73e381c0a5c5b4245473c68', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/launch.py': '21560018724dd9439648acbf68e61a05b9899c8e8fb66e2f1e605bf747e8da06', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/imports.py': 'abfec7fa64337072613e2d707989c8a0724c758d3e412d85072af14570c2b460', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/test_installation.py': 'cee84852f61d4ecbb9c16c96521dc205b7090a2783333bb076fe08475630361d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/test_imports.py': '78b8d7ecaa981c751206714bf282f6ce5cce108fbb86b1af163e3692ba81401d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01/environment.py': 'fbc563accfeebe2650902263ed9972031d37c84bc8c21986a3545ae4020d314d', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05/routes.json': '893d6102741b5206a829e2f5e130614667140b1eacc09d0c55616f7311f82e6a'}
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
raw=(HERE/'stderr').read_text();passed=record['returncode']==0 and 'Ran 30 tests' in raw and raw.rstrip().endswith('OK') and before==after
result=dict(status='passed' if passed else 'failed',actual_tests=30 if passed else None,
 sources_unchanged=before==after,returncode=record['returncode'],record_sha256=sha(HERE/'record.json'),
 controlled_qualification=False,scope='ordinary pure installation07 route/phase/prerequisite/budget25 plus factory selection5; provider definition loads mocked, no provider imports or commands')
write('result.json',result)
write('manifest.json',{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(HERE.iterdir()) if p.is_file()})
print(json.dumps(dict(status=result['status'],result_sha256=sha(HERE/'result.json'))))
raise SystemExit(0 if passed else 1)
