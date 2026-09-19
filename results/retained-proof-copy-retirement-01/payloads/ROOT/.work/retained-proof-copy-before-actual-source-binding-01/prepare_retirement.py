"""Unrun finite read-only packet preparation for the exact 21-copy retirement.

Only source/evidence pins are future bindings. This program cannot remove a file,
invoke a process, or manufacture an owner acknowledgment or rehearsal result.
The containing dispatcher owns canonical admission and the existing 16/9 bounds.
"""
import os
INITIAL_ENVIRONMENT=dict(os.environ)
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
import time
import types

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PACKET=HERE/'plan-01.json'
TARGET=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hir-options-hash-run-make-01/retained')
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
RECOVERY=dict(path=str(ROOT/'.work/retained-proof-copy-recovery-01.json'),sha256='b671db7b48989f16ebcecbe67c0396abf89a5ec59e937cecd29edcb7c682f251')
RECOVERY_EXECUTION=dict(path=str(ROOT/'.work/retained-proof-copy-recovery-execution-01/record.json'),sha256='85ce36c2e82e112a03cb18e6d429a3aa5b04c24caa7c3a279e884c9bb93e1862')
RECOVERY_SOURCE_SHA='572907bc8ebd093b33cbe82906e8ed5c1409eadd9de3adbe27bf8c3604009474'
RUNTIME_AUDIT=ROOT/'.work/runtime04-historical-copy-reader-independent-verification-05.json'
RUNTIME_AUDIT_SHA=None
DECLARATIONS=None  # Exact {path,sha256} to real owner acknowledgments/consumer declarations.
SOURCE_BINDINGS=None  # Final retire/no_consumer; this preparer is pinned by its outer.
ENV=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
    PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
CAPS=dict(entry_gib=9,live_gib=9,floor_gib=8,entry_reserve_bytes=16*2**20,
    wait_seconds=600,wall_seconds=600,cpu_seconds=300,file_bytes=16*2**20,retained_bytes=16*2**20)


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


