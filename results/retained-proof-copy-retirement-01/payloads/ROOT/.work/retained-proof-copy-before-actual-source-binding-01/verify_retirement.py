"""Unrun independent saved-evidence audit of exactly 21 ordinary file removals.

No controller/remover/consumer adapter is imported or called. The separately
qualified recovery reader supplies strict current-byte/route and gzip reads;
ledger replay, actual process closure and consumer observations are checked here.
All absent copies keep historical metadata, never synthetic live identities.
"""
import os
INITIAL_ENVIRONMENT=dict(os.environ)
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import stat
import sys
import time
import types

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORK=ROOT/'.work/retained-proof-copy-retirement-01'
OUTER=ROOT/'.work/retained-proof-copy-retirement-execution-01'
PACKET=HERE/'plan-01.json'
OUTPUT=ROOT/'.work/retained-proof-copy-retirement-independent-verification-01.json'
TARGET=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hir-options-hash-run-make-01/retained')
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
RECOVERY_SOURCE_SHA='572907bc8ebd093b33cbe82906e8ed5c1409eadd9de3adbe27bf8c3604009474'
RECOVERY=dict(path=str(ROOT/'.work/retained-proof-copy-recovery-01.json'),sha256='b671db7b48989f16ebcecbe67c0396abf89a5ec59e937cecd29edcb7c682f251')
RECOVERY_EXECUTION=dict(path=str(ROOT/'.work/retained-proof-copy-recovery-execution-01/record.json'),sha256='85ce36c2e82e112a03cb18e6d429a3aa5b04c24caa7c3a279e884c9bb93e1862')
RUNTIME_AUDIT=ROOT/'.work/runtime04-historical-copy-reader-independent-verification-05.json'
RUNTIME_AUDIT_SHA=None
RETIRE_SOURCE_SHA=None
NO_CONSUMER_SOURCE_SHA=None
REMOVER_SHA='834135905025ac03369a7b224daf995dbc29eb2579d06e72baba5db1a71b6960'
FIELDS={'dev','ino','mode','nlink','size','mtime_ns','ctime_ns'}
ACTORS={'/root','/root/oxc_baseline','/root/runtime_installation','/root/workspace_capacity'}


CF_ADDITION={'__CF_USER_TEXT_ENCODING':'0x1F5:0x0:0x52'}
ENVIRONMENT_VALIDATION=dict(path='/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/hash-driver-failure-archive-environment-probe-01.json',sha256='edc973c06f424ddb73a80b2369c6b30153895feef7b75088a0bea8b7e5911a5e')

def environment_observation(passed,observed=None):
    observed=dict(os.environ) if observed is None else dict(observed)
    require(all(k in observed and observed[k]==v for k,v in passed.items()),'passed environment key changed or disappeared')
    added={k:v for k,v in observed.items() if k not in passed}
    require(added=={} or added==CF_ADDITION,'unvalidated startup environment addition')
    return dict(passed=dict(passed),observed=observed,additions=added,changed={},removed={})

def require(ok,message):
    if not ok:raise RuntimeError(message)


def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def same(a,b):return encoded(a)==encoded(b)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def finite(value):return type(value) in (int,float) and math.isfinite(value)


def identity(row):
    require(type(row) is dict and set(row)==FIELDS
        and all(type(v) is int and v>=0 for v in row.values()) and row['ino']>0,'complete typed historical identity')


