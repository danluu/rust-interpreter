"""Source-only exact-file retirement wrapper. All future gates are unbound.

The old qualified remover is imported only after its current bytes and actual
six-control association are checked. No directories or permissions are changed.
The consumer adapter is deliberately absent/unbound: a later reviewed exact
protocol must perform fresh read-only observations under this canonical lock.
"""
import os
INITIAL_ENVIRONMENT=dict(os.environ)
import argparse
import hashlib
import json
from pathlib import Path
import resource
import shutil
import stat
import sys
import time
import types

HERE=Path(__file__).resolve().parent
R=HERE.parents[1]
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
WORK=R/'.work/retained-proof-copy-retirement-01'
EXECUTION=R/'.work/retained-proof-copy-retirement-execution-01'
PACKET=HERE/'plan-01.json'
TARGET=O/'.work/hir-options-hash-run-make-01/retained'
REMOVER=O/'experiments/hir-options-hash-intermediate-retirement/fd_remove.py'
REMOVER_SHA='834135905025ac03369a7b224daf995dbc29eb2579d06e72baba5db1a71b6960'
OWNED=X/'experiments/stable-cgu/owned_stage.py'
OWNED_SHA='7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e'
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
CANONICAL=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
RUNTIME_AUDIT=R/'.work/runtime04-historical-copy-reader-independent-verification-05.json'
# Fill these only after source review, actual independent qualification and a
# concrete single-use packet review. None is not an approval or a wildcard.
RECOVERY_SOURCE_SHA=None
RUNTIME_AUDIT_SHA=None
RECOVERY_REPORT=None
RECOVERY_REPORT_SHA=None
RECOVERY_EXECUTION=None
RECOVERY_EXECUTION_SHA=None
NO_CONSUMER_SOURCE=None
NO_CONSUMER_SOURCE_SHA=None
CAPS=dict(entry_gib=9,live_gib=9,floor_gib=8,entry_reserve_bytes=16*2**20,
          wait_seconds=600,wall_seconds=600,cpu_seconds=300,file_bytes=16*2**20,
          retained_bytes=16*2**20)

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
def digest(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()
def same(a,b):return encoded(a)==encoded(b)
def ordinary_bytes(path,expected,maximum=64*2**20):
    path=Path(path);s=path.lstat()
    require(path.resolve(strict=True)==path and stat.S_ISREG(s.st_mode) and s.st_size<=maximum,'ordinary bounded pinned source')
    raw=path.read_bytes();after=path.lstat()
    require(all(getattr(after,'st_'+k)==getattr(s,'st_'+k) for k in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns'])
            and digest(raw)==expected,'pinned source differs')
    return raw
def load(name,path,expected):
    raw=ordinary_bytes(path,expected);module=types.ModuleType(name);module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    require(ordinary_bytes(path,expected)==raw,'source changed during load')
    return module
def save(path,value):
    raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();require(len(raw)<=CAPS['file_bytes'],'bounded evidence document')
    with path.open('x') as out:out.write(raw.decode());out.flush();os.fsync(out.fileno())
    require(path.read_bytes()==raw,'evidence readback')

def replay(ledger,proposal):
    raw=ledger.read_bytes();require(len(raw)<=2**20 and (not raw or raw.endswith(b'\n')),'bounded complete ledger lines')
    events=[json.loads(line) for line in raw.splitlines()]
    require(len(events)==63,'exact 63 durable events required')
    rows=json.loads(json.dumps(proposal['complete_inventory']));remaining=set(rows)-{'.'};last=0
    for index,name in enumerate(proposal['selected']):
        intent,unlinked,validated=events[index*3:index*3+3];before=rows[name]['identity'];parent=rows['.']['identity']
        common=dict(path=str(TARGET/name),relative=name,before=before,sha256=rows[name]['sha256'],parent_before=parent)
        for event,label in [(intent,'intent'),(unlinked,'unlinked')]:
            require(set(event)==set(common)|{'event','time'} and same({k:event[k] for k in common},common)
                    and event['event']==label and type(event['time']) in (int,float) and event['time']>=last,'exact ordered intent/unlinked event')
            last=event['time']
        require(set(validated)=={'path','relative','event','after','parent_after','time'}
                and validated['path']==str(TARGET/name) and validated['relative']==name and validated['event']=='validated'
                and type(validated['time']) in (int,float) and validated['time']>=last,'exact validation event')
        last=validated['time'];after=validated['after'];parent_after=validated['parent_after']
        require(set(after)==set(before) and all(type(v) is int and v>=0 for v in after.values())
                and all(after[k]==before[k] for k in ['dev','ino','mode','size','mtime_ns']) and after['nlink']==0,'held inode unlink transition')
        require(set(parent_after)==set(parent) and all(type(v) is int and v>=0 for v in parent_after.values())
                and all(parent_after[k]==parent[k] for k in ['dev','ino','mode']),'retained directory transition')
        require(not (TARGET/name).exists() and not (TARGET/name).is_symlink(),'retired path remains')
        remaining.remove(name);del rows[name];rows['.']['identity']=parent_after
    require(len(remaining)==40 and sorted(os.listdir(TARGET))==sorted(remaining),'exact 40 preserved names')
    return rows

def ledger_status(path):
    result=dict(events=0,unlinked=[],uncertain_intents=[],validated=0,readback_error=None)
    try:
        if not path.exists():return result
        raw=path.read_bytes();require(len(raw)<=2**20,'ledger cap')
        rows=[]
        for line in raw.splitlines(keepends=True):require(line.endswith(b'\n'),'partial durable line');rows.append(json.loads(line))
        result['events']=len(rows);result['unlinked']=[r['path'] for r in rows if r['event']=='unlinked']
        result['uncertain_intents']=[r['path'] for r in rows if r['event']=='intent' and r['path'] not in result['unlinked']]
        result['validated']=sum(r['event']=='validated' for r in rows)
    except BaseException as error:result['readback_error']=repr(error)
    return result

def main(packet_sha):
    require(type(packet_sha) is str and len(packet_sha)==64 and all(c in '0123456789abcdef' for c in packet_sha),
            'exact reviewed packet digest required')
    pins=[RECOVERY_SOURCE_SHA,RUNTIME_AUDIT_SHA,RECOVERY_REPORT,RECOVERY_REPORT_SHA,
          RECOVERY_EXECUTION,RECOVERY_EXECUTION_SHA,NO_CONSUMER_SOURCE,NO_CONSUMER_SOURCE_SHA]
    require(all(type(value) is str and value for value in pins),'unbound future evidence bindings: no retirement permitted')
    require(Path.cwd()==R and Path(sys.executable).resolve()==PYTHON and sys.dont_write_bytecode
            and not sys.flags.optimize,'fixed retirement execution route')
    packet=json.loads(ordinary_bytes(PACKET,packet_sha,16*2**20))
    require(packet['status']=='reviewed-single-use-retirement' and packet['target']==str(TARGET)
            and same(packet['caps'],CAPS) and packet['proposal_sha256']=='e0599d87ab842b9e18932fddb54bb63aaf850cd2366279f67507e875731b3481',
            'exact reviewed packet/caps/scope')
    require(packet['runtime_audit']==dict(path=str(RUNTIME_AUDIT),sha256=RUNTIME_AUDIT_SHA)
            and packet['recovery']==dict(path=RECOVERY_REPORT,sha256=RECOVERY_REPORT_SHA)
            and packet['no_consumer_source']==dict(path=NO_CONSUMER_SOURCE,sha256=NO_CONSUMER_SOURCE_SHA),'exact future proof bindings')
    require(same(packet['environment_policy'],dict(passed_environment=packet['passed_environment'],
        allowed_additions=[{},CF_ADDITION],validation=ENVIRONMENT_VALIDATION)),'exact optional startup environment policy')
    initial_environment=environment_observation(packet['passed_environment'],INITIAL_ENVIRONMENT)
    before_helpers=environment_observation(packet['passed_environment'])
    owned=load('_proof_copy_retirement_owned',OWNED,OWNED_SHA)
    require(owned.CANONICAL_LOCK==CANONICAL,'unchanged canonical lock')
    recovery=load('_proof_copy_recovery',HERE/'recovery.py',RECOVERY_SOURCE_SHA)
    require(not WORK.exists() and not WORK.is_symlink(),'fresh retirement evidence required')
    started=time.monotonic();admitted_monotonic=None
    receipt=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),
        packet_sha256=packet_sha,workload_children=0,removed_directories=0,chmod_operations=0,allocation_credit_bytes=0,
        environment_observations=dict(initial=initial_environment,before_helpers=before_helpers,
            after_helpers=environment_observation(packet['passed_environment'])))
    def capacity():
        require(time.monotonic()-started<=CAPS['wait_seconds']+CAPS['wall_seconds'],'bounded total observation')
        if admitted_monotonic is not None:
            require(time.monotonic()-admitted_monotonic<=CAPS['wall_seconds'],'bounded admitted retirement time')
        free=owned.disk(R,9)
        files=[]
        for root in [WORK,EXECUTION]:
            if root.exists():
                require(not root.is_symlink() and root.is_dir(),'ordinary exact evidence root')
                files.extend(root.rglob('*'))
        require(len(files)<=256 and all(not p.is_symlink() for p in files),'bounded aggregate evidence names')
        require(sum(p.stat().st_size for p in files if p.is_file())<=CAPS['retained_bytes'],'aggregate retained evidence bound')
        return free
    resource.setrlimit(resource.RLIMIT_CPU,(CAPS['cpu_seconds'],CAPS['cpu_seconds']))
    resource.setrlimit(resource.RLIMIT_FSIZE,(CAPS['file_bytes'],CAPS['file_bytes']))
    with owned.workload_lock(CANONICAL,600) as lockfd:
        admitted_monotonic=time.monotonic()
        free=capacity();require(free>=9*2**30+CAPS['entry_reserve_bytes'],'fresh retirement reserve')
        WORK.mkdir(mode=0o700);receipt.update(status='running',admitted_at=time.time(),free_bytes_before=free)
        def publish():owned.write(WORK/'receipt.json',receipt)
        publish();ledger=WORK/'deleted.jsonl'
        try:
            reader=recovery.Reader(capacity);p,full,manifest,catalog=recovery.metadata(reader)
            environment_validation=reader.json(ENVIRONMENT_VALIDATION['path'],ENVIRONMENT_VALIDATION['sha256'])
            require(environment_validation['status']=='observed-read-only-python-startup-environment'
                and environment_validation['returncode']==0
                and environment_validation['passed_environment']==packet['passed_environment']
                and environment_validation['added']==CF_ADDITION
                and environment_validation['changed']==environment_validation['removed']=={},'validated optional startup addition proof')
            # All protected packet rows exclude the exact mutable target tree.
            for path,row in packet['protected_files'].items():
                require(not Path(path).is_relative_to(TARGET),'target row cannot masquerade as protected immutable input')
                reader.file(path,row)
            require(reader.json(recovery.CONTROLS_AUDIT,recovery.CONTROLS_AUDIT_SHA)['status']=='verified','actual40 qualification required')
            runtime=reader.json(RUNTIME_AUDIT,RUNTIME_AUDIT_SHA)
            require(runtime['status']=='verified-strict-callback-rehearsal' and runtime['runtime_admission'] is False
                    and runtime['retirement_authorized'] is False and runtime['proposal_sha256']==recovery.PROPOSAL_SHA
                    and runtime['historical_source_stage03_wire_sha256']==recovery.STAGE_INPUTS_SHA
                    and type(runtime['complete_original_rows']) is int and runtime['complete_original_rows']==109343
                    and type(runtime['current_context_rows']) is int and runtime['current_context_rows']==109322
                    and type(runtime['historical_copies']) is int and runtime['historical_copies']==21
                    and runtime['bootstrap_policy']=='continued-catalog-before-reader'
                    and runtime['no_live_api_virtualization'] is True,'actual qualified runtime Reader/collector rehearsal required')
            require(same(runtime,packet['runtime_qualification']),'complete exact runtime qualification proof')
            recovered=reader.json(RECOVERY_REPORT,RECOVERY_REPORT_SHA);execution=reader.json(RECOVERY_EXECUTION,RECOVERY_EXECUTION_SHA)
            require(recovered['status']=='verified-read-only-exact-copy-recovery' and recovered['proposal_sha256']==recovery.PROPOSAL_SHA
                    and recovered['recovery_source_sha256']==RECOVERY_SOURCE_SHA
                    and recovered['full_current_copy_original_witness_bytes'] is True and recovered['retirement_authorized'] is False
                    and execution['status']=='finished' and execution['returncode']==0
                    and execution['result_sha256']==RECOVERY_REPORT_SHA
                    and execution['finished_at']<=execution['canonical_released_at'],'actual recovery and closed execution required')
            require(same(recovered,packet['recovery_verification']),'complete exact recovery report')
            for path,row in recovered['current_file_records'].items():reader.file(path,row)
            # Recheck all original/preserved copies and selected witnesses while
            # canonical admission is held; old archive had full recovery above.
            recovery.target_inventory(reader,p['complete_inventory'])
            for item in p['recovery']:
                reader.file(item['retention_entry']['source'],full[item['retention_entry']['source']])
                row=catalog[item['physical_witness']];reader.gzip(row['path'],full[row['path']],row['blob']['logical_sha256'],row['blob']['logical_bytes'])
            controls=reader.reference(p['proposed_remover']['control_audit']);terminal=reader.reference(p['proposed_remover']['control_receipt'])
            inputs=reader.reference(p['proposed_remover']['control_input'])
            require(controls['status']=='verified' and controls['receipt_sha256']==p['proposed_remover']['control_receipt']['sha256']
                    and terminal['status']=='passed' and terminal['controls_passed']==6
                    and terminal['inputs_sha256']==p['proposed_remover']['control_input']['sha256']
                    and inputs['files'][str(REMOVER)]['sha256']==REMOVER_SHA,'actual six qualified remover controls')
            remover=load('_proof_copy_qualified_remove_files',REMOVER,REMOVER_SHA)
            consumer=load('_proof_copy_no_consumer',Path(NO_CONSUMER_SOURCE),NO_CONSUMER_SOURCE_SHA)
            receipt['environment_observations']['after_remover_imports']=environment_observation(packet['passed_environment']);publish()
            # Future adapter owns the exact fresh read-only target probes,
            # closed-owner identities and acknowledged pending consumers. Its
            # source, schema, observations and full audit need separate review.
            proof=consumer.verify(packet=packet,proposal=p,output=WORK/'no-consumer',canonical_fd=lockfd,
                admitted_at=receipt['admitted_at'],guard=capacity)
            require(proof['status']=='verified-exact-no-consumer' and proof['proposal_sha256']==recovery.PROPOSAL_SHA
                    and proof['selected_paths']==sorted(str(TARGET/n) for n in p['selected'])
                    and proof['canonical_admission_pid']==os.getpid() and proof['no_signals'] is True
                    and proof['acknowledged_active_or_pending_readers']==[]
                    and receipt['admitted_at']<=proof['started_at']<=proof['finished_at']<=time.time()
                    and time.time()-proof['finished_at']<=30,'fresh exact no-consumer proof required')
            save(WORK/'no-consumer-proof.json',proof)
            recovery.target_inventory(reader,p['complete_inventory'])
            require(recovery.identity(TARGET.parent)==p['outer_parent_identity'],'target outer parent changed')
            save(WORK/'admitted-inventory.json',p['complete_inventory'])
            save(WORK/'transition.json',dict(proposal_sha256=recovery.PROPOSAL_SHA,selected=p['selected'],runtime_audit=packet['runtime_audit'],
                recovery=packet['recovery'],historical_identities_remain_historical=True,removed_directories=0))
            with ledger.open('xb') as stream:stream.flush();os.fsync(stream.fileno())
            receipt['environment_observations']['before_removal']=environment_observation(packet['passed_environment']);publish()
            try:remaining=remover.remove_files(TARGET,p['complete_inventory'],p['selected'],p['outer_parent_identity'],ledger,capacity)
            finally:receipt['ledger']=ledger_status(ledger);publish()
            require(same(remaining,replay(ledger,p)),'complete qualified removal/ledger equality')
            recovery.target_inventory(reader,remaining)
            require(recovery.identity(TARGET.parent)==p['outer_parent_identity'],'outer parent changed after exact file removal')
            for path,row in packet['protected_files'].items():reader.file(path,row)
            for item in p['recovery']:
                source=item['retention_entry']['source'];reader.file(source,full[source])
                witness=catalog[item['physical_witness']];reader.gzip(witness['path'],full[witness['path']],witness['blob']['logical_sha256'],witness['blob']['logical_bytes'])
            save(WORK/'remaining-inventory.json',remaining)
            for directory in [TARGET,TARGET.parent,WORK]:
                fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:os.fsync(fd)
                finally:os.close(fd)
            receipt.update(status='passed',removed_files=21,preserved_files=40,ledger_sha256=digest(ledger.read_bytes()),
                complete_durable_events=63,free_bytes_after=capacity(),original61_manifest_unchanged=True,
                no_consumer_proof_sha256=digest((WORK/'no-consumer-proof.json').read_bytes()))
            receipt['environment_observations']['after_removal']=environment_observation(packet['passed_environment'])
        except BaseException as error:receipt.update(status='failed',error=repr(error),ledger=ledger_status(ledger));raise
        finally:receipt['finished_at']=time.time();publish()
    receipt['canonical_released_at']=time.time();owned.write(WORK/'receipt.json',receipt)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True)
    main(parser.parse_args().inputs_sha256)
