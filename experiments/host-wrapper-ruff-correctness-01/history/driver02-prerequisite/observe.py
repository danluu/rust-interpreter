#!/usr/bin/env python3
"""Observe the ordinary 24-command Ruff correctness history and saved verifier."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ('plan-sha256','inputs-sha256','sources-sha256'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args();here=Path(__file__).resolve().parent
    manifest=here/'sources.json';payload=manifest.read_bytes()
    if hashlib.sha256(payload).hexdigest()!=args.sources_sha256:
        raise RuntimeError('source manifest changed')
    sources=json.loads(payload);source=here/'prepare.py'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=sources['files'][str(source)]:
        raise RuntimeError('preparation helper changed')
    spec=importlib.util.spec_from_file_location('_host_ruff_correctness_prepare',source)
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    checked={};source_ref=dict(path=str(manifest),sha256=args.sources_sha256)
    p.authenticate(source_ref,checked)
    plan_ref=dict(path=str(p.PACKET/'plan.json'),sha256=args.plan_sha256)
    plan=p.pinned(plan_ref,checked)
    frozen=p.pinned(dict(path=str(p.PACKET/'inputs.json'),sha256=args.inputs_sha256))
    p.require(plan['policy']=='host-wrapper-ruff-correctness-plan-v1' and plan['sources']==source_ref
        and Path.cwd()==p.R and sys.dont_write_bytecode and not sys.flags.optimize,
        'packet, source, cwd or Python invocation differs')
    h=plan['history'];binding=plan['binding'];key=binding['tool_key']
    p.require(dict(os.environ)==h['environment'],'exact prepared workload environment required')
    owned=p.load(p.OWNED,'_host_ruff_correctness_owned')
    work=Path(h['observer']);p.absent(work);work.mkdir();(work/'tmp').mkdir()
    result_path=work/'result.json';record_path=work/'receipt.json'
    record=dict(policy='host-wrapper-ruff-correctness-observation-v1',status='starting',history='correctness',
        pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),cwd=str(p.R),
        environment=dict(os.environ),plan=plan_ref,child_receipts=[],
        application_correctness_qualified=False,timing_used=False,performance_qualified=False,
        observer_os_closure_observed=False)

    def save():owned.write(record_path,record)

    def guard():
        for name,row in frozen['files'].items():
            p.require(p.sha(name)==row['sha256'] and p.stamp(name)==row['stamp'],'prepared input changed: '+name)
        p.require(p.sha(p.PACKET/'plan.json')==args.plan_sha256
            and p.sha(p.PACKET/'inputs.json')==args.inputs_sha256,'packet changed')

    def footprint():
        # All generated task roots, including outer and normal-parent evidence.
        roots=[Path(h[k]) for k in ('work','results','observer','outer','parent')]
        roots+=list(map(Path,h['custom_caches'].values()))
        seen=set();allocated=logical=count=evidence=0
        caches=list(map(Path,[h['native_cache'],*h['custom_caches'].values()]))
        for root in roots:
            if not root.exists():continue
            p.require(not root.is_symlink(),'owned root replaced by symlink')
            for directory,dirs,files in os.walk(root,followlinks=False):
                for name in [*dirs,*files]:
                    path=Path(directory)/name;s=path.lstat()
                    p.require(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode),'unexpected owned output kind')
                    count+=1;p.require(count<=100000,'owned output entry bound exceeded')
                    logical+=s.st_size if stat.S_ISREG(s.st_mode) else 0
                    inode=(s.st_dev,s.st_ino)
                    if inode not in seen:
                        seen.add(inode);allocated+=s.st_blocks*512
                        if not any(path.is_relative_to(cache) for cache in caches):evidence+=s.st_blocks*512
        p.require(allocated<=7*p.GIB,'owned history allocation exceeded7GiB')
        p.require(evidence<=512*p.MIB,'retained history evidence exceeded512MiB')
        return dict(allocated_bytes=allocated,logical_file_bytes=logical,entries=count,
            retained_evidence_allocated_bytes=evidence,free_bytes=owned.disk(p.R,8),measured_at=time.time())

    def closed_child(name,command):
        child=p.pinned(p.ref(work/name/'receipt.json'))
        p.require(child['status']=='finished' and child['returncode']==0
            and child['command']==command and child['cwd']==str(p.R) and child['environment']==h['environment']
            and child['supervisor_pid']==os.getpid() and child['parent_pid']==os.getppid()
            and record['admitted_at']<=child['started_at']<=child['finished_at'],
            'owned child command, owner or normal closure differs')
        for stream in ('stdout','stderr'):
            p.require(p.sha(work/name/stream)==child[stream+'_sha256'],'owned child raw bytes changed')
        return child

    save()
    try:
        # Runner owns canonical itself. Release this admission before launching it;
        # task-specific absent namespaces bridge the two distinct acquisitions.
        with owned.workload_lock(p.LOCK,600):
            guard();p.prerequisites(binding,{})
            p.require(plan['timing_used'] is plan['performance_qualified'] is False,
                'this history may qualify only correctness')
            for path in [h['work'],h['results'],*h['custom_caches'].values()]:p.absent(path)
            record.update(status='admitted',admitted_at=time.time(),entry_free_bytes=owned.disk(p.R,21),before=footprint())
            save()
        record['admission_released_at']=time.time();save()
        try:
            owned.run(h['command'],cwd=p.R,env=h['environment'],out=work/'runner',capacity_root=p.R)
        finally:
            if (work/'runner/receipt.json').exists():
                record['child_receipts'].append(p.ref(work/'runner/receipt.json'));save()
        runner=closed_child('runner',h['command'])
        local_lock=p.R/'.work/benchmark.lock'
        p.require(local_lock.is_file() and local_lock.resolve(strict=True)!=p.LOCK
            and (local_lock.stat().st_dev,local_lock.stat().st_ino)!=(p.LOCK.stat().st_dev,p.LOCK.stat().st_ino),
            'saved verifier local lock must be distinct from canonical')
        with owned.workload_lock(p.LOCK,600):
            admitted=time.time();guard();record['after_history']=footprint()
            try:
                owned.run(h['verifier'],cwd=p.R,env=h['environment'],out=work/'verifier',capacity_root=p.R)
            finally:
                if (work/'verifier/receipt.json').exists():
                    record['child_receipts'].append(p.ref(work/'verifier/receipt.json'));save()
            verifier=closed_child('verifier',h['verifier'])
            p.require(runner['finished_at']<=admitted<=verifier['started_at'],'runner/verifier order differs')
            guard();record['after_verification']=footprint()
        released=time.time()
        verification=p.pinned(p.ref(h['verification']))
        p.require(json.loads(p.data(work/'verifier/stdout'))==verification,'ordinary verifier output differs')
        summary=p.pinned(p.ref(h['summary']));records=p.pinned(p.ref(h['records']))
        expected_states={r['state']:r['sha256'] for r in plan['workload']['state_sha256']}
        tests=plan['workload']['tests'];modes=('native','baseline','candidate')
        p.require(len(records)==len(summary['samples'])==24
            and {(r['state'],r['mode']) for r in records}=={(state,mode) for state in expected_states for mode in modes}
            and summary['tests']==tests and len(tests)==6 and summary['cycles']==1
            and summary['project']=='ruff' and summary['batch'] is True and summary['test_source_unchanged'] is True,
            'complete fixed24/six-test/eight-state history required')
        for row in records:
            p.require(row['tests']==tests and row['source_sha256']==expected_states[row['state']],
                'actual edit or selected tests differ from the existing strict workload')
            if row['mode']!='native' and row['state']!=-1:
                for call in row['calls']:
                    p.require(call['launch']['function_cache']==call['launch']['borrowck_cache']=='off',
                        'ordinary disabled function/borrow-check caches required')
        flags=['-Zmir-opt-level=3','-Zhir-body-cache-capture=false','-Zhir-body-cache-reuse=false']
        builds=summary['tool_builds'];policy=summary['host_codegen']
        p.require(builds['baseline']==builds['candidate'] and builds['baseline']['tool_key']==key
            and builds['baseline']['guest_rustflags']==summary['guest_rustflags']==summary['baseline_guest_rustflags']==flags
            and builds['baseline']['engine']=='jit'
            and all(builds['baseline'][n] is True for n in ('inline_leaves','jit_resumable_calls','jit_persistent_registers'))
            and all(builds['baseline'][n] is False for n in ('jit_native_calls','jit_native_call_stubs','trap_unsupported_calls','run_try_callbacks'))
            and policy['policy']=='host-codegen-opt-v1' and policy['modes']==dict(baseline='off',candidate='on')
            and summary['runtime_compiler']['key']==p.RUNTIME
            and summary['runtime_compiler']['prepared_std']['key']==summary['std_mir']['key']==p.STD,
            'same published tools/runtime/std or off/on settings differ')
        published=p.pinned(binding['proofs']['published_tools'])
        p.require(policy['receipt']['wrapper']==published['capabilities']['host_codegen_wrapper']
            and builds['baseline']['vm_sha256']==published['composition']['binaries']['rust-interp-vm']
            and builds['baseline']['exporter_sha256']==published['composition']['binaries']['rust-interp-mir-export'],
            'actual history names a different published physical toolset')
        native=summary['native_control']
        p.require(native['profile']=='repository' and native['jobs']==2 and native['test_threads']=='1'
            and native['rustflags']==[] and native['toolchain']=='nightly-2026-09-08'
            and summary['custom_build_jobs']==dict(baseline=2,candidate=2)
            and summary['minimum_free_gib']==16 and summary['workload_lock']==str(p.LOCK),
            'ordinary native/job/per-command policy differs')
        p.require(verification['measurement_controls_verified'] is True and verification['commands']==24
            and verification['edited_pairs']==5 and verification['paired_bytecode_identical'] is True
            and verification['restored_original_build_and_execution_verified'] is True
            and verification['exact_artifact_hashes_verified']==16
            and summary['cache_workspaces']==h['custom_caches'],'complete ordinary saved verification differs')
        # The unchanged verifier checked actual snapshots/catalogs and every mode's
        # wrong-edit rejection/restoration. Explicitly retain all eight RBC pairs.
        pairs=[]
        for state in expected_states:
            rows={r['mode']:r for r in records if r['state']==state}
            baseline=[a['sha256'] for a in rows['baseline']['artifacts']]
            candidate=[a['sha256'] for a in rows['candidate']['artifacts']]
            p.require(len(baseline)==1 and baseline==candidate,'an exact RBC pair differs')
            pairs.append(dict(state=state,source_sha256=expected_states[state],artifact_sha256=baseline[0]))
        result=dict(status='passed',history='correctness',plan=plan_ref,tool_key=key,runtime_key=p.RUNTIME,std_key=p.STD,
            prerequisites=binding['proofs'],runner=p.ref(work/'runner/receipt.json'),verifier=p.ref(work/'verifier/receipt.json'),
            summary=p.ref(h['summary']),records=p.ref(h['records']),verification=p.ref(h['verification']),
            canonical_verification=dict(admitted_at=admitted,released_at=released),exact_rbc_pairs=pairs,
            generated_cache_roots=sorted([h['native_cache'],*h['custom_caches'].values()]),
            before=record['before'],after=record['after_verification'],application_correctness_qualified=True,
            timing_used=False,performance_qualified=False,observer_os_closure_observed=False)
        p.write(result_path,result)
        record.update(status='passed',finished_at=time.time(),result=p.ref(result_path),application_correctness_qualified=True)
        save();print(json.dumps(record['result']))
    except BaseException as error:
        record.update(status='failed',error=repr(error),finished_at=time.time());save();raise


if __name__=='__main__':main()
