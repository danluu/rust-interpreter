#!/usr/bin/env python3
"""Inventory one completed task target and freeze an unrun cleanup proposal."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time

import remove_completed_targets as cleanup

a = cleanup.a
OWNER, ROOT, WORK = cleanup.OWNER, cleanup.ROOT, cleanup.WORK
A = cleanup.PROFILE_OWNER
HERE = Path(__file__).resolve().parent


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def prepare():
    a.require(Path.cwd() == OWNER and sys.dont_write_bytecode, 'fixed preparation owner required')
    a.absent(WORK)
    a.absent(cleanup.ASSESSMENT)
    packet = HERE/'plan-01'
    a.absent(packet)
    proof_paths = [A/'results/runtime-ruff-hir-self-profile-01'/name for name in
                   ['README.md','manifest.json','evidence.tar.gz','archive-execution.json','summary.json']]
    proof_paths.append(A/'.work/ruff-hir-profile-independent-verification-01.json')
    records = []
    for name, work, outer in [
        ('ruff-profile-02','ruff-hir-self-profile-02','ruff-hir-self-profile-supervisor-02'),
        ('ruff-profile-continuation-01','ruff-hir-self-profile-continuation-01',
         'ruff-hir-self-profile-continuation-supervisor-01')]:
        base = A/'experiments/runtime-application-admission'/name
        proof_paths.extend(base/'plan'/file for file in ['plan.json','inputs.json','launch.json'])
        proof_paths.append(base/('profile.py' if name == 'ruff-profile-02' else 'continue.py'))
        proof_paths.extend(A/'.work'/work/file for file in ['supervision.json','result.json'])
        proof_paths.append(A/'.work/experiments'/outer/'status.json')
        records.append((a.read(A/'.work'/work/'supervision.json'),
                        a.read(A/'.work/experiments'/outer/'status.json')))
    finished = records[-1][0]['finished_at']
    a.require(records[0][0]['status'] == 'failed' and records[-1][0]['status'] == 'passed',
              'expected complete continued history required')
    rows, allocated = cleanup.snapshot()
    a.require(len(rows) == 14139 and all(max(row['mtime_ns'],row['ctime_ns'])/1e9 <= finished
              for row in rows.values()), 'target membership or post-completion changes differ')
    groups = {}
    for name,row in rows.items():
        if stat.S_ISREG(row['mode']): groups.setdefault((row['dev'],row['ino']),[]).append(name)
    outside = [names for names in groups.values() if rows[names[0]]['nlink'] != len(names)]
    a.require(not outside,'outside target hardlinks')
    proofs = {}
    for path in proof_paths:
        a.ordinary(path); proofs[str(path)] = a.sha(path)
    assessment = dict(schema_version=1,root=str(ROOT),owner=str(A),prepared_at=time.time(),
        completed_at=finished,entries={name:row for name,row in rows.items() if name != '.'},
        root_stamp=rows['.'],allocated_bytes=allocated,entries_with_root=len(rows),
        outside_hardlink_candidates=outside,proofs=proofs,
        source_only=True,allocation_blocks_are_observation=True,
        scope='Only the exact completed Ruff profile-02 targets directory; all preserved profiles, compiler records and evidence are outside it.')
    write(cleanup.ASSESSMENT,assessment)
    starts = {}
    for record, outer in records:
        for key in ['supervisor_identity','child_identity']:
            fields = outer[key].splitlines()[-1].split()
            a.require(len(fields)>=8,'recorded supervisor process identity missing')
            starts[fields[0]] = fields[2:7]
        for child in record['children']:
            fields = child['receipt']['identity']['ps'].split()
            a.require(len(fields)>=9,'recorded profile child identity missing')
            starts[fields[0]] = fields[3:8]
    a.require(len(starts)==18,'complete original process set required')
    template = a.read(OWNER/'experiments/oxc-runtime-compatibility/strict-cleanup-plan-01/plan.json')
    plan = dict(template,owner=str(OWNER),profile_owner=str(A),root=str(ROOT),work=str(WORK),
        owned_start_times=starts,
        purpose='Retire only the completed exact Ruff profile targets after complete 14-child,650-wrapper,6-suite,2-profile archival; future workload entry gates remain unchanged')
    plan['commands'] = [dict(label='open-handles',argv=['/usr/sbin/lsof','-nP','+D',str(ROOT)],expected=[1]),
        dict(label='owned-pids',argv=['/bin/ps','-p',','.join(sorted(starts,key=int)),
             '-o','pid=,ppid=,pgid=,lstart=,tty=,command='],expected=[0,1])]
    plan['platform'] = list(os.uname())
    plan['executors'] = {name:dict(resolved=str(Path(name).resolve(strict=True)),stamp=a.stamp(name),sha256=a.sha(name))
                         for name in ['/opt/homebrew/bin/python3','/usr/sbin/lsof','/bin/ps']}
    packet.mkdir()
    write(packet/'plan.json',plan)
    files = set(proof_paths + [cleanup.ASSESSMENT,Path(__file__).resolve(),HERE/'remove_completed_targets.py',
        OWNER/'experiments/oxc-runtime-compatibility/acquire_runtime_source.py',
        OWNER/'experiments/stable-cgu/owned_stage.py',OWNER/'scripts/supervise_experiment.py',packet/'plan.json'])
    files.update(Path(record['resolved']) for record in plan['executors'].values())
    for path in files: a.frozen_input_file(path,plan['executors'])
    freeze = dict(schema_version=1,files={str(path):a.sha(path) for path in sorted(files)})
    write(packet/'inputs.json',freeze)
    command = ['/opt/homebrew/bin/python3','-B',str(OWNER/'scripts/supervise_experiment.py'),
        '--run-id','ruff-profile-target-cleanup-supervisor-01','--','/opt/homebrew/bin/python3','-B',
        str(HERE/'remove_completed_targets.py'),'--plan',str(packet/'plan.json'),
        '--freeze',str(packet/'inputs.json'),'--frozen-sha256',a.sha(packet/'inputs.json')]
    write(packet/'launch.json',dict(command=command,cwd=str(OWNER),environment=plan['environment'],
        owner=str(OWNER),review_required_before_execution=True))
    print(json.dumps(dict(packet=str(packet),inputs=len(files),input_bytes=sum(p.stat().st_size for p in files),
        allocated_bytes=allocated,entries=len(rows),assessment_sha256=a.sha(cleanup.ASSESSMENT),
        plan_sha256=a.sha(packet/'plan.json'),freeze_sha256=a.sha(packet/'inputs.json'),
        launch_sha256=a.sha(packet/'launch.json')),indent=2))


if __name__ == '__main__':
    prepare()
