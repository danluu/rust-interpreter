#!/usr/bin/env python3
"""Freeze only actual completed producer bytes; never runs a recipe or probe."""
import argparse
import ast
import os
import signal
import time
from pathlib import Path
import sys
import tomllib

import adapter
s=adapter.load("support")
history=adapter.load("history")
prerequisite=adapter.load("prerequisite")

UNUSED=['LLVM_COMPONENTS','LLVM_BIN_DIR','LLVM_FILECHECK','CC','CXX','AR','CC_DEFAULT_FLAGS','CXX_DEFAULT_FLAGS',
        'RUSTDOC','RUSTC_SANITIZER_SUPPORT']


def environments(build,python,directories):
    config=tomllib.loads((s.S/'bootstrap.toml').read_text())
    assert config['build']['jobs']==2 and config['rust']['channel']=='dev'
    assert config['rust']['remap-debuginfo'] is True
    assert all(config['rust'][name] is False for name in ['debug-assertions','debug-assertions-std','debug-assertions-tools'])
    base=dict(build['environment']);assert 'DYLD_LIBRARY_PATH' not in base
    forbidden=['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTC','CARGO',
               'RUSTC_BOOTSTRAP','RUSTC_FORCE_RUSTC_VERSION','RUNNER','REMOTE_TEST_CLIENT','IS_MUSL_HOST',
               '__RUSTC_DEBUG_ASSERTIONS_ENABLED','__STD_DEBUG_ASSERTIONS_ENABLED']
    assert not any(key in base for key in forbidden)
    removed={key:base.pop(key) for key in UNUSED if key in base}
    assert not any(key.startswith(('DYLD_','LD_','RUST_INTERP')) for key in base)
    base.update(TMPDIR=str(s.BASE/'tmp'),RUSTC_FORCE_RUSTC_VERSION='compiletest',RUST_TEST_THREADS='2',
                DOC_RUST_LANG_ORG_CHANNEL='https://doc.rust-lang.org/nightly',RUST_TEST_TMPDIR=str(s.S/'build/tmp'),
                __BOOTSTRAP_JOBS='2',__STD_REMAP_DEBUGINFO_ENABLED='1',PYTHON=str(python),
                SOURCE_ROOT=str(s.S),BUILD_ROOT=str(s.BUILD),TARGET=s.HOST)
    joined=':'.join(directories['loader_directories'])
    compile_env=dict(base,DYLD_LIBRARY_PATH=joined,RUSTC_BOOTSTRAP='-1')
    run_env=dict(base,DYLD_LIBRARY_PATH=':'.join([*joined.split(':'),str(s.D2/'lib/rustlib'/s.HOST/'lib')]),
                 RUSTC_BOOTSTRAP='1',RUSTC=str(s.E2/'bin/rustc'),LD_LIB_PATH_ENVVAR='DYLD_LIBRARY_PATH',
                 HOST_RUSTC_DYLIB_PATH=str(s.E2/'lib'),TARGET_EXE_DYLIB_PATH=str(s.E2/'lib/rustlib'/s.HOST/'lib'),
                 __RMAKE_VERBOSE_SUBPROCESS_OUTPUT='1')
    # Mirror only values used by this recipe/support call graph. The unused
    # C/C++/LLVM/rustdoc/sanitizer values are deliberately not guessed.
    return compile_env,run_env,dict(omitted_unused=UNUSED,removed_from_build=removed,
        proof='Unchanged rmake uses Rustc, run, filesystem and assertions; setup_common, Rustc::new, target, command and run_common do not call C/C++/LLVM/rustdoc/sanitizer helpers.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--independent-build-verification',type=Path,required=True)
    parser.add_argument('--independent-build-verification-sha256',required=True)
    parser.add_argument('--evidence-root',type=Path,action='append',required=True)
    args=parser.parse_args()
    assert sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==s.OWNER
    owned=adapter.monitor().owned
    with owned.workload_lock(owned.CANONICAL_LOCK,600):
        owned.disk(s.OWNER,16)
        signal.alarm(600)
        s.DISCOVERY=dict(files=set(),read_bytes=0)
        try:prepare(args)
        finally:s.DISCOVERY=None;signal.alarm(0)

