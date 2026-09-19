"""Read-only current-context proposal; does not construct or run the Reader."""
import argparse
import os
from pathlib import Path
import resource
import sys
import time

import common as c


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--canonical-fd',type=int,required=True)
    parser.add_argument('--passed-environment-json',required=True);args=parser.parse_args()
    c.require(Path.cwd()==c.ROOT and sys.dont_write_bytecode and not sys.flags.optimize,'fixed rehearsal preparer owner')
    lock=os.fstat(args.canonical_fd);named=c.CANONICAL.lstat()
    c.require((lock.st_dev,lock.st_ino)==(named.st_dev,named.st_ino) and lock.st_nlink==1,'exact inherited canonical descriptor')
    resource.setrlimit(resource.RLIMIT_CPU,(900,900));resource.setrlimit(resource.RLIMIT_FSIZE,(64*2**20,64*2**20))
    io_policy=c.readonly_policy('prepare')
    c.require(all(not (c.HERE/name).exists() and not (c.HERE/name).is_symlink() for name in
        ['plan.json','inputs.json','launch.json','preparation.json']) and not c.WORK.exists(),'fresh rehearsal proposal and WORK')
    environments=dict(passed=c.json.loads(args.passed_environment_json),before_runtime_imports=dict(os.environ))
    started=time.time();runtime_absent=c.runtime_absent();entry,factory,frozen,modules=c.authenticate()
    environments['after_runtime_imports']=dict(os.environ)
    d=entry.discovery(modules);d.floor=c.guard
    closure,census=c.reader_closure()
    for name,row in closure['files'].items():d.add(name,row,snapshot=True)
    for name,row in closure['historical_failed_rehearsal']['files'].items():d.add(name,row,snapshot=True)
    for ref in [closure['original_rehearsal'],closure['qualified_hash_audit'],closure['qualified_hash_result'],
                closure['publication_proposal'],closure['prior_preparation']]:d.add(ref['path'],ref,snapshot=True)
    delta=c.read(c.HERE/'producer-import-delta.json')
    for name,row in c.IMPORT_DELTA_ROWS.items():d.add(name,row,snapshot=True)
    for name,row in delta['historical_failure']['files'].items():d.add(name,row,snapshot=True)
    plan=d.inherit(c.HASH)
    for name,resolved in plan['executor_routes'].items():
        c.require(str(Path(name).resolve(strict=True))==resolved,'completed executor route changed');d.routes[name]=resolved
    d.add(c.HASH/'snapshot-plan.json',snapshot=True);d.tree(c.HASH_WORK)
    for root in [c.ROOT/'.work/experiments/hir-options-hash-driver-supervisor-02',c.ROOT/'.work/hash-driver-launch-execution-02']:
        d.tree(root)
    audits=dict(plan['independent_audits']);audits.pop('compiler')
    audits['hash']=dict(path=str(c.AUDIT),sha256=c.AUDIT_SHA)
    c.require(set(audits)=={'beta','native','run_make','hash'},'four exact completed audits required')
    for ref in audits.values():d.add(ref['path'],ref,snapshot=True)
    bindings=c.read(c.RUNTIME/'source-bindings.json')
    for name,row in bindings['predecessor_sources'].items():d.add(name,row,snapshot=True)
    for row in bindings['inherited_actual_proofs']:d.add(row['path'],row,snapshot=True)
    for source,work,audit in [(c.CONTROL,c.CONTROL_WORK,c.CONTROL_AUDIT),
                             (modules.copies.CONTROLS,modules.copies.CONTROL_WORK,modules.copies.CONTROL_AUDIT)]:
        for name in ['inputs.json','launch.json']:d.add(source/name,snapshot=True)
        for name,row in c.read(source/'inputs.json')['files'].items():d.add(name,row,snapshot=True)
        d.tree(work);d.add(audit,snapshot=True)
    for namespace in ['runtime-prerequisite-controls-preparation-execution-04',
        'runtime-prerequisite-controls-launch-execution-04','runtime-prerequisite-controls-verification-execution-04',
        'experiments/runtime-prerequisite-controls-supervisor-04']:d.tree(c.ROOT/'.work'/namespace)
    for name in ['launch_runtime_prerequisite_controls_04_bounded.py','verify_runtime_prerequisite_controls_04.py',
                 'execute_runtime_prerequisite_controls_audit_04.py']:d.add(c.ROOT/'.work'/name,snapshot=True)
    for name,digest in c.RUNTIME_SOURCES.items():d.add(c.RUNTIME/name,dict(sha256=digest),snapshot=True)
    for path in sorted(c.HERE.iterdir()):
        c.require(path.is_file() and not path.is_symlink(),'ordinary rehearsal source only');d.add(path,snapshot=True)
    d.add(c.OWNED,dict(sha256=c.OWNED_SHA),snapshot=True)
    d.imports()
    c.require(set(census['required_paths'])<=set(d.files),'reviewed Reader dependency omitted from physical freeze')
    c.require(all(c.same(d.files[name],row) for name,row in closure['files'].items()),
        'qualified completed-owner closure changed during collection')
    c.require(all(c.same(d.files[name],row) for name,row in c.IMPORT_DELTA_ROWS.items()),
        'every authenticated producer import must remain in the physical freeze')
    original=d.hash_original;present=c.present(original,d.historical_names,frozen)
    c.require(len(original['files'])==109343 and len(set(original['files'])-d.historical_names)==109322
        and all(name in d.files and c.same(d.files[name],row) for name,row in original['files'].items()
            if name not in d.historical_names),'complete old physical context required')
    denials=c.deny(d.historical_names,{'RuntimeDiscovery.add':d.add})
    c.require(not set(d.historical_names)&(set(d.files)|d.absent|d.snapshots),
        'live historical copies cannot be current files, absences or selected payloads')
    data=dict(status='prepared-strict-rehearsal-unrun',owner=str(c.ROOT),work=str(c.WORK),
        producer_import_delta=dict(path=str(c.HERE/'producer-import-delta.json'),sha256=c.PRODUCER_DELTA_SHA),
        reader_closure_delta=dict(path=str(c.HERE/'reader-closure-delta.json'),sha256=c.READER_DELTA_SHA),
        reader_dependency_census=dict(path=str(c.HERE/'reader-dependency-census.json'),sha256=c.READER_CENSUS_SHA),
        hash_source=str(c.HASH),hash_work=str(c.HASH_WORK),original_inputs_sha256=c.ORIGINAL_SHA,
        independent_audits=audits,runtime52=dict(path=str(c.CONTROL_AUDIT),sha256=c.CONTROL_AUDIT_SHA),
        proposal=dict(path=str(modules.copies.PROPOSAL),sha256=modules.copies.PROPOSAL_SHA256),
        original_file_table_integrity=c.read(c.HASH/'inputs.json')['file_table_integrity'],
        complete_original_rows=109343,current_context_rows=109322,historical_copies=21,
        pre_plan_physical_rows=len(d.files),pre_plan_physical_bytes=d.total,
        historical_names=sorted(d.historical_names),copy_presence=present,collector_denials=denials,
        original_snapshot_inputs=original['snapshot_inputs'],evidence_roots=plan['evidence_roots'],
        runtime_absent=runtime_absent,runtime_admission=False,retirement_authorized=False)
    c.write(c.HERE/'plan.json',data);d.add(c.HERE/'plan.json',snapshot=True)
    freeze=dict(files=d.files,links=d.links,absent_paths=sorted(d.absent),executor_routes=d.routes,
        python=str(Path(sys.executable).resolve(strict=True)),plan_sha256=c.sha(c.HERE/'plan.json'),
        snapshot_inputs=sorted(d.snapshots))
    table=modules.stage.load_file_table(freeze,d.comp)
    wire=table.split(freeze,base_path=entry.FILE_TABLE_BASE['path'],base_sha256=entry.FILE_TABLE_BASE['sha256'],guard=c.guard)
    c.require(c.same(modules.stage.expand_file_table(wire,table,guard=c.guard),freeze),'complete physical rehearsal table roundtrip')
    c.write(c.HERE/'inputs.json',wire,16*2**20)
    bound=frozen.Frozen(c.HERE/'inputs.json',c.sha(c.HERE/'inputs.json'),output_root=c.WORK,table=table,base=entry.FILE_TABLE_BASE)
    bound.check(True)
    c.require(c.same(present,c.present(original,d.historical_names,frozen)),'historical copies changed during preparation')
    c.require(c.runtime_absent()==runtime_absent,'runtime namespace appeared')
    c.require(io_policy['blocked_events']==0,'forbidden preparation API was attempted')
    c.write(c.HERE/'preparation.json',dict(status='passed-read-only-preparation',started_at=started,finished_at=time.time(),
        files=len(d.files),bytes=d.total,inputs_sha256=c.sha(c.HERE/'inputs.json'),plan_sha256=c.sha(c.HERE/'plan.json'),
        collector_denials=len(denials),reader_executions=0,provider_probes=0,compiler_calls=0,
        environments=dict(environments,at_completion=dict(os.environ)),import_environments=c.IMPORT_OBSERVATIONS,
        producer_import_delta_sha256=c.PRODUCER_DELTA_SHA,reader_closure_delta_sha256=c.READER_DELTA_SHA,
        reader_dependency_census_sha256=c.READER_CENSUS_SHA,io_policy=io_policy,
        runtime_admission=False,retirement_authorized=False))
    c.write(c.HERE/'launch.json',dict(status='prepared-rehearsal-awaiting-review',cwd=str(c.ROOT),
        inputs_sha256=c.sha(c.HERE/'inputs.json'),plan_sha256=c.sha(c.HERE/'plan.json'),
        reader_sha256=c.sha(c.HERE/'rehearse.py'),common_sha256=c.sha(c.HERE/'common.py'),
        runtime52_audit_sha256=c.CONTROL_AUDIT_SHA,capacity=dict(entry_gib=16,live_gib=9,floor_gib=8),
        canonical_wait_seconds=600,maximum_observation_seconds=1250,maximum_child_cpu_seconds=900,
        runtime_admission=False,retirement_authorized=False))
    print(c.encoded(dict(status='prepared-rehearsal-unrun',launch_sha256=c.sha(c.HERE/'launch.json'),
        inputs_sha256=c.sha(c.HERE/'inputs.json'),files=len(d.files),bytes=d.total)).decode(),end='')


if __name__=='__main__':c.observed_main(main)
