#!/usr/bin/env python3
"""Prepare one-file retirement; no child process or deletion."""
import ast
import json
import os
from pathlib import Path
import sys
import retire as c

def write(p,value):
    with p.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def record(p):
    assert p.resolve(strict=True)==p and p.is_file()
    before=c.ident(p);digest=c.sha(p);assert c.ident(p)==before
    return dict(identity=before,sha256=digest)
def main():
    assert Path.cwd()==c.OWNER and sys.dont_write_bytecode and not sys.flags.optimize
    assert not c.WORK.exists() and all(not (c.HERE/n).exists() for n in ['plan.json','inputs.json','launch.json'])
    assessment=c.read(c.ASSESSMENT)
    assert c.ident(c.TARGET)==assessment['identity'] and c.sha(c.TARGET)==assessment['sha256']
    assert c.TARGET.stat().st_blocks*512==assessment['allocated_bytes']==139567104
    protected={Path(p) for p in assessment['independent_qualified_copies']}
    R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
    X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
    key='7610e295912b132303c95db6a587f9288c03a7f84b691de8ea60093e2829622a'
    installed=R/'.work/interpreter-tools'/key
    protected.update(installed/name for name in ['compiler.json','capabilities.json','ready.json','rust-interp-mir-export','rust-interp-rustc-wrapper','rust-interp-vm'])
    runtime=R/'.work/runtime-compilers/eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03/sysroot'
    protected.add(runtime/'bin/rustc');protected.update((runtime/'lib').glob('*.dylib'))
    D=X/'.work/hir-options-hash-compiler-01/source/build/aarch64-apple-darwin'
    protected.update(D/name for name in ['stage0/bin/rustc','stage0/bin/cargo','ci-llvm/bin/llvm-config'])
    protected.update((D/'stage0/lib').glob('*.dylib'));protected.update((D/'ci-llvm/lib').glob('*.dylib'))
    aliases={str(p):dict(identity=c.ident(p),target=os.readlink(p),resolved=str(p.resolve(strict=True))) for p in protected if p.is_symlink()}
    protected={p.resolve(strict=True) for p in protected}
    routes={str(p):record(p) for p in sorted(protected)}
    assert all(not Path(p).is_relative_to(c.PREFIX) for p in routes)
    for name,proof in assessment['independent_qualified_copies'].items():assert routes[name]==proof
    histories={}
    for name in ['oxc-native-compatibility-01','oxc-native-compatibility-02','oxc-native-toolchain-composition-continuation-01','oxc-runtime-strict-compatibility-01']:
        p=c.OWNER/'.work'/name/'receipt.json';row=c.read(p);assert row['status']=='passed'
        histories[str(p)]=dict(sha256=c.sha(p),status=row['status'],finished_at=row['finished_at'])
    environment=c.read(c.OWNER/'experiments/completed-negative-source-cleanup/plan-01/plan.json')['environment']
    executors={}
    for name in ['/opt/homebrew/bin/python3','/usr/sbin/lsof']:
        p=Path(name);resolved=p.resolve(strict=True)
        executors[name]=dict(resolved=str(resolved),route_identity=c.ident(p),file_identity=c.ident(resolved),sha256=c.sha(resolved))
    plan=dict(owner=str(c.OWNER),target=str(c.TARGET),parent_identity=c.ident(c.TARGET.parent),allocated_bytes=139567104,
        official_archive=str(assessment['archive']),archive_member=assessment['archive_member'],inventory=assessment['original_inventory']['path'],
        protected_routes=routes,protected_aliases=aliases,historical_receipts=histories,environment=environment,platform=list(os.uname()),executors=executors,
        commands=[dict(label='exact-file-handles',argv=['/usr/sbin/lsof','-nP',str(c.TARGET)]),
                  dict(label='original-toolchain-handles',argv=['/usr/sbin/lsof','-nP','+D',str(c.PREFIX)])],
        canonical_lock=str(c.owned.CANONICAL_LOCK),wait_seconds=600,minimum_free_gib=9,
        scope='Retire exactly the original completed native01 LLVM provider. The original private toolchain becomes incomplete. No historical guard may be skipped or relabelled, and reusing that original toolchain requires restoration/requalification. Preserve official component archive, both qualified composed copies and the independently keyed R/X routes.',
        limitation='Point-in-time lsof absence is not a kernel reservation. Held nofollow parent/file descriptors and repeated exact identity/hash guards anchor the single unlink. No process signaling or other provider mutation.')
    write(c.HERE/'plan.json',plan)
    files={c.ASSESSMENT,c.HERE/'plan.json',Path(assessment['archive']),Path(assessment['original_inventory']['path'])}
    files.update(c.HERE/name for name in ['retire.py','prepare.py','README.md'])
    files.update(c.OWNER/name for name in ['scripts/supervise_experiment.py','experiments/stable-cgu/owned_stage.py',
        '.work/oxc-llvm-tools-acquisition-01/receipt.json','.work/oxc-llvm-tools-acquisition-01/component-proof.json',
        '.work/oxc-native-toolchain-composition-01/composition.json',
        '.work/oxc-native-toolchain-composition-01/toolchain-inventory.json',
        '.work/oxc-native-toolchain-composition-01/native-toolchain-identity.json'])
    files.update(Path(name) for name in histories)
    files.update(Path(row['resolved']) for row in executors.values())
    for directory in ['oxc-native-compatibility-01','oxc-native-compatibility-02','oxc-runtime-strict-compatibility-01']:
        files.add(c.OWNER/'results'/directory/'manifest.json')
    frozen={}
    for p in sorted(files):
        frozen[str(p)]=record(p)
        if p.suffix=='.py':ast.parse(p.read_text())
    write(c.HERE/'inputs.json',dict(files=frozen))
    command=['/opt/homebrew/bin/python3','-B',str(c.OWNER/'scripts/supervise_experiment.py'),'--run-id','oxc-original-llvm-retirement-supervisor-01','--',
             '/opt/homebrew/bin/python3','-B',str(c.HERE/'retire.py'),'--inputs-sha256',c.sha(c.HERE/'inputs.json')]
    write(c.HERE/'launch.json',dict(command=command,cwd=str(c.OWNER),environment=environment,review_required_before_execution=True))
    print(json.dumps(dict(inputs=len(frozen),protected_routes=len(routes),plan_sha256=c.sha(c.HERE/'plan.json'),
        freeze_sha256=c.sha(c.HERE/'inputs.json'),launch_sha256=c.sha(c.HERE/'launch.json')),indent=2))

if __name__=='__main__':main()
