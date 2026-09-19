#!/usr/bin/env python3
"""Read-only freeze for the exact completed three-copy cleanup."""
import ast
import json
import os
from pathlib import Path
import stat
import sys
import remove as c

def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')

def main():
    assert Path.cwd()==c.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    packet=c.HERE/'plan-01';assert not packet.exists() and not c.WORK.exists()
    assessment=c.read(c.ASSESSMENT);starts={}
    for name,root in c.ROOTS.items():
        rows,allocated=c.snapshot(root);assert rows==assessment['roots'][name]['entries'] and allocated<=assessment['roots'][name]['allocated_bytes']+16*2**20
        status=c.preserve.validate_outer(name)
        for field in ['supervisor_identity','child_identity']:
            values=status[field].splitlines()[-1].split();assert len(values)>=8
            starts[values[0]]=values[2:7]
    assert set(starts)=={'99781','99784','91736','91753','96831','96835'}
    template=c.read(c.OWNER/'experiments/oxc-runtime-compatibility/strict-cleanup-plan-01/plan.json')
    environment=template['environment'];executors={}
    for name in ['/opt/homebrew/bin/python3','/usr/sbin/lsof','/bin/ps']:
        path=Path(name);resolved=path.resolve(strict=True)
        executors[name]=dict(resolved=str(resolved),route_identity=c.identity(path),file_identity=c.identity(resolved),sha256=c.sha(resolved))
    commands=[dict(label='open-handles-'+name,argv=['/usr/sbin/lsof','-nP','+D',str(root)],expected=[1]) for name,root in c.ROOTS.items()]
    commands.append(dict(label='owned-pids',argv=['/bin/ps','-p',','.join(sorted(starts,key=int)),'-o','pid=,ppid=,pgid=,lstart=,tty=,command='],expected=[0,1]))
    original_dirs={}
    for root in {Path(proof['original']) for row in assessment['roots'].values() for proof in row['roles'].values()}:
        rows,unused=c.snapshot(root,False)
        for name,row in rows.items():
            if stat.S_ISDIR(row['mode']):original_dirs[str(root if name=='.' else root/name)]=row
    packet.mkdir();write(packet/'original-directories.json',original_dirs)
    plan=dict(roots={name:str(root) for name,root in c.ROOTS.items()},owner=str(c.OWNER),source_owner=str(c.R),work=str(c.WORK),
              environment=environment,executors=executors,platform=list(os.uname()),commands=commands,owned_start_times=starts,
              canonical_lock=str(c.owned.CANONICAL_LOCK),wait_seconds=600,minimum_free_gib=9,entries=52548,allocated_observation=4772057088,
              permission_policy='Only exact inventoried duplicate directories lacking owner-write receive S_IWUSR via identity-bound O_NOFOLLOW directory fd; full before/after mode+ctime ledger; no file chmod or original-tree mutation.',
              quiescence_limitation='lsof and old exact process-start checks are point-in-time observations, not a kernel reservation; repeated exact tree guards precede mutation.')
    write(packet/'plan.json',plan)
    files={c.ASSESSMENT,packet/'plan.json',packet/'original-directories.json',c.preserve.WORK/'receipt.json',c.qualified.WORK/'receipt.json',
           c.preserve.ORIGINAL/'manifest.json',c.preserve.ORIGINAL/'evidence.tar.gz',c.preserve.RESULT/'manifest.json',c.preserve.RESULT/'evidence.tar.gz',
           c.OWNER/'.work/completed-source-prefix-preservation-preflight-01.json',
           c.OWNER/'experiments/stable-cgu/owned_stage.py',c.OWNER/'scripts/supervise_experiment.py',
           c.R/'.work/root-completed-source-prefix-assessment-02.json',c.R/'.work/root-completed-prefix-capacity-verification-01.json'}
    files.update(c.HERE/name for name in ['assess.py','preserve.py','preserve-unadmitted-01.py','qualify_preservation.py','remove.py','prepare.py','README.md'])
    files.update(Path(row['resolved']) for row in executors.values())
    for name,root in c.ROOTS.items():
        files.update(root.parent/file for file in ['plan.json','result.json','commands.json','controls.json'])
        files.update(c.preserve.outer(name)/file for file in ['plan.json','status.json','command.log'])
    frozen={}
    for path in sorted(files):
        assert path.resolve(strict=True)==path and path.is_file()
        before=c.identity(path);digest=c.sha(path);assert c.identity(path)==before
        frozen[str(path)]=dict(identity=before,sha256=digest)
        if path.suffix=='.py':ast.parse(path.read_text())
    write(packet/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(c.OWNER/'scripts/supervise_experiment.py'),'--run-id','completed-source-prefix-cleanup-supervisor-01','--',
             '/opt/homebrew/bin/python3','-B',str(c.HERE/'remove.py'),'--inputs-sha256',c.sha(packet/'inputs.json')]
    write(packet/'launch.json',dict(command=command,cwd=str(c.OWNER),environment=environment,owner=str(c.OWNER),review_required_before_execution=True))
    print(json.dumps(dict(packet=str(packet),inputs=len(files),input_bytes=sum(p.stat().st_size for p in files),entries=52548,
                         plan_sha256=c.sha(packet/'plan.json'),freeze_sha256=c.sha(packet/'inputs.json'),launch_sha256=c.sha(packet/'launch.json')),indent=2))
if __name__=='__main__':main()
