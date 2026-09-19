"""Actual full-current Reader rehearsal; no installation or retirement authority."""
import argparse
import os
from pathlib import Path
import resource
import sys
import time

import common as c


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--canonical-fd',type=int,required=True)
    parser.add_argument('--inputs-sha256',required=True);parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--passed-environment-json',required=True)
    args=parser.parse_args()
    c.require(Path.cwd()==c.ROOT and sys.dont_write_bytecode and not sys.flags.optimize,'fixed rehearsal owner')
    lock=os.fstat(args.canonical_fd);named=c.CANONICAL.lstat()
    c.require((lock.st_dev,lock.st_ino)==(named.st_dev,named.st_ino) and lock.st_nlink==1,'exact inherited canonical descriptor')
    resource.setrlimit(resource.RLIMIT_CPU,(900,900));resource.setrlimit(resource.RLIMIT_FSIZE,(4*2**20,4*2**20))
    io_policy=c.readonly_policy('rehearse')
    c.require(not c.WORK.exists() and not c.WORK.is_symlink(),'fresh rehearsal result namespace')
    c.require(c.sha(c.HERE/'inputs.json')==args.inputs_sha256 and c.sha(c.HERE/'plan.json')==args.plan_sha256,
        'exact reviewed rehearsal packet')
    environments=dict(passed=c.json.loads(args.passed_environment_json),before_runtime_imports=dict(os.environ))
    started=time.time();runtime_absent=c.runtime_absent();entry,factory,frozen,modules=c.authenticate()
    environments['after_runtime_imports']=dict(os.environ)
    wire=c.read(c.HERE/'inputs.json');plan=c.read(c.HERE/'plan.json')
    c.require(wire['plan_sha256']==args.plan_sha256 and plan['original_inputs_sha256']==c.ORIGINAL_SHA
        and plan['runtime_admission'] is False and plan['retirement_authorized'] is False
        and plan['runtime_absent']==runtime_absent,'rehearsal packet scope changed')
    table=entry.load_table(wire,frozen)
    bound=frozen.Frozen(c.HERE/'inputs.json',args.inputs_sha256,output_root=c.WORK,table=table,base=entry.FILE_TABLE_BASE)
    bound.check(True)
    closure,census=c.reader_closure()
    c.require(plan['reader_closure_delta']==dict(path=str(c.HERE/'reader-closure-delta.json'),sha256=c.READER_DELTA_SHA)
        and plan['reader_dependency_census']==dict(path=str(c.HERE/'reader-dependency-census.json'),sha256=c.READER_CENSUS_SHA)
        and set(census['required_paths'])<=set(bound.value['files'])
        and all(c.same(bound.value['files'][name],row) for name,row in closure['files'].items()),
        'complete reviewed Reader current closure required')
    c.require(not set(plan['historical_names'])&(set(bound.value['files'])|set(bound.value['absent_paths'])),
        'still-present historical copies must not be current inputs or absences')
    c.require(c.same(plan['runtime52'],dict(path=str(c.CONTROL_AUDIT),sha256=c.CONTROL_AUDIT_SHA)),'actual52 packet association')
    reader=modules.prerequisites.Reader(modules.stage,modules.hash_modules,combined_freeze=bound.value,
        references=plan['independent_audits'],read_json=bound.read_json,sha=bound.sha,
        copy_partition=lambda r:entry.copy_partition(modules,r,load=factory.load,directory_record=frozen.ordinary_directory))
    environments['after_reader_construction']=dict(os.environ)
    before=c.present(reader.original,plan['historical_names'],frozen)
    c.require(c.same(before,plan['copy_presence']),'prepared original21 presence differs')
    denials=c.deny(plan['historical_names'],{'Frozen.file':bound.file,'Frozen.record':bound.record,
        'Frozen.read_bytes':bound.read_bytes,'Frozen.read_json':bound.read_json,'Frozen.sha':bound.sha,
        'Stage.frozen':reader.reader.frozen,'Stage.read_bytes':reader.reader.read_bytes,'Stage.read_json':reader.reader.read_json})
    qualified=reader.check(full=True)
    environments['after_full_reader_check']=dict(os.environ)
    controls=entry.runtime_qualification(reader)
    c.require(c.same(controls['audit'],plan['runtime52']),'full actual52 source/raw qualification differs')
    continued=entry.catalog_qualification(reader)
    catalog=factory.load('completed_catalog',entry.CATALOG_SOURCE,bound.file)
    snapshots=factory.load('qualified_snapshots',modules.stage.SNAPSHOT_SOURCE,bound.file)
    complete=entry.completed_catalog(modules,reader,catalog,snapshots,plan['evidence_roots'],
        read_json=bound.read_json,read_bytes=bound.read_bytes,sha=bound.sha,file_record=bound.record,
        directory_record=frozen.ordinary_directory,guard=c.guard)
    c.require(complete['priority'][-1]=='hash' and len(complete['records'])>len(reader.copy_state['prior_catalog']['records']),
        'successful hash02 catalog extension is mandatory')
    bound.check(True)
    c.require(c.same(before,c.present(reader.original,plan['historical_names'],frozen)),'original copies changed during rehearsal')
    c.require(c.runtime_absent()==runtime_absent,'runtime namespace appeared during rehearsal')
    c.require(io_policy['blocked_events']==0,'forbidden rehearsal API was attempted')
    refs=reader.copy_state['references'];original=reader.original
    result=dict(status='passed-strict-callback-rehearsal-awaiting-independent-audit',started_at=started,finished_at=time.time(),
        pid=os.getpid(),parent_pid=os.getppid(),inputs_sha256=args.inputs_sha256,plan_sha256=args.plan_sha256,
        proposal_sha256=modules.copies.PROPOSAL_SHA256,historical_source_stage03_wire_sha256=c.ORIGINAL_SHA,
        complete_original_rows=len(original['files']),current_context_rows=reader.copy_state['current_context_files'],
        historical_copies=len(reader.copy_state['historical_files']),bootstrap_policy=reader.copy_state['bootstrap_policy'],
        no_live_api_virtualization=True,runtime_admission=False,retirement_authorized=False,
        selected_paths=sorted(plan['historical_names']),selected_paths_sha256=c.hashlib.sha256(c.encoded(plan['historical_names'])).hexdigest(),
        protected_paths_sha256=c.hashlib.sha256(c.encoded(sorted(set(original['files'])-set(plan['historical_names'])))).hexdigest(),
        current_physical_files=len(bound.value['files']),current_physical_bytes=sum(row['size'] for row in bound.value['files'].values()),
        original_file_table_integrity=plan['original_file_table_integrity'],copy_presence=before,
        collector_denials=plan['collector_denials'],physical_api_denials=denials,historical_references=refs,
        actual52=controls,continuation70=continued,helper40=dict(path=str(modules.copies.CONTROL_AUDIT),sha256=modules.copies.CONTROL_AUDIT_SHA256),
        successful_hash02_audit=dict(path=str(c.AUDIT),sha256=c.AUDIT_SHA),qualified_prerequisites=qualified,
        prior_catalog_records=len(reader.copy_state['prior_catalog']['records']),completed_catalog_records=len(complete['records']),
        completed_catalog_sha256=c.hashlib.sha256(c.encoded(complete)).hexdigest(),
        witness_count=len(refs['witnesses']),full_current_input_rehash=True,full_current_recipe_check=True,
        full_compressed_and_logical_EOF=True,runtime_absent=runtime_absent,provider_probes=0,compiler_calls=0,
        environments=dict(environments,at_completion=dict(os.environ)),import_environments=c.IMPORT_OBSERVATIONS,
        producer_import_delta_sha256=c.PRODUCER_DELTA_SHA,reader_closure_delta_sha256=c.READER_DELTA_SHA,
        reader_dependency_census_sha256=c.READER_CENSUS_SHA,io_policy=io_policy,
        runtime_packets_created=0,runtime_work_created=0,retired_files=0,samples=c.SAMPLES,
        source_sha256={name:c.sha(c.HERE/name) for name in ['common.py','prepare.py','rehearse.py','README.md','producer-import-delta.json',
            'reader-closure-delta.json','reader-dependency-census.json']})
    c.WORK.mkdir(mode=0o700);c.write(c.WORK/'result.json',result)
    print(c.encoded(dict(status=result['status'],result=str(c.WORK/'result.json'),sha256=c.sha(c.WORK/'result.json'),
        pid=os.getpid(),runtime_admission=False,retirement_authorized=False)).decode(),end='')


if __name__=='__main__':c.observed_main(main)