def prepare(args):
    s.absent(s.WORK);s.absent(s.BASE)
    for name in ['plan.json','inputs.json','launch.json']:s.absent(s.HERE/name)
    consumed=set()
    def consume(path):
        path=Path(path);s.ordinary(path);consumed.add(path);return path
    source=s.source_guard();actual=s.completed_build(consume)
    terminal,compiled,build=actual['terminal'],actual['compiled'],actual['plan']
    verification=args.independent_build_verification
    audit_ref=prerequisite.audit(actual,verification,args.independent_build_verification_sha256,consume)
    compiler_prerequisite=prerequisite.reference(actual,audit_ref)
    m=s.metadata_module();metadata_here=Path(m.__file__).parent;metadata_freeze=s.read(metadata_here/'inputs.json')
    s.ancestor_guard(True)
    assert len(metadata_freeze['files'])<=150000 and len(metadata_freeze['links'])<=20000
    assert all(row['stamp'][3]<=s.MAX_FILE_BYTES for row in metadata_freeze['files'].values())
    assert sum(row['stamp'][3] for row in metadata_freeze['files'].values())<=16*2**30
    assert len(build['metadata_plan']['sdk_inventory'])<=150000
    s.capacity();m.guard(build['metadata_plan'],metadata_freeze,True);s.capacity()
    monitor=adapter.monitor();evidence_roots=tuple(args.evidence_root)
    monitor.evidence_contract(s.WORK,evidence_roots)
    support=s.discover_support();directories=s.directory_contract()
    outputs={str(root):s.inventory(root) for root in [s.D2,s.E2,s.TOOLS]}
    admitted={str(Path(root)/name):{key:row[key] for key in ['sha256','stamp']}
              for root,files in outputs.items() for name,row in files.items() if row['kind']=='file'}
    python=Path(sys.executable).resolve(strict=True)
    compile_env,run_env,environment_proof=environments(build,python,directories)
    argv=[str(s.D2/'bin/rustc'),'-o',str(s.BASE/'rmake')]
    argv.extend('-Ldependency='+name for group in ['host','dependencies'] for name in directories[group]['directories'])
    argv.extend(['--extern','run_make_support='+support['artifacts']['rlib']['path'],'--edition=2024',
                 str(s.S/'tests/run-make/hir-body-cache-capture/rmake.rs'),'-Cprefer-dynamic'])
    if 'rmeta' in support['artifacts']:argv.extend(['--extern','run_make_support='+support['artifacts']['rmeta']['path']])
    argv.append('-Dunused_must_use')
    children=[dict(argv=argv,cwd=str(s.S),environment=compile_env),dict(argv=[str(s.BASE/'rmake')],cwd=str(s.OUT),environment=run_env)]
    # The launch is explicit too; preserve the actual Darwin startup value.
    launch_environment=dict(build['environment'],__CF_USER_TEXT_ENCODING='0x1F5:0x0:0x0')
    assert os.getuid()==501
    selected={str(path):s.file(path) for path in [*sorted(s.HERE.glob('*')),verification,s.BUILT/'receipt.json',s.BUILT/'compiled.json',s.BUILT/'run-make-support-inventory.json',s.BUILT/'run-make-support-producer.json'] if path.is_file()}
    for path in [*(s.S/row['path'] for row in source['source_files']),*(s.S/name for name in s.read(s.HERE/'source-supplement.json')['files'])]:selected[str(path)]=s.file(path)
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name and name.startswith('/Users/danluu/dev/'):
            path=Path(name).resolve(strict=True);selected[str(path)]=s.file(path)
    assert len(selected)<=512 and sum(row['stamp'][3] for row in selected.values())<=32*2**20
    plan=dict(status='prepared-unrun',owner=str(s.OWNER),producer=str(s.BUILT),source_identity=compiled['source_identity'],
              build_receipt_sha256=s.sha(s.BUILT/'receipt.json'),compiled_sha256=s.sha(s.BUILT/'compiled.json'),
              independent_verification=dict(path=str(verification),sha256=s.sha(verification)),compiler_prerequisite=compiler_prerequisite,
              evidence_roots=list(map(str,evidence_roots)),retained_selection=selected,retention_bounds=dict(files=514,bytes=96*2**20),
              discovery_bounds=dict(entry_gib=16,live_gib=9,wait_seconds=600,alarm_seconds=600,unique_read_files=150000,hash_read_bytes=64*2**30,maximum_file_bytes=s.MAX_FILE_BYTES,maximum_json_bytes=s.MAX_JSON_BYTES,tree_entries=s.MAX_TREE_ENTRIES),
              metadata_inputs_sha256=build['metadata_inputs_sha256'],metadata_plan=build['metadata_plan'],
              support=support,directory_contract=directories,outputs=outputs,admitted_provider_files=admitted,
              fixture_copies={name:s.file(s.S/'tests/run-make/hir-body-cache-capture'/name) for name in source['fixture_members'] if name!='rmake.rs'},
              children=children,environment_proof=environment_proof,expected_nested_calls=history.expected_calls(),
              capacity=dict(entry_gib=24,stop_gib=9,floor_gib=8,namespace_allocated_gib=14,evidence_allocated_mib=256),
              canonical_lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock',wait_seconds=600,performance_measurement=False)
    s.write(s.HERE/'plan.json',plan)
    files={}
    def add(path):
        path=Path(path);assert len(files)<4096;row=s.file(path);assert str(path) not in files or files[str(path)]==row;files[str(path)]=row
    for path in s.HERE.glob('*'):
        if path.is_file():add(path)
        if path.suffix=='.py':ast.parse(path.read_text())
    for path in [s.BHERE/'inputs.json',s.BHERE/'plan.json',verification,python,
                 s.OWNER/'scripts/supervise_experiment.py',s.OWNER/'experiments/stable-cgu/owned_stage.py']:
        add(path)
    for path in consumed:add(path)
    for path in selected:add(path)
    add(metadata_here/'inputs.json')
    for path in s.BUILT.rglob('*'):
        if path.is_symlink():raise AssertionError(('producer evidence symlink',path))
        if path.is_file():add(path)
    for name in s.read(s.HERE/'source-supplement.json')['files']:add(s.S/name)
    for module in list(sys.modules.values()):
        path=getattr(module,'__file__',None)
        if path and path.startswith('/Users/danluu/dev/'):add(Path(path).resolve(strict=True))
    s.write(s.HERE/'inputs.json',dict(files=files,python=str(python),plan_sha256=s.sha(s.HERE/'plan.json'),environment=launch_environment))
    s.write(s.HERE/'launch.json',dict(status='prepared-unrun-awaiting-review',owner=str(s.OWNER),environment=launch_environment,
            command=[str(python),'-B',str(s.OWNER/'scripts/supervise_experiment.py'),'--run-id','hir-options-hash-run-make-supervisor-01','--',str(python),'-B',str(s.HERE/'run.py'),'--inputs-sha256',s.sha(s.HERE/'inputs.json')],
            expected_workload_children=2,expected_nested_commands=230,inputs_sha256=s.sha(s.HERE/'inputs.json'),plan_sha256=s.sha(s.HERE/'plan.json'),capacity=plan['capacity']))

if __name__=='__main__':main()
