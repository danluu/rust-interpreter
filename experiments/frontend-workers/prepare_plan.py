#!/usr/bin/env python3
"""Freeze source and exact commands; do not build, prepare std, or predict a tool key."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from custom_compiler import require
from compare_saved_runtime import acquire_lock, lock_wait_seconds
from frontend_worker_screen import CAMPAIGN_LOCK
from qualified_public_tools import BINARIES, COMPILER_REVISION, TOOLCHAIN, WORKER_BUILD_POLICY
from workflow_io import write_json


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen-root', type=Path, required=True)
    parser.add_argument('--std-mir-ready', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--qualification-run-id', default='frontend-worker-qualification-01')
    parser.add_argument('--supersedes', type=Path, action='append', default=[])
    parser.add_argument('--lock-wait-seconds', type=lock_wait_seconds, default=600)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Source/ready metadata hashing shares the same campaign admission as the
    # later build. This command never executes compiler, Cargo or test probes.
    require(CAMPAIGN_LOCK.is_file() and CAMPAIGN_LOCK.resolve(strict=True) == CAMPAIGN_LOCK,
            'metadata freeze requires the canonical campaign lock')
    waiting_at = time.time()
    with CAMPAIGN_LOCK.open('a') as lock:
        acquire_lock(lock,args.lock_wait_seconds)
        receipt_path = args.output.with_suffix('.process.json')
        require(not receipt_path.exists() and not receipt_path.is_symlink(), 'metadata receipt already exists')
        receipt = dict(schema_version=1,status='running',kind='source-metadata-only',
            pid=os.getpid(),parent_pid=os.getppid(),cwd=os.getcwd(),command=sys.argv,
            lock=str(CAMPAIGN_LOCK),waiting_at=waiting_at,started_at=time.time(),workloads_executed=0)
        write_json(receipt_path,receipt)
        try:
            freeze(args)
            receipt.update(status='passed',plan_sha256=sha(args.output))
        except BaseException as error:
            receipt.update(status='failed',error=str(error))
            raise
        finally:
            receipt['finished_at']=time.time()
            write_json(receipt_path,receipt)


def freeze(args):
    import re
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.qualification_run_id), 'invalid qualification run ID')
    owner = args.screen_root.resolve(strict=True)
    ready_path = args.std_mir_ready.resolve(strict=True)
    ready = json.loads(ready_path.read_bytes()); identity = ready['identity']
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    require(ready['owner'] == str(owner) and ready_path == owner / '.work/std-mir' / key / 'ready.json'
            and not any(k in identity for k in ['compiler_key','cargo','namespace','source_sha256']),
            'worker plan requires the existing public std owned by the future qualifier/screen')
    require(not args.output.exists() and args.output.parent.is_dir(), 'plan output must be new')
    superseded = []
    for previous in args.supersedes:
        previous = previous.resolve(strict=True)
        require(previous.parent == Path(__file__).resolve().parent and previous.name.startswith('planned-build-'),
                'superseded plan is outside the owned worker experiment')
        payload = previous.read_bytes(); prior = json.loads(payload)
        require(prior['owner'] == str(ROOT) and prior['status'] == 'not-executed'
                and prior['workloads_executed'] == 0 and prior['tool_key'] is None
                and not Path(prior['commands'][0]['receipt']).parent.exists(),
                'only an unexecuted owned plan can be superseded')
        superseded.append(dict(path=str(previous),sha256=hashlib.sha256(payload).hexdigest(),
            status='superseded-not-executed',source_revision=prior['production_source_revision']))
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    subprocess.check_call(['git','diff','--exit-code',revision,'--','Cargo.toml','Cargo.lock','rust-toolchain.toml','crates'],cwd=ROOT)
    work = ROOT / '.work' / args.run_id
    require(not work.exists() and not work.is_symlink(), 'build destination already exists')
    target = work / 'target'; public = Path.home() / '.rustup/toolchains' / TOOLCHAIN
    tool_paths = [ROOT/'Cargo.toml', ROOT/'Cargo.lock']
    for crate in ['bytecode','mir-export']:
        tool_paths += sorted((ROOT/'crates'/crate).rglob('*.rs'))
        tool_paths.append(ROOT/'crates'/crate/'Cargo.toml')
    workspace = [ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'rust-toolchain.toml',
                 *sorted(p for p in (ROOT/'crates').rglob('*') if p.is_file())]
    require(not any(p.is_symlink() for p in [*workspace,*tool_paths]), 'source inventory contains a symlink')
    source_key = hashlib.sha256(b''.join(str(p.relative_to(ROOT)).encode()+b'\0'+p.read_bytes() for p in tool_paths)).hexdigest()
    relative = lambda paths: {str(p.relative_to(ROOT)):sha(p) for p in paths}
    harness = [*sorted((ROOT/'scripts').glob('*.py')),
        *sorted(p for p in Path(__file__).parent.rglob('*') if p.is_file() and p.suffix in ['.py','.md','.rs','.toml','.lock']),
        ROOT/'benchmarks/experiments/host-proc-macro/build.py', ROOT/'benchmarks/corpus.json',
        *[ROOT/'tests'/name for name in ['test_frontend_workers.py','test_frontend_worker_screen.py',
            'test_frontend_worker_publication.py','test_qualified_public_tools.py','test_public_tool_publication.py']],
        *[ROOT/'benchmarks/experiments/strict-warm-build'/name for name in
            ['screen.py','PROTOCOL.md','FRONTEND_WORKERS_SCREEN.md','assess_owned_screen.py']]]
    env = dict(CARGO_TERM_COLOR='never',CARGO_TERM_VERBOSE='true',CARGO_INCREMENTAL='0',
        CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',CARGO_PROFILE_RELEASE_DEBUG='1',
        RUSTC=str(public/'bin/rustc'),RUSTDOC=str(public/'bin/rustdoc'),RUSTUP_TOOLCHAIN=TOOLCHAIN)
    common = ['--release','--locked','--offline','--jobs','2','--target-dir',str(target)]
    commands = [
        ('public-rustc-identity',[str(public/'bin/rustc'),'-vV']),
        ('public-cargo-identity',[str(public/'bin/cargo'),'-vV']),
        ('rust-workspace-tests',[str(public/'bin/cargo'),'test',*common,'--workspace']),
        ('release-tools',[str(public/'bin/cargo'),'build',*common,'-p','rust-interp-bytecode','-p','rust-interp-mir-export','--bins']),
        ('launcher-contracts',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_frontend_workers.py','-v']),
        ('screen-contracts',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_frontend_worker_screen.py','-v']),
        ('capabilities',[str(target/'release/rust-interp-mir-export'),'--rust-interp-capabilities']),
        ('wrapper-capabilities',[str(target/'release/rust-interp-rustc-wrapper'),'--rust-interp-frontend-worker-capability'])]
    contract = Path(__file__).with_name('PUBLICATION.md')
    project = owner/'.work/sources/nushell-frontend-workers'
    qualification = owner / '.work' / args.qualification_run_id
    require(not qualification.exists() and not qualification.is_symlink(), 'qualification destination already exists')
    plan = dict(schema_version=2,kind='source-only-build-qualification-plan',status='not-executed',
        qualification_policy=WORKER_BUILD_POLICY,owner=str(ROOT),screen_owner=str(owner),
        superseded_plans=superseded,
        production_source_revision=revision,public_compiler_source_revision=COMPILER_REVISION,
        source_input_key=source_key,source_input_paths=[str(p.relative_to(ROOT)) for p in tool_paths],
        tool_sources=relative(tool_paths),workspace_sources=relative(workspace),harness=relative(harness),
        tool_key=None,screen_command=None,shared_std=dict(path=str(ready_path),sha256=sha(ready_path),
            key=key,identity=identity,compiler=identity['compiler'],target=identity['target']),
        clean_environment=dict(remove_prefixes=['RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_'],
            remove=['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','CARGO_BUILD_RUSTC','RUSTC_WRAPPER',
                'RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET',
                'RUST_TEST_THREADS','RUSTDOC','CARGO','RUSTUP_TOOLCHAIN'],reject_prefixes=['LD_','DYLD_'],overrides=env),
        commands=[dict(label=label,argv=argv,cwd=str(ROOT),receipt=str(work/(label+'-process.json')),
            stdout=str(work/(label+'.stdout')),stderr=str(work/(label+'.stderr'))) for label,argv in commands],
        workload_admission=dict(lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock',wait_seconds=600,
            tool_build_minimum_free_gib=12,per_command_minimum_free_gib=8),
        publication=dict(composition_kind='qualified-public-toolset-v1',contract=str(contract.relative_to(ROOT)),
            contract_sha256=sha(contract),source_binaries={name:str(target/'release'/name) for name in BINARIES}),
        worker_qualification=dict(python=sys.executable,run_dir=str(qualification),result=str(qualification/'result.json'),
            expected_commands=30,status='pending-final-published-key',same_source_and_shared_std_required=True),
        project_preparation=dict(destination=str(project),revision='9d3157963241cf89447119d34d6e887859f5e7e8',
            owner_marker=dict(owner=str(owner),revision='9d3157963241cf89447119d34d6e887859f5e7e8')),
        screen_request=dict(python=sys.executable,driver=str(owner/'benchmarks/experiments/strict-warm-build/screen.py'),
            run_id='strict-warm-frontend-worker-screen-01',source=str(project),candidate_policy='frontend-workers',
            std_mir_ready=str(ready_path),lock_wait_seconds=45,materialize_to=str(work/'screen-command.json')),
        implementation_contract_tests=dict(status='not-executed',patterns=['test_qualified_public_tools.py',
            'test_public_tool_publication.py','test_frontend_worker_publication.py'],expected_tests=[5,5,2],canonical_lock_required=True),
        final_qualification=False,performance_claim=False,screen_ready=False,workloads_executed=0)
    write_json(args.output,plan)
    print(json.dumps(dict(path=str(args.output),sha256=sha(args.output),source_input_key=source_key,tool_key=None,workloads_executed=0)))


if __name__ == '__main__':
    main()
