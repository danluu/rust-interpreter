"""Read only the actual closed publication and five-test RBC prerequisite."""
from pathlib import Path

TESTS=('test_cargo_shared_library_macro_input_spans_error_and_restoration',
 'test_macro_cfg_debug_and_overflow_checks','test_native_debug_overflow_ub_cfg_generics_inline_and_drop_effects',
 'test_uncalled_macro_errors_and_restoration','test_uncalled_type_borrow_const_and_position_changes_reject_then_restore')
RBC_SOURCES_SHA='28d76e71027f08ecf0a27af6eb6a9c1ac4345ba12db0b3e8fd2e4ed7526cde7b'


def validate(p,binding,checked):
    require=p.require
    def get(reference,raw=False):
        require(type(reference) is dict and {'path','sha256'}<=set(reference),'proof reference differs')
        return p.pinned({k:reference[k] for k in ('path','sha256')},checked,raw=raw)
    def same(a,b):return {k:a[k] for k in ('path','sha256')}=={k:b[k] for k in ('path','sha256')}
    require(binding['policy']=='host-wrapper-ruff-correctness-binding-v1'
        and binding['runtime_key']==p.RUNTIME and binding['std_key']==p.STD,'fixed policy/runtime/std required')
    key=binding['tool_key'];proof=binding['proofs']
    require(set(proof)=={'publication','published_tools','publication_execution','rbc_binding','rbc_record',
        'rbc_result','rbc_execution'},'complete actual prerequisite selection required')
    values={k:get(v) for k,v in proof.items()}
    pub=values['publication'];tools=values['published_tools'];execution=values['publication_execution']
    pubwork=p.X/'.work/host-wrapper-exporter-publication-01'
    require(proof['publication']['path']==str(pubwork/'receipt.json')
        and proof['published_tools']['path']==str(pubwork/'published-tools.json')
        and proof['publication_execution']['path']==str(p.ROOT/'.work/host-wrapper-exporter-publication-execution-01/record.json'),
        'fixed publication proof routes required')
    require(pub['status']=='passed' and pub['phase']=='publication' and pub['publication'] is True
        and pub['frontend_qualified'] is True and pub['runtime_key']==p.RUNTIME
        and pub['tool_key']==tools['tool_key']==key and same(pub['result'],proof['published_tools'])
        and pub['published_tools_sha256']==proof['published_tools']['sha256'] and len(pub['commands'])==4,
        'complete actual new tool publication required')
    require(execution['status']=='finished' and execution['returncode']==execution['controller_returncode']==0
        and execution['supervisor_may_be_live'] is execution['controller_may_be_live'] is False,
        'publication normal closure required')
    execution_root=Path(proof['publication_execution']['path']).parent
    for stream in ('stdout','stderr'):
        get(dict(path=str(execution_root/stream),sha256=execution[stream+'_sha256']),raw=True)
    outer=p.X/'.work/experiments/host-wrapper-exporter-publication-supervisor-01'
    status=get(dict(path=str(outer/'status.json'),sha256=execution['outer_status_sha256']))
    get(dict(path=str(outer/'command.log'),sha256=status['log_sha256']),raw=True)
    require(status['status']=='finished' and status['returncode']==0 and status['child_pid']==pub['pid']
        and status['supervisor_pid']==pub['parent_pid']==execution['pid']
        and status['supervisor_parent_pid']==execution['parent_pid']
        and execution['started_at']<=status['started_at']<=pub['started_at']<=pub['finished_at']
          <=status['finished_at']<=execution['finished_at'],'publication closed process association differs')
    previous=pub['admitted_at']
    for index,saved in enumerate(pub['commands']):
        require(saved['path']==str(pubwork/'commands'/f'{index:03d}'/'receipt.json'),'publication child order differs')
        row=get(saved)
        require(row['status']=='finished' and row['returncode']==saved['returncode']==0 and row['pid']==saved['pid']
            and row['supervisor_pid']==pub['pid'] and previous<=row['started_at']<=row['finished_at']<=pub['finished_at'],
            'publication child closure differs')
        previous=row['finished_at']
        for stream in ('stdout','stderr'):get(dict(path=str(Path(saved['path']).parent/stream),sha256=row[stream+'_sha256']),raw=True)
    require(tools['directory']==str(p.R/'.work/interpreter-tools'/key)
        and tools['composition']['compiler_key']==p.RUNTIME
        and tools['composition']['host_codegen_policy']=='host-codegen-opt-v1'
        and tools['composition']['host_codegen_helper']==dict(path=str(p.H/'host_codegen_opt.py'),sha256=p.sha(p.H/'host_codegen_opt.py'))
        and tools['host_codegen_application_qualified'] is False,'physical published policy association differs')
    # No installed binary/provider payload is read here. The qualified ordinary
    # runner validates those physical inputs again before starting its history.
    for name,value in [('compiler.json',tools['composition']),('capabilities.json',tools['capabilities']),
                       ('ready.json',tools['composition']['binaries'])]:
        require(get(p.ref(Path(tools['directory'])/name))==value,'published metadata differs')
    rb=values['rbc_binding'];record=values['rbc_record'];result=values['rbc_result'];parent=values['rbc_execution']
    out=p.ROOT/'results/host-wrapper-rbc-fixture-03'
    require(proof['rbc_binding']['path']==str(p.RBC/'binding.json')
        and proof['rbc_record']['path']==str(out/'record.json') and proof['rbc_result']['path']==str(out/'suite-result.json')
        and proof['rbc_execution']['path']==str(p.ROOT/'.work/host-wrapper-rbc-execution-03/record.json'),
        'fixed RBC proof routes required')
    require(rb['policy']=='host-wrapper-rbc-binding-v1' and rb['tool_key']==key
        and rb['runtime_key']==p.RUNTIME and rb['std_key']==p.STD and rb['tests']==list(TESTS),
        'five-test actual RBC tool/runtime/std selection differs')
    manifest=get(dict(path=str(p.RBC/'sources.json'),sha256=RBC_SOURCES_SHA))
    require(rb['sources']==manifest['files'] and rb['source_manifest']==dict(path=str(p.RBC/'sources.json'),sha256=RBC_SOURCES_SHA),
        'reviewed RBC source selection differs')
    for name,digest in rb['sources'].items():get(dict(path=name,sha256=digest),raw=True)
    require(all(rb['evidence'].get(proof[k]['path'])==proof[k]['sha256']
        for k in ('publication','published_tools','publication_execution')),'RBC qualified another publication')
    require(record['status']=='passed' and record['returncode']==0 and record['normal_wait_completed'] is True
        and record['child_may_be_live'] is False and record['inputs_unchanged'] is True
        and record['application_fixture_qualified'] is True and record['observation_errors']==[]
        and record['signals']==record['retries']==0 and record['tool_key']==key
        and same(record['binding'],proof['rbc_binding']) and same(record['result'],proof['rbc_result']),
        'RBC driver has no complete successful suite closure')
    require(parent['status']=='passed' and parent['returncode']==0 and parent['normal_wait_completed'] is True
        and parent['driver_may_be_live'] is False and parent['pid']==record['parent_pid']
        and parent['parent_pid']==record['parent_parent_pid'] and same(parent['driver_record'],proof['rbc_record'])
        and same(parent['result'],proof['rbc_result'])
        and parent['started_at']<=record['started_at']<=record['child_started_at']<=record['child_finished_at']
          <=record['finished_at']<=parent['child_finished_at']<=parent['finished_at'],
        'RBC external parent did not normally wait this driver/suite')
    for owner in (parent,record):
        for stream in ('stdout','stderr'):get(owner[stream],raw=True)
    expected=['_host_codegen_rbc_fixture.HostCodegenNativeTests.'+n for n in sorted(TESTS)]
    require(result['status']=='passed' and result['tests_run']==5
        and result['test_ids']==result['expected_test_ids']==expected and result['violations']==[]
        and all(result[n]==0 for n in ('skipped','expected_failures','unexpected_successes','failures','errors'))
        and result['benchmark'] is False and 0<len(result['commands'])<=256,'all exact five RBC tests must pass')
    seen=set();previous=record['child_started_at']
    artifact_root=p.ROOT/'.work/host-wrapper-rbc-fixture-03/artifacts'
    for row in result['commands']:
        require(row['passed'] is True and row['limit_seconds']==30 and row['seconds']<=30,'RBC command observation failed')
        child=get(row['receipt'])
        receipt_path=Path(row['receipt']['path']);directory=receipt_path.parent
        require(receipt_path.name=='record.json' and directory.parent.name=='commands'
            and receipt_path.is_relative_to(artifact_root) and str(receipt_path) not in seen
            and child['status']=='finished' and child['parent_pid']==record['child_pid']
            and previous<=child['started_at']<=child['finished_at']<=record['child_finished_at'],
            'RBC command route, owner or normal closure differs')
        seen.add(str(receipt_path));previous=child['finished_at']
        for stream in ('stdout','stderr'):
            require(row[stream]['path']==str(directory/stream),'RBC raw stream belongs to another command')
            get(row[stream],raw=True)
    before=get(p.ref(out/'inputs-before.json'));after=get(p.ref(out/'inputs-after.json'))
    require(before==after and set(before['sources'])==set(rb['sources']) and set(before['payloads'])==set(rb['payloads'])
        and set(before['evidence'])==set(rb['evidence']),
        'RBC source/provider before-after association differs')
    for name,digest in rb['sources'].items():require(before['sources'][name]['sha256']==digest,'RBC source map differs')
    for name,digest in rb['payloads'].items():require(before['payloads'][name]['sha256']==digest,'RBC provider declaration differs')
    for name,digest in rb['evidence'].items():require(before['evidence'][name]['sha256']==digest,'RBC evidence map differs')
    return dict(environment=rb['environment'],tool_key=key)
