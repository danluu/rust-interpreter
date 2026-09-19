#!/usr/bin/env python3
"""Freeze completed original-toolchain retirement evidence, without running it."""
import ast
import json
import os
from pathlib import Path
import sys
import archive as a
def write(p,value):
    with p.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def main():
    assert Path.cwd()==a.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    for p in [a.HERE/'plan.json',a.HERE/'inputs.json',a.HERE/'launch.json',a.WORK,a.RESULT]:assert not p.exists() and not p.is_symlink()
    paths=set()
    for stem in ['oxc-original-llvm-retirement','oxc-original-docs-cleanup']:
        for root in [a.OWNER/'experiments'/stem,a.OWNER/'.work'/(stem+'-01'),a.OWNER/'.work/experiments'/(stem+'-supervisor-01')]:
            assert root.resolve(strict=True)==root
            for p in root.rglob('*'):
                assert not p.is_symlink()
                if p.is_file():paths.add(p)
        for suffix in ['actual.json','stdout','stderr']:paths.add(a.OWNER/'.work'/(stem+'-launch-01.'+suffix))
        paths.add(a.OWNER/'.work'/(stem+'-actual-verification-01.json'))
        paths.add(a.OWNER/'.work'/('verify-'+stem+'-01.py'))
    for name in ['oxc-original-llvm-provider-capacity-assessment-01.json','oxc-original-docs-capacity-assessment-01.json','assess-oxc-original-docs-01.py',
                 'oxc-llvm-tools-acquisition-01/component-proof.json','oxc-llvm-tools-acquisition-01/receipt.json',
                 'oxc-native-toolchain-composition-01/composition.json','oxc-native-toolchain-composition-01/toolchain-inventory.json',
                 'oxc-native-toolchain-composition-01/native-toolchain-identity.json','oxc-acquisition-continuation-01/toolchain-inventory.json',
                 'oxc-native-toolchain-composition-continuation-01/receipt.json','oxc-native-compatibility-01/receipt.json',
                 'oxc-native-compatibility-02/receipt.json','oxc-runtime-strict-compatibility-01/receipt.json']:
        paths.add(a.OWNER/'.work'/name)
    paths.update(a.HERE/name for name in ['archive.py','prepare.py','README.md'])
    paths.update(a.OWNER/name for name in ['experiments/stable-cgu/owned_stage.py','scripts/supervise_experiment.py',
        'experiments/completed-negative-source-cleanup/remove.py','experiments/completed-negative-source-cleanup/assess.py',
        'experiments/completed-source-prefix-cleanup/assess.py','experiments/oxc-plugin-normalization/compose_native_toolchain.py',
        'experiments/oxc-plugin-normalization/native-toolchain-composition-plan-01.json'])
    root=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
    for name in ['root-original-llvm-retirement-plan-verification-01.json','root-original-docs-cleanup-plan-verification-01.json']:
        paths.add(root/'.work'/name)
    references={}
    for directory in [a.OWNER/'.work/oxc-llvm-tools-acquisition-01',a.OWNER/'results/oxc-native-compatibility-01']:
        names=['llvm-tools.tar.xz','component-proof.json'] if directory.name=='oxc-llvm-tools-acquisition-01' else ['evidence.tar.gz','manifest.json']
        references[str(directory)]={name:dict(bytes=(directory/name).stat().st_size,sha256=a.sha(directory/name)) for name in names}
        paths.add(directory/names[1])
    passed=[a.OWNER/'.work'/name/'receipt.json' for name in ['oxc-original-llvm-retirement-01','oxc-original-docs-cleanup-01']]
    assert all(a.read(p)['status']=='passed' for p in passed)
    environment=a.read(a.OWNER/'experiments/oxc-original-docs-cleanup/plan.json')['environment']
    members={str(p).lstrip('/'):dict(source=str(p),bytes=p.stat().st_size,sha256=a.sha(p)) for p in sorted(paths)}
    plan=dict(owner=str(a.OWNER),members=members,prior_artifact_archives=references,passed_receipts=[str(p) for p in passed],
        environment=environment,platform=list(os.uname()),canonical_lock=str(a.owned.CANONICAL_LOCK),wait_seconds=600,minimum_free_gib=9,
        executor=dict(path='/opt/homebrew/bin/python3',resolved=str(Path('/opt/homebrew/bin/python3').resolve(strict=True)),route_identity=a.identity(Path('/opt/homebrew/bin/python3'))),
        archive_limit_bytes=32*2**20,maximum_logical_bytes=192*2**20,children=0,
        member_count=len(members),logical_bytes=sum(row['bytes'] for row in members.values()),
        scope='Retain completed original native01 LLVM retirement and duplicate-documentation cleanup. Explicitly incomplete original toolchain; current R/X and qualified composed providers/documentation unchanged. Reference existing official component and historical native archive payloads without duplication.')
    assert plan['member_count']<=128 and plan['logical_bytes']<plan['maximum_logical_bytes']
    write(a.HERE/'plan.json',plan)
    files=set(paths)|{a.HERE/'plan.json',Path('/opt/homebrew/bin/python3').resolve(strict=True)}
    for directory,rows in references.items():files.update(Path(directory)/name for name in rows)
    frozen={}
    for p in sorted(files):
        assert p.resolve(strict=True)==p and p.is_file()
        before=a.identity(p);digest=a.sha(p);assert a.identity(p)==before
        frozen[str(p)]=dict(identity=before,sha256=digest)
        if p.suffix=='.py':ast.parse(p.read_text())
    write(a.HERE/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(a.OWNER/'scripts/supervise_experiment.py'),'--run-id','oxc-original-retirement-evidence-supervisor-01','--',
             '/opt/homebrew/bin/python3','-B',str(a.HERE/'archive.py'),'--inputs-sha256',a.sha(a.HERE/'inputs.json')]
    write(a.HERE/'launch.json',dict(command=command,cwd=str(a.OWNER),environment=environment,review_required_before_execution=True))
    print(json.dumps(dict(members=len(members),logical_bytes=plan['logical_bytes'],inputs=len(files),plan_sha256=a.sha(a.HERE/'plan.json'),
        freeze_sha256=a.sha(a.HERE/'inputs.json'),launch_sha256=a.sha(a.HERE/'launch.json')),indent=2))

if __name__=='__main__':main()
