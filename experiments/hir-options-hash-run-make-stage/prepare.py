#!/usr/bin/env python3
"""Freeze only actual completed producer bytes; never runs a recipe or probe."""
import argparse
import ast
import os
from pathlib import Path
import sys
import tomllib

import history
import support as s

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
    args=parser.parse_args()
    assert sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==s.OWNER
    s.absent(s.WORK);s.absent(s.BASE)
    source=s.source_guard();terminal,compiled,build=s.completed_build()
    verification=args.independent_build_verification
    s.ordinary(verification);assert s.sha(verification)==args.independent_build_verification_sha256
    independent=s.read(verification)
    assert independent['status']=='verified' and independent['children']==25 and independent['compiler_stages']==8
    assert independent['receipt_sha256']==s.sha(s.BUILT/'receipt.json')
    assert independent['compiled_sha256']==s.sha(s.BUILT/'compiled.json')
    b=s.build_module();metadata_freeze=s.read(b.MHERE/'inputs.json')
    s.ancestor_guard(True)
    b.m.guard(build['metadata_plan'],metadata_freeze,True)
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
    plan=dict(status='prepared-unrun',owner=str(s.OWNER),producer=str(s.BUILT),source_identity=compiled['source_identity'],
              build_receipt_sha256=s.sha(s.BUILT/'receipt.json'),compiled_sha256=s.sha(s.BUILT/'compiled.json'),
              independent_verification=dict(path=str(verification),sha256=s.sha(verification)),
              metadata_inputs_sha256=build['metadata_inputs_sha256'],metadata_plan=build['metadata_plan'],
              support=support,directory_contract=directories,outputs=outputs,admitted_provider_files=admitted,
              fixture_copies={name:s.file(s.S/'tests/run-make/hir-body-cache-capture'/name) for name in source['fixture_members'] if name!='rmake.rs'},
              children=children,environment_proof=environment_proof,expected_nested_calls=history.expected_calls(),
              capacity=dict(entry_gib=24,stop_gib=9,floor_gib=8,namespace_allocated_gib=14,evidence_allocated_mib=256),
              canonical_lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock',wait_seconds=600,performance_measurement=False)
    s.write(s.HERE/'plan.json',plan)
    files={}
    def add(path):
        path=Path(path);row=s.file(path);assert str(path) not in files or files[str(path)]==row;files[str(path)]=row
    for path in s.HERE.glob('*'):
        if path.is_file():add(path)
        if path.suffix=='.py':ast.parse(path.read_text())
    for path in [s.BHERE/'inputs.json',s.BHERE/'plan.json',verification,python,
                 s.OWNER/'scripts/supervise_experiment.py',s.OWNER/'experiments/stable-cgu/owned_stage.py']:
        add(path)
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
