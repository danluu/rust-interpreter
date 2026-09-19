"""One bounded read-only hash proposal preparation after all four actual audits."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
HERE=ROOT/'experiments/hir-options-hash-driver-stage'
WORK=ROOT/'.work/hash-driver-preparation-execution-01'
PREREQUISITES=ROOT/'.work/hash-driver-preparation-predecessors-01.json'
AUDIT=A/'.work/native-reconciliation-independent-verification-01.json'
RECEIPT=A/'.work/hir-options-hash-native-controls-reconciliation-01/receipt.json'
FIELDS=('dev','ino','mode','size','mtime_ns','ctime_ns','nlink')
SOURCES={'prepare.py':'679bcccbddfadbda1e0ebb891f73f7bb19aad2e72e5655ddeaae1b5798082948',
 'stage.py':'8daf98086fd3eabb3e2a403f0f19995140956edf52178345a3fd11493d999b2d',
 'prerequisites.py':'30a5e0d0f686d0568f919aa0532bc2b8b206c26eed4fc737e3187d0c05ed9cd5',
 'snapshot_bindings.py':'355b890ee48fe36aad2bdfc0e65aeb6b596d4a73f6a199b21ebe243d6dba35bc',
 'verify.py':'99635ff121f2225bed43b4056da095594312b6004c348728a857afffbca0dca5'}
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
 assert len(args.native_audit_sha256)==64 and all(c in '0123456789abcdef' for c in args.native_audit_sha256)
 assert sha(PREREQUISITES)=='be1ca83d7e2e2ee6d220927dd30ee502a9343d21e1eee15cc28d1fd20e375b7c'
 prior=read(PREREQUISITES)
 for row in prior['audits'].values():
  assert sha(row['path'])==row['sha256'] and sha(row['receipt'])==row['receipt_sha256']
  assert read(row['path'])['status']=='verified' and read(row['receipt'])['status']=='passed'
 assert sha(AUDIT)==args.native_audit_sha256
 audit=read(AUDIT);receipt=read(RECEIPT)
 assert audit['status']=='verified' and audit['receipt_sha256']==sha(RECEIPT) and receipt['status']=='passed'
 assert audit['read_only_reconciliation'] is True and audit['actual_workload_children']==0 and audit['qualified_native_children']==20
 assert audit['original_failed_receipt_sha256']=='76fe70afd8eb6486b445e39366de2dd1ffd52ed9578e63203dc7cf74a679a272'
 assert sha(ROOT/'.work/hir-options-hash-prerequisite-controls-independent-verification-04.json')=='3a13fc479808c1a6433811a237bf4d1d1319f5c5b67b527c878d5ca185f05d99'
 for name,h in SOURCES.items():assert sha(HERE/name)==h,name
 assert not WORK.exists() and not WORK.is_symlink()
 for name in ['plan.json','inputs.json','snapshot-plan.json','launch.json','metadata-preflight.json','catalogs']:
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
  record.update(status='running',pid=child.pid);save(record)
  try:code=child.wait()
  finally:
   record.update(status='finished' if child.returncode is not None else 'unclosed',returncode=child.returncode,finished_at=time.time(),stdout_sha256=sha(WORK/'stdout'),stderr_sha256=sha(WORK/'stderr'));save(record)
 print(json.dumps(dict(record=str(WORK/'record.json'),sha256=sha(WORK/'record.json'),pid=child.pid,returncode=code)))
 if code:raise SystemExit(code)
 for name,h in SOURCES.items():assert sha(HERE/name)==h,name
 assert not (ROOT/'.work/hir-options-hash-driver-01').exists()
if __name__=='__main__':main()
