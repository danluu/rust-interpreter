"""One ordinary isolated development unittest pass; no runtime/provider work."""
from pathlib import Path
import hashlib, json, os, resource, subprocess, time
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = Path(__file__).resolve().parent
SOURCE = ROOT/'experiments/runtime-native-loader-probes-01'
PYTHON = '/opt/homebrew/bin/python3'
PATHS = [Path(p) for p in ['/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/runtime_compiler.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/producer_recipe.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/audit_recipe.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/test_native_loader.py', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/runtime_compiler.py', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/custom_compiler.py', '/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/hir-options-hash/runtime-installation-01/recipe.py', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/installation-plan-01/specification.json']]
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
EXPECTED={'/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/runtime_compiler.py': '9591f94735c5b7d8333292c7ce3baf2cde7cf556eb4e75354fd19536f33b6f5b', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/producer_recipe.py': '38ccb1d5ac03f0ce80eca0e397de507b3aa9534fae5da8f3102f1b902adcdb50', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/audit_recipe.py': 'a464993d8200f43fe30f365215a07383a76e9be08c63e1ee844c27e8aaf985b2', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-native-loader-probes-01/test_native_loader.py': 'fa84b34a52e9f6b0eeb29bf727f718528891570e2dc274bdf2a594690ec70659', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/runtime_compiler.py': 'f38cdfd9e9c719185d9e002abf76a8883ad718b3771c62a9788f6feedd52a61b', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/custom_compiler.py': 'c6a44c3d271664de2c97bf6c3af3ea6426eba6dd3730ac0612411230a02b7449', '/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/hir-options-hash/runtime-installation-01/recipe.py': '0fad2d783d750bc2ffd3a1694e52505bb7fa7c4b983f1e8b1edb3691dc455e3e', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-02/installation-plan-01/specification.json': '96c228e2b561de69c2d56a8e1364ac349437418a47a5c1935f6e4f14e67ab6b9'}
before=rows();assert all(before[p]['sha256']==digest for p,digest in EXPECTED.items()), 'reviewed source differs'
write('source-before.json',before)
command=[PYTHON,'-B',str(HERE/'child.py')]
environment={'PATH':'/usr/bin:/bin:/opt/homebrew/bin','LANG':'C','LC_ALL':'C',
 'TMPDIR':str(HERE/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
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
raw=(HERE/'stderr').read_text();passed=record['returncode']==0 and 'Ran 18 tests' in raw and raw.rstrip().endswith('OK') and before==after
result=dict(status='passed' if passed else 'failed',actual_tests=18 if passed else None,
 sources_unchanged=before==after,returncode=record['returncode'],record_sha256=sha(HERE/'record.json'),
 controlled_qualification=False,scope='ordinary pure native loader policy/identity/recipe controls; selected exact AST runtime bodies, no provider imports or commands')
write('result.json',result)
write('manifest.json',{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(HERE.iterdir()) if p.is_file()})
print(json.dumps(dict(status=result['status'],result_sha256=sha(HERE/'result.json'))))
raise SystemExit(0 if passed else 1)
