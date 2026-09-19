#!/usr/bin/env python3
"""Freeze a single, unrun retention-and-cleanup packet for the native01 target."""
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
    assessment=c.read(c.ASSESSMENT);terminal,outer,verification=c.history()
    rows,allocated=c.snapshot(c.ROOT);assert rows==assessment['entries'] and allocated<=assessment['allocated_bytes']+16*2**20
    starts={}
    for field in ['supervisor_identity','child_identity']:
        values=outer[field].splitlines()[-1].split();starts[values[0]]=values[2:7]
    assert set(starts)=={'19684','19687'}
    environment=c.read(c.OWNER/'experiments/oxc-runtime-compatibility/strict-cleanup-plan-01/plan.json')['environment']
    executors={}
    for name in ['/opt/homebrew/bin/python3','/usr/sbin/lsof','/bin/ps']:
        path=Path(name);resolved=path.resolve(strict=True)
        executors[name]=dict(resolved=str(resolved),route_identity=c.identity(path),file_identity=c.identity(resolved),sha256=c.sha(resolved))
    commands=[dict(label='open-handles-native01',argv=['/usr/sbin/lsof','-nP','+D',str(c.ROOT)],expected=[1]),
        dict(label='owned-pids',argv=['/bin/ps','-p','19684,19687','-o','pid=,ppid=,pgid=,lstart=,tty=,command='],expected=[0,1])]
    packet.mkdir()
    plan=dict(owner=str(c.OWNER),roots={name:str(root) for name,root in c.ROOTS.items()},work=str(c.WORK),
        environment=environment,platform=list(os.uname()),executors=executors,commands=commands,owned_start_times=starts,
        canonical_lock=str(c.owned.CANONICAL_LOCK),wait_seconds=600,minimum_free_gib=9,
        entries=4595,unique_inode_allocated_observation=assessment['allocated_bytes'],
        retention=dict(result=str(c.RESULT),members=7,logical_bytes=sum(p['bytes'] for p in assessment['final_artifacts'].values()),
                       maximum_archive_bytes=64*2**20,full_readback_before_removal=True),
        policy='Only the exact completed native01 derived target. Preserve all286 prior archived evidence members and seven final output files; keep original strip-warning performance limitation.',
        links='Ordinary-file link count must equal exact within-target alias count. Unlinks decrement only that admitted group and rebind surviving aliases to the observed inode stamp.',
        mutation='Held nofollow parent directory FDs, exact current identity checks and dir_fd unlink/rmdir only; directory owner-write may be enabled on exact admitted target directories with a before/after ledger.',
        quiescence_limitation='Read-only lsof and exact historical PID/start checks are point-in-time observations. Repeated full identity/membership guards precede mutation; no process signaling.')
    write(packet/'plan.json',plan)
    files={c.ASSESSMENT,packet/'plan.json',c.ARCHIVE/'manifest.json',c.ARCHIVE/'evidence.tar.gz',
        c.OWNER/'experiments/stable-cgu/owned_stage.py',c.OWNER/'scripts/supervise_experiment.py',
        c.OWNER/'experiments/oxc-plugin-normalization/native-compatibility-plan-01.json'}
    files.update(c.HERE/name for name in ['assess.py','remove.py','prepare.py','README.md'])
    files.update(Path(row['resolved']) for row in executors.values())
    manifest=c.read(c.ARCHIVE/'manifest.json')['members'];assert len(manifest)==286
    for name,proof in manifest.items():
        path=c.OWNER/name;assert path.resolve(strict=True)==path and path.stat().st_size==proof['bytes'] and c.sha(path)==proof['sha256']
        files.add(path)
    frozen={}
    for path in sorted(files):
        assert path.resolve(strict=True)==path and path.is_file()
        before=c.identity(path);digest=c.sha(path);assert c.identity(path)==before
        frozen[str(path)]=dict(identity=before,sha256=digest)
        if path.suffix=='.py':ast.parse(path.read_text())
    write(packet/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(c.OWNER/'scripts/supervise_experiment.py'),'--run-id','oxc-native-first-target-cleanup-supervisor-01','--',
        '/opt/homebrew/bin/python3','-B',str(c.HERE/'remove.py'),'--inputs-sha256',c.sha(packet/'inputs.json')]
    write(packet/'launch.json',dict(command=command,cwd=str(c.OWNER),environment=environment,review_required_before_execution=True))
    print(json.dumps(dict(packet=str(packet),inputs=len(files),input_bytes=sum(p.stat().st_size for p in files),entries=4595,
        plan_sha256=c.sha(packet/'plan.json'),freeze_sha256=c.sha(packet/'inputs.json'),launch_sha256=c.sha(packet/'launch.json')),indent=2))

if __name__=='__main__':main()
