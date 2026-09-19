#!/usr/bin/env python3
"""Prepare, never execute, a closed evidence-only archive."""
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
    roots=['experiments/completed-source-prefix-cleanup','experiments/oxc-native-first-target-cleanup',
        '.work/completed-source-prefix-cleanup-01','.work/oxc-native-first-target-cleanup-01',
        '.work/experiments/completed-source-prefix-cleanup-supervisor-01','.work/experiments/oxc-native-first-target-cleanup-supervisor-01',
        '.work/completed-source-prefix-preservation-01','.work/completed-source-prefix-preservation-admission-02',
        '.work/completed-capacity-evidence-unrun-01','.work/completed-capacity-evidence-unrun-02']
    for name in roots:
        root=a.OWNER/name;assert root.resolve(strict=True)==root
        for path in root.rglob('*'):
            assert not path.is_symlink()
            if path.is_file():paths.add(path)
    for name in ['completed-source-prefix-assessment-01.json','completed-source-prefix-preservation-preflight-01.json',
        'completed-source-prefix-cleanup-actual-verification-01.json','oxc-native-first-target-assessment-01.json',
        'oxc-native-first-target-cleanup-actual-verification-01.json','verify-oxc-native-first-target-cleanup-01.py']:
        paths.add(a.OWNER/'.work'/name)
    for stem in ['completed-source-prefix-cleanup-launch-01','oxc-native-first-target-cleanup-launch-01']:
        for suffix in ['actual.json','stdout','stderr']:paths.add(a.OWNER/'.work'/(stem+'.'+suffix))
    paths.update(a.HERE/name for name in ['archive.py','prepare.py','README.md'])
    paths.update(a.OWNER/name for name in ['experiments/stable-cgu/owned_stage.py','scripts/supervise_experiment.py'])
    R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
    for name in ['root-completed-prefix-capacity-verification-01.json','root-completed-prefix-retention-verification-01.json',
        'root-completed-prefix-cleanup-plan-verification-01.json','root-oxc-native-first-target-cleanup-plan-verification-01.json']:
        paths.add(R/'.work'/name)
    references={}
    for directory in [a.OWNER/'results/completed-source-prefix-preservation-01',a.OWNER/'results/oxc-native-first-target-preservation-01',
                      a.OWNER/'results/oxc-native-compatibility-01',R/'results/mono-production-source-observables-02']:
        references[str(directory)]={name:dict(bytes=(directory/name).stat().st_size,sha256=a.sha(directory/name)) for name in ['evidence.tar.gz','manifest.json']}
        paths.add(directory/'manifest.json')
    assert sum(path.stat().st_size for path in paths)<192*2**20
    passed=[a.OWNER/'.work'/name/'receipt.json' for name in ['completed-source-prefix-cleanup-01','oxc-native-first-target-cleanup-01']]
    assert all(a.read(path)['status']=='passed' for path in passed)
    environment=a.read(a.OWNER/'experiments/oxc-native-first-target-cleanup/plan-01/plan.json')['environment']
    members={str(path).lstrip('/'):dict(source=str(path),bytes=path.stat().st_size,sha256=a.sha(path)) for path in sorted(paths)}
    plan=dict(owner=str(a.OWNER),members=members,prior_artifact_archives=references,passed_receipts=[str(path) for path in passed],
        environment=environment,platform=list(os.uname()),canonical_lock=str(a.owned.CANONICAL_LOCK),wait_seconds=600,minimum_free_gib=9,
        executor=dict(path='/opt/homebrew/bin/python3',resolved=str(Path('/opt/homebrew/bin/python3').resolve(strict=True)),route_identity=a.identity(Path('/opt/homebrew/bin/python3'))),
        archive_limit_bytes=32*2**20,maximum_logical_bytes=192*2**20,children=0,
        member_count=len(members),logical_bytes=sum(row['bytes'] for row in members.values()),
        scope='Retain completed cleanup evidence only; no archive payload duplicated from four separately retained result directories.')
    write(a.HERE/'plan.json',plan)
    files=set(paths)|{a.HERE/'plan.json',Path('/opt/homebrew/bin/python3').resolve(strict=True)}
    for directory in references:
        files.update(Path(directory)/name for name in ['evidence.tar.gz','manifest.json'])
    frozen={}
    for path in sorted(files):
        assert path.resolve(strict=True)==path and path.is_file()
        before=a.identity(path);digest=a.sha(path);assert a.identity(path)==before
        frozen[str(path)]=dict(identity=before,sha256=digest)
        if path.suffix=='.py':ast.parse(path.read_text())
    write(a.HERE/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(a.OWNER/'scripts/supervise_experiment.py'),'--run-id','completed-capacity-evidence-supervisor-01','--',
             '/opt/homebrew/bin/python3','-B',str(a.HERE/'archive.py'),'--inputs-sha256',a.sha(a.HERE/'inputs.json')]
    write(a.HERE/'launch.json',dict(command=command,cwd=str(a.OWNER),environment=environment,review_required_before_execution=True))
    print(json.dumps(dict(members=len(members),logical_bytes=sum(row['bytes'] for row in members.values()),inputs=len(files),
        plan_sha256=a.sha(a.HERE/'plan.json'),freeze_sha256=a.sha(a.HERE/'inputs.json'),launch_sha256=a.sha(a.HERE/'launch.json')),indent=2))

if __name__=='__main__':main()