def raw_source(path,digest):
    before=path.lstat();raw=path.read_bytes();after=path.lstat()
    require(path.resolve(strict=True)==path and stat.S_ISREG(before.st_mode) and len(raw)<=2**20
        and all(getattr(before,'st_'+k)==getattr(after,'st_'+k) for k in
            ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink'])
        and hashlib.sha256(raw).hexdigest()==digest,'exact ordinary reviewed source required')
    return raw


def definitions(name,path,digest):
    raw=raw_source(path,digest);module=types.ModuleType(name);module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    require(raw_source(path,digest)==raw,'reviewed source changed during loading')
    return module


def main():
    require(type(RUNTIME_AUDIT_SHA) is str and len(RUNTIME_AUDIT_SHA)==64
        and type(DECLARATIONS) is dict and set(DECLARATIONS)=={'path','sha256'}
        and type(SOURCE_BINDINGS) is dict and set(SOURCE_BINDINGS)=={'retire.py','no_consumer.py'},
        'future rehearsal/declaration/final source evidence is unbound')
    require(Path.cwd()==ROOT and Path(sys.executable).resolve()==PYTHON
        and sys.dont_write_bytecode and not sys.flags.optimize,'fixed read-only preparation route')
    require(not PACKET.exists() and not PACKET.is_symlink(),'fresh single-use retirement packet required')
    initial_environment=environment_observation(ENV,INITIAL_ENVIRONMENT)
    before_helpers=environment_observation(ENV)
    started=time.monotonic()
    def guard():
        require(time.monotonic()-started<=600,'bounded packet preparation time')
        require(shutil.disk_usage(ROOT).free>=9*2**30,'read-only preparation live floor')
    r=definitions('_retirement_prepare_recovery',HERE/'recovery.py',RECOVERY_SOURCE_SHA)
    reader=r.Reader(guard)
    environment_validation=reader.json(ENVIRONMENT_VALIDATION['path'],ENVIRONMENT_VALIDATION['sha256'])
    require(environment_validation['status']=='observed-read-only-python-startup-environment'
        and environment_validation['returncode']==0 and environment_validation['passed_environment']==ENV
        and environment_validation['added']==CF_ADDITION
        and environment_validation['changed']==environment_validation['removed']=={},'exact validated optional macOS startup addition')
    p,full,manifest,catalog=r.metadata(reader)
    recovered=reader.json(RECOVERY['path'],RECOVERY['sha256'])
    execution=reader.json(RECOVERY_EXECUTION['path'],RECOVERY_EXECUTION['sha256'])
    require(recovered['status']=='verified-read-only-exact-copy-recovery'
        and recovered['recovery_source_sha256']==RECOVERY_SOURCE_SHA
        and recovered['proposal_sha256']==r.PROPOSAL_SHA and recovered['full_current_copy_original_witness_bytes'] is True
        and recovered['complete_frozen_input_readback'] is True and recovered['retirement_authorized'] is False
        and recovered['child_processes']==recovered['compiler_calls']==0
        and execution['status']=='finished' and execution['returncode']==0
        and execution['result_path']==RECOVERY['path'] and execution['result_sha256']==RECOVERY['sha256']
        and execution['pid']==recovered['pid'] and execution['parent_pid']==recovered['parent_pid']
        and execution['child_started_at']<=recovered['started_at']<=recovered['finished_at']
            <=execution['finished_at']<=execution['canonical_released_at'],'complete actual closed recovery binding')
    for path,row in recovered['current_file_records'].items():reader.file(path,row)
    # Retain the complete finite recovery execution closure, including sources.
    e=Path(RECOVERY_EXECUTION['path']).parent
    for name in ['stdout','stderr','source/recovery.py','source/prepare_recovery.py',
                 'source/recover.py','source/execute_recovery.py','source/owned_stage.py']:
        reader.file(e/name)
    require(reader.records[str(e/'stdout')]['sha256']==execution['stdout_sha256']
        and reader.records[str(e/'stderr')]['sha256']==execution['stderr_sha256']
        and (e/'stderr').stat().st_size==0,'recovery raw closure differs')
    runtime=reader.json(RUNTIME_AUDIT,RUNTIME_AUDIT_SHA)
    require(runtime['status']=='verified-strict-callback-rehearsal'
        and runtime['runtime_admission'] is False and runtime['retirement_authorized'] is False
        and runtime['proposal_sha256']==r.PROPOSAL_SHA
        and runtime['historical_source_stage03_wire_sha256']==r.STAGE_INPUTS_SHA
        and runtime['bootstrap_policy']=='continued-catalog-before-reader'
        and runtime['no_live_api_virtualization'] is True
        and all(type(runtime[k]) is int and runtime[k]==v for k,v in
            dict(complete_original_rows=109343,current_context_rows=109322,historical_copies=21).items()),
        'actual strict-callback rehearsal required; no production-admission substitution')
    decl=reader.json(DECLARATIONS['path'],DECLARATIONS['sha256'])
    require(set(decl)=={'status','proposal_sha256','owned_consumer_roots','no_consumer'}
        and decl['status']=='explicit-task-owner-no-consumer-declaration'
        and decl['proposal_sha256']==r.PROPOSAL_SHA,'exact no-consumer declaration schema')
    roots=decl['owned_consumer_roots']
    owners=[ROOT,Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918'),
        Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918'),
        Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918'),
        Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')]
    require(type(roots) is list and 0<len(roots)<=16 and roots==sorted(set(roots))
        and all(Path(n).is_absolute() and '..' not in Path(n).parts
            and any(Path(n).is_relative_to(owner/'.work') or Path(n).is_relative_to(owner/'experiments') for owner in owners)
            for n in roots),'explicit bounded task-owned consumer roots')
    spec=decl['no_consumer']
    require(set(spec)=={'acknowledgments','current_consumers','closed_owners','closed_metadata','pending_absences','executors','environment'},
        'complete explicit consumer fields required')
    require(len(spec['current_consumers'])<=32 and len(spec['closed_owners'])<=64,'finite current/closed consumer declarations')
    for ref in spec['acknowledgments'].values():reader.json(ref['path'],ref['sha256'])
    for row in spec['closed_owners']:reader.json(row['receipt']['path'],row['receipt']['sha256'])
    require(type(spec['closed_metadata']) is list and 0<len(spec['closed_metadata'])<=16,'finite separately associated closure metadata')
    for group in spec['closed_metadata']:
        for key in ['terminal','outer','launch','audit','launcher','result','execution']:
            if key in group:reader.json(group[key]['path'],group[key]['sha256'])
        for key in ['stdout','stderr']:
            if key in group:
                row=reader.file(group[key]['path'])
                require(row['size']<=256*1024 and row['sha256']==group[key]['sha256'],'bounded closed-failure raw binding')
    for row in spec['current_consumers']:
        wire=reader.json(row['inputs']['path'],row['inputs']['sha256'])
        require('base_inputs' not in wire,'broader inherited-proof consumer requires a separate reviewed schema')
        if 'file_table_base' in wire:
            ref=wire['file_table_base'];require(set(ref)=={'path','sha256'},'exact nonrecursive current file-table reference')
            reader.json(ref['path'],ref['sha256'])
    require(set(spec['executors'])=={'/usr/sbin/lsof','/bin/ps'} and spec['environment']==ENV,
        'only exact fixed read-only executors and passed environment')
    for name,row in spec['executors'].items():reader.file(name,row)
    retire=definitions('_retirement_prepared_controller',HERE/'retire.py',SOURCE_BINDINGS['retire.py'])
    consumer=definitions('_retirement_prepared_no_consumer',HERE/'no_consumer.py',SOURCE_BINDINGS['no_consumer.py'])
    require(retire.RECOVERY_SOURCE_SHA==RECOVERY_SOURCE_SHA and retire.RUNTIME_AUDIT_SHA==RUNTIME_AUDIT_SHA
        and retire.RECOVERY_REPORT==RECOVERY['path'] and retire.RECOVERY_REPORT_SHA==RECOVERY['sha256']
        and retire.RECOVERY_EXECUTION==RECOVERY_EXECUTION['path'] and retire.RECOVERY_EXECUTION_SHA==RECOVERY_EXECUTION['sha256']
        and retire.NO_CONSUMER_SOURCE==str(HERE/'no_consumer.py')
        and retire.NO_CONSUMER_SOURCE_SHA==SOURCE_BINDINGS['no_consumer.py'] and r.same(retire.CAPS,CAPS),
        'final controller evidence bindings differ')
    temporary=dict(no_consumer=spec,owned_consumer_roots=roots,passed_environment=ENV)
    consumer.MAX_READ_BYTES=min(consumer.MAX_READ_BYTES,r.LIMITS['maximum_total_read_bytes']-reader.bytes)
    consumer.STARTED=time.monotonic();consumer.GUARD=guard
    consumer.declarations(temporary,sorted(str(TARGET/n) for n in p['selected']),time.time())
    reader.tick(consumer.READ_BYTES)
    reader.json(r.CONTROLS_AUDIT,r.CONTROLS_AUDIT_SHA)
    control=p['proposed_remover']
    for key in ['control_audit','control_receipt','control_input']:reader.reference(control[key])
    tested=reader.reference(control['control_input'])
    for name,row in tested['files'].items():
        identity=dict(zip(['dev','ino','mode','size','mtime_ns','ctime_ns','nlink'],row['stamp'],strict=True))
        reader.file(name,dict(identity=identity,size=identity['size'],sha256=row['sha256']))
    reader.file(retire.REMOVER);require(reader.records[str(retire.REMOVER)]['sha256']==retire.REMOVER_SHA,'qualified remover changed')
    reader.file(retire.OWNED);require(reader.records[str(retire.OWNED)]['sha256']==retire.OWNED_SHA,'qualified admission helper changed')
    for name in ['recovery.py','retire.py','no_consumer.py','prepare_retirement.py']:reader.file(HERE/name)
    reader.file(PYTHON)
    require(r.identity(TARGET.parent)==p['outer_parent_identity'],'target outer directory changed')
    r.target_inventory(reader,p['complete_inventory'])
    protected={name:row for name,row in reader.records.items() if not Path(name).is_relative_to(TARGET)}
    require(len(protected)<=512 and sum(row['size'] for row in protected.values())<=384*2**20,
        'finite immutable retirement input closure')
    for name,row in reader.records.items():require(r.same(r.identity(name),row['identity']),'preparation input changed')
    packet=dict(status='reviewed-single-use-retirement',target=str(TARGET),proposal_sha256=r.PROPOSAL_SHA,
        caps=CAPS,passed_environment=ENV,
        environment_policy=dict(passed_environment=ENV,allowed_additions=[{},CF_ADDITION],validation=ENVIRONMENT_VALIDATION),
        preparation_environment=dict(initial=initial_environment,before_helpers=before_helpers,after_helpers=environment_observation(ENV)),
        runtime_audit=dict(path=str(RUNTIME_AUDIT),sha256=RUNTIME_AUDIT_SHA),runtime_qualification=runtime,
        recovery=RECOVERY,recovery_verification=recovered,recovery_execution=RECOVERY_EXECUTION,
        no_consumer_source=dict(path=str(HERE/'no_consumer.py'),sha256=SOURCE_BINDINGS['no_consumer.py']),
        declarations=DECLARATIONS,no_consumer=spec,owned_consumer_roots=roots,protected_files=protected,
        selected_paths=sorted(str(TARGET/n) for n in p['selected']),selected_files=21,preserved_files=40,
        removed_directories=0,chmod_operations=0,expected_durable_events=63,
        historical_source_stage03_wire_sha256=r.STAGE_INPUTS_SHA,source_bindings=SOURCE_BINDINGS)
    raw=r.encoded(packet);require(len(raw)<=16*2**20,'retirement packet output bound')
    with PACKET.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    require(PACKET.read_bytes()==raw,'packet full readback')
    fd=os.open(HERE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
    print(json.dumps(dict(status='prepared-unrun-exact-copy-retirement',path=str(PACKET),
        sha256=hashlib.sha256(raw).hexdigest(),files=len(protected),logical_bytes=sum(row['size'] for row in protected.values())),sort_keys=True))


if __name__=='__main__':main()
