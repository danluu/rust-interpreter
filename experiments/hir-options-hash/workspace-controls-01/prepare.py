#!/usr/bin/env python3
"""Read-only producer discovery and freeze; never executes Cargo or a compiler."""
import ast
import json
from pathlib import Path
import sys

import run as r

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
def put(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')

def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==r.OWNER
    assert not r.WORK.exists() and not r.FIXTURE.exists() and not r.FIXTURE.is_symlink()
    assert (r.HERE/'controls.py').read_bytes()==(ROOT/'experiments/generated-workspace-isolation/controls.py').read_bytes()
    terminal,original=r.failed_history()
    metadata=r.read(r.b.MRESULT/'receipt.json');assert metadata['status']=='passed' and metadata['compiler_builds']==0
    assert metadata['metadata_sha256']==r.sha(r.b.MRESULT/'metadata.json')
    assert r.sha(r.b.MHERE/'inputs.json')==original['metadata_inputs_sha256']
    provider=r.providers(original)
    environment=original['environment']
    assert 'DYLD_LIBRARY_PATH' not in environment
    outer=r.FIXTURE/'outer';inner=outer/'.work/generated/source';bootstrap=inner/'src/bootstrap'
    paths=[outer,bootstrap,outer,bootstrap,inner,outer/'orphan'];expected=[0,101,0,0,0,101]
    child_environment=dict(environment,CARGO_NET_OFFLINE='true',CARGO_HOME=str(r.FIXTURE/'cargo-home'),CARGO_TARGET_DIR=str(r.FIXTURE/'target'),RUSTC=str(r.D2/'bin/rustc'))
    children=[dict(label=label,argv=[str(r.D2/'bin/cargo'),'metadata','--offline','--no-deps','--format-version','1','--manifest-path',str(path/'Cargo.toml')],cwd=str(path),environment=child_environment,expected_returncode=rc)
              for label,path,rc in zip(r.controls.LABELS,paths,expected,strict=True)]
    plan=dict(status='prepared-unrun',owner=str(r.OWNER),fixture=str(r.FIXTURE),environment=environment,children=children,providers=provider,
              failed_build_receipt=dict(path=str(r.FAILED/'receipt.json'),sha256=r.sha(r.FAILED/'receipt.json')),
              metadata_inputs_sha256=original['metadata_inputs_sha256'],metadata_plan=original['metadata_plan'],
              source_revision=original['candidate_revision'],source_identity=original['source_identity'],
              capacity=dict(entry_gib=16,stop_gib=9,floor_gib=8,fixture_allocated_mib=4,evidence_allocated_mib=256),
              canonical_lock=str(r.owned.CANONICAL_LOCK),wait_seconds=600,compiler_builds=0)
    put(r.HERE/'plan.json',plan)
    files={}
    def add(path):
        path=Path(path);row=r.m.file(path);assert str(path) not in files or files[str(path)]==row;files[str(path)]=row
    original_freeze=r.read(r.BHERE/'inputs.json')
    assert r.sha(r.BHERE/'plan.json')==original_freeze['plan_sha256']
    for path,expected in original_freeze['files'].items():
        assert r.m.file(Path(path))==expected,path
        add(path)
    for path in [*r.HERE.glob('*'),r.BHERE/'inputs.json',r.BHERE/'plan.json',r.OWNER/'Cargo.toml',
                 ROOT/'experiments/generated-workspace-isolation/controls.py',ROOT/'experiments/generated-workspace-isolation/README.md',
                 r.b.MRESULT/'receipt.json',r.b.MRESULT/'metadata.json']:
        if path.is_file():add(path)
        if path.suffix=='.py':ast.parse(path.read_text())
    for path in r.FAILED.rglob('*'):
        if path.is_file():add(path)
        elif path.is_symlink():raise AssertionError(('unexpected failed evidence link',path))
    for path in (r.OWNER/'.work/experiments/hir-options-hash-compiler-build-supervisor-01').rglob('*'):
        if path.is_file():add(path)
        elif path.is_symlink():raise AssertionError(('unexpected outer evidence link',path))
    for root in [r.b.MHERE,r.b.CHERE]:
        for path in root.glob('*.py'):add(path)
    for path,row in provider['seed_files'].items():
        if row['kind']=='file':add(path)
    python=Path(sys.executable).resolve(strict=True);add(python)
    freeze=dict(files=files,python=str(python),plan_sha256=r.sha(r.HERE/'plan.json'),environment=environment,
                inherited_metadata_inputs_sha256=plan['metadata_inputs_sha256'])
    put(r.HERE/'inputs.json',freeze)
    launch=dict(status='prepared-unrun-awaiting-review',owner=str(r.OWNER),environment=environment,
                command=[str(python),'-B',str(r.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-workspace-controls-supervisor-01','--',str(python),'-B',str(r.HERE/'run.py'),'--inputs-sha256',r.sha(r.HERE/'inputs.json')],
                plan_sha256=r.sha(r.HERE/'plan.json'),inputs_sha256=r.sha(r.HERE/'inputs.json'),helper_sha256=r.sha(r.HERE/'run.py'),expected_children=6,compiler_builds=0,capacity=plan['capacity'])
    put(r.HERE/'launch.json',launch)
    print(json.dumps(dict(launch_sha256=r.sha(r.HERE/'launch.json'),inputs_sha256=launch['inputs_sha256'],plan_sha256=launch['plan_sha256'],files=len(files),children=6),indent=2))
if __name__=='__main__':main()
