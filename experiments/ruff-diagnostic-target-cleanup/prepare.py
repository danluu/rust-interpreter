#!/usr/bin/env python3
"""Freeze a proposal for exactly three completed Ruff diagnostic targets."""
import json
import os
from pathlib import Path
import sys

import remove_completed_targets as c

a, OWNER, WORK = c.a, c.OWNER, c.WORK
HERE = Path(__file__).resolve().parent


def write(path,value):
    with path.open('x') as output:
        json.dump(value,output,sort_keys=True,indent=2); output.write('\n')


def prepare():
    a.require(Path.cwd() == OWNER and sys.dont_write_bytecode and not sys.flags.optimize, 'fixed owner/Python required')
    a.absent(WORK)
    packet = HERE/'plan-01'; a.absent(packet)
    assessment = a.read(c.ASSESSMENT)
    total = 0
    for mode,root in c.ROOTS.items():
        rows,allocated = c.snapshot(root); proof = assessment['roots'][mode]
        a.require(rows == proof['entries'] and allocated <= proof['allocated_bytes']+16*2**20, 'assessed cache changed')
        total += len(rows)
    a.require(total == 22953, 'exact three-root membership differs')
    outer = a.read(c.OUTER/'status.json'); workflow = a.read(c.HISTORY/'workflow/receipt.json')
    starts = {}
    for key in ['supervisor_identity','child_identity']:
        fields = outer[key].splitlines()[-1].split()
        a.require(len(fields)>=8, 'original supervisor identity missing')
        starts[fields[0]] = fields[2:7]
    fields = workflow['identity']['ps'].split()
    a.require(len(fields)>=9, 'original workflow identity missing')
    starts[fields[0]] = fields[3:8]
    a.require(set(starts) == {'16028','16031','16033'}, 'original recorded process set differs')
    template = a.read(OWNER/'experiments/oxc-runtime-compatibility/strict-cleanup-plan-01/plan.json')
    plan = dict(template,owner=str(OWNER),runtime_owner=str(c.R),roots={k:str(v) for k,v in c.ROOTS.items()},
                work=str(WORK),owned_start_times=starts,
                purpose='Remove only three completed diagnostic targets after final native/guest preservation and all historical evidence verification')
    plan.pop('root',None)
    plan['commands'] = [dict(label='open-handles-'+mode,argv=['/usr/sbin/lsof','-nP','+D',str(root)],expected=[1])
                        for mode,root in c.ROOTS.items()]
    plan['commands'].append(dict(label='owned-pids',argv=['/bin/ps','-p',','.join(sorted(starts,key=int)),
        '-o','pid=,ppid=,pgid=,lstart=,tty=,command='],expected=[0,1]))
    plan['platform'] = list(os.uname())
    plan['executors'] = {name:dict(resolved=str(Path(name).resolve(strict=True)),stamp=a.stamp(name),sha256=a.sha(name))
        for name in ['/opt/homebrew/bin/python3','/usr/sbin/lsof','/bin/ps']}
    packet.mkdir(); write(packet/'plan.json',plan)
    files = {c.ASSESSMENT,c.RECIPE,c.INDEPENDENT,c.CORRECTION,c.SOURCE_INVENTORY,
        c.HISTORY/'receipt.json',c.HISTORY/'workflow/receipt.json',c.HISTORY/'workflow-verification.json',
        c.OUTER/'status.json',c.RUN/'records.json',c.RUN/'source-transitions.json',
        c.DEST/'receipt.json',c.DEST/'original-archive/manifest.json',c.DEST/'original-archive/evidence.tar.gz',
        c.RESULT/'manifest.json',c.RESULT/'evidence.tar.gz',packet/'plan.json',
        OWNER/'experiments/oxc-runtime-compatibility/acquire_runtime_source.py',
        OWNER/'experiments/stable-cgu/owned_stage.py',OWNER/'scripts/supervise_experiment.py'}
    files.update(HERE/name for name in ['assess.py','preserve.py','remove_completed_targets.py','prepare.py','README.md'])
    files.update(Path(row['resolved']) for row in plan['executors'].values())
    for path in files: a.frozen_input_file(path,plan['executors'])
    write(packet/'inputs.json',dict(schema_version=1,files={str(path):a.sha(path) for path in sorted(files)}))
    command = ['/opt/homebrew/bin/python3','-B',str(OWNER/'scripts/supervise_experiment.py'),
        '--run-id','ruff-diagnostic-target-cleanup-supervisor-01','--','/opt/homebrew/bin/python3','-B',
        str(HERE/'remove_completed_targets.py'),'--plan',str(packet/'plan.json'),
        '--freeze',str(packet/'inputs.json'),'--frozen-sha256',a.sha(packet/'inputs.json')]
    write(packet/'launch.json',dict(command=command,cwd=str(OWNER),environment=plan['environment'],
        owner=str(OWNER),review_required_before_execution=True))
    print(json.dumps(dict(packet=str(packet),inputs=len(files),input_bytes=sum(p.stat().st_size for p in files),
        entries=total,assessment_sha256=a.sha(c.ASSESSMENT),plan_sha256=a.sha(packet/'plan.json'),
        freeze_sha256=a.sha(packet/'inputs.json'),launch_sha256=a.sha(packet/'launch.json')),indent=2))


if __name__ == '__main__': prepare()
