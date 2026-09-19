#!/usr/bin/env python3
"""Freeze only the completed six-negative cleanup evidence for retention."""
import ast
import json
import os
from pathlib import Path
import sys
import archive as a

def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')

def main():
    assert Path.cwd()==a.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    for path in [a.HERE/'plan.json',a.HERE/'inputs.json',a.HERE/'launch.json',a.WORK,a.RESULT]:assert not path.exists() and not path.is_symlink()
    paths=set()
    for relative in ['experiments/completed-negative-source-cleanup','.work/completed-negative-source-cleanup-01',
                     '.work/experiments/completed-negative-source-cleanup-supervisor-01']:
        root=a.OWNER/relative;assert root.resolve(strict=True)==root
        for path in root.rglob('*'):
            assert not path.is_symlink()
            if path.is_file():paths.add(path)
    for name in ['completed-negative-source-assessment-01.json','completed-negative-source-cleanup-actual-verification-01.json',
                 'verify-completed-negative-source-cleanup-01.py']:
        paths.add(a.OWNER/'.work'/name)
    for suffix in ['actual.json','stdout','stderr']:paths.add(a.OWNER/'.work'/('completed-negative-source-cleanup-launch-01.'+suffix))
    paths.update(a.HERE/name for name in ['archive.py','prepare.py','README.md'])
    paths.update(a.OWNER/name for name in ['experiments/stable-cgu/owned_stage.py','scripts/supervise_experiment.py',
        'experiments/completed-source-prefix-cleanup/assess.py'])
    root=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
    paths.add(root/'.work/root-negative-source-cleanup-plan-verification-01.json')
    references={}
    for directory in [a.OWNER/'results/completed-negative-source-preservation-01',a.OWNER/'results/completed-source-prefix-preservation-01',
                      root/'results/mono-production-source-observables-02']:
        references[str(directory)]={name:dict(bytes=(directory/name).stat().st_size,sha256=a.sha(directory/name)) for name in ['evidence.tar.gz','manifest.json']}
        paths.add(directory/'manifest.json')
    passed=a.OWNER/'.work/completed-negative-source-cleanup-01/receipt.json'
    audit=a.read(a.OWNER/'.work/completed-negative-source-cleanup-actual-verification-01.json')
    assert a.read(passed)['status']=='passed' and audit['status']=='verified' and audit['receipt_sha256']==a.sha(passed)
    assert audit['exact_deleted_entries']==27657 and audit['retained_original_files']==7340
    environment=a.read(a.OWNER/'experiments/completed-negative-source-cleanup/plan-01/plan.json')['environment']
    members={str(path).lstrip('/'):dict(source=str(path),bytes=path.stat().st_size,sha256=a.sha(path)) for path in sorted(paths)}
    plan=dict(owner=str(a.OWNER),members=members,prior_artifact_archives=references,passed_receipts=[str(passed)],
        environment=environment,platform=list(os.uname()),canonical_lock=str(a.owned.CANONICAL_LOCK),wait_seconds=600,minimum_free_gib=9,
        executor=dict(path='/opt/homebrew/bin/python3',resolved=str(Path('/opt/homebrew/bin/python3').resolve(strict=True)),route_identity=a.identity(Path('/opt/homebrew/bin/python3'))),
        archive_limit_bytes=32*2**20,maximum_logical_bytes=192*2**20,children=0,
        member_count=len(members),logical_bytes=sum(row['bytes'] for row in members.values()),
        scope='Retain completed six-negative cleanup evidence only; reference three separately retained archive payloads without duplication.')
    assert plan['member_count']<=128 and plan['logical_bytes']<plan['maximum_logical_bytes']
    write(a.HERE/'plan.json',plan)
    files=set(paths)|{a.HERE/'plan.json',Path('/opt/homebrew/bin/python3').resolve(strict=True)}
    for directory in references:files.update(Path(directory)/name for name in ['evidence.tar.gz','manifest.json'])
    frozen={}
    for path in sorted(files):
        assert path.resolve(strict=True)==path and path.is_file()
        before=a.identity(path);digest=a.sha(path);assert a.identity(path)==before
        frozen[str(path)]=dict(identity=before,sha256=digest)
        if path.suffix=='.py':ast.parse(path.read_text())
    write(a.HERE/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(a.OWNER/'scripts/supervise_experiment.py'),'--run-id','completed-negative-source-evidence-supervisor-01','--',
             '/opt/homebrew/bin/python3','-B',str(a.HERE/'archive.py'),'--inputs-sha256',a.sha(a.HERE/'inputs.json')]
    write(a.HERE/'launch.json',dict(command=command,cwd=str(a.OWNER),environment=environment,review_required_before_execution=True))
    print(json.dumps(dict(members=len(members),logical_bytes=plan['logical_bytes'],inputs=len(files),
        plan_sha256=a.sha(a.HERE/'plan.json'),freeze_sha256=a.sha(a.HERE/'inputs.json'),launch_sha256=a.sha(a.HERE/'launch.json')),indent=2))

if __name__=='__main__':main()
