#!/usr/bin/env python3
"""Isolated native Nushell test-configuration input-gate coverage, not timing."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
PUBLIC=Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
DONOR=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/sources/nushell-frontend-workers')
REVISION='9d3157963241cf89447119d34d6e887859f5e7e8'
DRIVER_SHA='a0b17054036457f4fece952ba9f470f90bac610da4e4e9446a72c9bb16987efd'
QUALIFIED=ROOT/'.work/hir-owner-coverage-01'
HELPERS=ROOT/'.work/hir-owner-coverage-setup-01/helpers'
DESTINATION=ROOT/'.work/sources/nushell-hir-owner-coverage-01'
LOCK=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
sys.path.insert(0,str(HELPERS))
from owned_stage import workload_lock, run as owned_run, disk
from workflow_io import capture, write_json
from custom_cargo_libraries import library_state
from toolchain_lookup import _stamp


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def require(value,message):
    if not value:raise RuntimeError(message)


def environment():
    # Ordinary native development defaults: fail on ambient flag/profile overrides
    # instead of silently counteracting them. Cargo receives its unchanged project
    # configuration and the explicit diagnostic compiler/target selection below.
    names={'PATH','HOME','USER','LOGNAME','TMPDIR','LANG','LC_ALL','SHELL','TERM','CARGO_HOME',
           'RUSTUP_HOME','SDKROOT','DEVELOPER_DIR','MACOSX_DEPLOYMENT_TARGET'}
    bad=[k for k,v in os.environ.items() if v and
         (k.startswith(('LD_','DYLD_','CARGO_PROFILE_','CARGO_ENCODED_', 'HIR_')) or k in
          {'RUSTFLAGS','RUSTDOCFLAGS','RUSTC_LOG','RUSTC_BOOTSTRAP','RUSTC_FORCE_RUSTC_VERSION',
           'RUSTC_OVERRIDE_VERSION_STRING','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER'})]
    require(not bad,'inherited compiler/profile overrides: '+', '.join(sorted(bad)))
    return {k:v for k,v in os.environ.items() if k in names}


def capture_command(base,label,command,cwd,env):
    child,stdout,stderr=capture([str(x) for x in command],cwd=cwd,env=env,
        receipt_path=base/(label+'.process.json'),receipt={'label':label,'environment':env})
    (base/(label+'.stdout')).write_text(stdout)
    (base/(label+'.stderr')).write_text(stderr)
    require(child.returncode==0,label+' failed')
    return stdout


def source_inventory(source,base,env,label):
    names=capture_command(base,label+'-files',['git','-C',source,'ls-files','-z'],ROOT,env).split('\0')
    result={}
    tracked=set(names)
    for name in names:
        if not name:continue
        path=source/name
        if path.is_symlink():
            link=os.readlink(path)
            target=path.resolve(strict=True)
            require(not Path(link).is_absolute() and target.is_relative_to(source),
                    'source symlink is not relative and in-checkout: '+name)
            record={'kind':'symlink','link_text':link,'sha256':hashlib.sha256(os.fsencode(link)).hexdigest(),
                    'resolved_relative':str(target.relative_to(source))}
            if target.is_dir():
                members={}
                for member in sorted(target.rglob('*')):
                    require(not member.is_symlink(),'nested symlink in directory alias: '+name)
                    relative=str(member.relative_to(source))
                    require(member.is_dir() or (member.is_file() and relative in tracked),
                            'untracked/nonregular directory alias member: '+relative)
                    members[str(member.relative_to(target))]=({'kind':'directory'} if member.is_dir() else
                        {'kind':'file','sha256':sha(member),'bytes':member.stat().st_size})
                require(members,'empty directory alias has no tracked source proof: '+name)
                record.update(resolved_kind='directory',resolved_members=members)
            else:
                require(target.is_file() and str(target.relative_to(source)) in tracked,
                        'source symlink target is not a tracked regular file: '+name)
                record.update(resolved_kind='file',resolved_sha256=sha(target),resolved_bytes=target.stat().st_size)
            result[name]=record
        else:
            require(path.is_file(),'unexpected tracked source entry: '+name)
            result[name]={'kind':'file','sha256':sha(path),'bytes':path.stat().st_size}
    return result


def configurations(source,env):
    records={}
    for parent in (source,*source.parents):
        for name in ('config','config.toml'):
            path=parent/'.cargo'/name
            records[str(path)]=sha(path) if path.is_file() else None
    cargo_home=Path(env.get('CARGO_HOME',str(Path(env['HOME'])/'.cargo')))
    for name in ('config','config.toml'):
        path=cargo_home/name
        records[str(path)]=sha(path) if path.is_file() else None
    # Config includes add unbounded inherited precedence. Existing checked input
    # has none; fail closed rather than pretend it is covered by the ancestor list.
    import tomllib
    for name,identity in records.items():
        if identity is not None:
            require('include' not in tomllib.loads(Path(name).read_text()),'unbound Cargo configuration include')
    return records


def tools(rehash=True):
    result=json.loads((QUALIFIED/'result.json').read_text())
    require(result['status']=='passed' and result['binary_sha256']==DRIVER_SHA,'driver qualification changed')
    tool=json.loads((QUALIFIED/'driver.json').read_text())
    require(sha(Path(tool['path']))==DRIVER_SHA,'actual driver changed')
    records=json.loads((QUALIFIED/'compiler-inputs.json').read_text())['files']
    for item in records:
        path=Path(item['path'])
        require(_stamp(path)==item['stamp'],'public input stamp changed: '+str(path))
        if rehash:require(sha(path)==item['sha256'],'public input bytes changed: '+str(path))
    libraries=json.loads((QUALIFIED/'compiler-libraries.json').read_text())['subjects']
    for item in (tool,libraries['rustc'],libraries['cargo']):
        require(library_state(item['identity'])==item['state'],'compiler/driver/Cargo loader state changed')
    return tool


def prepare(args):
    out=ROOT/f'.work/hir-owner-development-setup-{args.setup_attempt}'
    out.mkdir(parents=True,exist_ok=False)
    env=environment()
    receipt={'status':'waiting','pid':os.getpid(),'parent_pid':os.getppid(),'started_at':time.time(),
             'lock':str(LOCK),'donor':str(DONOR),'destination':str(DESTINATION),'cargo_commands':0}
    write_json(out/'result.json',receipt)
    print(json.dumps(receipt),flush=True)
    try:
        with workload_lock(LOCK,600):
            receipt.update(status='running',lock_acquired_at=time.time(),free_bytes=disk(ROOT))
            write_json(out/'result.json',receipt)
            previous=None
            if args.reuse_source_setup:
                previous=args.reuse_source_setup.resolve(strict=True)
                old=json.loads(previous.read_text())
                require(old['status']=='failed' and old['cargo_commands']==0
                        and old['destination']==str(DESTINATION) and old['donor']==str(DONOR),
                        'previous source-only attempt is not this owned clone')
                require(DESTINATION.is_dir(),'previous clone is absent')
                receipt['previous_source_setup']={'path':str(previous),'sha256':sha(previous)}
            else:
                require(not DESTINATION.exists(),'source destination already exists')
            marker=json.loads((DONOR/'.rust-interp-owned.json').read_text())
            require(marker['revision']==REVISION and marker['owner']==str(DONOR.parents[2]),'donor ownership mismatch')
            require(capture_command(out,'donor-head',['git','-C',DONOR,'rev-parse','HEAD'],ROOT,env).strip()==REVISION,
                    'donor revision differs')
            capture_command(out,'donor-tracked-clean',['git','-C',DONOR,'diff','--exit-code','HEAD','--'],ROOT,env)
            if previous is None:
                DESTINATION.parent.mkdir(parents=True,exist_ok=True)
                capture_command(out,'clone',['git','clone','--no-local','--no-hardlinks','--no-checkout',DONOR,DESTINATION],ROOT,env)
                capture_command(out,'checkout',['git','-C',DESTINATION,'checkout','--detach',REVISION],ROOT,env)
            require(capture_command(out,'source-head',['git','-C',DESTINATION,'rev-parse','HEAD'],ROOT,env).strip()==REVISION,
                    'owned source revision differs')
            require(not (DESTINATION/'.git/objects/info/alternates').exists(),'clone depends on alternate objects')
            require(not capture_command(out,'clean',['git','-C',DESTINATION,'status','--porcelain'],ROOT,env).strip(),'clone not clean')
            inventory=source_inventory(DESTINATION,out,env,'source')
            write_json(out/'source-inventory.json',inventory)
            tool=tools()
            target=ROOT/'.work/hir-owner-development-coverage-01/target'
            reports=ROOT/'.work/hir-owner-development-coverage-01/reports'
            cargo_env=dict(env,RUSTC=str(PUBLIC/'bin/rustc'),RUSTC_WRAPPER=tool['path'],RUSTC_WORKSPACE_WRAPPER='',
                CARGO_TARGET_DIR=str(target),HIR_OWNER_COVERAGE_WRAPPER='1',HIR_OWNER_COVERAGE_OUTPUT=str(reports))
            command=[str(PUBLIC/'bin/cargo'),'check','--locked','--offline','--jobs','2','--package','nu-protocol','--lib','--tests']
            proofs={str(p):sha(p) for p in [QUALIFIED/'result.json',QUALIFIED/'plan.json',QUALIFIED/'driver.json',
                QUALIFIED/'compiler-inputs.json',QUALIFIED/'compiler-libraries.json',Path(__file__)]}
            for directory in (QUALIFIED/'source',HELPERS):
                proofs.update({str(p):sha(p) for p in sorted(directory.rglob('*')) if p.is_file() and '__pycache__' not in p.parts})
            plan={'policy':'development-native-hir-input-coverage-v1','status':'prepared-awaiting-retirement-handoff',
                'source_setup':str(out),'previous_source_setup':receipt.get('previous_source_setup'),
                'source':str(DESTINATION),'source_revision':REVISION,'source_inventory_sha256':sha(out/'source-inventory.json'),
                'compiler_commit':'cea272fa356e94bd2ee2cadf376630aa0683867a','driver':tool['path'],'driver_sha256':DRIVER_SHA,
                'command':command,'cwd':str(DESTINATION),'environment':cargo_env,'target':str(target),'reports':str(reports),
                'cargo_configurations':configurations(DESTINATION,env),'frozen_proofs':proofs,
                'lock':str(LOCK),'lock_wait_seconds':600,'cargo_admission_minimum_gib':16,'running_floor_gib':8,
                'scope':'native development check of nu-protocol library and tests with default features/profile',
                'benchmark':False,'strict_14_test_workflow':False,'cache_hits':False,'holdout':False}
            write_json(out/'plan.json',plan)
            receipt.update(status='passed',completed_at=time.time(),plan_sha256=sha(out/'plan.json'),files=len(inventory))
            write_json(out/'result.json',receipt)
            print(json.dumps(receipt),flush=True)
    except BaseException as error:
        receipt.update(status='failed',error=repr(error),completed_at=time.time())
        write_json(out/'result.json',receipt);raise


def aggregate(reports):
    groups={}; probes=[]
    for path in sorted(reports.glob('*.json')):
        report=json.loads(path.read_text())
        require(not report['problems'],'driver instrumentation disagreement')
        require(report['compiler_commit']=='cea272fa356e94bd2ee2cadf376630aa0683867a','report compiler differs')
        if not report['after_expansion_seen']:
            require(not report['coverage_usable'],'compiler probe reported coverage')
            probes.append(path.name);continue
        require(report['ordinary_compiler_succeeded'] and report['after_analysis_seen'] and report['coverage_usable'],
                'ordinary compiler invocation has unusable coverage: '+path.name)
        require(report['unvisited_resolver_owners']==0,'unexplained owner gap')
        argv=report['compiler_argv']
        # A target with harness=false is checked with `--cfg test`, not `--test`
        # (pinned Cargo src/compiler/mod.rs:1484-1498). Match exact argument pairs;
        # `--check-cfg cfg(test)` and feature values must not classify as tests.
        test='--test' in argv or '--cfg=test' in argv or any(
            option=='--cfg' and value=='test' for option,value in zip(argv,argv[1:]))
        role='test' if test else 'build-script' if report['crate_name']=='build_script_build' else 'normal'
        key=report['crate_name']+'|'+role
        group=groups.setdefault(key,{'crate':report['crate_name'],'role':role,'invocations':0,'resolver_owners':0,
             'counts':{},'reasons':{},'reports':[],'incremental_sessions':0})
        group['invocations']+=1;group['resolver_owners']+=report['resolver_owners']
        group['incremental_sessions']+=int(report['incremental_session']);group['reports'].append(path.name)
        for kind,count in report['counts'].items():
            total=group['counts'].setdefault(kind,{name:0 for name in count})
            for name,value in count.items():total[name]+=value
        for reason,value in report['reasons'].items():group['reasons'][reason]=group['reasons'].get(reason,0)+value
    require('nu_protocol|test' in groups and 'nu_protocol|normal' in groups,'missing selected test/normal compile configurations')
    return {'groups':groups,'compiler_probes':probes,'input_gate_only':True,'benchmark':False,'cache_hits':False}


def execute(args):
    require(args.retirement_receipt is not None,'explicit completed retirement receipt is required before Cargo admission')
    setup=ROOT/f'.work/hir-owner-development-setup-{args.setup_attempt}'
    require(sha(setup/'plan.json')==args.plan_sha256,'prepared admission hash differs')
    retirement=args.retirement_receipt.resolve(strict=True)
    retired=json.loads(retirement.read_text())
    require(retired.get('status') in ('passed','complete'),'retirement is not recorded complete')
    plan=json.loads((setup/'plan.json').read_text())
    out=Path(plan['target']).parent;out.mkdir(parents=True,exist_ok=False)
    receipt={'status':'waiting','pid':os.getpid(),'parent_pid':os.getppid(),'started_at':time.time(),
        'plan_sha256':args.plan_sha256,'retirement_receipt':str(retirement),'retirement_sha256':sha(retirement),
        'benchmark':False,'cargo_commands':0}
    write_json(out/'result.json',receipt)
    print(json.dumps(receipt),flush=True)
    try:
        with workload_lock(LOCK,600):
            disk(ROOT,16)
            receipt.update(status='running',lock_acquired_at=time.time())
            write_json(out/'result.json',receipt)
            for name,expected in plan['frozen_proofs'].items():require(sha(Path(name))==expected,'frozen proof changed: '+name)
            tools()
            source=Path(plan['source']);env=plan['environment']
            require(configurations(source,env)==plan['cargo_configurations'],'Cargo configuration changed')
            require(source_inventory(source,out,env,'before')==json.loads((setup/'source-inventory.json').read_text()),'source changed')
            reports=Path(plan['reports']);reports.mkdir()
            wrapper=capture_command(out,'wrapper-probe',[plan['driver'],PUBLIC/'bin/rustc','-vV'],source,env)
            ordinary=capture_command(out,'ordinary-probe',[PUBLIC/'bin/rustc','-vV'],source,env)
            require(wrapper==ordinary and 'commit-hash: '+plan['compiler_commit'] in wrapper,'public wrapper probe differs')
            records=list(reports.glob('*.json'))
            require(len(records)==1 and not json.loads(records[0].read_text())['coverage_usable'],'wrapper probe was not isolated')
            receipt['cargo_commands']=1;write_json(out/'result.json',receipt)
            command=owned_run(plan['command'],cwd=source,env=env,out=out/'cargo-check',capacity_root=ROOT)
            tools()
            require(configurations(source,env)==plan['cargo_configurations'],'Cargo configuration changed during check')
            require(source_inventory(source,out,env,'after')==json.loads((setup/'source-inventory.json').read_text()),'source changed during check')
            capture_command(out,'after-tracked-clean',['git','-C',source,'diff','--exit-code','HEAD','--'],ROOT,env)
            for name,expected in plan['frozen_proofs'].items():require(sha(Path(name))==expected,'frozen proof changed: '+name)
            summary=aggregate(reports);write_json(out/'coverage.json',summary)
            receipt.update(status='passed',completed_at=time.time(),source_unchanged=True,groups=len(summary['groups']),
                report_count=len(list(reports.glob('*.json'))),cargo_pid=command['pid'],cargo_exit=command['returncode'])
            write_json(out/'result.json',receipt);print(json.dumps(receipt),flush=True)
    except BaseException as error:
        receipt.update(status='failed',error=repr(error),completed_at=time.time())
        write_json(out/'result.json',receipt);raise


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['prepare','run'])
    parser.add_argument('--plan-sha256')
    parser.add_argument('--setup-attempt',default='01')
    parser.add_argument('--reuse-source-setup',type=Path)
    parser.add_argument('--retirement-receipt',type=Path)
    args=parser.parse_args()
    require(args.setup_attempt.isdigit() and len(args.setup_attempt)==2,'invalid setup attempt')
    (prepare if args.stage=='prepare' else execute)(args)

if __name__=='__main__':main()
