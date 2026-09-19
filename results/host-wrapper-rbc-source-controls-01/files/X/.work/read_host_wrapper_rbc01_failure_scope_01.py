"""Bounded independent confirmation of O's closed RBC01 failure census."""
import hashlib,json,os,re,stat,time
from collections import Counter
from pathlib import Path
Q=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913');X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918');O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
D=Q/'experiments/host-wrapper-rbc-driver-01';P=Q/'results/host-wrapper-rbc-fixture-01';E=Q/'.work/host-wrapper-rbc-execution-01';OUT=X/'.work/host-wrapper-rbc01-failure-scope-independent-readback-01.json'
checked={};started=time.time()
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
review=doc(O/'.work/host-wrapper-rbc01-failure-independent-readback-01.json','fb65862461ee2ae1497298f69e482c3b37145780e81606a72eef8c4fc5cd6020')
outer=doc(E/'record.json','e90ff0d3bbdcc607c15f8f7c8840bff5a52b56ef1022a0ca614a95c977ced547');driver=doc(P/'record.json',ref=outer['driver_record']);suite=doc(P/'suite-result.json','5e677d651676d5f4d300dfa89bb3df9bbe235e617ece5b8818dda0d74c78ff7f')
binding=doc(outer['binding']['path'],ref=outer['binding']);read(outer['source']['path'],ref=outer['source'])
assert (outer['parent_pid'],outer['pid'],driver['child_pid'])==(77872,79134,79861)
assert outer['returncode']==driver['returncode']==1 and outer['normal_wait_completed'] is driver['normal_wait_completed'] is True
assert outer['driver_may_be_live'] is driver['child_may_be_live'] is False and outer['status']==driver['status']==suite['status']=='failed'
assert driver['parent_pid']==outer['pid'] and driver['parent_parent_pid']==outer['parent_pid']
assert outer['started_at']<=outer['child_started_at']<=driver['started_at']<=driver['child_started_at']<=driver['child_finished_at']<=driver['finished_at']<=outer['child_finished_at']<=outer['finished_at']
assert driver['binding']==outer['binding'] and driver['tool_key']==outer['tool_key']==binding['tool_key'] and driver['limits']==binding['limits']
assert outer['signals']==outer['retries']==driver['signals']==driver['retries']==0 and not driver['observation_errors'] and not suite['violations'] and not (P/'STOP.json').exists()
assert driver['suite_seconds']<=600 and suite['seconds']<=600 and max(driver['observed_peak'][k] for k in ('allocated_bytes','logical_bytes'))<=2**30 and driver['observed_peak']['entries']<=65536
for field in ('stdout','stderr'):read(outer[field]['path'],ref=outer[field])
assert outer['environment']==binding['environment'] and outer['cwd']==driver['cwd']=='/Users/danluu/dev/rust-interp-runtime-installation-r-20260918'
assert outer['command'][2:]==[str(D/'run.py'),'--binding',str(D/'binding.json'),'--binding-sha256',outer['binding']['sha256'],'--tool-key',binding['tool_key']]
assert driver['command'][2:]==[str(D/'suite.py'),'--binding',str(D/'binding.json'),'--binding-sha256',outer['binding']['sha256'],'--tool-key',binding['tool_key']]
a=read(P/'inputs-before.json',ref=review['input_before']);b=read(P/'inputs-after.json',ref=review['input_after']);assert a==b;before=json.loads(a)
for key in ('sources','evidence','payloads'):
 assert set(before[key])==set(binding[key])
 assert all(before[key][p]['path']==p and before[key][p]['sha256']==h for p,h in binding[key].items())
for p,h in binding['sources'].items():read(p,h,ref=before['sources'][p])
assert len(binding['sources'])==24 and len(binding['payloads'])==11045 and len(binding['evidence'])==35
assert suite['loaded_sources'].keys()<=binding['sources'].keys()
for p,r in suite['loaded_sources'].items():assert r==before['sources'][p]
expected=['_host_codegen_rbc_fixture.HostCodegenNativeTests.'+n for n in sorted(binding['tests'])]
assert suite['test_ids']==suite['expected_test_ids']==expected and suite['tests_run']==5 and suite['failures']==1 and suite['errors']==suite['skipped']==suite['expected_failures']==suite['unexpected_successes']==0
stderr=read(P/'stderr',ref=review['suite_stderr']).decode();stdout=read(P/'stdout').decode()
for i,name in enumerate(sorted(binding['tests'])):
 assert f'{name} (_host_codegen_rbc_fixture.HostCodegenNativeTests.{name}) ... '+('FAIL' if i==0 else 'ok') in stderr
