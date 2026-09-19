"""Bind installation preparation only from explicit, actually closed proofs.

Source-only until both actual proof pins are supplied. No project imports,
provider calls, process control, canonical admission, or existing-file mutation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
SOURCE = ROOT/'experiments/runtime-installation-after-preflight05-03'
CONTROL = ROOT/'experiments/runtime-installation-controls-08'
WORK = ROOT/'.work/runtime-installation-controls-08'
CONTROLS_PREPARATION_SHA = None
CONTROLS_PREPARER_SHA = None
CONTROLS_FILES = None
CONTROLS_BYTES = None
NATIVE = SOURCE.parent/'runtime-native-loader-probes-01'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')


def raw(path):
    path = Path(path)
    before = path.lstat()
    assert path.is_absolute() and path.resolve(strict=True) == path
    assert stat.S_ISREG(before.st_mode) and before.st_size <= 64*2**20
    identity = {key: getattr(before, 'st_'+key) for key in FIELDS}
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        assert {key: getattr(os.fstat(stream.fileno()), 'st_'+key) for key in FIELDS} == identity
        data = stream.read(64*2**20+1)
        assert {key: getattr(os.fstat(stream.fileno()), 'st_'+key) for key in FIELDS} == identity
    assert {key: getattr(path.lstat(), 'st_'+key) for key in FIELDS} == identity
    assert len(data) == before.st_size
    return data, dict(identity=identity, size=len(data), sha256=hashlib.sha256(data).hexdigest())


def document(path, expected=None):
    data, row = raw(path)
    assert expected is None or row['sha256'] == expected
    return json.loads(data)


def ref(path):
    return dict(path=str(path), sha256=raw(path)[1]['sha256'])


def write(path, value):
    data = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    assert raw(path)[0] == data


def main():
    parser = argparse.ArgumentParser()
    for key in ['controls-audit', 'controls-execution', 'preflight-audit', 'preflight-execution']:
        parser.add_argument('--'+key+'-sha256', required=True)
    args = parser.parse_args()
    assert Path.cwd() == ROOT
    assert all(re.fullmatch('[a-f0-9]{64}', value) for value in vars(args).values())
    assert all(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin) for pin in [CONTROLS_PREPARATION_SHA,CONTROLS_PREPARER_SHA]), 'future controls48 closure not bound'
    assert type(CONTROLS_FILES) is int and type(CONTROLS_BYTES) is int, 'future controlled packet census not bound'
    audit_path = ROOT/'.work/runtime-installation-controls-independent-verification-08.json'
    audit = document(audit_path, args.controls_audit_sha256)
    execution_path = ROOT/'.work/runtime-installation-controls-verification-execution-08/record.json'
    execution = document(execution_path, args.controls_execution_sha256)
    assert audit['status'] == 'verified' and type(audit['controls']) is int and audit['controls'] == 48
    assert execution['status'] == 'finished' and type(execution['returncode']) is int and execution['returncode'] == 0
    assert execution['observation_errors'] == [] and 'execution_error' not in execution and 'publication_error' not in execution
    assert execution.get('may_be_live', False) is False
    assert execution['mode'] == 'one authorized independent read-only actual48 verification; no test or provider calls'
    assert execution['verified_output'] == dict(path=str(audit_path), sha256=args.controls_audit_sha256,
                                               receipt_sha256=audit['receipt_sha256'])
    assert execution['started_at'] <= execution['finished_at']
    assert type(execution['pid']) is int and type(execution['parent_pid']) is int
    for field, name in [('source_sha256','source.py'), ('execution_source_sha256','execution.py')]:
        assert ref(execution_path.parent/name)['sha256'] == execution[field]
    for name in ['stdout', 'stderr']:
        assert ref(execution_path.parent/name)['sha256'] == execution[name+'_sha256']
        assert ref(WORK/'command'/name)['sha256'] == audit['raw_sha256'][name]
    assert raw(execution_path.parent/'stderr')[0] == b''
    for name in ['receipt', 'result']:
        assert ref(WORK/(name+'.json'))['sha256'] == audit[name+'_sha256']

    preflight_path = R/'.work/hir-options-hash-runtime-preflight-independent-verification-05.json'
    preflight = document(preflight_path, args.preflight_audit_sha256)
    preflight_execution_path = ROOT/'.work/runtime10-saved-audit-preflight-execution-01/record.json'
    preflight_execution = document(preflight_execution_path, args.preflight_execution_sha256)
    assert preflight['status'] == 'verified' and preflight['phase'] == 'preflight'
    assert type(preflight['actual_children']) is int and preflight['actual_children'] == 2
    assert preflight_execution['status'] == 'finished' and preflight_execution['returncode'] == 0
    assert type(preflight_execution['returncode']) is int and 'execution_error' not in preflight_execution
    assert preflight_execution['mode'] == 'audit' and preflight_execution['phase'] == 'preflight'
    assert preflight_execution['result_sha256'] == args.preflight_audit_sha256
    assert preflight_execution['report'] == str(preflight_path)
    assert preflight['pid'] == preflight_execution['pid'] and preflight['parent_pid'] == preflight_execution['parent_pid']
    assert preflight_execution['may_be_live'] is False and preflight_execution['observation_errors'] == []
    assert preflight_execution['finished_at'] <= preflight_execution['canonical_released_at']
    for name in ['stdout', 'stderr']:
        assert ref(preflight_execution_path.parent/name)['sha256'] == preflight_execution[name+'_sha256']
    assert raw(preflight_execution_path.parent/'stderr')[0] == b''

    # The future preparation08 must freeze the current installation07/native-loader source selection.
    controls_preparation_path = ROOT/'.work/runtime-installation-controls-preparation-execution-08/record.json'
    controls_preparation = document(controls_preparation_path,
        CONTROLS_PREPARATION_SHA)
    controls_preparer = ROOT/'.work/prepare_runtime_installation_controls_08_once.py'
    assert ref(controls_preparer)['sha256'] == controls_preparation['execution_source_sha256'] == \
        CONTROLS_PREPARER_SHA
    assert ref(controls_preparation_path.parent/'source/execution.py')['sha256'] == controls_preparation['execution_source_sha256']
    assert controls_preparation['status'] == 'finished' and type(controls_preparation['returncode']) is int and controls_preparation['returncode'] == 0
    assert controls_preparation['observation_errors'] == [] and 'execution_error' not in controls_preparation
    assert controls_preparation.get('may_be_live', False) is False
    assert controls_preparation['started_at'] <= controls_preparation['admitted_at'] <= controls_preparation['child_started_at'] <= controls_preparation['finished_at'] <= controls_preparation['canonical_released_at'] <= document(WORK/'receipt.json')['started_at']
    assert controls_preparation['cwd'] == str(ROOT) and controls_preparation['capacity'] == dict(entry_gib=10, stop_gib=9, floor_gib=8)
    assert controls_preparation['command'] == [document(CONTROL/'inputs.json')['python'], '-B', str(CONTROL/'prepare.py')]
    for name, digest in controls_preparation['source_sha256'].items():
        assert name in ['run.py', 'prepare.py', 'child.py']
        assert ref(CONTROL/name)['sha256'] == ref(controls_preparation_path.parent/'source'/name)['sha256'] == digest
    assert set(controls_preparation['source_sha256']) == {'run.py', 'prepare.py', 'child.py'}
    assert ref(controls_preparation_path.parent/'source/owned_stage.py')['sha256'] == controls_preparation['owned_source_sha256']
    for name in ['stdout', 'stderr']:
        assert ref(controls_preparation_path.parent/name)['sha256'] == controls_preparation[name+'_sha256']
    assert raw(controls_preparation_path.parent/'stderr')[0] == b''
    prepared = controls_preparation['prepared_packet']
    assert document(controls_preparation_path.parent/'stdout') == prepared
    assert prepared == dict(status='prepared-unrun', controls=48, files=CONTROLS_FILES, bytes=CONTROLS_BYTES,
        inputs_sha256=ref(CONTROL/'inputs.json')['sha256'], launch_sha256=ref(CONTROL/'launch.json')['sha256'])

    inputs = document(CONTROL/'inputs.json')
    assert ref(CONTROL/'inputs.json')['sha256'] == document(WORK/'receipt.json')['inputs_sha256']
    assert inputs['environment'] == controls_preparation['environment'] and inputs['capacity'] == controls_preparation['capacity']
    for name, expected in inputs['files'].items():
        row = raw(name)[1]
        assert row['sha256'] == expected['sha256'] and row['size'] == expected['stamp'][3]
        assert [row['identity'][key] for key in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']] == expected['stamp']
    for name, target in inputs['routes'].items():
        assert str(Path(name).resolve(strict=True)) == target

    # Retain every row from actual preparation06, including historical02
    # source, actual07 control proof and its old manifest; no source is dropped.
    old_path = R/'.work/hir-options-hash-runtime-installation-preparation-execution-06/source-rows.json'
    old_record_path = old_path.with_name('record.json')
    old_record = document(old_record_path, '2979f64660c2154d6fda90da711f3c967e15442cdb93191ff854ced5385c90f8')
    old = document(old_path, 'b7e76927bfc727cbad9542b3d6ac47c98289886d2fd6e2c6268831e65e24887d')
    files = dict(old)
    assert len(files) == 502
    assert old_record['status']=='finished' and old_record['returncode']==0 and old_record['preparation_passed'] is True
    old_invocation_path = ROOT/'.work/runtime-installation06-preparation-invocation-01.json'
    invocation = document(old_invocation_path, '0fb2866a8922cb4ba72ab6270b84b167e3725715c1bfa6a1fc25a3b7984aa32d')
    for name, row in files.items():
        assert raw(name)[1] == row
    source_names = ['entry.py','controller.py','audit_owner.py','routes.json',
                    'prepare.py','prepare_once.py','launch.py','imports.py','test_installation.py','test_imports.py']
    # The preflight JSON is authenticated separately by invocation.preflight before
    # producer imports. It is then re-read into the producer's physical file table
    # by completed_preflight; it is not executable startup source.
    selected_sources=[SOURCE/name for name in source_names]+[NATIVE/name for name in
        ['runtime_compiler.py','producer_recipe.py','audit_recipe.py','test_native_loader.py']]
    selected_sources.append(SOURCE.with_name('runtime-installation-after-preflight05-02')/'installation-plan-01/specification.json')
    for path in selected_sources + [audit_path]:
        row = raw(path)[1]
        assert str(path) not in files or files[str(path)] == row
        files[str(path)] = row
    for path in selected_sources:
        assert files[str(path)]['sha256'] == inputs['files'][str(path)]['sha256']

    wire = document(invocation['rehearsal_inputs']['path'], invocation['rehearsal_inputs']['sha256'])
    base = document(wire['file_table_base']['path'], wire['file_table_base']['sha256'])
    assert not set(base['files']) & set(wire['files'])
    historical = set(document(invocation['retirement']['path'], invocation['retirement']['sha256'])['selected_paths'])
    assert not set(files) & (historical | set(wire['absent_paths']))
    full = dict(base['files'], **wire['files'])
    union = {name: row for name, row in full.items() if name.startswith('/Users/danluu/dev/') and name.endswith('.py')}
    for name, row in files.items():
        assert name not in full or full[name] == row
        assert name not in union or union[name] == row
        union[name] = row
    assert len(union)+1 <= 520
    assert sum(row['size'] for row in union.values()) + 256*1024 <= 8*2**20
    manifest_path = ROOT/'.work/runtime-installation07-startup-qualified-source-manifest-01.json'
    invocation_path = ROOT/'.work/runtime-installation07-preparation-invocation-01.json'
    review_path = ROOT/'.work/runtime-installation07-preparation-source-binding-review-01.json'
    assert all(not os.path.lexists(path) for path in [manifest_path, invocation_path, review_path])
    for name, row in union.items():
        assert raw(name)[1] == row
    write(manifest_path, dict(status='reviewed-runtime-installation07-startup-source-closure', files=files))
    union[str(manifest_path)] = raw(manifest_path)[1]
    assert len(union) <= 520 and sum(row['size'] for row in union.values()) <= 8*2**20
    invocation['status'] = 'reviewed-runtime-installation07-preparation'
    invocation['phase'] = 'installation'
    invocation['preflight'] = ref(preflight_path)
    invocation['adapter'] = dict(preparer=ref(SOURCE/'prepare.py'), source_manifest=ref(manifest_path),
        startup_controls=invocation['adapter']['startup_controls'], retry_controls=invocation['adapter']['retry_controls'],
        installation_controls=ref(audit_path))
    write(invocation_path, invocation)
    write(review_path, dict(status='bound-from-actual-closed-installation48-and-preflight05',
        old_manifest=ref(old_path), source_manifest=ref(manifest_path), invocation=ref(invocation_path),
        controls_audit=ref(audit_path), controls_execution=ref(execution_path),
        controls_preparation=ref(controls_preparation_path), controls_preparer=ref(controls_preparer),
        preflight_audit=ref(preflight_path), preflight_execution=ref(preflight_execution_path),
        retained_old_manifest_rows=502, omitted_from_preimport_only=sorted(set(old)-set(files)),
        separately_authenticated_preflight=ref(preflight_path), preflight_omitted_from_preimport_only=True,
        omitted_files_deleted=False,
        reason='All actual06 source-rows502 retained. Add current source03/native sources and exact old specification fixture; current control audit and new manifest remain bounded. Preflight audit is authenticated separately before imports and re-added by production.',
        new_harness_executed_by_preparer=False,
        manifest_files=len(files), full_preimport_files=len(union),
        full_preimport_bytes=sum(row['size'] for row in union.values()),
        compiler_calls=0, provider_calls=0, runtime_preparation_executed=False))
    print(json.dumps(dict(manifest=ref(manifest_path), invocation=ref(invocation_path), review=ref(review_path))))


if __name__ == '__main__':
    main()
