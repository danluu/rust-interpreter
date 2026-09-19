"""Observe one ordinary std07 launch after its packet binder has closed successfully.

The existing supervisor and std CLI are unchanged. The CLI owns canonical and
std locks; this observer holds neither. Timeout or failed observation preserves
the task without signaling or retrying. A detached supervisor terminal is an
observed receipt, not an independently waited OS process closure.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

PROOF_ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
ROOT=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE=PROOF_ROOT/'experiments/runtime-std07-launch-01'
PACKET=PROOF_ROOT/'experiments/runtime-std-after-installation07-01'
LAUNCH=PACKET/'launch.json'
BINDING=X/'.work/runtime-std07-packet-binding-execution-02'
BINDING_REPORT=X/'.work/runtime-std07-packet-binding-01.json'
BUILDER=X/'.work/bind_runtime_std07_packet_02.py'
BUILDER_SHA='207387c61af5740a2daf5f48e1a5618d6174d73da366c41ffd81456853cd83a1'
TRANSPORT=X/'.work/execute_runtime_std07_packet_binding_02.py'
TRANSPORT_SHA='fd8d5ff432f04ad3e3e1e1da524f2d30f34e8eaaf86959d6fc7a73c6529d3c9c'
WORK=ROOT/'.work/hir-options-hash-runtime-std-launch-execution-07-01'
OUTER=ROOT/'.work/experiments/hir-options-hash-runtime-std-supervisor-07-01'
CONTROLLER=ROOT/'.work/hir-options-hash-runtime-std-supervision-07-01'
RUN=ROOT/'.work/hir-options-hash-runtime-std-07-01'
MAXIMUM_OBSERVATION_SECONDS=1800
MAXIMUM_WRAPPER_SECONDS=30


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


def stamp(path):
    value=Path(path).lstat()
    return [value.st_dev,value.st_ino,value.st_mode,value.st_size,
            value.st_mtime_ns,value.st_ctime_ns,value.st_nlink]


def bound_row(row,path):
    require(row['path']==str(path) and row['sha256']==sha(path)
            and row['identity']==stamp(path) and row['bytes']==Path(path).stat().st_size,
            'actual binding byte/identity association changed: '+str(path))


def closed_binding(expected):
    # Do not read future packet files before the exact binding closure gate.
    require(sha(BINDING/'record.json')==expected,'reviewed closed binding execution required')
    execution=read(BINDING/'record.json')
    require(execution['status']=='finished' and execution['returncode']==0
            and execution['may_be_live'] is False and execution['std_execution'] is False
            and 'error' not in execution, 'binding is failed, unclosed or not source-only')
    for name,path,pinned in [('builder',BUILDER,BUILDER_SHA),('transport',TRANSPORT,TRANSPORT_SHA)]:
        require(execution[name]['sha256']==pinned,'binding source association differs')
        bound_row(execution[name],path)
    bound_row(execution['result'],BINDING_REPORT)
    for name in ['stdout','stderr']:
        bound_row(execution[name],BINDING/name)
    require((BINDING/'stderr').read_bytes()==b'','successful binding stderr differs')
    output=read(BINDING/'stdout'); result=read(BINDING_REPORT)
    require(output['status']==result['status']=='bound-unexecuted-std07-packet'
            and output['report']==execution['result']
            and result['pid']==execution['child_pid']
            and result['parent_pid']==execution['parent_pid']
            and result['std_execution'] is False
            and result['passed_environment']==execution['passed_environment']
            and result['observed_before']==result['observed_after_imports']
                ==result['observed_after_publication']==execution['observed_child_environment']
                ==execution['passed_environment'], 'actual binder result/observation association differs')
    times=[execution['started_at'],execution['child_started_at'],result['finished_at'],
           execution['child_closed_at'],execution['finished_at']]
    require(all(type(t) in (int,float) and 0<t<=time.time() for t in times)
            and times==sorted(times),'actual binding closure chronology differs')
    return execution,result


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ['launch-sha256','inputs-sha256','binding-execution-sha256','launcher-sha256']:
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    require(all(re.fullmatch('[a-f0-9]{64}',value) for value in vars(args).values()),
            'actual reviewed launch/input/binding/source digests must be bound')
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize
            and Path(__file__).resolve()==HERE/'launch.py'
            and sha(Path(__file__))==args.launcher_sha256,
            'exact reviewed launcher route, owner and unoptimized Python -B required')
    execution,binding=closed_binding(args.binding_execution_sha256)
    for key,path in [('launch',LAUNCH),('inputs',PACKET/'inputs.json'),('plan',PACKET/'plan.json')]:
        bound_row(binding[key],path)
    require(binding['launch']['sha256']==args.launch_sha256
            and binding['inputs']['sha256']==args.inputs_sha256,
            'independently reviewed packet differs from closed binder output')
    proposal=read(LAUNCH); frozen=read(PACKET/'inputs.json'); plan=read(PACKET/'plan.json')
    python='/opt/homebrew/bin/python3'
    command=[python,'-B',str(ROOT/'scripts/supervise_experiment.py'),'--run-id',OUTER.name,'--',
             python,'-B',str(PACKET/'prepare.py'),'--frozen-sha',args.inputs_sha256]
    require(proposal['status']=='unexecuted' and proposal['owner']==proposal['cwd']==str(ROOT)
            and proposal['command']==command and proposal['environment']==plan['environment']
                ==binding['passed_environment'] and proposal['expected_direct_cli_children']==7
            and proposal['review_required_before_launch'] is True and proposal['wait_seconds']==600,
            'ordinary std launch command/environment/recipe differs')
    require(proposal['source_freeze']==dict(path=str(PACKET/'inputs.json'),sha256=args.inputs_sha256)
            and proposal['plan']==dict(path=str(PACKET/'plan.json'),sha256=binding['plan']['sha256'])
            and frozen['owner']==plan['owner']==str(ROOT) and plan['work']==str(CONTROLLER)
            and plan['run_work']==str(RUN) and plan['status']=='prepared-unexecuted'
            and plan['runtime_key']==proposal['runtime_key']
            and plan['canonical_lock']==proposal['canonical_lock']==str(Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock'))
            and plan['lock_wait_seconds']==600,
            'bound std packet owner/routes differ')
    require(proposal['bounds']==plan['bounds'] and all(plan['bounds'][k]==v for k,v in {
        'entry_free_gib':16,'active_child_stop_gib':9,'running_floor_gib':8,'build_jobs':2,
        'retained_input_bytes':64*2**20,'retained_single_input_bytes':32*2**20,'source_copy_count':2}.items()),
        'ordinary std resource bounds changed')
    require(frozen['python']==proposal['python']
            and frozen['python']['path']==python
            and frozen['python']['resolved']==str(Path(sys.executable).resolve(strict=True))
                ==str(Path(python).resolve(strict=True))
            and sha(Path(python).resolve(strict=True))==frozen['python']['sha256'],
            'exact bound Python executor differs')
    for path in [PACKET/'prepare.py',PACKET/'imports.py',PACKET/'std_cli.py',
                 PACKET/'plan.json',ROOT/'scripts/supervise_experiment.py']:
        require(frozen['files'].get(str(path))==sha(path),'selected frozen launch source differs: '+str(path))
    require(proposal['helper']==dict(path=str(PACKET/'prepare.py'),sha256=sha(PACKET/'prepare.py')),
            'selected std helper differs')
    require(all(not os.path.lexists(p) for p in [WORK,OUTER,CONTROLLER,RUN]),
            'fresh std launcher/supervisor/controller/CLI namespaces required')
    free=shutil.disk_usage(ROOT).free
    require(free>=16*2**30,'fresh 16 GiB required before std launch')
    WORK.mkdir()
    for name,path in [('launcher.py',Path(__file__)),('launch.json',LAUNCH),
                      ('inputs.json',PACKET/'inputs.json'),('plan.json',PACKET/'plan.json'),
                      ('binding-record.json',BINDING/'record.json'),('binding-result.json',BINDING_REPORT)]:
        data=path.read_bytes()
        with (WORK/name).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        require(sha(WORK/name)==sha(path),'retained launch input changed')
    record=dict(status='starting',schema_version=1,launch_path=str(LAUNCH),
        launch_sha256=args.launch_sha256,inputs_sha256=args.inputs_sha256,
        binding_execution=dict(path=str(BINDING/'record.json'),sha256=args.binding_execution_sha256),
        binding_result=execution['result'],launcher_source_path=str(Path(__file__).resolve()),
        launcher_source_sha256=args.launcher_sha256,launcher_pid=os.getpid(),launcher_parent_pid=os.getppid(),
        launcher_identity=dict(source='in-process observation',pid=os.getpid(),parent_pid=os.getppid(),
                               pgid=os.getpgrp(),cwd=os.getcwd(),argv=sys.argv),
        started_at=time.time(),command=command,cwd=str(ROOT),environment=proposal['environment'],
        entry_free_bytes=free,maximum_observation_seconds=MAXIMUM_OBSERVATION_SECONDS,
        maximum_wrapper_seconds=MAXIMUM_WRAPPER_SECONDS,signals=0,retries=0,
        workload_lock_owned_by='unchanged ordinary std CLI',wrapper_may_be_live=False,
        controller_may_be_live=False,detached_supervisor_os_closure_observed=False,
        closure_scope='Direct wrapper wait; detached supervisor terminal reports its waited controller. No supervisor OS-reap claim.',
        wrapper_identity_limitation='Popen PID retained; no separate contemporaneous wrapper ps/cwd probe.')

    def save():
        with (WORK/'record.staged').open('w') as stream:
            json.dump(record,stream,indent=2,sort_keys=True)
            stream.write('\n');stream.flush();os.fsync(stream.fileno())
        (WORK/'record.staged').replace(WORK/'record.json')

    def unchanged_packet():
        require(sha(Path(__file__))==args.launcher_sha256
                and sha(BINDING/'record.json')==args.binding_execution_sha256,
                'launcher or closed binding changed')
        for key,path in [('launch',LAUNCH),('inputs',PACKET/'inputs.json'),('plan',PACKET/'plan.json')]:
            bound_row(binding[key],path)
        for path in [PACKET/'prepare.py',PACKET/'imports.py',PACKET/'std_cli.py',
                     ROOT/'scripts/supervise_experiment.py']:
            require(sha(path)==frozen['files'][str(path)],'selected launch source changed')

    unchanged_packet();save()
    child=None
    try:
        with (WORK/'stdout').open('xb') as stdout,(WORK/'stderr').open('xb') as stderr:
            child=subprocess.Popen(command,cwd=ROOT,env=proposal['environment'],
                stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
            deadline=time.monotonic()+MAXIMUM_WRAPPER_SECONDS
            record.update(status='wrapper-running',pid=child.pid,wrapper_started_at=time.time(),
                          wrapper_may_be_live=True,controller_may_be_live=True)
            try:save()
            finally:
                try:child.wait(timeout=max(.001,deadline-time.monotonic()))
                finally:
                    record.update(launcher_returncode=child.returncode,launcher_finished_at=time.time(),
                                  wrapper_may_be_live=child.returncode is None)
                    save()
        require(child.returncode==0,'supervisor wrapper failed; task requires inspection without retry')
        record.update(status='wrapper-finished-awaiting-terminal',stdout_sha256=sha(WORK/'stdout'),
                      stderr_sha256=sha(WORK/'stderr'))
        handoff=read(WORK/'stdout')
        require(type(handoff['supervisor_pid']) is int and handoff['supervisor_pid']>0
                and handoff['directory']==str(OUTER),'actual supervisor handoff differs')
        record['supervisor_handoff']=handoff;save()
        deadline=time.monotonic()+MAXIMUM_OBSERVATION_SECONDS
        while time.monotonic()<=deadline:
            status=OUTER/'status.json'
            if status.exists():
                terminal=read(status)
                require(terminal['owner']==terminal['cwd']==str(ROOT)
                        and terminal['command']==command[6:]
                        and terminal['supervisor_pid']==handoff['supervisor_pid'],
                        'actual supervisor owner/process association differs')
                if terminal['status'] in ['finished','supervisor failed']:
                    now=time.time()
                    record.update(status='terminal-observed',outer_sha256=sha(status),outer_status=terminal['status'],
                        terminal_observed_at=now,finished_at=now,returncode=terminal.get('returncode'),
                        supervisor_pid=terminal['supervisor_pid'],controller_pid=terminal.get('child_pid'),
                        controller_may_be_live=terminal['status']!='finished')
                    # Copy only terminal metadata and supervisor raw, never std/provider trees.
                    record['supervisor_evidence']={}
                    for name,path in [('supervisor-terminal.json',status),('supervisor-plan.json',OUTER/'plan.json'),
                                      ('command.log',OUTER/'command.log'),('supervisor.log',OUTER/'supervisor.log')]:
                        before=sha(path)
                        with (WORK/name).open('xb') as stream:stream.write(path.read_bytes())
                        require(sha(WORK/name)==sha(path)==before,'supervisor evidence changed during readback')
                        record['supervisor_evidence'][name]=dict(path=str(path),sha256=before,
                            retained_path=str(WORK/name),observation='current bytes at terminal observation')
                    require(sha(OUTER/'plan.json')==terminal['plan_sha256'], 'supervisor plan differs')
                    if terminal['status']=='finished':
                        require(sha(OUTER/'command.log')==terminal['log_sha256'],'supervisor raw differs')
                    receipt=CONTROLLER/'receipt.json'
                    if receipt.exists():
                        own=read(receipt)
                        require(own['pid']==terminal.get('child_pid')
                                and own['parent_pid']==terminal['supervisor_pid'], 'std controller association differs')
                        record['controller_receipt']=dict(path=str(receipt),sha256=sha(receipt),
                            status=own['status'],pid=own['pid'],parent_pid=own['parent_pid'])
                    unchanged_packet()
                    save()
                    require(terminal['status']=='finished' and terminal['returncode']==0,
                            'actual std supervisor did not finish successfully')
                    require(receipt.exists() and own['status']=='passed' and own['inner_children']==7,
                            'std controller did not complete the ordinary seven-command recipe')
                    print(json.dumps(dict(path=str(WORK/'record.json'),**{k:record[k] for k in
                        ['status','returncode','supervisor_pid','controller_pid']}),sort_keys=True))
                    return
            time.sleep(min(2,max(0,deadline-time.monotonic())))
        raise RuntimeError('std terminal observation expired; task retained without process control')
    except BaseException as error:
        record.update(observation_error=repr(error),observation_failed_at=time.time())
        if child is not None:
            record['wrapper_may_be_live']=child.returncode is None
        for name in ['stdout','stderr']:
            if (WORK/name).exists() and child is not None and child.returncode is not None:
                try:record[name+'_sha256']=sha(WORK/name)
                except BaseException as raw_error:record[name+'_observation_error']=repr(raw_error)
        save();raise


if __name__=='__main__':main()
