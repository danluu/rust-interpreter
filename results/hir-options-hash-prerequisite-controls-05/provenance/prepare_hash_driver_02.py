"""One bounded read-only hash proposal preparation after all four actual audits."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
HERE=ROOT/'experiments/hir-options-hash-driver-stage'
WORK=ROOT/'.work/hash-driver-preparation-execution-02'
PREREQUISITES=ROOT/'.work/hash-driver-preparation-predecessors-02.json'
AUDIT=A/'.work/native-reconciliation-independent-verification-01.json'
RECEIPT=A/'.work/hir-options-hash-native-controls-reconciliation-01/receipt.json'
MAXIMUM_OBSERVATION_SECONDS=1800
EXPECTED_CONTROLS_AUDIT='7d17277c1551a40faa717ed06056184d156519cee4b2002a83e69f7d3424265a'  # Bound to actual66 independent audit.
SOURCES={'prepare.py':'61fffaab5f10aafbda9cfb63b01ca27e1fb83a38d03b58cffb56dbb29f4350b6',
 'stage.py':'8daf98086fd3eabb3e2a403f0f19995140956edf52178345a3fd11493d999b2d',
 'prerequisites.py':'30a5e0d0f686d0568f919aa0532bc2b8b206c26eed4fc737e3187d0c05ed9cd5',
 'snapshot_bindings.py':'06e0d4c7304f192f851479218b8e9dbfc666e58c6c2cc5d68b9373053c2360cc',
 'verify.py':'265a408bada10659e7de42b636b247465b31d2dfc2e84dd8aae80a21b569b6f4'}
def sha(p):
 with Path(p).open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def save(record):
 staged=WORK/'record.staged';assert not staged.exists()
 with staged.open('x') as s:json.dump(record,s,sort_keys=True,indent=2);s.write('\n');s.flush();os.fsync(s.fileno())
 staged.replace(WORK/'record.json')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--native-audit-sha256',required=True);args=parser.parse_args()
 assert Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize
 assert type(EXPECTED_CONTROLS_AUDIT) is str and len(EXPECTED_CONTROLS_AUDIT)==64,'unbound actual66 controls qualification'
 assert len(args.native_audit_sha256)==64 and all(c in '0123456789abcdef' for c in args.native_audit_sha256)
 assert sha(PREREQUISITES)=='6c34637a76b0e890816f776e7b55fd553e4f25ee0d4676ae3eac21c91b47da0a'
 prior=read(PREREQUISITES)
 assert sha(prior['previous_preparation']['record'])==prior['previous_preparation']['sha256']
 for name,row in prior['previous_preparation']['partial_catalogs'].items():assert sha(name)==row['sha256'] and Path(name).stat().st_size==row['size']
 for row in prior['audits'].values():
  assert sha(row['path'])==row['sha256'] and sha(row['receipt'])==row['receipt_sha256']
  assert read(row['path'])['status']=='verified' and read(row['receipt'])['status']=='passed'
 assert sha(AUDIT)==args.native_audit_sha256
 audit=read(AUDIT);receipt=read(RECEIPT)
 assert audit['status']=='verified' and audit['receipt_sha256']==sha(RECEIPT) and receipt['status']=='passed'
 assert audit['read_only_reconciliation'] is True and audit['actual_workload_children']==0 and audit['qualified_native_children']==20
 assert audit['original_failed_receipt_sha256']=='76fe70afd8eb6486b445e39366de2dd1ffd52ed9578e63203dc7cf74a679a272'
 assert sha(ROOT/'.work/hir-options-hash-prerequisite-controls-independent-verification-05.json')==EXPECTED_CONTROLS_AUDIT
 for name,h in SOURCES.items():assert sha(HERE/name)==h,name
 assert not WORK.exists() and not WORK.is_symlink()
 for name in ['plan.json','inputs.json','snapshot-plan.json','launch.json','metadata-preflight.json','catalogs-02']:
  assert not (HERE/name).exists() and not (HERE/name).is_symlink(),name
 assert not (ROOT/'.work/hir-options-hash-driver-01').exists()
 free=shutil.disk_usage(ROOT).free;assert free>=16*2**30,'fresh16GiB readonly preparation entry required'
 argv=prior['partial_argv_not_runnable']+['--native-audit',str(AUDIT),'--native-audit-sha256',args.native_audit_sha256]
 assert argv[:3]==[str(Path('/opt/homebrew/bin/python3').resolve()),'-B',str(HERE/'prepare.py')]
 env=dict(HOME='/Users/danluu',LANG='C',LC_ALL='C',LOGNAME='danluu',PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TZ='UTC',USER='danluu')
 WORK.mkdir();(WORK/'source').mkdir()
 for name,h in SOURCES.items():
  data=(HERE/name).read_bytes();assert hashlib.sha256(data).hexdigest()==h
  with (WORK/'source'/name).open('xb') as s:s.write(data)
 record=dict(status='starting',command=argv,cwd=str(ROOT),environment=env,parent_pid=os.getpid(),started_at=time.time(),entry_free_bytes=free,
  sources_sha256=SOURCES,native_audit_sha256=args.native_audit_sha256,runner_source=str(Path(__file__).resolve()),runner_sha256=sha(__file__),
  scope='Read-only prerequisite and provider bytes; writes fresh proposal only, no compiler/provider commands or WORK controller.',
  identity_limitation='Popen PID, parent, launch command/directory and times; no contemporaneous ps/cwd probes.',workload_children=0)
 save(record)
 with (WORK/'stdout').open('xb') as out,(WORK/'stderr').open('xb') as err:
  child=subprocess.Popen(argv,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
  record.update(status='running',pid=child.pid,maximum_observation_seconds=MAXIMUM_OBSERVATION_SECONDS)
  try:
   try:save(record)
   except BaseException as error:record['initial_child_publication_error']=repr(error)
   try:
    code=child.wait(timeout=MAXIMUM_OBSERVATION_SECONDS)
   except subprocess.TimeoutExpired:
    code=None;record.update(status='observation-expired-task-not-signaled',may_be_live=True)
  finally:
   record.update(returncode=child.returncode,observation_finished_at=time.time(),stdout_sha256=sha(WORK/'stdout'),stderr_sha256=sha(WORK/'stderr'))
   if child.returncode is not None:record.update(status='finished',finished_at=time.time())
   else:record.update(status='unclosed-task-not-signaled',may_be_live=True)
   try:save(record)
   except BaseException as error:
    print(json.dumps(dict(status='publication-failed',error=repr(error),observed_record=record)),flush=True)
    raise
 print(json.dumps(dict(record=str(WORK/'record.json'),sha256=sha(WORK/'record.json'),pid=child.pid,returncode=code)))
 if code is None:raise RuntimeError('Preparation may still be live; no signal or retry authorized by this observation')
 if code:raise SystemExit(code)
 if 'initial_child_publication_error' in record:raise RuntimeError('Preparation completed but initial child record publication failed; inspect retained evidence')
 for name,h in SOURCES.items():assert sha(HERE/name)==h,name
 assert not (ROOT/'.work/hir-options-hash-driver-01').exists()
if __name__=='__main__':main()
