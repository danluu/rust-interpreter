"""Once-only independent archive audit with retained source/raw and bounded wait; no signals."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE=ROOT/'.work/verify_native_qualification_publication_01.py'
EXPECTED='4ad1a0638568fafc486af4f56f290b74d88195600845856683657e9b7f31e326'
WORK=ROOT/'.work/native-qualification-publication-verification-execution-01'
LAUNCH_RECORD=ROOT/'.work/native-qualification-publication-launch-execution-01/record.json'
RECEIPT=ROOT/'.work/native-qualification-publication-01/receipt.json'
OUT=ROOT/'.work/native-qualification-publication-independent-verification-01.json'

def require(ok,message):
    if not ok:raise RuntimeError(message)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def save(record):
    staged=WORK/'record.staged'
    with staged.open('x') as stream:json.dump(record,stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    staged.replace(WORK/'record.json')

def main():
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize,'exact audit owner/Python')
    require(sha(SOURCE)==EXPECTED,'reviewed auditor source differs')
    require(all(not path.exists() and not path.is_symlink() for path in [WORK,OUT]),'fresh audit namespace required')
    launch=json.loads(LAUNCH_RECORD.read_bytes());receipt=json.loads(RECEIPT.read_bytes())
    require(launch['status']=='terminal-observed' and launch['returncode']==launch['launcher_returncode']==0
        and receipt['status']=='passed' and launch['controller_pid']==receipt['pid'],'archive closure required before audit')
    command=[str(Path('/opt/homebrew/bin/python3').resolve(strict=True)),'-B',str(SOURCE)]
    env=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
        PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR='/tmp')
    WORK.mkdir();data=SOURCE.read_bytes();require(hashlib.sha256(data).hexdigest()==EXPECTED,'auditor snapshot differs')
    with (WORK/'source.py').open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    record=dict(status='starting',command=command,cwd=str(ROOT),environment=env,parent_pid=os.getpid(),started_at=time.time(),
        auditor_source=str(SOURCE),auditor_sha256=EXPECTED,runner_source=str(Path(__file__).resolve()),runner_sha256=sha(__file__),
        receipt_sha256=sha(RECEIPT),launch_record_sha256=sha(LAUNCH_RECORD),maximum_observation_seconds=1800,workload_children=0,
        identity_limitation='Exact Popen PID, parent, command, cwd and times recorded; no separate process probes.',
        runner_identity=dict(pid=os.getpid(),parent_pid=os.getppid(),pgid=os.getpgrp(),cwd=os.getcwd(),argv=sys.argv))
    save(record)
    with (WORK/'stdout').open('xb') as out,(WORK/'stderr').open('xb') as err:
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
        record.update(status='running',pid=child.pid)
        try:
            try:save(record)
            except BaseException as error:record['initial_child_publication_error']=repr(error)
            try:child.wait(timeout=1800)
            except subprocess.TimeoutExpired:record.update(status='unclosed-task-not-signaled',may_be_live=True)
        finally:
            record.update(returncode=child.returncode,observation_finished_at=time.time(),
                stdout_sha256=sha(WORK/'stdout'),stderr_sha256=sha(WORK/'stderr'))
            if child.returncode is not None:record.update(status='finished',finished_at=time.time())
            else:record.update(status='unclosed-task-not-signaled',may_be_live=True)
            save(record)
    require(child.returncode is not None,'independent auditor may remain live; no signal/retry')
    require(child.returncode==0,'independent audit failed; preserve raw/source without retry')
    require(sha(SOURCE)==EXPECTED and sha(WORK/'source.py')==EXPECTED,'reviewed audit bytes changed')
    require('initial_child_publication_error' not in record,'initial child record failed; inspect retained evidence')
    print(json.dumps(dict(path=str(WORK/'record.json'),sha256=sha(WORK/'record.json'),pid=child.pid,returncode=child.returncode,
        audit_path=str(OUT),audit_sha256=sha(OUT))))

if __name__=='__main__':main()
