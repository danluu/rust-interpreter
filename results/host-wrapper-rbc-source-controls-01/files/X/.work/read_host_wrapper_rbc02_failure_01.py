"""Saved-only RBC02 observer-stop failure readback; no provider payloads."""
import hashlib,json,os,re,stat,time
from pathlib import Path
Q=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
D=Q/'experiments/host-wrapper-rbc-driver-02';P=Q/'results/host-wrapper-rbc-fixture-02';E=Q/'.work/host-wrapper-rbc-execution-02';W=Q/'.work/host-wrapper-rbc-fixture-02'
OUT=X/'.work/host-wrapper-rbc02-failure-independent-readback-01.json';checked={};started=time.time()
def stamp(s):return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]

def read(p,sha=None,ref=None):
 p=Path(p);a=stamp(p.lstat());assert p.resolve(strict=True)==p and stat.S_ISREG(a[2]) and a[3]<=16*2**20
 with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as f:
  assert stamp(os.fstat(f.fileno()))==a;b=f.read(16*2**20+1);assert stamp(os.fstat(f.fileno()))==a
 assert stamp(p.lstat())==a and len(b)==a[3];r=dict(path=str(p),bytes=len(b),identity=a,sha256=hashlib.sha256(b).hexdigest())
 if sha:assert r['sha256']==sha
 if ref:assert all(r[k]==v for k,v in ref.items())
 if str(p) in checked:assert checked[str(p)]==r
 checked[str(p)]=r;return b

def doc(p,sha=None,ref=None):return json.loads(read(p,sha,ref))
outer=doc(E/'record.json','dad552e21a6b87441ef018de5c03b55adb870a2211c42ad6588aa074f50f11f8');driver=doc(P/'record.json','5e6b9631cd54621cae00a4c7f2746ccfdd1e5730fe0a3f24d3b9c180774d98cb');suite=doc(P/'suite-result.json','88f34bd8dea046cbb6b273fe28b80b63f0dbb8150413f9fbcc79eea55d650db2');stop=doc(P/'STOP.json','c8ea624056b61fb4062d5e2c2925f0245942cbbd089f9bef7f7b2ab9b677bf60')
binding=doc(driver['binding']['path'],ref=driver['binding']);read(outer['source']['path'],ref=outer['source'])
assert (outer['parent_pid'],outer['pid'],driver['child_pid'])==(93431,94203,96216) and driver['parent_pid']==94203 and driver['parent_parent_pid']==93431
assert outer['driver_record']==checked[str(P/'record.json')] and outer['binding']==driver['binding']
assert outer['normal_wait_completed'] is driver['normal_wait_completed'] is True and outer['driver_may_be_live'] is driver['child_may_be_live'] is False
assert outer['status']==driver['status']==suite['status']=='failed' and outer['returncode']==driver['returncode']==1
assert outer['started_at']<=outer['child_started_at']<=driver['started_at']<=driver['child_started_at']<=driver['child_finished_at']<=driver['finished_at']<=outer['child_finished_at']<=outer['finished_at']
assert outer['signals']==outer['retries']==driver['signals']==driver['retries']==0
assert driver['observation_errors']==stop['errors']==["FileNotFoundError(2, 'No such file or directory')"] and stop['at']==1789844505.1990058 and suite['violations']==[]
assert driver['limits']==binding['limits'] and driver['suite_seconds']<600 and max(driver['observed_peak'][n] for n in ('logical_bytes','allocated_bytes'))<=2**30
for k in ('stdout','stderr'):read(outer[k]['path'],ref=outer[k])
a=read(P/'inputs-before.json');b=read(P/'inputs-after.json');assert a==b;inputs=json.loads(a)
for k in ('sources','evidence','payloads'):
 assert set(inputs[k])==set(binding[k]) and all(inputs[k][p]['sha256']==h for p,h in binding[k].items())
