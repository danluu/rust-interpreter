#!/usr/bin/env python3
"""Freeze exact six-copy delta retention/removal; never execute it."""
import ast
import json
import os
from pathlib import Path
import sys
import remove as c

def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')

def main():
    assert Path.cwd()==c.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    packet=c.HERE/'plan-01';assert not packet.exists() and not c.WORK.exists() and not c.RESULT.exists()
    assessment=c.read(c.ASSESSMENT);starts={};deltas={}
    assert assessment['entries']==27657 and assessment['allocated_bytes']==1166352384
    for name,root in c.ROOTS.items():
        rows,allocated=c.snapshot(root);expected=assessment['roots'][name]
        assert rows==expected['entries'] and allocated<=expected['allocated_bytes']+16*2**20
        control=expected['negative'];kind=control['kind']
        deltas[name]=dict(root=str(root),original=expected['original'],kind=kind,victim=c.VICTIM,
            original_sha256=control['expected_sha256'],actual_absence=kind=='missing',
            actual_corrupt_sha256=expected['divergent_file']['sha256'] if kind=='corrupt' else None,
            actual_corrupt_bytes=6751 if kind=='corrupt' else None,
            current_victim_identity=rows[c.VICTIM] if kind=='corrupt' else None,
            original_command_index=control['command_index'],original_validator_rejection=control['validator_rejection'],
            original_result_sha256=expected['history']['terminal_sha256'],original_status=expected['history']['status'])
    for name in c.base.NAMES:
        status=c.validate_outer(name)
        for field in ['supervisor_identity','child_identity']:
            values=status[field].splitlines()[-1].split();starts[values[0]]=values[2:7]
    assert set(starts)=={'99781','99784','91736','91753','96831','96835'}
    environment=c.read(c.OWNER/'experiments/oxc-native-first-target-cleanup/plan-01/plan.json')['environment'];executors={}
    for name in ['/opt/homebrew/bin/python3','/usr/sbin/lsof','/bin/ps']:
        path=Path(name);resolved=path.resolve(strict=True)
        executors[name]=dict(resolved=str(resolved),route_identity=c.identity(path),file_identity=c.identity(resolved),sha256=c.sha(resolved))
    commands=[dict(label='open-handles-'+name,argv=['/usr/sbin/lsof','-nP','+D',str(root)],expected=[1]) for name,root in c.ROOTS.items()]
    commands.append(dict(label='owned-pids',argv=['/bin/ps','-p',','.join(sorted(starts,key=int)),'-o','pid=,ppid=,pgid=,lstart=,tty=,command='],expected=[0,1]))
    packet.mkdir()
    plan=dict(owner=str(c.OWNER),roots={name:str(root) for name,root in c.ROOTS.items()},work=str(c.WORK),deltas=deltas,
        environment=environment,platform=list(os.uname()),executors=executors,commands=commands,owned_start_times=starts,
        canonical_lock=str(c.owned.CANONICAL_LOCK),wait_seconds=600,minimum_free_gib=9,entries=27657,
        allocated_observation=1166352384,delta_archive=dict(result=str(c.RESULT),members=4,raw_limit=64*2**10,compressed_cap=2**20),
        scope='Only six completed negative-{missing,corrupt} copies. Retain three actual6751-byte corrupt payloads and three exact absence/origin records, full945 historical members, all unchanged live original source bytes/identities. Failed38/passed61/passed61 outcomes remain unchanged.',
        quiescence_limitation='Seven read-only probes give point-in-time observations, not a kernel reservation. Repeated exact current membership/identity guards precede fd-anchored mutation. No process signaling.')
    write(packet/'plan.json',plan)
    files={c.ASSESSMENT,packet/'plan.json',c.PRESERVED,c.ADMITTED,
        c.ORIGINAL/'evidence.tar.gz',c.ORIGINAL/'manifest.json',c.SHARED/'evidence.tar.gz',c.SHARED/'manifest.json',
        c.OWNER/'experiments/completed-source-prefix-cleanup/assess.py',
        c.OWNER/'experiments/stable-cgu/owned_stage.py',c.OWNER/'scripts/supervise_experiment.py'}
    files.update(c.HERE/name for name in ['assess.py','remove.py','prepare.py','README.md'])
    files.update(Path(row['resolved']) for row in executors.values())
    for name in c.base.NAMES:
        work=c.R/'.work'/('mono-production-source-observables-'+name)
        files.update(work/file for file in ['plan.json','result.json','commands.json','controls.json','source-snapshots/qualify_std_source_observables.py'])
        files.update(c.outer(name)/file for file in ['plan.json','status.json','command.log'])
    frozen={}
    for path in sorted(files):
        assert path.resolve(strict=True)==path and path.is_file()
        before=c.identity(path);digest=c.sha(path);assert c.identity(path)==before
        frozen[str(path)]=dict(identity=before,sha256=digest)
        if path.suffix=='.py':ast.parse(path.read_text())
    write(packet/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(c.OWNER/'scripts/supervise_experiment.py'),'--run-id','completed-negative-source-cleanup-supervisor-01','--',
        '/opt/homebrew/bin/python3','-B',str(c.HERE/'remove.py'),'--inputs-sha256',c.sha(packet/'inputs.json')]
    write(packet/'launch.json',dict(command=command,cwd=str(c.OWNER),environment=environment,review_required_before_execution=True))
    print(json.dumps(dict(packet=str(packet),inputs=len(files),input_bytes=sum(p.stat().st_size for p in files),entries=27657,
        plan_sha256=c.sha(packet/'plan.json'),freeze_sha256=c.sha(packet/'inputs.json'),launch_sha256=c.sha(packet/'launch.json')),indent=2))

if __name__=='__main__':main()