def ledger(raw,proposal,terminal):
    """Replay all 63 events without executing or trusting the remover's parser."""
    require(len(raw)<=2**20 and raw.endswith(b'\n'),'bounded newline-terminated durable ledger')
    events=[json.loads(line) for line in raw.splitlines()]
    require(len(events)==63,'exact 21 triplets, no unaccounted event')
    remaining=json.loads(json.dumps(proposal['complete_inventory']))
    previous=terminal['admitted_at']
    for index,name in enumerate(proposal['selected']):
        require(Path(name).name==name and name!='.','only selected direct file names')
        row=remaining[name];before=row['identity'];parent=remaining['.']['identity']
        identity(before);identity(parent)
        require(row['kind']=='file' and stat.S_ISREG(before['mode']) and before['nlink']==1,'ordinary sole-copy historical entry')
        common=dict(path=str(TARGET/name),relative=name,before=before,sha256=row['sha256'],parent_before=parent)
        intent,unlinked,validated=events[3*index:3*index+3]
        for actual,label in [(intent,'intent'),(unlinked,'unlinked')]:
            require(set(actual)==set(common)|{'event','time'} and actual['event']==label
                and same({k:actual[k] for k in common},common),'independent exact intent/unlinked replay')
            require(finite(actual['time']) and previous<=actual['time']<=terminal['finished_at'],'ordered event lifetime')
            previous=actual['time']
        require(set(validated)=={'path','relative','event','after','parent_after','time'}
            and validated['event']=='validated' and validated['path']==str(TARGET/name)
            and validated['relative']==name and finite(validated['time'])
            and previous<=validated['time']<=terminal['finished_at'],'exact completed validation event')
        previous=validated['time'];after=validated['after'];parent_after=validated['parent_after']
        identity(after);identity(parent_after)
        require(all(after[k]==before[k] for k in ['dev','ino','mode','size','mtime_ns'])
            and after['nlink']==0 and after['ctime_ns']>=before['ctime_ns'],'observed held-inode removal transition')
        require(all(parent_after[k]==parent[k] for k in ['dev','ino','mode','nlink'])
            and parent_after['mtime_ns']>=parent['mtime_ns'] and parent_after['ctime_ns']>=parent['ctime_ns'],
            'only directory membership/time changed')
        require(not (TARGET/name).exists() and not (TARGET/name).is_symlink(),'selected path remains or was recreated')
        del remaining[name];remaining['.']['identity']=parent_after
    require(len(remaining)==41 and set(remaining)==set(proposal['complete_inventory'])-set(proposal['selected']),
        'exact preserved 40 files and original directory')
    return remaining


