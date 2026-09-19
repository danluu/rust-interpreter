"""Launch one reviewed preflight05 proposal and observe its detached supervisor to closure.

The launch digest is supplied only after concrete packet review. No provider,
compiler or controller starts before the phase-specific fresh 16 GiB entry check.
An observation timeout preserves the running task and reports it as unclosed.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from types import ModuleType, SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
SOURCE = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/hir-options-hash/runtime-installation-04')
CAPACITY = dict(entry_gib=16,stop_gib=9,floor_gib=8,
                combined_namespace_bytes=14*2**30,evidence_bytes=256*2**20)
MAXIMUM_OBSERVATION_SECONDS = 1800
MAXIMUM_WRAPPER_SECONDS = 30


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    path=Path(path)
    require(path.resolve(strict=True)==path and path.is_file() and not path.is_symlink()
            and path.stat().st_size<=64*2**20,'ordinary bounded launcher input')
    before=path.stat()
    with path.open('rb') as stream:
        result=hashlib.file_digest(stream,'sha256').hexdigest()
    after=path.stat()
    require(all(getattr(before,'st_'+key)==getattr(after,'st_'+key)
                for key in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']),'launcher input changed')
    return result


def read(path):
    path=Path(path);digest=sha(path);data=path.read_bytes()
    require(len(data)<=64*2**20 and hashlib.sha256(data).hexdigest()==digest,'launcher JSON changed')
    return json.loads(data)



ADAPTER = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01')
PROOF_ROOT = ADAPTER.parents[1]
STARTUP_CONTROL = PROOF_ROOT/'experiments/runtime-startup-environment-controls-01'
STARTUP_WORK = PROOF_ROOT/'.work/runtime-startup-environment-controls-01'
STARTUP_AUDIT = dict(path=str(PROOF_ROOT/'.work/runtime-startup-environment-controls-independent-verification-01.json'),
    sha256='016e80b8169e8da75a82d29cecb3be9c0dd3e89cd6deae90b50522b927fa88f0')
HASH_PLAN = dict(path=str(PROOF_ROOT/'experiments/hir-options-hash-driver-stage-03/plan.json'),
    sha256='24faa0611eacda26748727e443bef844c695c3ed362cda75b5aa60223e4d6055')
PREPARATION_LAUNCHER = HERE/'prepare_once.py'
RETRY_CONTROL = PROOF_ROOT/'experiments/runtime-preflight-retry-controls-05'
RETRY_WORK = PROOF_ROOT/'.work/runtime-preflight-retry-controls-05'
RETRY_AUDIT = PROOF_ROOT/'.work/runtime-preflight-retry-controls-independent-verification-05.json'
RETRY_SOURCES = ['entry.py', 'controller.py', 'audit_owner.py', 'routes.json',
                 'prepare.py', 'prepare_once.py', 'launch.py']
ROUTES_SHA = '893d6102741b5206a829e2f5e130614667140b1eacc09d0c55616f7311f82e6a'
POLICY_SHA = 'fbc563accfeebe2650902263ed9972031d37c84bc8c21986a3545ae4020d314d'
OWNER_SHA = 'f93dd25d4d58e3133d2737c718f6b4e41d1f37ad788f914f9ed2adf268fca595'


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def same(left,right):
    return encoded(left)==encoded(right)


def identity(path):
    value=Path(path).lstat()
    return {key:getattr(value,'st_'+key) for key in ['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']}


def read_bytes(path):
    path=Path(path);digest=sha(path);data=path.read_bytes()
    require(len(data)<=64*2**20 and hashlib.sha256(data).hexdigest()==digest,'bounded raw evidence changed')
    return data


def qualified_module(name,path,expected,files,*,dependencies=None):
    """Compile only exact authenticated source bytes, without an unchecked reread."""
    path=Path(path);row=files[str(path)]
    require(row['sha256']==expected and row['size']==path.stat().st_size
        and same(identity(path),row['identity']),'current selected qualified source differs')
    data=read_bytes(path);require(hashlib.sha256(data).hexdigest()==expected,'qualified source bytes differ')
    module=ModuleType('_runtime_preflight05_launch_'+name);module.__file__=str(path)
    missing=object();before={key:sys.modules.get(key,missing) for key in dependencies or {}}
    sys.modules.update(dependencies or {})
    try:
        exec(compile(data,str(path),'exec'),module.__dict__)
    finally:
        for key,value in before.items():
            if value is missing:sys.modules.pop(key,None)
            else:sys.modules[key]=value
    require(same(identity(path),row['identity']) and sha(path)==expected,'qualified module source changed at load')
    return module


def controls(*, source, work, audit_path, source_paths, test_paths, read_json, read_bytes, sha, identity):
    """Recheck actual bounded pure controls before loading their selected modules."""
    source, work = Path(source), Path(work)
    freeze = read_json(source/'inputs.json'); terminal = read_json(work/'receipt.json')
    result = read_json(work/'result.json'); audit = read_json(audit_path)
    require(type(freeze['files']) is dict and len(freeze['files']) <= 256, 'bounded control source closure required')
    for name, row in freeze['files'].items():
        stamp = identity(name)
        require([stamp[key] for key in ['dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink']] == row['stamp']
                and sha(name) == row['sha256'], 'actual control frozen file differs')
    for name, target in freeze['routes'].items():
        require(str(Path(name).resolve(strict=True)) == target, 'actual control route differs')
    require(all(str(path) in freeze['files'] for path in [*source_paths, *test_paths]),
            'selected audit source not tested')
    names = []
    for path in test_paths:
        path = Path(path)
        for cls in ast.parse(read_bytes(path), filename=str(path)).body:
            if isinstance(cls, ast.ClassDef):
                names.extend(path.stem+'.'+cls.name+'.'+method.name for method in cls.body
                             if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'))
    require(names and len(names) == len(set(names)) and sorted(names) == freeze['expected_names'] == result['expected_names']
            and sorted(names) == sorted(audit['exact_names']), 'actual source-derived control names differ')
    require(terminal['status'] == result['status'] == 'passed' and audit['status'] == 'verified'
            and type(terminal['controls_passed']) is int and type(result['tests_run']) is int
            and terminal['controls_passed'] == result['tests_run'] == audit['controls'] == len(names)
            and terminal['inputs_sha256'] == sha(source/'inputs.json')
            and terminal['result_sha256'] == audit['result_sha256'] == sha(work/'result.json')
            and audit['receipt_sha256'] == sha(work/'receipt.json'), 'passed actual control proof differs')
    require(all(type(result[key]) is int and result[key] == 0 for key in
                ['failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes', 'child_processes', 'compiler_calls']),
            'control failed or performed unexpected work')
    child_path = work/'command/receipt.json'; child = read_json(child_path)
    require(terminal['commands'] == [dict(path=str(child_path), pid=child['pid'], sha256=sha(child_path))]
            and child['status'] == 'finished' and child['returncode'] == 0
            and child['command'] == freeze['command'] and child['environment'] == freeze['environment']
            and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid'],
            'actual control child association differs')
    for stream in ['stdout', 'stderr']:
        require(sha(work/'command'/stream) == child[stream+'_sha256'] == audit['raw_sha256'][stream],
                'actual control raw differs')
    raw = read_bytes(work/'command/stderr').decode('utf-8', 'strict')
    observed = re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$', raw, re.M)
    require(not read_bytes(work/'command/stdout') and sorted(observed) == sorted(names)
            and re.search(r'^Ran '+str(len(names))+r' tests in [0-9.]+s\n\nOK\n$', raw, re.M),
            'actual control names/footer differ')
    return dict(controls=len(names), receipt_sha256=sha(work/'receipt.json'), result_sha256=sha(work/'result.json'),
                audit=dict(path=str(audit_path), sha256=sha(audit_path)))


def startup_admission(args,proposal,frozen,plan,packet,controller):
    """Admit the observed launch map using actual controls and closed preparation.

    No terminal is fabricated. The actual current prelaunch time is a stricter
    chronology bound than a future runtime start. The saved runtime auditor
    repeats the same owner validator against the real terminal start later.
    """
    require(same(proposal['environment'],frozen['launch_environment'])
        and same(proposal['environment'],plan['launch_environment']),
        'three explicit launch environments differ')
    require(sha(STARTUP_AUDIT['path'])==STARTUP_AUDIT['sha256'],'exact actual39 startup audit required')
    proof=controls(source=STARTUP_CONTROL,work=STARTUP_WORK,audit_path=STARTUP_AUDIT['path'],
        source_paths=[ADAPTER/'environment.py',ADAPTER/'audit_owner.py'],
        test_paths=[ADAPTER/'test_environment.py',ADAPTER/'test_audit_owner.py'],
        read_json=read,read_bytes=read_bytes,sha=sha,identity=identity)
    require(type(proof['controls']) is int and proof['controls']==39
        and same(proof['audit'],STARTUP_AUDIT),'complete actual startup qualification differs')
    tested=read(STARTUP_CONTROL/'inputs.json')
    for path,expected in [(ADAPTER/'environment.py',POLICY_SHA),(ADAPTER/'audit_owner.py',OWNER_SHA)]:
        name=str(path);row=frozen['files'][name];old=tested['files'][name]
        require(row['sha256']==old['sha256']==expected
            and same([row['identity'][key] for key in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']],old['stamp']),
            'packet policy must be the exact actual39 tested source')
    require(sha(HASH_PLAN['path'])==HASH_PLAN['sha256'],'fixed qualified workload source changed')
    wire=read(HASH_PLAN['path'])
    require(set(wire)=={'policy','member','reference','remainder','integrity'}
        and wire['policy']=='external-json-member-v1' and wire['member']=='metadata_plan',
        'qualified workload source envelope differs')
    workload=dict(wire['remainder']['environment']);workload['TMPDIR']=str(controller/'tmp')
    qualification=dict(proof,source=str(STARTUP_CONTROL),evidence=str(STARTUP_WORK))
    policy=qualified_module('environment',ADAPTER/'environment.py',POLICY_SHA,frozen['files'])
    require(sha(RETRY_AUDIT)==args.retry_audit_sha256,'exact completed retry audit required')
    retry_proof=controls(source=RETRY_CONTROL,work=RETRY_WORK,audit_path=RETRY_AUDIT,
        source_paths=[HERE/name for name in RETRY_SOURCES],test_paths=[HERE/'test_retry.py'],
        read_json=read,read_bytes=read_bytes,sha=sha,identity=identity)
    retry_tested=read(RETRY_CONTROL/'inputs.json')
    for name in RETRY_SOURCES:
        path=HERE/name;row=frozen['files'][str(path)];old=retry_tested['files'][str(path)]
        require(row['sha256']==old['sha256']
            and same([row['identity'][key] for key in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']],old['stamp']),
            'retry packet source must match its actual separate controls')
    retry_qualification=dict(retry_proof,source=str(RETRY_CONTROL),evidence=str(RETRY_WORK))
    owner=qualified_module('owner',HERE/'audit_owner.py',frozen['files'][str(HERE/'audit_owner.py')]['sha256'],
        frozen['files'],dependencies={'environment':policy})
    preparation=dict(path=str(ROOT/('.work/hir-options-hash-runtime-'+args.phase+'-preparation-execution-05/record.json')),
        sha256=args.preparation_sha256)
    preparation_launcher=dict(path=str(PREPARATION_LAUNCHER),sha256=args.preparation_launcher_sha256)
    context=SimpleNamespace(require=require,same=same,R=ROOT,
        phase_paths=lambda phase: dict(packet=HERE/(phase+'-plan-01')))
    admission_time=time.time()
    owner.startup_admission(plan,proposal,phase=args.phase,
        expected=dict(preparation=preparation,preparation_launcher=preparation_launcher),
        sha=sha,read_json=read,original=context,workload_environment=workload,
        validate_qualification=lambda actual:same(actual,qualification),
        validate_retry_qualification=lambda actual:same(actual,retry_qualification),runtime_started_at=admission_time)
    return dict(preparation=preparation,preparation_launcher=preparation_launcher,
        startup_controls=STARTUP_AUDIT,retry_controls=dict(path=str(RETRY_AUDIT),sha256=args.retry_audit_sha256),
        workload_source=HASH_PLAN,validated_before_launch_at=admission_time,
        chronology_scope='Actual prelaunch bound; no future terminal or runtime-start timestamp invented.')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase',choices=['preflight'],required=True)
    parser.add_argument('--launch-sha256',required=True)
    parser.add_argument('--launcher-sha256',required=True)
    parser.add_argument('--preparation-sha256',required=True)
    parser.add_argument('--preparation-launcher-sha256',required=True)
    parser.add_argument('--retry-audit-sha256',required=True)
    args=parser.parse_args();expected=args.launch_sha256;phase=args.phase
    require(all(re.fullmatch('[a-f0-9]{64}',value) for value in
        [args.preparation_sha256,args.preparation_launcher_sha256,args.retry_audit_sha256]),'actual preparation source/closure pins required')
    require(re.fullmatch('[a-f0-9]{64}',args.launcher_sha256)
            and sha(Path(__file__))==args.launcher_sha256,'exact independently reviewed launcher source required')
    packet=HERE/(phase+'-plan-01')
    LAUNCH=packet/'launch.json'
    WORK=ROOT/('.work/hir-options-hash-runtime-'+phase+'-launch-execution-05')
    OUTER=ROOT/('.work/experiments/hir-options-hash-runtime-'+phase+'-supervisor-05')
    CONTROLLER=ROOT/('.work/hir-options-hash-runtime-'+phase+'-05')
    require(Path.cwd() == ROOT and sys.dont_write_bytecode and not sys.flags.optimize,
            'fixed owner and unoptimized Python -B required')
    require(re.fullmatch('[a-f0-9]{64}', expected) and sha(LAUNCH) == expected,
            'reviewed launch digest required')
    proposal = read(LAUNCH)
    frozen = read(packet/'inputs.json')
    plan = read(packet/'plan.json')
    require(sha(HERE/'routes.json') == ROUTES_SHA
            and plan['attempt'] == dict(path=str(HERE/'routes.json'), sha256=ROUTES_SHA),
            'fixed reviewed preflight retry descriptor required')
    routes=read(HERE/'routes.json')
    require(routes['phase']==phase and routes['qualified_source']==str(SOURCE)
            and routes['attempt_source']==str(HERE) and routes['packet']==str(packet)
            and routes['work']==str(CONTROLLER) and routes['supervisor']==str(OUTER)
            and routes['launcher_execution']==str(WORK) and routes['capacity']==CAPACITY
            and routes['installation_entry_gib']==24, 'runtime retry routes differ')
    base = dict(path='/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/experiments/hir-options-hash-native-controls-03/inputs.json',
                sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d')
    integrity = frozen.get('file_table_integrity')
    require(frozen.get('file_table_base') == base and type(frozen.get('files')) is dict
            and base['path'] in frozen['files'] and len(frozen['files']) <= 180000
            and type(integrity) is dict and set(integrity) == {'sha256', 'count', 'total_bytes'}
            and type(integrity['count']) is int and len(frozen['files']) <= integrity['count'] <= 180000
            and type(integrity['total_bytes']) is int and 0 <= integrity['total_bytes'] <= 8 * 2**30
            and type(integrity['sha256']) is str and re.fullmatch('[a-f0-9]{64}', integrity['sha256']),
            'reviewed compact input representation required')
    python = str(Path(sys.executable).resolve(strict=True))
    command=[python,'-B',str(ROOT/'scripts/supervise_experiment.py'),'--run-id',OUTER.name,'--',
             python,'-B',str(HERE/'entry.py'),'--packet',str(packet),
             '--inputs-sha256',proposal['inputs_sha256'],
             '--snapshot-plan-sha256',proposal['snapshot_plan_sha256']]
    require(proposal['cwd']==str(ROOT) and proposal['command']==command and frozen['python']==python
            and plan['owner']==str(ROOT) and plan['phase']==phase and plan['work']==str(CONTROLLER)
            and plan['supervisor_work']==str(OUTER) and proposal['capacity']==plan['capacity']==CAPACITY,
            'exact runtime owner/phase/context/capacity required')
    require(sha(packet/'inputs.json')==proposal['inputs_sha256']
            and sha(packet/'plan.json')==frozen['plan_sha256']==proposal['plan_sha256']
            and sha(packet/'snapshot-plan.json')==proposal['snapshot_plan_sha256']
            and sha(HERE/'entry.py')==proposal['helper_sha256']==frozen['files'][str(HERE/'entry.py')]['sha256'],
            'reviewed runtime proposal and frozen entry changed')
    specification=packet/'specification.json'
    require(plan['specification']==dict(path=str(specification),sha256=sha(specification)),
            'exact runtime specification binding required')
    spec=read(specification)
    expected_children=2 if phase=='preflight' else len(spec['loader'])+5
    require(type(proposal['children']) is int and proposal['children']==len(plan['children'])==expected_children,
            'complete runtime probe/loader recipe required')
    startup_proof=startup_admission(args,proposal,frozen,plan,packet,CONTROLLER)
    require(all(not p.exists() and not p.is_symlink() for p in [WORK, OUTER, CONTROLLER]),
            'fresh launch and workload namespaces required')
    free = shutil.disk_usage(ROOT).free
    require(free >= CAPACITY['entry_gib'] * 2**30, 'fresh 16 GiB required before controller or WORK')
    WORK.mkdir()
    source_bytes=Path(__file__).read_bytes()
    require(hashlib.sha256(source_bytes).hexdigest()==args.launcher_sha256,'launcher changed before source retention')
    with (WORK/'launcher.py').open('xb') as stream:
        stream.write(source_bytes);stream.flush();os.fsync(stream.fileno())
    require(sha(WORK/'launcher.py')==args.launcher_sha256,'retained launcher source differs')
    record = dict(status='starting', phase=phase, launch_path=str(LAUNCH), launch_sha256=expected,
                  retained_launcher_source=str(WORK/'launcher.py'),
                  launcher_source_path=str(Path(__file__).resolve()),
                  launcher_source_sha256=sha(Path(__file__)),
                  launcher_pid=os.getpid(), launcher_parent_pid=os.getppid(),
                  launcher_identity=dict(source='in-process observation', pid=os.getpid(),
                      parent_pid=os.getppid(), pgid=os.getpgrp(), cwd=os.getcwd(), argv=sys.argv),
                  started_at=time.time(), startup_environment_admission=startup_proof,
                  command=command, cwd=str(ROOT), environment=proposal['environment'],
                  entry_free_bytes=free, maximum_observation_seconds=MAXIMUM_OBSERVATION_SECONDS,
                  maximum_wrapper_seconds=MAXIMUM_WRAPPER_SECONDS,
                  wrapper_identity_limitation='Popen PID retained; no separate contemporaneous wrapper ps/cwd probe.')

    def save():
        with (WORK / 'record.staged').open('w') as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        (WORK / 'record.staged').replace(WORK / 'record.json')

    save()
    with (WORK / 'stdout').open('xb') as stdout, (WORK / 'stderr').open('xb') as stderr:
        child = subprocess.Popen(command, cwd=ROOT, env=proposal['environment'],
                                 stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                 start_new_session=True)
        try:
            record.update(status='wrapper-running', pid=child.pid)
            save()
        finally:
            try:
                code = child.wait(timeout=MAXIMUM_WRAPPER_SECONDS)
            except subprocess.TimeoutExpired:
                record.update(status='wrapper-observation-expired-task-not-signaled',
                              wrapper_may_be_live=True, observation_expired_at=time.time())
                save()
                raise RuntimeError('wrapper has not closed; owned task retained without process control')
            record.update(status='wrapper-finished-awaiting-terminal', launcher_returncode=code,
                          launcher_finished_at=time.time(), stdout_sha256=sha(WORK / 'stdout'),
                          stderr_sha256=sha(WORK / 'stderr'))
            save()
    require(code == 0, 'supervisor wrapper failed; retained history requires inspection')
    handoff = read(WORK / 'stdout')
    require(type(handoff['supervisor_pid']) is int and handoff['supervisor_pid'] > 0
            and handoff['directory'] == str(OUTER), 'wrapper supervisor handoff differs')
    record['supervisor_handoff'] = handoff
    save()
    started = time.monotonic()
    while time.monotonic() - started <= MAXIMUM_OBSERVATION_SECONDS:
        status = OUTER / 'status.json'
        if status.exists():
            terminal = read(status)
            require(terminal['command'] == command[6:] and terminal['cwd'] == str(ROOT),
                    'outer process association differs')
            require(terminal['supervisor_pid'] == handoff['supervisor_pid'],
                    'outer supervisor differs from actual wrapper handoff')
            if terminal['status'] in ['finished', 'supervisor failed']:
                now = time.time()
                record.update(status='terminal-observed', outer_sha256=sha(status),
                              outer_status=terminal['status'], terminal_observed_at=now,
                              finished_at=now, returncode=terminal.get('returncode'),
                              supervisor_pid=terminal['supervisor_pid'],
                              controller_pid=terminal.get('child_pid'))
                save()
                print(json.dumps(dict(path=str(WORK / 'record.json'), **{
                    k: record[k] for k in ['status', 'returncode', 'supervisor_pid', 'controller_pid']})))
                require(terminal['status'] == 'finished' and terminal['returncode'] == 0,
                        'actual supervisor did not finish successfully')
                return
        time.sleep(2)
    record.update(status='observation-expired-task-not-signaled', observation_expired_at=time.time())
    save()
    raise RuntimeError('actual terminal not observed within bound; task retained without process control')


if __name__ == '__main__':
    main()