assert 'Ran 5 tests in ' in stderr and 'FAILED (failures=1)' in stderr and 'test_host_codegen_native.py", line 170' in stderr
assert len(suite['commands'])==review['command_count']==len(review['commands'])==180
previous=driver['child_started_at'];counts=Counter();testcounts=Counter();directories=set();failure=None
for actual,confirmed in zip(suite['commands'],review['commands'],strict=True):
 r=doc(actual['receipt']['path'],ref=actual['receipt']);p=Path(actual['receipt']['path']);assert confirmed['receipt']==actual['receipt']
 assert r['status']=='finished' and type(r['returncode']) is int and r['parent_pid']==79861 and previous<=r['started_at']<=r['finished_at']<=driver['child_finished_at'];previous=r['finished_at']
 assert r['returncode']==confirmed['returncode'] and r['cwd']==str(p.parents[2]) and r['benchmark'] is False and r['scope']=='real host-policy correctness'
 assert actual['limit_seconds']==30 and actual['passed'] is True and 0<=actual['seconds']<=30 and actual['seconds']==confirmed['seconds']
 assert doc(p.parent/'observation.json')==actual
 raw={k:read(actual[k]['path'],ref=actual[k]) for k in ('stdout','stderr')}
 for k in raw:assert checked[actual[k]['path']]==confirmed['raw'][k]
 counts[str(r['returncode'])]+=1;testcounts[p.parents[2].name]+=1;directories.add(str(p.parent));assert p.name=='record.json'
 if p.parent.name=='0039' and p.parents[2].name.startswith('test_cargo_shared_'):
  failure=(p,r,raw)
assert dict(counts)==review['returncodes'] and len(directories)==180
for root,n in testcounts.items():
 w=Q/'.work/host-wrapper-rbc-fixture-01/artifacts'/root
 assert sorted(p.name for p in (w/'commands').iterdir())==[f'{i:04d}' for i in range(1,n+1)]
 assert 'borrowck correctness artifacts: '+str(w) in stdout
p,r,raw=failure;assert r['returncode']==101 and r['command'][0]==binding['cargo'] and '--message-format=json-render-diagnostics' in r['command']
assert r['environment']['RUST_INTERP_HOST_CODEGEN_OPT']=='off' and r['environment']['RUST_INTERP_COMPILER_ARGV_RECORD_DIR'].endswith('/stock/generated-error')
messages=[json.loads(line) for line in raw['stdout'].decode().splitlines() if line.startswith('{')];reasons=Counter(m['reason'] for m in messages)
assert reasons.get('compiler-message',0)==0 and messages[-1]==dict(reason='build-finished',success=False)
assert b'error[E0308]: mismatched types' in raw['stderr'] and b'expected `u32`, found `bool`' in raw['stderr'] and b'proc_opt_macros::make!();' in raw['stderr'] and b'could not compile `proc-opt-fixture` (lib test)' in raw['stderr']
# The failed test's finally restores the generated project, but its later
# explicit restored-state Cargo history was never reached.
w=p.parents[2];names=['Cargo.toml','build.rs','shared/Cargo.toml','macros/Cargo.toml','macros/build.rs','macros/input.txt','src/lib.rs','macros/src/lib.rs','shared/src/lib.rs'];restored={}
for name in names:
 old=w/'source-states/original'/name;current=w/'package'/name;assert read(old)==read(current);restored[name]=dict(original=checked[str(old)],current=checked[str(current)])
assert read(w/'package/Cargo.lock')==read(w/'source-states/generated-error/Cargo.lock')
assert not (w/'source-states/restored').exists()
for mode in ('off','on'):assert not (w/'final-argv'/mode/'generated-error').exists()
read(Path(__file__).absolute())
for p,r in checked.items():assert stamp(Path(p).lstat())==r['identity']
compact={p:r for p,r in checked.items() if '/commands/' not in p}
result=dict(status='independently-confirmed-closed-failure',started_at=started,finished_at=time.time(),pid=os.getpid(),parent_pid=os.getppid(),original_O_report=checked[str(O/'.work/host-wrapper-rbc01-failure-independent-readback-01.json')],refs=compact,checked_files_count=len(checked),complete_checked_rows_sha256=hashlib.sha256(json.dumps(checked,sort_keys=True,separators=(',',':')).encode()).hexdigest(),direct_commands=180,commands_per_test=dict(testcounts),returncodes=dict(counts),normal_wait_chains=[77872,79134,79861],suite_tests=5,suite_passed=4,suite_failures=1,inputs_byte_equal=True,input_census={k:len(before[k]) for k in ('sources','payloads','evidence')},observational_violations=[],source24_unchanged=True,failed_Cargo=dict(receipt=checked[str(failure[0])],stdout=checked[str(failure[0].parent/'stdout')],stderr=checked[str(failure[0].parent/'stderr')],returncode=101,stdout_reasons=dict(reasons),rendered_error='E0308',compiler_message_records=0),restored_source9=restored,restored_Cargo_history_executed=False,generated_error_off_on_executed=False,complete_RBC_qualified=False,benchmark=False,provider_payload_reads=0,compiler_calls=0,diagnosis='The stock generated-error Cargo command rejected invalid generated code with rendered E0308 on stderr and terminal build-finished false. The collector asserted an E0308 compiler-message JSON row on stdout, where json-render-diagnostics supplied none. Four other tests passed. Source restoration happened in finally; the failed test did not reach off/on generated-error or explicit restored history. No retry or source mutation by this reader.')
assert not OUT.exists();OUT.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(report=str(OUT),sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),checked=len(checked),returncodes=dict(counts))))
