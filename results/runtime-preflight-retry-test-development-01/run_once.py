"""One ordinary isolated development unittest pass; no runtime/provider work."""
from pathlib import Path
import hashlib, json, os, resource, subprocess, time
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = Path(__file__).resolve().parent
SOURCE = ROOT/'experiments/runtime-preflight-retry-05'
STARTUP = ROOT/'experiments/runtime04-environment-adapter-01'
PYTHON = '/opt/homebrew/bin/python3'
PATHS = [SOURCE/n for n in ['test_retry.py','audit_owner.py','controller.py','routes.json']]
PATHS += [STARTUP/'environment.py', ROOT/'experiments/hir-options-hash-runtime-audit-05/test_reader.py',
 ROOT/'experiments/hir-options-hash-runtime-audit-05/reader.py',
 Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/stable-cgu/owned_stage.py'), Path(__file__)]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(): return {str(p): {'sha256':sha(p),'bytes':p.stat().st_size} for p in PATHS}
def write(n,v):
 with (HERE/n).open('x') as f: json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(60,60))
 resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024,256*1024))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
before=rows();write('source-before.json',before)
command=[PYTHON,'-B','-m','unittest','-v','test_retry']
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
raw=(HERE/'stderr').read_text();passed=record['returncode']==0 and 'Ran 33 tests' in raw and raw.rstrip().endswith('OK') and before==after
result=dict(status='passed' if passed else 'failed',actual_tests=33 if passed else None,
 sources_unchanged=before==after,returncode=record['returncode'],record_sha256=sha(HERE/'record.json'),
 controlled_qualification=False,scope='ordinary in-memory and owned temporary lock development controls only')
write('result.json',result)
write('manifest.json',{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(HERE.iterdir()) if p.is_file()})
print(json.dumps(dict(status=result['status'],result_sha256=sha(HERE/'result.json'))))
raise SystemExit(0 if passed else 1)
