"""Unrun exact-path no-consumer adapter; never signal or scan all processes.

The containing retirement packet must freeze this source, the two executors,
explicit owner acknowledgments, every current consumer packet/base and closed
owner receipt. This adapter creates only its exact task-owned probe evidence.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import stat
import subprocess
import time

OWNER=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
TARGET=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hir-options-hash-run-make-01/retained')
OUTPUT=OWNER/'.work/retained-proof-copy-retirement-01/no-consumer'
PROPOSAL_SHA='e0599d87ab842b9e18932fddb54bb63aaf850cd2366279f67507e875731b3481'
MAX_FILE=256*1024
MAX_READ_BYTES=256*2**20
READ_BYTES=0
STARTED=None
GUARD=None
ACTORS={'/root','/root/oxc_baseline','/root/runtime_installation','/root/workspace_capacity'}
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')

def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def same(a,b):return encoded(a)==encoded(b)
def finite(value):return type(value) in (int,float) and math.isfinite(value)
def stamp(path):
    s=Path(path).lstat();return {k:getattr(s,'st_'+k) for k in FIELDS}
def raw(path,maximum=64*2**20):
    global READ_BYTES
    path=Path(path);before=stamp(path)
    require(path.resolve(strict=True)==path and stat.S_ISREG(before['mode']) and before['size']<=maximum,'ordinary bounded exact proof')
    require(READ_BYTES+before['size']<=MAX_READ_BYTES,'cumulative no-consumer metadata/raw bound')
    if STARTED is not None:require(time.monotonic()-STARTED<=90,'bounded no-consumer observation time')
    if GUARD is not None:GUARD()
    value=path.read_bytes();READ_BYTES+=len(value);require(stamp(path)==before,'proof changed during read');return value
def reference(ref):
    require(set(ref)=={'path','sha256'},'exact proof reference')
    value=raw(ref['path']);require(sha(value)==ref['sha256'],'proof digest differs');return json.loads(value)
def write(path,value):
    data=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();require(len(data)<=MAX_FILE,'bounded probe receipt')
    with path.open('x') as out:out.write(data.decode());out.flush();os.fsync(out.fileno())
def current_file(path,row):
    require(same(stamp(path),row['identity']) and sha(raw(path))==row['sha256'],'frozen no-consumer input differs')

def closed_metadata(groups,started):
    """Retain closure associations without inventing process-start observations."""
    require(type(groups) is list and 0<len(groups)<=16,'explicit bounded no-PS closure groups')
    seen=set()
    for group in groups:
        schema=group['schema']
        if schema=='supervised-owner-v1':
            require(set(group)=={'schema','terminal','outer','launch','audit','launcher','launcher_schema'},'supervised closure fields')
            terminal=reference(group['terminal']);outer=reference(group['outer']);launch=reference(group['launch'])
            audit=reference(group['audit']);launcher=reference(group['launcher'])
            require(type(launch) is dict and 'owner' in launch and 'cwd' not in launch
                and type(launch['owner']) is str and Path(launch['owner']).is_absolute(),
                'explicit historical owner launch schema; runtime cwd launch is distinct')
            require(group['terminal']['path'] not in seen,'duplicate closure owner');seen.add(group['terminal']['path'])
            require(terminal['status'] in ['passed','passed-awaiting-independent-audit','failed']
                and outer['status']=='finished' and type(outer['returncode']) is int
                and outer['returncode']==(1 if terminal['status']=='failed' else 0)
                and outer['child_pid']==terminal['pid'] and outer['supervisor_pid']==terminal['parent_pid']
                and outer['command']==launch['command'][6:] and outer['cwd']==launch['owner']
                and all(finite(v) for v in [outer['child_started_at'],terminal['started_at'],terminal['finished_at'],outer['finished_at']])
                and outer['child_started_at']<=terminal['started_at']<=terminal['finished_at']<=outer['finished_at']<=started
                and audit['status'] in ['verified','verified-retained-failure']
                and audit['receipt_sha256']==group['terminal']['sha256'],'actual complete closed supervised owner')
            require(launcher['command']==launch['command'] and launcher['cwd']==launch['owner']
                and launcher['launch_sha256']==group['launch']['sha256']
                and launcher['launcher_returncode']==0 and finite(launcher['launcher_finished_at'])
                and launcher['launcher_finished_at']<=outer['finished_at'],'actual launch wrapper closure')
            if group['launcher_schema']=='terminal-observed-v1':
                require(launcher['status']=='terminal-observed' and launcher['outer_sha256']==group['outer']['sha256']
                    and launcher['outer_status']=='finished' and launcher['returncode']==outer['returncode']
                    and launcher['controller_pid']==terminal['pid'] and launcher['supervisor_pid']==terminal['parent_pid']
                    and outer['finished_at']<=launcher['terminal_observed_at']<=launcher['finished_at']<=started,
                    'explicit actual terminal observation')
            else:
                require(group['launcher_schema']=='legacy-launcher-finished-v1'
                    and launcher['status']=='launcher-finished'
                    and audit['launcher_sha256']==group['launcher']['sha256']
                    and audit['outer_sha256']==group['outer']['sha256'],
                    'legacy wrapper must remain separately bound to actual closed outer audit')
        elif schema in ['direct-reader-failure-v1','direct-rehearsal-failure-v1','direct-reader-audit-failure-v1']:
            require(set(group)=={'schema','execution','stdout','stderr','expected_returncode','missing_outputs'},
                'explicit failed-reader closure fields')
            execution=reference(group['execution']);directory=Path(group['execution']['path']).parent
            require(group['execution']['path'] not in seen,'duplicate failed-reader closure');seen.add(group['execution']['path'])
            require(execution['status']=='finished' and type(execution['returncode']) is int
                and type(group['expected_returncode']) is int and group['expected_returncode']!=0
                and execution['returncode']==group['expected_returncode']
                and type(execution['execution_error']) is str and execution['execution_error']
                and execution.get('child_may_remain_live') is not True and execution.get('may_be_live') is not True
                and same(execution.get('observation_errors',[]),[])
                and type(execution['pid']) is int and execution['pid']>0
                and all(type(execution[k]) is int and execution[k]==0 for k in ['compiler_calls','provider_probes'])
                and execution['runtime_admission'] is False and execution['retirement_authorized'] is False
                and all(finite(execution[k]) for k in ['started_at','child_started_at','observation_finished_at','finished_at'])
                and execution['started_at']<=execution['child_started_at']<=execution['observation_finished_at']
                    <=execution['finished_at']<=started,'actual failed child was explicitly waited and closed')
            if 'canonical_released_at' in execution:
                require(finite(execution['canonical_released_at']) and execution['finished_at']<=execution['canonical_released_at']<=started,
                    'reported release time differs')
            for stream in ['stdout','stderr']:
                ref=group[stream];require(ref['path']==str(directory/stream),'exact failed-reader raw route')
                require(sha(raw(ref['path'],MAX_FILE))==ref['sha256']==execution[stream+'_sha256'],'full closed-failure raw binding')
            if schema=='direct-reader-failure-v1':
                source=OWNER/'experiments/runtime04-historical-copy-reader-rehearsal-01'
                expected=sorted(str(source/name) for name in ['inputs.json','plan.json','launch.json','preparation.json'])
                require(execution['mode']=='prepare' and execution['result']==str(source/'preparation.json'),
                    'exact original failed preparation route')
            elif schema=='direct-rehearsal-failure-v1':
                result=OWNER/'.work/runtime04-historical-copy-reader-rehearsal-02/result.json'
                expected=[str(result)]
                require(group['execution']['path']==str(OWNER/'.work/runtime04-historical-copy-reader-rehearsal-execution-02/record.json')
                    and execution['mode']=='rehearse' and execution['result']==str(result)
                    and execution['pid']==84047 and execution['parent_pid']==82686
                    and execution['returncode']==1 and 'result_sha256' not in execution
                    and 'canonical_released_at' not in execution,
                    'exact closed failed rehearsal02; no fabricated result or release')
            else:
                known={
                    str(OWNER/'.work/runtime04-historical-copy-reader-verification-execution-03/record.json'):dict(
                        record_sha256='b5202c1dde0422dc33d6d7f38a84c638506d0346bbf392b561259baface0a103',
                        report=str(OWNER/'.work/runtime04-historical-copy-reader-independent-verification-03.json'),
                        pid=77431,parent_pid=76714,
                        source_sha256='525ac3fd9ddd2f3c81ba8e420469f2b8d7b6a36cc3f225f221b30f2270dad54c',
                        execution_source_sha256='aecc23154d2e51c02179c5a5f53607ea9aa15b75bcfdff51c1609374c2c4ec27'),
                    str(OWNER/'.work/runtime04-historical-copy-reader-verification-execution-04/record.json'):dict(
                        record_sha256='7b19b35072f337910404801c1c40a1d39f7df20ab597fa21af29da27eedcde2d',
                        report=str(OWNER/'.work/runtime04-historical-copy-reader-independent-verification-04.json'),
                        pid=65092,parent_pid=64356,
                        source_sha256='9e9aa4efd43fd5c770cde6147159c771d9f405b0e6896fb426dffe504887a34b',
                        execution_source_sha256='683b1439987e6873e4c41f0a5a0d4f4f13824d74c57293a57245bd143ca7c608'),
                }
                require(group['execution']['path'] in known,'only the two exact closed failed audits are admitted')
                saved=known[group['execution']['path']];expected=[saved['report']]
                require(group['execution']['sha256']==saved['record_sha256']
                    and execution['report']==saved['report'] and execution['pid']==saved['pid']
                    and execution['parent_pid']==saved['parent_pid'] and execution['returncode']==1
                    and 'mode' not in execution and 'result' not in execution
                    and 'report_sha256' not in execution and 'result_sha256' not in execution
                    and 'canonical_released_at' not in execution
                    and execution['source_sha256']==saved['source_sha256']
                    and execution['execution_source_sha256']==saved['execution_source_sha256']
                    and same(execution['actual_closure_pins'],dict(
                        EXPECTED_EXECUTION_RECORD='4326a5029150369e4a23bbc786388d26f6f041e2a818db1701f9953adfba3e4e',
                        EXPECTED_LAUNCH='89c38791a7e927f30cb2b2b4dcfadc0dc90bc2a54aa33156b922da1249d49ca4',
                        EXPECTED_PREPARATION_RECORD='74c8d0e9833fcd945a5711f64c5cb8b8bd88a860bd691be273cc6f131bb62078',
                        EXPECTED_RESULT='10b88b94df6c8df07e2ccba1cfc04e9c702d5606e114a3c2a71e378975433b41')),
                    'exact closed failed independent audit03/04; passed Reader03 remains separate')
            require(group['missing_outputs']==expected
                and all(not Path(name).exists() and not Path(name).is_symlink() for name in expected),
                'original failed outputs must remain absent')
        else:
            require(schema=='direct-reader-v1' and set(group)=={'schema','result','execution','expected_status'},
                'explicit direct-reader closure fields')
            result=reference(group['result']);execution=reference(group['execution'])
            require(group['result']['path'] not in seen,'duplicate reader closure');seen.add(group['result']['path'])
            require(type(group['expected_status']) is str and result['status']==group['expected_status'] and execution['status']=='finished'
                and type(execution['returncode']) is int and execution['returncode']==0
                and execution['result_sha256']==group['result']['sha256']
                and execution['pid']==result['pid'] and execution['parent_pid']==result['parent_pid']
                and all(finite(v) for v in [result['started_at'],result['finished_at'],execution['finished_at'],execution['canonical_released_at']])
                and result['started_at']<=result['finished_at']<=execution['finished_at']<=execution['canonical_released_at']<=started
                and all(execution.get(k) is None for k in ['error','publication_error','capacity_violation','child_may_remain_live']),
                'actual direct-reader Popen closure; no synthetic PS')

def declarations(packet,selected,started):
    """Authenticate exact task-owned scope without discovering new consumers."""
    spec=packet['no_consumer']
    require(set(spec)=={'acknowledgments','current_consumers','closed_owners','closed_metadata','pending_absences','executors','environment'},'explicit complete no-consumer declaration')
    acknowledgments=spec['acknowledgments']
    require(type(acknowledgments) is dict and set(acknowledgments)==ACTORS,'all current task owners acknowledge exact scope')
    for owner,ref in acknowledgments.items():
        doc=reference(ref)
        require(doc['owner']==owner and doc['proposal_sha256']==PROPOSAL_SHA and doc['selected_paths']==selected
                and doc['no_active_or_pending_readers_of_selected_paths'] is True
                and doc['all_current_task_consumer_packets_declared'] is True,'exact owner acknowledgment differs')
        require(type(doc['observed_at']) in (int,float) and doc['observed_at']<=started,'actual acknowledgment timestamp required')
    consumers=spec['current_consumers'];require(type(consumers) is list and len(consumers)<=32,'bounded explicit current consumers')
    seen=set()
    for consumer in consumers:
        require(set(consumer)=={'owner','inputs','state'} and consumer['owner'] in ACTORS
                and consumer['state'] in ['prepared','active'],'exact current consumer descriptor')
        ref=consumer['inputs'];require(ref['path'] not in seen,'duplicate current consumer');seen.add(ref['path'])
        wire=reference(ref);files=wire['files']
        require(type(files) is dict and len(files)<=180000,'bounded complete consumer table')
        if 'file_table_base' in wire:
            base=reference(wire['file_table_base'])
            require('file_table_base' not in base and not set(base['files'])&set(files),'nonrecursive disjoint current base')
            files=dict(base['files'],**files)
            require(same(wire['file_table_integrity'],dict(count=len(files),total_bytes=sum(r['size'] for r in files.values()),
                        sha256=sha(encoded(files)))),'complete current consumer integrity')
        require(not set(selected)&set(files),'prepared/active consumer still requires a selected copy')
    absences=spec['pending_absences']
    require(type(absences) is list and len(absences)<=64 and absences==sorted(set(absences)),'explicit unique pending consumer absences')
    for name in absences:
        path=Path(name);require(path.is_absolute() and '..' not in path.parts
            and any(path.is_relative_to(Path(root)) for root in packet['owned_consumer_roots']),'task-owned exact absence route')
        require(not path.exists() and not path.is_symlink(),'pending consumer appeared')
    owners=spec['closed_owners'];require(type(owners) is list and 0<len(owners)<=64,'explicit bounded closed owner identities')
    pids={};starts={}
    for owner in owners:
        require(set(owner)=={'schema','receipt','expected_status','pid','identity_ps','identity_ps_sha256'},'closed owner fields')
        child=reference(owner['receipt']);pid=owner['pid'];line=owner['identity_ps'];fields=line.split()
        require(type(pid) is int and 0<pid<2**31 and len(fields)>9 and fields[0]==str(pid)
                and sha(line.encode())==owner['identity_ps_sha256'],'exact historical PID/start observation')
        require(child['status']==owner['expected_status'] and child['pid']==pid and finite(child['started_at']),
                'explicit typed PS-child owner association')
        if owner['schema']=='normal-child-v1':
            require(child['status'] in ['finished','failed'] and type(child['returncode']) is int
                and finite(child['finished_at']) and child['started_at']<=child['finished_at']<=started,
                'normal child has an actual finished_at and returncode')
        else:
            require(owner['schema']=='driver-wait-v1' and child['status']=='passed'
                and child['wait']['status']=='exited' and type(child['wait']['returncode']) is int
                and child['wait']['returncode']==0 and child['wait']['child_may_be_live'] is False
                and child['child_may_be_live'] is False and child['probe_may_be_live'] is False
                and child['wait']['errors']==child['errors']==[]
                and finite(child['child_finished_at']) and finite(child['controller_finished_at'])
                and child['started_at']<=child['child_finished_at']<=child['controller_finished_at']<=started,
                'driver requires actual wait and separate child/controller closure')
        require(child['identity']['ps_returncode']==0 and child['identity']['ps']==line,'historical PS observation must belong to that receipt')
        key=(pid,tuple(fields[3:8]));require(key not in starts,'duplicate complete old process identity');starts[key]=True
        pids.setdefault(pid,[]).append(fields[3:8])
    closed_metadata(spec['closed_metadata'],started)
    return spec,pids

def probe(label,command,output,environment,canonical_fd,guard):
    directory=output/label;directory.mkdir(mode=0o700)
    record=dict(status='starting',command=command,cwd=str(OWNER),environment=environment,
        parent_pid=os.getpid(),parent_parent_pid=os.getppid(),started_at=time.time(),signals=[],
        identity_limitation='Exact Popen PID/parent/argv/requested cwd retained. No extra contemporaneous ps/cwd observation of this fast read-only child.')
    stdout=directory/'stdout';stderr=directory/'stderr';child=None
    try:
        with stdout.open('xb') as out,stderr.open('xb') as err:
            previous=resource.getrlimit(resource.RLIMIT_FSIZE)
            require(previous[1]==resource.RLIM_INFINITY or previous[1]>=MAX_FILE,'child file bound unavailable')
            resource.setrlimit(resource.RLIMIT_FSIZE,(MAX_FILE,previous[1]))
            try:child=subprocess.Popen(command,cwd=OWNER,env=environment,stdin=subprocess.DEVNULL,stdout=out,stderr=err,pass_fds=(canonical_fd,))
            finally:resource.setrlimit(resource.RLIMIT_FSIZE,previous)
            record.update(status='running',pid=child.pid,child_started_at=time.time())
            pending_error=None
            try:write(directory/'started.json',record)
            except BaseException as error:pending_error=repr(error)
            deadline=time.monotonic()+30
            while True:
                try:code=child.wait(timeout=min(.25,max(.001,deadline-time.monotonic())));break
                except subprocess.TimeoutExpired:
                    try:
                        guard()
                        require(stdout.stat().st_size<=MAX_FILE and stderr.stat().st_size<=MAX_FILE,'probe raw bound')
                    except BaseException as error:pending_error=repr(error)
                    if time.monotonic()>=deadline:
                        record.update(status='unresolved-live-child-not-signaled',observation_finished_at=time.time());raise
            record.update(status='finished',returncode=code,finished_at=time.time())
            if pending_error is not None:record['publication_or_guard_error']=pending_error
            require(pending_error is None,'probe evidence/guard failed after explicit child closure')
        for name in ['stdout','stderr']:
            data=raw(directory/name,MAX_FILE);record[name+'_sha256']=sha(data);record[name+'_bytes']=len(data)
        return record,raw(stdout,MAX_FILE),raw(stderr,MAX_FILE)
    except BaseException as error:
        record['error']=repr(error)
        if child is not None and record.get('status')!='finished':record['child_may_remain_live']=child.poll() is None
        raise
    finally:
        record['observation_closed_at']=time.time();write(directory/'receipt.json',record)

def verify(*,packet,proposal,output,canonical_fd,admitted_at,guard):
    global READ_BYTES,STARTED,GUARD
    READ_BYTES=0;STARTED=time.monotonic();GUARD=guard
    started=time.time();output=Path(output)
    require(output==OUTPUT and not output.exists() and not output.is_symlink(),'fresh exact no-consumer output')
    require(proposal['target_root']==str(TARGET) and packet['proposal_sha256']==PROPOSAL_SHA,'exact no-consumer target/proposal')
    selected=sorted(str(TARGET/name) for name in proposal['selected'])
    require(len(selected)==21 and all(Path(p).parent==TARGET for p in selected),'exact direct selected paths')
    require(admitted_at<=started and type(canonical_fd) is int and canonical_fd>=0,'active containing canonical admission')
    os.fstat(canonical_fd)
    guard();spec,pids=declarations(packet,selected,started)
    require(set(spec['executors'])=={'/usr/sbin/lsof','/bin/ps'},'only two fixed read-only executors')
    for name,row in spec['executors'].items():current_file(name,row)
    environment=spec['environment']
    require(environment==packet['passed_environment'],'same explicit task environment')
    output.mkdir(mode=0o700)
    observations=[]
    command=['/usr/sbin/lsof','-nP','-Fpfn',*selected]
    child,out,err=probe('selected-paths',command,output,environment,canonical_fd,guard)
    require(child['returncode']==1 and out==err==b'','selected copy has an open handle or lsof diagnostic')
    observations.append(dict(path=str(output/'selected-paths/receipt.json'),sha256=sha(raw(output/'selected-paths/receipt.json',MAX_FILE)),pid=child['pid']))
    command=['/bin/ps','-p',','.join(map(str,sorted(pids))),'-o','pid=,ppid=,pgid=,lstart=,tty=,command=']
    child,out,err=probe('closed-owner-pids',command,output,environment,canonical_fd,guard)
    require(child['returncode'] in [0,1] and not err and (child['returncode']==0)==bool(out.strip()),'exact PID query return/output differs')
    observed=[];seen=set()
    for line in out.decode('utf-8',errors='strict').splitlines():
        fields=line.split();require(len(fields)>9 and fields[0].isdigit(),'complete observed PID row')
        pid=int(fields[0]);require(pid in pids and pid not in seen,'unexpected or duplicate PID query row');seen.add(pid)
        require(fields[3:8] not in pids[pid],'exact original task-owned producer identity is still alive')
        observed.append(dict(pid=pid,observed_ps=line,historical_starts=pids[pid],meaning='PID number reused; observed start differs. No process control.'))
    observations.append(dict(path=str(output/'closed-owner-pids/receipt.json'),sha256=sha(raw(output/'closed-owner-pids/receipt.json',MAX_FILE)),pid=child['pid']))
    guard();spec_after,pids_after=declarations(packet,selected,time.time())
    require(same(spec,spec_after) and same(pids,pids_after),'consumer declarations changed during probes')
    for name,row in spec['executors'].items():current_file(name,row)
    return dict(status='verified-exact-no-consumer',proposal_sha256=PROPOSAL_SHA,selected_paths=selected,
        canonical_admission_pid=os.getpid(),started_at=started,finished_at=time.time(),no_signals=True,
        acknowledged_active_or_pending_readers=[],acknowledgments=spec['acknowledgments'],
        current_consumer_packets=spec['current_consumers'],pending_absences=spec['pending_absences'],
        closed_owner_receipts=spec['closed_owners'],probes=observations,observed_reused_pids=observed,
        closed_owner_metadata=spec['closed_metadata'],
        metadata_and_raw_read_bytes=READ_BYTES,
        limitations=['Two exact read-only observations, not a host-wide process census.','Owner acknowledgments bind pending task-owned consumers; no ownership inferred from age.'])

if __name__=='__main__':
    raise SystemExit('Source-only exact no-consumer adapter; no standalone probe execution.')
