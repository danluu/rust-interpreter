#!/usr/bin/env python3
"""Assess the retained successful Cargo run; no compiler/benchmark subprocesses."""
from __future__ import annotations
import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('development_coverage',HERE/'coverage.py')
coverage=importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)
ROOT=coverage.ROOT
sha,require,write=coverage.sha,coverage.require,coverage.write_json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--plan-sha256',required=True)
    args=parser.parse_args()
    out=ROOT/'.work/hir-owner-development-assessment-01';out.mkdir(exist_ok=False)
    run=ROOT/'.work/hir-owner-development-coverage-01'
    setup=ROOT/'.work/hir-owner-development-setup-03'
    record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),
                lock=str(coverage.LOCK),lock_wait_seconds=600,compiler_commands=0,benchmark=False)
    write(out/'result.json',record);print(json.dumps(record),flush=True)
    try:
        with coverage.workload_lock(coverage.LOCK,600):
            record['lock_acquired_at']=time.time();write(out/'result.json',record)
            require(sha(setup/'plan.json')==args.plan_sha256,'original plan changed')
            plan=json.loads((setup/'plan.json').read_text())
            original=json.loads((run/'result.json').read_text())
            require(original['status']=='failed' and original['cargo_commands']==1
                    and original['plan_sha256']==args.plan_sha256
                    and original['error']=="RuntimeError('missing selected test/normal compile configurations')",
                    'not the retained reporting-only failure')
            command=json.loads((run/'cargo-check/receipt.json').read_text())
            require(command['returncode']==0 and command['command']==plan['command']
                    and command['cwd']==plan['cwd'] and command['environment']==plan['environment'],
                    'original complete native Cargo command did not pass')
            for stream in ('stdout','stderr'):
                require(sha(run/'cargo-check'/stream)==command[stream+'_sha256'],'raw Cargo output changed')
            for name,expected in plan['frozen_proofs'].items():
                path=run/'runner.py' if name==str(HERE/'coverage.py') else Path(name)
                require(sha(path)==expected,'original frozen input changed: '+name)
            coverage.tools()
            require(coverage.configurations(Path(plan['source']),plan['environment'])==plan['cargo_configurations'],
                    'original Cargo configuration changed')
            require(coverage.source_inventory(Path(plan['source']),out,plan['environment'],'retained-source')==
                    json.loads((setup/'source-inventory.json').read_text()),'original source changed')
            generated=coverage.QUALIFIED/'source/diagnostic/generated.json'
            reasons=json.loads(generated.read_text())
            summary=coverage.aggregate(run/'reports')
            by_invocation=[]; identities={};total=Counter();rejections=Counter()
            for path in sorted((run/'reports').glob('*.json')):
                r=json.loads(path.read_text());identities[path.name]=sha(path)
                require(r['gate_sha256']==reasons['gate_sha256'] and r['candidate_patch_sha256']==reasons['patch_sha256'],
                        'raw report gate binding differs')
                if not r['after_expansion_seen']:continue
                require(r['effective_sysroot']==str(coverage.PUBLIC),'raw report compiler sysroot differs')
                require(len(r['owners'])==r['resolver_owners'] and sum(c['owners'] for c in r['counts'].values())==r['resolver_owners']
                        and sum(r['reasons'].values())==r['resolver_owners'],'owner/row denominator differs')
                require(Counter(x['reason'] for x in r['owners'])==r['reasons'],'raw owner reasons differ')
                kinds=Counter(x['kind'] for x in r['owners'])
                for kind,c in r['counts'].items():
                    rows=[x for x in r['owners'] if x['kind']==kind]
                    require(kinds[kind]==c['owners'] and sum(x['input_eligible'] for x in rows)==c['input_eligible']
                            and sum(x['key_budget_eligible'] for x in rows)==c['key_budget_eligible'],
                            'raw owner eligibility counts differ')
                group=next(g for g in summary['groups'].values() if path.name in g['reports'])
                item=dict(report=path.name,crate=r['crate_name'],role=group['role'],pid=r['pid'],
                    incremental_session=r['incremental_session'],resolver_owners=r['resolver_owners'],
                    eligible=sum(c['input_eligible'] for c in r['counts'].values()),
                    free_functions=r['counts'].get('function',{}),reasons=r['reasons'])
                by_invocation.append(item)
                total.update(invocations=1,resolver_owners=item['resolver_owners'],input_eligible=item['eligible'])
                for c in r['counts'].values():
                    total.update(key_budget_eligible=c['key_budget_eligible'],eligible_source_bytes=c['eligible_source_bytes'],
                                 encoded_input_bytes=c['encoded_input_bytes'],encoded_candidate_key_bytes=c['encoded_candidate_key_bytes'])
                rejections.update(r['reasons'])
            summary.update(per_invocation=by_invocation,totals=dict(total),reasons=dict(rejections),
                report_files=identities,reason_sites=reasons['reason_sites'],invocation_weighted=True,
                missing_owners=0,instrumentation_mismatches=0,source_unchanged=True,
                interpretation='Exact input gate upper bound; output capture and cache hits are unmeasured.')
            write(out/'coverage.json',summary)
            record.update(status='passed',finished_at=time.time(),plan_sha256=args.plan_sha256,
                original_result=dict(path=str(run/'result.json'),sha256=sha(run/'result.json')),
                original_command=dict(path=str(run/'cargo-check/receipt.json'),sha256=sha(run/'cargo-check/receipt.json')),
                original_runner_sha256=sha(run/'runner.py'),corrected_runner_sha256=sha(HERE/'coverage.py'),
                assessor_sha256=sha(Path(__file__)),source_inventory_sha256=plan['source_inventory_sha256'],
                coverage_sha256=sha(out/'coverage.json'),reports=len(identities),totals=dict(total),
                reporting_correction='harness=false target test role recognizes exact --cfg test; no Cargo replay',
                source_unchanged=True,checking_preserved=True,cache_hits=False,strict_14_test_workflow=False,
                benchmark=False,compiler_commands=0)
            write(out/'result.json',record);print(json.dumps(record),flush=True)
    except BaseException as error:
        record.update(status='failed',error=repr(error),finished_at=time.time());write(out/'result.json',record);raise

if __name__=='__main__':main()