def verify_closed_metadata(reader,groups,started):
    """Retain closure associations without inventing process-start observations."""
    require(type(groups) is list and 0<len(groups)<=16,'explicit bounded no-PS closure groups')
    reference=lambda ref:reader.json(ref['path'],ref['sha256'])
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
                data=reader.file(ref['path'],keep=True)
                require(len(data)<=256*1024 and digest(data)==ref['sha256']==execution[stream+'_sha256'],'full closed-failure raw binding')
            if schema=='direct-reader-failure-v1':
                source=ROOT/'experiments/runtime04-historical-copy-reader-rehearsal-01'
                expected=sorted(str(source/name) for name in ['inputs.json','plan.json','launch.json','preparation.json'])
                require(execution['mode']=='prepare' and execution['result']==str(source/'preparation.json'),
                    'exact original failed preparation route')
            elif schema=='direct-rehearsal-failure-v1':
                result=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-02/result.json'
                expected=[str(result)]
                require(group['execution']['path']==str(ROOT/'.work/runtime04-historical-copy-reader-rehearsal-execution-02/record.json')
                    and execution['mode']=='rehearse' and execution['result']==str(result)
                    and execution['pid']==84047 and execution['parent_pid']==82686
                    and execution['returncode']==1 and 'result_sha256' not in execution
                    and 'canonical_released_at' not in execution,
                    'exact closed failed rehearsal02; no fabricated result or release')
            else:
                known={
                    str(ROOT/'.work/runtime04-historical-copy-reader-verification-execution-03/record.json'):dict(
                        record_sha256='b5202c1dde0422dc33d6d7f38a84c638506d0346bbf392b561259baface0a103',
                        report=str(ROOT/'.work/runtime04-historical-copy-reader-independent-verification-03.json'),
                        pid=77431,parent_pid=76714,
                        source_sha256='525ac3fd9ddd2f3c81ba8e420469f2b8d7b6a36cc3f225f221b30f2270dad54c',
                        execution_source_sha256='aecc23154d2e51c02179c5a5f53607ea9aa15b75bcfdff51c1609374c2c4ec27'),
                    str(ROOT/'.work/runtime04-historical-copy-reader-verification-execution-04/record.json'):dict(
                        record_sha256='7b19b35072f337910404801c1c40a1d39f7df20ab597fa21af29da27eedcde2d',
                        report=str(ROOT/'.work/runtime04-historical-copy-reader-independent-verification-04.json'),
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

def no_consumer(reader,packet,proposal,terminal):
    proof=reader.json(WORK/'no-consumer-proof.json',terminal['no_consumer_proof_sha256'])
    selected=sorted(str(TARGET/n) for n in proposal['selected']);spec=packet['no_consumer']
    require(proof['status']=='verified-exact-no-consumer' and proof['proposal_sha256']==packet['proposal_sha256']
        and proof['selected_paths']==selected and proof['canonical_admission_pid']==terminal['pid']
        and proof['no_signals'] is True and proof['acknowledged_active_or_pending_readers']==[]
        and finite(proof['started_at']) and finite(proof['finished_at'])
        and terminal['admitted_at']<=proof['started_at']<=proof['finished_at']<=terminal['finished_at'],
        'exact no-consumer proof scope/lifetime')
    require(set(spec)=={'acknowledgments','current_consumers','closed_owners','closed_metadata','pending_absences','executors','environment'}
        and set(spec['acknowledgments'])==ACTORS,'explicit complete task-owner declaration')
    for owner,ref in spec['acknowledgments'].items():
        doc=reader.json(ref['path'],ref['sha256'])
        require(doc['owner']==owner and doc['proposal_sha256']==packet['proposal_sha256'] and doc['selected_paths']==selected
            and doc['no_active_or_pending_readers_of_selected_paths'] is True
            and doc['all_current_task_consumer_packets_declared'] is True
            and finite(doc['observed_at']) and doc['observed_at']<=proof['started_at'],'actual exact owner acknowledgment')
    require(same(proof['acknowledgments'],spec['acknowledgments'])
        and same(proof['current_consumer_packets'],spec['current_consumers'])
        and same(proof['pending_absences'],spec['pending_absences'])
        and same(proof['closed_owner_receipts'],spec['closed_owners'])
        and same(proof['closed_owner_metadata'],spec['closed_metadata']),'complete declarations were actually observed')
    seen=set()
    for consumer in spec['current_consumers']:
        require(set(consumer)=={'owner','inputs','state'} and consumer['owner'] in ACTORS
            and consumer['state'] in ['prepared','active'],'explicit current consumer scope')
        ref=consumer['inputs'];require(ref['path'] not in seen,'unique current consumer');seen.add(ref['path'])
        wire=reader.json(ref['path'],ref['sha256']);files=wire['files']
        require('base_inputs' not in wire,'unsupported broader current-consumer proof')
        if 'file_table_base' in wire:
            ref=wire['file_table_base'];require(set(ref)=={'path','sha256'},'two-field file-table reference')
            base=reader.json(ref['path'],ref['sha256'])
            require('file_table_base' not in base and not set(base['files'])&set(files),'disjoint nonrecursive current table')
            files=dict(base['files'],**files)
            require(same(wire['file_table_integrity'],dict(count=len(files),total_bytes=sum(r['size'] for r in files.values()),
                sha256=digest(encoded(files)))),'complete current consumer table integrity')
        require(len(files)<=180000 and not set(selected)&set(files),'current consumer requires removed file')
    for name in spec['pending_absences']:
        require(any(Path(name).is_relative_to(Path(root)) for root in packet['owned_consumer_roots'])
            and not Path(name).exists() and not Path(name).is_symlink(),'acknowledged pending consumer changed')
    pids={};identities=set()
    for old in spec['closed_owners']:
        require(set(old)=={'schema','receipt','expected_status','pid','identity_ps','identity_ps_sha256'},'exact typed PS-child declaration')
        ref=old['receipt'];doc=reader.json(ref['path'],ref['sha256']);parts=old['identity_ps'].split();pid=old['pid']
        require(type(pid) is int and pid>0 and len(parts)>9 and parts[0]==str(pid)
            and digest(old['identity_ps'].encode())==old['identity_ps_sha256']
            and doc['pid']==pid and doc['status']==old['expected_status']
            and doc['identity']['ps_returncode']==0 and doc['identity']['ps']==old['identity_ps']
            and finite(doc['started_at']),
            'complete actually closed predecessor PID/start identity')
        if old['schema']=='normal-child-v1':
            require(doc['status'] in ['finished','failed'] and type(doc['returncode']) is int
                and finite(doc['finished_at']) and doc['started_at']<=doc['finished_at']<=proof['started_at'],
                'normal child actual finished_at closure')
        else:
            require(old['schema']=='driver-wait-v1' and doc['status']=='passed' and doc['wait']['status']=='exited'
                and type(doc['wait']['returncode']) is int and doc['wait']['returncode']==0
                and doc['wait']['child_may_be_live'] is False and doc['child_may_be_live'] is False
                and doc['probe_may_be_live'] is False and doc['wait']['errors']==doc['errors']==[]
                and finite(doc['child_finished_at']) and finite(doc['controller_finished_at'])
                and doc['started_at']<=doc['child_finished_at']<=doc['controller_finished_at']<=proof['started_at'],
                'driver wait and child/controller closure remain distinct')
        key=(pid,tuple(parts[3:8]));require(key not in identities,'duplicate old identity');identities.add(key)
        pids.setdefault(pid,[]).append(parts[3:8])
    verify_closed_metadata(reader,spec['closed_metadata'],proof['started_at'])
    require(pids and len(proof['probes'])==2,'exact two read-only probe receipts')
    commands=[['/usr/sbin/lsof','-nP','-Fpfn',*selected],
        ['/bin/ps','-p',','.join(map(str,sorted(pids))),'-o','pid=,ppid=,pgid=,lstart=,tty=,command=']]
    reused=[];previous=proof['started_at']
    for index,label in enumerate(['selected-paths','closed-owner-pids']):
        path=WORK/'no-consumer'/label;ref=proof['probes'][index]
        require(ref['path']==str(path/'receipt.json'),'exact probe owner route')
        child=reader.json(ref['path'],ref['sha256']);started=reader.json(path/'started.json')
        out=reader.file(path/'stdout',keep=True);err=reader.file(path/'stderr',keep=True)
        require(child['status']=='finished' and type(child['pid']) is int and child['pid']==ref['pid']
            and child['parent_pid']==terminal['pid'] and child['parent_parent_pid']==terminal['parent_pid']
            and child['command']==commands[index] and child['cwd']==str(ROOT)
            and same(child['environment'],packet['passed_environment']) and child['signals']==[]
            and previous<=child['started_at']<=child['child_started_at']<=child['finished_at']
                <=child['observation_closed_at']<=proof['finished_at']
            and all(child.get(k) is None for k in ['error','publication_or_guard_error','child_may_remain_live']),
            'exact closed read-only probe association')
        require(started['status']=='running' and all(same(v,child[k]) for k,v in started.items() if k!='status'),
            'probe initial identity association')
        require(len(out)<=256*1024 and len(err)<=256*1024 and child['stdout_bytes']==len(out)
            and child['stderr_bytes']==len(err) and child['stdout_sha256']==digest(out)
            and child['stderr_sha256']==digest(err),'complete bounded probe raw readback')
        previous=child['observation_closed_at']
        if index==0:require(child['returncode']==1 and out==err==b'','lsof did not prove exact selected paths unused')
        else:
            require(child['returncode'] in [0,1] and not err
                and (child['returncode']==0)==bool(out.strip()),'exact PID query status')
            found=set()
            for line in out.decode('utf-8',errors='strict').splitlines():
                parts=line.split();require(len(parts)>9 and parts[0].isdigit(),'full PID observation')
                pid=int(parts[0]);require(pid in pids and pid not in found and parts[3:8] not in pids[pid],
                    'old task-owned producer identity remains or unexpected PID');found.add(pid)
                reused.append(dict(pid=pid,observed_ps=line,historical_starts=pids[pid],
                    meaning='PID number reused; observed start differs. No process control.'))
    require(same(reused,proof['observed_reused_pids']),'complete reuse observations differ')
    return proof


def main(packet_sha,receipt_sha,execution_sha):
    require(all(type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v)
        for v in [packet_sha,receipt_sha,execution_sha,RUNTIME_AUDIT_SHA,RETIRE_SOURCE_SHA,NO_CONSUMER_SOURCE_SHA]),
        'actual immutable evidence/source pins remain unbound')
    require(Path.cwd()==ROOT and Path(sys.executable).resolve()==PYTHON and sys.dont_write_bytecode
        and not sys.flags.optimize and not OUTPUT.exists() and not OUTPUT.is_symlink(),'fixed fresh independent audit')
    started=time.time();monotonic=time.monotonic()
    def guard():
        require(time.monotonic()-monotonic<=600 and shutil.disk_usage(ROOT).free>=9*2**30,'bounded read-only audit floor/time')
    source=HERE/'recovery.py';raw=source.read_bytes()
    require(source.resolve(strict=True)==source and stat.S_ISREG(source.lstat().st_mode)
        and digest(raw)==RECOVERY_SOURCE_SHA,'qualified actual recovery reader source')
    r=types.ModuleType('_retirement_audit_recovery');r.__file__=str(source);exec(compile(raw,str(source),'exec'),r.__dict__)
    reader=r.Reader(guard);reader.file(source)
    packet=reader.json(PACKET,packet_sha);terminal=reader.json(WORK/'receipt.json',receipt_sha)
    outer=reader.json(OUTER/'record.json',execution_sha)
    require(packet['target']==str(TARGET) and packet['proposal_sha256']==r.PROPOSAL_SHA
        and packet['historical_source_stage03_wire_sha256']==r.STAGE_INPUTS_SHA
        and packet['runtime_audit']==dict(path=str(RUNTIME_AUDIT),sha256=RUNTIME_AUDIT_SHA)
        and same(packet['recovery'],RECOVERY) and same(packet['recovery_execution'],RECOVERY_EXECUTION),
        'exact prepared scope/recovery/rehearsal bindings')
    require(same(packet['environment_policy'],dict(passed_environment=packet['passed_environment'],
        allowed_additions=[{},CF_ADDITION],validation=ENVIRONMENT_VALIDATION)),
        'exact no-normalization startup environment policy')
    audit_initial_environment=environment_observation(packet['passed_environment'],INITIAL_ENVIRONMENT)
    require(set(packet['preparation_environment'])=={'initial','before_helpers','after_helpers'},'complete preparation environment observations')
    for observation in packet['preparation_environment'].values():
        require(same(observation,environment_observation(packet['passed_environment'],observation['observed'])),
            'exact preparation passed/observed/additions changed')
    require(set(terminal['environment_observations'])=={'initial','before_helpers','after_helpers',
        'after_remover_imports','before_removal','after_removal'},'complete actual controller environment observations')
    for observation in terminal['environment_observations'].values():
        require(same(observation,environment_observation(packet['passed_environment'],observation['observed'])),
            'exact controller passed/observed/additions changed')
    require(same(packet['caps'],dict(entry_gib=9,live_gib=9,floor_gib=8,entry_reserve_bytes=16*2**20,
        wait_seconds=600,wall_seconds=600,cpu_seconds=300,file_bytes=16*2**20,retained_bytes=16*2**20))
        and outer['canonical_lock']=='/Users/danluu/dev/rust-interp/.work/benchmark.lock'
        and outer['wait_seconds']==600 and outer['observation_seconds']==1250
        and terminal['free_bytes_before']>=9*2**30+16*2**20
        and terminal['free_bytes_after']>=9*2**30,'unchanged actual admission and finite bounds')
    for name,row in packet['protected_files'].items():
        require(not Path(name).is_relative_to(TARGET),'historical removed rows cannot be current protected inputs')
        reader.file(name,row)
    validation=reader.json(ENVIRONMENT_VALIDATION['path'],ENVIRONMENT_VALIDATION['sha256'])
    require(validation['status']=='observed-read-only-python-startup-environment' and validation['returncode']==0
        and validation['passed_environment']==packet['passed_environment'] and validation['added']==CF_ADDITION
        and validation['changed']==validation['removed']=={},'actual previously validated optional macOS addition')
    require(reader.records[str(HERE/'retire.py')]['sha256']==RETIRE_SOURCE_SHA
        and reader.records[str(HERE/'no_consumer.py')]['sha256']==NO_CONSUMER_SOURCE_SHA,'reviewed final actual controller/adapter')
    require(outer['status']=='finished' and outer['returncode']==0 and outer['phase']=='retire'
        and outer['receipt_sha256']==receipt_sha and outer['pid']==terminal['pid'] and outer['parent_pid']==terminal['parent_pid']
        and outer['command']==[str(PYTHON),'-B',str(HERE/'retire.py'),'--inputs-sha256',packet_sha]
        and outer['cwd']==str(ROOT) and same(outer['environment'],packet['passed_environment'])
        and outer['signals']==[] and outer['canonical_owner']=='child'
        and outer['started_at']<=outer['admitted_at']<=outer['launch_requested_at']<=terminal['started_at']
            <=terminal['admitted_at']<=terminal['finished_at']<=terminal['canonical_released_at']
            <=outer['finished_at']<=outer['observation_closed_at']
        and outer['launch_requested_at']<=outer['child_started_at']<=outer['finished_at']
        and outer['actual_canonical_released_at']==terminal['canonical_released_at']
        and all(outer.get(k) is None for k in ['error','publication_error','capacity_violation','child_may_remain_live']),
        'explicit successful controller and outer closure')
    require(terminal['status']=='passed' and terminal['packet_sha256']==packet_sha
        and all(type(terminal[k]) is int and terminal[k]==v for k,v in
            dict(removed_files=21,preserved_files=40,complete_durable_events=63,removed_directories=0,
                chmod_operations=0,workload_children=0,allocation_credit_bytes=0).items())
        and terminal['original61_manifest_unchanged'] is True,'actual exact retired scope, no phase relabel')
    for stream in ['stdout','stderr']:
        data=reader.file(OUTER/stream,keep=True);require(not data and digest(data)==outer[stream+'_sha256'],'empty actual controller raw')
    for name,sha in outer['source_sha256'].items():
        require('/' not in name and reader.file(OUTER/'source'/name)['sha256']==sha,'complete saved outer source')
        if name in ['recovery.py','retire.py','no_consumer.py','prepare_retirement.py']:
            require(reader.records[str(HERE/name)]['sha256']==sha,'saved source and protected source differ')
    require(reader.file(OUTER/'source/execute_retirement.py')['sha256']==outer['wrapper_sha256']
        and reader.file(OUTER/'source/owned_stage.py')['sha256']==outer['owned_sha256'],'saved wrapper/helper bindings')
    recovered=reader.json(RECOVERY['path'],RECOVERY['sha256'])
    recovery_execution=reader.json(RECOVERY_EXECUTION['path'],RECOVERY_EXECUTION['sha256'])
    require(same(recovered,packet['recovery_verification']) and recovered['full_current_copy_original_witness_bytes'] is True
        and recovered['archive']['full_member_readback'] is recovered['archive']['full_gzip_eof'] is True
        and recovered['retirement_authorized'] is False and recovery_execution['status']=='finished'
        and recovery_execution['returncode']==0 and recovery_execution['result_sha256']==RECOVERY['sha256']
        and recovery_execution['finished_at']<=recovery_execution['canonical_released_at']<=terminal['started_at'],
        'actual complete pre-retirement archive recovery and closure')
    rehearsal=reader.json(RUNTIME_AUDIT,RUNTIME_AUDIT_SHA)
    require(same(rehearsal,packet['runtime_qualification']) and rehearsal['status']=='verified-strict-callback-rehearsal'
        and rehearsal['runtime_admission'] is False and rehearsal['retirement_authorized'] is False
        and rehearsal['bootstrap_policy']=='continued-catalog-before-reader'
        and rehearsal['no_live_api_virtualization'] is True
        and rehearsal['proposal_sha256']==r.PROPOSAL_SHA
        and rehearsal['historical_source_stage03_wire_sha256']==r.STAGE_INPUTS_SHA
        and all(type(rehearsal[k]) is int and rehearsal[k]==v for k,v in
            dict(complete_original_rows=109343,current_context_rows=109322,historical_copies=21).items()),
        'separate actual current-reader rehearsal required')
    proposal,full,manifest,catalog=r.metadata(reader)
    require(same(reader.json(WORK/'admitted-inventory.json'),proposal['complete_inventory']),'complete original61 admitted inventory')
    transition=reader.json(WORK/'transition.json')
    require(same(transition,dict(proposal_sha256=r.PROPOSAL_SHA,selected=proposal['selected'],
        runtime_audit=packet['runtime_audit'],recovery=RECOVERY,historical_identities_remain_historical=True,
        removed_directories=0)),'exact intended transition')
    raw=reader.file(WORK/'deleted.jsonl',keep=True)
    require(digest(raw)==terminal['ledger_sha256'],'actual durable ledger digest')
    remaining=ledger(raw,proposal,terminal)
    require(same(remaining,reader.json(WORK/'remaining-inventory.json')),'independent full remaining inventory equality')
    require(same(terminal['ledger'],dict(events=63,unlinked=[str(TARGET/n) for n in proposal['selected']],
        uncertain_intents=[],validated=21,readback_error=None)),'no uncertain or omitted unlink')
    r.target_inventory(reader,remaining)
    require(same(r.identity(TARGET.parent),proposal['outer_parent_identity']),'unchanged outer target parent')
    witnesses=[]
    for item in proposal['recovery']:
        path=item['retention_entry']['source'];reader.file(path,full[path])
        path=item['physical_witness'];blob=catalog[path]['blob']
        witnesses.append(reader.gzip(path,full[path],blob['logical_sha256'],blob['logical_bytes']))
    proof=no_consumer(reader,packet,proposal,terminal)
    first=json.loads(raw.splitlines()[0])['time']
    require(0<=first-proof['finished_at']<=30,'fresh exact consumer observations immediately preceded removal')
    expected={'receipt.json','admitted-inventory.json','transition.json','deleted.jsonl','remaining-inventory.json','no-consumer-proof.json'}
    for label in ['selected-paths','closed-owner-pids']:
        expected.update('no-consumer/'+label+'/'+n for n in ['started.json','receipt.json','stdout','stderr'])
    actual=set();directories=set();entries=0
    for p in WORK.rglob('*'):
        entries+=1;guard();require(entries<=256,'finite closed evidence entries')
        require(not p.is_symlink(),'no extra symlink in actual evidence')
        if p.is_file():actual.add(str(p.relative_to(WORK)))
        elif p.is_dir():directories.add(str(p.relative_to(WORK)))
        else:raise RuntimeError('nonordinary evidence entry')
    require(actual==expected and directories=={'no-consumer','no-consumer/selected-paths','no-consumer/closed-owner-pids'},
        'complete closed actual retirement file/directory membership')
    outer_expected={'record.json','stdout','stderr','source/execute_retirement.py','source/owned_stage.py'}
    outer_expected.update('source/'+name for name in outer['source_sha256'])
    outer_files=set();outer_dirs=set();entries=0
    for p in OUTER.rglob('*'):
        entries+=1;guard();require(entries<=256 and not p.is_symlink(),'bounded ordinary closed outer evidence')
        if p.is_file():outer_files.add(str(p.relative_to(OUTER)))
        elif p.is_dir():outer_dirs.add(str(p.relative_to(OUTER)))
        else:raise RuntimeError('nonordinary outer evidence')
    require(outer_files==outer_expected and outer_dirs=={'source'},'complete outer source/raw/record membership')
    for path,row in reader.records.items():require(same(r.identity(path),row['identity']),'audited current input changed before return')
    report=dict(status='verified-exact-proof-copy-retirement',started_at=started,finished_at=time.time(),
        pid=os.getpid(),parent_pid=os.getppid(),verifier_sha256=digest(Path(__file__).read_bytes()),
        proposal_sha256=r.PROPOSAL_SHA,historical_source_stage03_wire_sha256=r.STAGE_INPUTS_SHA,
        receipt_sha256=receipt_sha,packet_sha256=packet_sha,execution_sha256=execution_sha,ledger_sha256=terminal['ledger_sha256'],
        recovery=RECOVERY,runtime_rehearsal=dict(path=str(RUNTIME_AUDIT),sha256=RUNTIME_AUDIT_SHA),
        helper40_audit=dict(path=str(r.CONTROLS_AUDIT),sha256=r.CONTROLS_AUDIT_SHA),remover_sha256=REMOVER_SHA,
        selected_paths=sorted(str(TARGET/n) for n in proposal['selected']),removed_files=21,preserved_files=40,
        removed_directories=0,chmod_operations=0,durable_events=63,current_context_rows=109322,
        full_ledger_replay=True,source_witness_readback=True,preserved40_readback=True,
        original_retained_inputs_sha256='587139f94eeb3d6ccac398f9c12ec65f4eb33b0e79b40e513678826cdd9f2c0d',
        no_consumer_proof_sha256=terminal['no_consumer_proof_sha256'],read_only_probe_children=2,
        historical_identities_are_not_current_filesystem_objects=True,witnesses=witnesses,
        audit_environment=dict(initial=audit_initial_environment,final=environment_observation(packet['passed_environment'])),
        allocation_sample=dict(free_bytes_before=terminal['free_bytes_before'],free_bytes_after=terminal['free_bytes_after'],
            estimated_or_hypothetical_credit_bytes=0),current_file_records=reader.records,total_read_bytes=reader.bytes)
    raw=encoded(report);require(len(raw)<=16*2**20,'bounded independent report')
    with OUTPUT.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    require(OUTPUT.read_bytes()==raw,'independent report readback')
    print(json.dumps(dict(status=report['status'],report=str(OUTPUT),sha256=digest(raw)),sort_keys=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True)
    parser.add_argument('--receipt-sha256',required=True);parser.add_argument('--execution-sha256',required=True)
    args=parser.parse_args();main(args.inputs_sha256,args.receipt_sha256,args.execution_sha256)
