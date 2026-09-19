#!/usr/bin/env python3
"""Freeze only the original installed documentation duplicate for review."""
import ast
import json
import os
from pathlib import Path
import sys
import cleanup as c
def write(p,value):
    with p.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def main():
    assert Path.cwd()==c.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    assert not c.WORK.exists() and all(not (c.HERE/name).exists() for name in ['plan.json','inputs.json','launch.json'])
    a=c.read(c.ASSESSMENT);assert len(a['entries'])==len(a['retained_entries'])==67312 and len(a['files'])==65826 and a['allocated_bytes']==953249792
    assert c.snapshot(c.ROOT)[0]==a['entries'] and c.snapshot(c.RETAINED)[0]==a['retained_entries']
    prior=c.OWNER/'experiments/oxc-original-llvm-retirement/plan.json';old=c.read(prior)
    retirement=c.OWNER/'.work/oxc-original-llvm-retirement-01/receipt.json';assert c.read(retirement)['status']=='passed'
    plan=dict(owner=str(c.OWNER),root=str(c.ROOT),retained=str(c.RETAINED),entries=67312,files=65826,allocated_bytes=953249792,
        environment=old['environment'],platform=list(os.uname()),executors=old['executors'],
        protected_routes=old['protected_routes'],protected_aliases=old['protected_aliases'],llvm_retirement=str(retirement),
        canonical_lock=str(c.owned.CANONICAL_LOCK),wait_seconds=600,minimum_free_gib=9,
        commands=[dict(label='documentation-handles',argv=['/usr/sbin/lsof','-nP','+D',str(c.ROOT)]),
                  dict(label='original-toolchain-handles',argv=['/usr/sbin/lsof','-nP','+D',str(c.ROOT.parents[2])])],
        scope='Only original completed toolchain share/doc/rust duplicate. All65826 actual files equal independent qualified composed documentation and both historical inventories. No compiler/provider, source, archive, other documentation tree or registry deletion.',
        limitation='Exact lsof point-in-time absence is not a kernel reservation. Full before/after inventory/hash guards and exact nofollow parent-FD removal are required. Historical original toolchain completeness is already retired and is not relabelled.')
    write(c.HERE/'plan.json',plan)
    files={c.ASSESSMENT,prior,retirement,c.HERE/'plan.json',c.OWNER/'.work/assess-oxc-original-docs-01.py',
        c.OWNER/'.work/oxc-original-llvm-retirement-actual-verification-01.json',
        c.OWNER/'experiments/stable-cgu/owned_stage.py',c.OWNER/'scripts/supervise_experiment.py',
        c.OWNER/'experiments/completed-negative-source-cleanup/remove.py',
        c.OWNER/'.work/oxc-native-toolchain-composition-01/composition.json',
        c.OWNER/'experiments/oxc-plugin-normalization/compose_native_toolchain.py',
        c.OWNER/'experiments/oxc-plugin-normalization/native-toolchain-composition-plan-01.json'}
    files.update(Path(name) for name in a['inventory_proofs'])
    files.update(Path(name) for name in a['historical_receipts'])
    files.update(c.HERE/name for name in ['cleanup.py','prepare.py','README.md','fd_methods.txt'])
    files.update(Path(row['resolved']) for row in plan['executors'].values())
    frozen={}
    for p in sorted(files):
        assert p.resolve(strict=True)==p and p.is_file()
        before=c.identity(p);digest=c.sha(p);assert c.identity(p)==before
        frozen[str(p)]=dict(identity=before,sha256=digest)
        if p.suffix=='.py':ast.parse(p.read_text())
    # The actual mutation methods are byte-identical to the already reviewed
    # anchored remover; this creates no new deletion authority or process route.
    def methods(path):
        tree=ast.parse(path.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Cleanup')
        return {n.name:ast.dump(n,include_attributes=False) for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ['remove','writable_directories']}
    assert methods(c.HERE/'cleanup.py')==methods(c.OWNER/'experiments/completed-negative-source-cleanup/remove.py')
    write(c.HERE/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(c.OWNER/'scripts/supervise_experiment.py'),'--run-id','oxc-original-docs-cleanup-supervisor-01','--',
             '/opt/homebrew/bin/python3','-B',str(c.HERE/'cleanup.py'),'--inputs-sha256',c.sha(c.HERE/'inputs.json')]
    write(c.HERE/'launch.json',dict(command=command,cwd=str(c.OWNER),environment=plan['environment'],review_required_before_execution=True))
    print(json.dumps(dict(inputs=len(frozen),input_bytes=sum(p.stat().st_size for p in files),plan_sha256=c.sha(c.HERE/'plan.json'),
        freeze_sha256=c.sha(c.HERE/'inputs.json'),launch_sha256=c.sha(c.HERE/'launch.json')),indent=2))

if __name__=='__main__':main()