for p,h in binding['sources'].items():read(p,h,inputs['sources'][p])
for p,r in suite['loaded_sources'].items():assert inputs['sources'][p]==r
assert len(binding['sources'])==24 and len(binding['payloads'])==11045 and len(binding['evidence'])==35
assert suite['tests_run']==suite['errors']==5 and suite['failures']==suite['skipped']==suite['expected_failures']==suite['unexpected_successes']==0
ids=['_host_codegen_rbc_fixture.HostCodegenNativeTests.'+n for n in sorted(binding['tests'])];assert suite['test_ids']==suite['expected_test_ids']==ids
stderr=read(P/'stderr').decode();stdout=read(P/'stdout').decode();assert stderr.count('RuntimeError: parent observation requires no further child')==5 and 'FAILED (errors=5)' in stderr and 'Ran 5 tests in ' in stderr
for n in sorted(binding['tests']):assert f'{n} (_host_codegen_rbc_fixture.HostCodegenNativeTests.{n}) ... ERROR' in stderr
assert len(suite['commands'])==11;previous=driver['child_started_at'];rows=[]
for o in suite['commands']:
 p=Path(o['receipt']['path']);r=doc(p,ref=o['receipt']);assert r['status']=='finished' and r['returncode']==0 and r['parent_pid']==96216 and r['cwd']==str(p.parents[2])
 assert previous<=r['started_at']<=r['finished_at']<=driver['child_finished_at'];previous=r['finished_at']
 assert o['passed'] is True and o['limit_seconds']==30 and o['seconds']<30 and doc(p.parent/'observation.json')==o
 for k in ('stdout','stderr'):read(o[k]['path'],ref=o[k])
 rows.append(dict(receipt=checked[str(p)],pid=r['pid'],returncode=0,command=r['command'],started_at=r['started_at'],finished_at=r['finished_at']))
assert rows[-1]['started_at']<stop['at']<rows[-1]['finished_at'] and rows[-1]['command'][1]=='test'
case_roots=[Path(line.removeprefix('borrowck correctness artifacts: ')) for line in stdout.splitlines() if line.startswith('borrowck correctness artifacts: ')]
assert len(case_roots)==5 and set((W/'artifacts').iterdir())==set(case_roots)
empty=[];memberships={}
for case in case_roots:
 assert case.parent==W/'artifacts' and any(case.name.startswith(n+'-') for n in binding['tests']);children=[]
 for p in sorted((case/'commands').iterdir()):
  names=sorted(x.name for x in p.iterdir());children.append(dict(path=str(p),members=names))
  if names:assert names==['observation.json','record.json','stderr','stdout'] and str(p/'record.json') in checked
  else:empty.append(str(p))
 memberships[str(case/'commands')]=children
assert len(empty)==5 and any(p.endswith('/0012') for p in empty) and sum(p.endswith('/0001') for p in empty)==4
case=Path(rows[0]['receipt']['path']).parents[2];names=['Cargo.toml','build.rs','shared/Cargo.toml','macros/Cargo.toml','macros/build.rs','macros/input.txt','src/lib.rs','macros/src/lib.rs','shared/src/lib.rs'];restored={}
for n in names:
 old=case/'source-states/original'/n;cur=case/'package'/n;assert read(old)==read(cur);restored[n]=dict(original=checked[str(old)],current=checked[str(cur)])
read(case/'package/Cargo.lock')
assert set(p.name for p in (case/'source-states').iterdir())=={'original','macro-body'}
read(Path(__file__).absolute())
for p,r in checked.items():assert stamp(Path(p).lstat())==r['identity']
result=dict(status='independently-confirmed-closed-failure',pid=os.getpid(),parent_pid=os.getppid(),started_at=started,finished_at=time.time(),refs=checked,direct_commands=11,all_direct_returncodes=0,normal_wait_chain=[93431,94203,96216],tests_started=5,tests_passed=0,tests_errors=5,collector_failures=0,STOP=checked[str(P/'STOP.json')],observation_errors=stop['errors'],suite_child_time_violations=[],empty_pre_spawn_command_directories=empty,command_memberships=memberships,commands=rows,inputs_byte_equal=True,input_census={k:len(inputs[k]) for k in ('sources','payloads','evidence')},source24_unchanged=True,generated_source9_restored=restored,complete_RBC_qualified=False,benchmark=False,provider_payload_reads=0,compiler_calls=0,diagnosis='The parent recorded FileNotFoundError with no path or traceback during its active observation block and wrote STOP while direct child 0011 was running. That Cargo test still completed rc0 and was normally waited. The next invocation and four later setUp invocations refused before spawning, leaving five empty command directories. All five tests therefore errored; no assertion of failed compiler semantics is supported. Active footprint lstat and live receipt reads are possible ENOENT sites; the exact missing path/site cannot be established from the retained repr alone.')
assert not OUT.exists();OUT.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(report=str(OUT),sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),checked=len(checked))))
