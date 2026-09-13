#!/usr/bin/env python3
"""Native development body-v2 coverage with fresh outputs; never a timing gate."""
from __future__ import annotations
import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'experiments/hir-owner-reuse/development/coverage.py'
spec=importlib.util.spec_from_file_location('body_development_io',BASE)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
b.QUALIFIED=ROOT/'.work/hir-body-coverage-native-01'
b.DRIVER_SHA='ae65fd5f5207e62c121ba070fe3e8dd8f6ecb2b2252235634e63e021cd3d1167'
GATE_SHA='6df8b5b4fe1c0c88f6c21acbbf0514a61b48173bd037456b7563755c50ca15d1'
SOURCE_SETUP=ROOT/'.work/hir-owner-development-setup-03'
SETUP=ROOT/'.work/hir-body-development-setup-01'
RUN=ROOT/'.work/hir-body-development-coverage-01'
sha,require,write=b.sha,b.require,b.write_json


def aggregate(directory):
    groups={};probes=[];files={};by_invocation=[]
    for path in sorted(directory.glob('*.json')):
        r=json.loads(path.read_text());files[path.name]=sha(path)
        require(r['policy']=='hir-body-input-coverage-v2' and r['gate_sha256']==GATE_SHA
                and r['compiler_commit']=='cea272fa356e94bd2ee2cadf376630aa0683867a','report identity differs')
        require(not r['problems'] and not r['cache_effects_qualified'] and not r['hir_ids_observed']
                and not r['benchmark'] and not r['cache_hits_measured'],'report diagnostic scope differs')
        if not r['after_expansion_seen']:
            require(not r['coverage_usable'],'probe claims coverage');probes.append(path.name);continue
        require(r['coverage_usable'] and r['ordinary_compiler_succeeded'] and r['after_analysis_seen']
                and r['unvisited_resolver_owners']==0,'incomplete normal compilation or owner coverage')
        require(len(r['owners'])==r['resolver_owners']==sum(x['owners'] for x in r['counts'].values())
                and Counter(x['reason'] for x in r['owners'])==r['reasons'],'owner/reason counts differ')
        require(sum(x['structural_body_input_eligible'] for x in r['owners'])==
                sum(c.get('input_eligible',0) for c in r['counts'].values()),'eligibility counts differ')
        argv=r['compiler_argv']
        test='--test' in argv or '--cfg=test' in argv or any(a=='--cfg' and v=='test' for a,v in zip(argv,argv[1:]))
        role='test' if test else 'build-script' if r['crate_name']=='build_script_build' else 'normal'
        key=r['crate_name']+'|'+role
        group=groups.setdefault(key,dict(crate=r['crate_name'],role=role,invocations=0,incremental_sessions=0,
            resolver_owners=0,counts={},reasons={},reports=[]))
        group['invocations']+=1;group['incremental_sessions']+=int(r['incremental_session'])
        group['resolver_owners']+=r['resolver_owners'];group['reports'].append(path.name)
        for kind,count in r['counts'].items():
            total=group['counts'].setdefault(kind,{})
            for name,value in count.items():total[name]=total.get(name,0)+value
        for name,count in r['reasons'].items():group['reasons'][name]=group['reasons'].get(name,0)+count
        by_invocation.append(dict(report=path.name,crate=r['crate_name'],role=role,pid=r['pid'],
            incremental_session=r['incremental_session'],resolver_owners=r['resolver_owners'],counts=r['counts'],reasons=r['reasons']))
    require('nu_protocol|test' in groups and 'nu_protocol|normal' in groups,'selected normal/test configuration missing')
    return dict(policy='hir-body-input-coverage-v2',groups=groups,per_invocation=by_invocation,probes=probes,report_files=files,
        invocation_weighted=True,missing_owners=0,benchmark=False,cache_effects_qualified=False,hir_ids_observed=False,cache_hits=False,
        note='Structural/resolved input eligibility only; first rejection counts do not estimate gains from widening.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','run']);parser.add_argument('--plan-sha256')
    args=parser.parse_args();out=SETUP if args.stage=='prepare' else RUN;out.mkdir(parents=True,exist_ok=False)
    receipt=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),stage=args.stage,
        canonical_lock=str(b.LOCK),wait_seconds=600,cargo_commands=0,benchmark=False)
    write(out/'result.json',receipt);print(json.dumps(receipt),flush=True)
    try:
        with b.workload_lock(b.LOCK,600):
            receipt.update(lock_acquired_at=time.time(),status='running',free_bytes=b.disk(ROOT,16));write(out/'result.json',receipt)
            old=json.loads((SOURCE_SETUP/'plan.json').read_text());source=Path(old['source']);env=b.environment()
            require(sha(SOURCE_SETUP/'source-inventory.json')==old['source_inventory_sha256'],'old source proof changed')
            require(b.source_inventory(source,out,env,'source-before')==json.loads((SOURCE_SETUP/'source-inventory.json').read_text()),'owned source changed')
            require(b.capture_command(out,'source-head',['git','-C',source,'rev-parse','HEAD'],ROOT,env).strip()==b.REVISION,'source revision changed')
            b.capture_command(out,'source-clean',['git','-C',source,'diff','--exit-code','HEAD','--'],ROOT,env)
            require(b.configurations(source,env)==old['cargo_configurations'],'default source Cargo config changed')
            tool=b.tools()
            if args.stage=='prepare':
                frozen={str(p):sha(p) for p in [Path(__file__),BASE,SOURCE_SETUP/'plan.json',SOURCE_SETUP/'source-inventory.json',
                    b.QUALIFIED/'result.json',b.QUALIFIED/'plan.json',b.QUALIFIED/'driver.json',b.QUALIFIED/'compiler-inputs.json',b.QUALIFIED/'compiler-libraries.json']}
                for directory in (b.QUALIFIED/'source',b.HELPERS):
                    frozen.update({str(p):sha(p) for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
                cargo_env=dict(env,RUSTC=str(b.PUBLIC/'bin/rustc'),RUSTC_WRAPPER=tool['path'],RUSTC_WORKSPACE_WRAPPER='',
                    CARGO_TARGET_DIR=str(RUN/'target'),HIR_BODY_COVERAGE_WRAPPER='1',HIR_BODY_COVERAGE_OUTPUT=str(RUN/'reports'))
                plan=dict(policy='hir-body-input-coverage-v2',source=str(source),source_revision=b.REVISION,source_inventory_sha256=old['source_inventory_sha256'],
                    driver=tool['path'],driver_sha256=b.DRIVER_SHA,gate_sha256=GATE_SHA,environment=cargo_env,
                    command=[str(b.PUBLIC/'bin/cargo'),'check','--locked','--offline','--jobs','2','--package','nu-protocol','--lib','--tests'],
                    cwd=str(source),target=str(RUN/'target'),reports=str(RUN/'reports'),frozen_proofs=frozen,
                    cargo_configurations=old['cargo_configurations'],canonical_lock=str(b.LOCK),lock_wait_seconds=600,
                    admission_gib=16,running_floor_gib=8,benchmark=False,strict_14_test_workflow=False,holdout=False,
                    cache_effects_qualified=False,hir_ids_observed=False)
                write(out/'plan.json',plan);receipt['plan_sha256']=sha(out/'plan.json')
            else:
                require(sha(SETUP/'plan.json')==args.plan_sha256,'plan identity differs')
                plan=json.loads((SETUP/'plan.json').read_text())
                for name,expected in plan['frozen_proofs'].items():require(sha(Path(name))==expected,'frozen proof changed: '+name)
                env=plan['environment'];reports=RUN/'reports';reports.mkdir()
                wrapped=b.capture_command(out,'wrapper-probe',[tool['path'],b.PUBLIC/'bin/rustc','-vV'],source,env)
                normal=b.capture_command(out,'ordinary-probe',[b.PUBLIC/'bin/rustc','-vV'],source,env)
                require(wrapped==normal,'exact public wrapper probe differs')
                files=list(reports.glob('*.json'));require(len(files)==1 and not json.loads(files[0].read_text())['coverage_usable'],'wrapper probe differs')
                receipt['cargo_commands']=1;receipt['plan_sha256']=args.plan_sha256;write(out/'result.json',receipt)
                command=b.owned_run(plan['command'],cwd=source,env=env,out=out/'cargo-check',capacity_root=ROOT)
                b.tools();require(b.configurations(source,env)==plan['cargo_configurations'],'Cargo config changed')
                require(b.source_inventory(source,out,env,'source-after')==json.loads((SOURCE_SETUP/'source-inventory.json').read_text()),'source changed')
                b.capture_command(out,'source-after-clean',['git','-C',source,'diff','--exit-code','HEAD','--'],ROOT,env)
                for name,expected in plan['frozen_proofs'].items():require(sha(Path(name))==expected,'frozen proof changed during run: '+name)
                summary=aggregate(reports);write(out/'coverage.json',summary)
                receipt.update(cargo_pid=command['pid'],cargo_exit=command['returncode'],reports=len(summary['report_files']),
                    source_unchanged=True,coverage_sha256=sha(out/'coverage.json'))
            receipt.update(status='passed',completed_at=time.time());write(out/'result.json',receipt);print(json.dumps(receipt),flush=True)
    except BaseException as error:
        receipt.update(status='failed',error=repr(error),completed_at=time.time());write(out/'result.json',receipt);raise

if __name__=='__main__':main()
