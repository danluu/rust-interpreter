"""Read-only runtime04 saved-evidence orchestration, awaiting source review.

This module has no CLI and publishes nothing. A separately reviewed bounded
entry must authenticate its own source, actual53/45 qualification, the complete
expanded packet and supplemental source manifest before importing this module.
The function below rechecks those associations and returns a report only after
the actual owner's complete saved evidence has passed. It never constructs a
Controller, RuntimeCompiler or final-validator factory.
"""
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
HERE = ROOT/'experiments/hir-options-hash-runtime-audit-05'
PHASE_SOURCE = ROOT/'experiments/hir-options-hash-runtime-audit-04'
SOURCE = X/'experiments/hir-options-hash/runtime-installation-04'
HASH = ROOT/'experiments/hir-options-hash-driver-stage-03'
HASH_AUDIT = dict(path=str(ROOT/'.work/hir-options-hash-driver-independent-verification-02.json'),
    sha256='9540ad45b5423f793e323bac31d593f1c1b030fe0e1dd5fc3665565277885ebb')
PHASE_AUDIT = dict(path=str(ROOT/'.work/hir-options-hash-runtime-audit-controls-independent-verification-04.json'),
    sha256='c86c5f2e33c0aeed5b67fd75256e20f47626b21bdbb494bcd4eb6b74af57b25d')
CONTROL_SOURCE = ROOT/'experiments/runtime-saved-audit-controls-05'
CONTROL_WORK = ROOT/'.work/runtime-saved-audit-controls-05'
CONTROL_AUDIT = ROOT/'.work/runtime-saved-audit-controls-independent-verification-05.json'
STARTUP_SOURCE = ROOT/'experiments/runtime04-environment-adapter-01'
STARTUP_CONTROL = ROOT/'experiments/runtime-startup-environment-controls-01'
STARTUP_WORK = ROOT/'.work/runtime-startup-environment-controls-01'
STARTUP_AUDIT = ROOT/'.work/runtime-startup-environment-controls-independent-verification-01.json'
HASH_PLAN = dict(path=str(HASH/'plan.json'),
    sha256='24faa0611eacda26748727e443bef844c695c3ed362cda75b5aa60223e4d6055')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False)+'\n').encode()


def same(left, right):
    return encoded(left) == encoded(right)


def source_identity(module, io, expected_path):
    name = Path(module.__file__)
    require(name == expected_path and str(name) in io.files, 'separately bound source module route required')
    io.file(name)


def actual_controls(reader, io, reference, *, source, work, modules, tests, count):
    require(set(reference) == {'path', 'sha256'} and io.sha(reference['path']) == reference['sha256'],
            'exact actual control audit reference required')
    proof = reader.controls(source=source, work=work, audit_path=reference['path'],
        source_paths=modules, test_paths=tests, read_json=io.read_json,
        read_bytes=io.read_bytes, sha=io.sha, identity=io.identity)
    # The independent reader returns the count as controls; this is an actual
    # source-derived count, not an invented future digest or a source-only AST.
    require(type(proof['controls']) is int and proof['controls'] == count, 'complete actual control count differs')
    return proof


def current_guard(freeze, io, guard, *, full):
    for name in freeze['files']:
        guard()
        if full:
            io.file(name)
        else:
            io.identity(name)
    for name, row in freeze['links'].items():
        guard(); identity = io.identity(name)
        stamp = [identity[k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
        require(stat.S_ISLNK(identity['mode']) and same(stamp, row['stamp'])
                and os.readlink(name) == row['target'] and str(Path(name).resolve(strict=True)) == row['resolved'],
                'complete frozen provider link changed')
    for name in freeze['absent_paths']:
        require(not os.path.lexists(name), 'actual prepared absence changed')
    for name, resolved in freeze['executor_routes'].items():
        require(str(Path(name).resolve(strict=True)) == resolved, 'actual executor route changed')
    for module in list(sys.modules.values()):
        source = getattr(module, '__file__', None)
        if source and source.startswith('/Users/danluu/dev/'):
            require(str(Path(source).resolve(strict=True)) in io.files,
                    'unqualified imported audit/producer source is outside inspection union')


def exact_output_tree(io, root, files, empty_directories=()):
    """Compare complete actual membership, not a pre-write observation prefix."""
    root = Path(root); wanted_files = set()
    for name in files:
        p = Path(name)
        require(p.is_relative_to(root) and p != root, 'output member is outside exact owner')
        wanted_files.add(str(p.relative_to(root)))
    directories = {'.'} | set(empty_directories)
    for name in wanted_files | directories.copy():
        directories.update(str(p) for p in PurePosixPath(name).parents)
    observed = io.inventory(root)
    require(set(observed) == wanted_files | directories, 'complete closed output membership differs')
    for name, row in observed.items():
        require(row['kind'] == ('file' if name in wanted_files else 'directory'), 'closed output kind differs')
    return dict(files=len(wanted_files), directories=len(directories),
        inventory_sha256=hashlib.sha256(encoded(observed)).hexdigest())


def verify(*, phase, expected, prepared, inspection, io, reader, recipe,
           preflight, final_runtime, factory, entry, actual53, startup_owner, actual39, guard):
    """Verify one actual phase with an authenticated inspection context.

    ``prepared`` is the original fully expanded runtime freeze. ``inspection``
    is audit_io.inspection_union's result, with all supplemental rows separately
    qualified by the enclosing entry. ``io`` is Access over that union, explicit
    provider metadata entries and exactly packet/work/outer/launcher/prefix
    output scopes. No future audit may satisfy any argument with a placeholder.
    The entry authenticates helpers/controls before their import; this function
    repeats their saved-evidence qualification before any producer Reader use.
    """
    started = time.time(); guard()
    require(phase in ['preflight', 'installation'] and same(prepared, inspection['prepared'])
            and same(io.files, inspection['value']['files']), 'exact original/inspection distinction required')
    require(same({k:v for k,v in prepared.items() if k != 'files'},
                 {k:v for k,v in inspection['value'].items() if k != 'files'}),
            'inspection union changed original runtime metadata')
    source_identity(reader, io, HERE/'reader.py')
    source_identity(recipe, io, PHASE_SOURCE/'recipe.py')
    source_identity(preflight, io, PHASE_SOURCE/'preflight.py')
    source_identity(final_runtime, io, PHASE_SOURCE/'final_runtime.py')
    source_identity(factory, io, SOURCE/'imports.py')
    source_identity(entry, io, SOURCE/'entry.py')
    source_identity(startup_owner, io, STARTUP_SOURCE/'audit_owner.py')
    source_identity(startup_owner.environment, io, STARTUP_SOURCE/'environment.py')
    require(actual53['path'] == str(CONTROL_AUDIT), 'exact actual53 control route required')
    controls53 = actual_controls(reader, io, actual53, source=CONTROL_SOURCE, work=CONTROL_WORK,
        modules=[HERE/'reader.py', HERE/'audit_io.py'],
        tests=[HERE/'test_reader.py', HERE/'test_audit_io.py'], count=53)
    controls45 = actual_controls(reader, io, PHASE_AUDIT,
        source=ROOT/'experiments/hir-options-hash-runtime-audit-controls-04',
        work=ROOT/'.work/hir-options-hash-runtime-audit-controls-04',
        modules=[PHASE_SOURCE/(n+'.py') for n in ['recipe','preflight','final_runtime']],
        tests=[PHASE_SOURCE/(n+'.py') for n in ['test_recipe','test_preflight','test_final_runtime']], count=45)

    require(actual39['path'] == str(STARTUP_AUDIT), 'exact actual startup control route required')
    controls39 = actual_controls(reader, io, actual39, source=STARTUP_CONTROL, work=STARTUP_WORK,
        modules=[STARTUP_SOURCE/'environment.py',STARTUP_SOURCE/'audit_owner.py'],
        tests=[STARTUP_SOURCE/'test_environment.py',STARTUP_SOURCE/'test_audit_owner.py'], count=39)
    startup_qualification = dict(controls39, source=str(STARTUP_CONTROL), evidence=str(STARTUP_WORK))
    paths = reader.phase_paths(phase); packet, work, outer = [paths[k] for k in ['packet','work','outer']]
    launcher_root = R/('.work/hir-options-hash-runtime-'+phase+'-launch-execution-04')
    require(expected['launcher_record'] == str(launcher_root/'record.json'), 'exact standalone runtime launcher route')
    plan = io.read_json(packet/'plan.json'); launch = io.read_json(packet/'launch.json')
    terminal = io.read_json(work/'receipt.json'); supervisor = io.read_json(outer/'status.json')
    launcher = io.read_json(expected['launcher_record']); snapshot = io.read_json(packet/'snapshot-plan.json')
    require(io.sha(outer/'status.json') == expected['outer']
            and io.sha(work/'source-probe/result.json') == expected['result']
            and prepared['plan_sha256'] == io.sha(packet/'plan.json'), 'exact actual result/outer/original plan pins')
    # Derive the expected workload independently of the candidate runtime plan.
    # The immutable compact hash wire binds the original environment directly;
    # the unchanged Reader below also reconstructs its complete metadata member.
    require(io.sha(HASH_PLAN['path']) == HASH_PLAN['sha256'], 'actual hash environment source changed')
    hash_wire = io.read_json(HASH_PLAN['path'])
    require(set(hash_wire) == {'policy','member','reference','remainder','integrity'}
        and hash_wire['policy'] == 'external-json-member-v1' and hash_wire['member'] == 'metadata_plan',
        'actual hash plan envelope differs')
    workload_environment = copy.deepcopy(hash_wire['remainder']['environment'])
    require(type(workload_environment) is dict, 'actual hash workload environment required')
    workload_environment['TMPDIR'] = str(work/'tmp')
    startup_owner.owner(plan, launch, terminal, supervisor, launcher, phase=phase, expected=expected,
        sha=io.sha, read_json=io.read_json, original=reader, workload_environment=workload_environment,
        validate_qualification=lambda given: same(given, startup_qualification))
    require(plan['hash_source'] == str(HASH) and same(plan['independent_audits']['hash'], HASH_AUDIT),
            'actual successful hash02 owner is required')

    # Authenticate the complete possible local Python closure before the
    # factory's transitive stage.dependencies imports. New audit and producer
    # rows are explicit physical rows in the inspection context.
    for name in io.files:
        if name.startswith('/Users/danluu/dev/') and name.endswith('.py'):
            io.file(name)
    current_guard(inspection['value'], io, guard, full=True)
    modules = factory.definitions(HASH, io.file)
    state = modules.prerequisites.Reader(modules.stage, modules.hash_modules,
        combined_freeze=inspection['value'], references=plan['independent_audits'],
        read_json=io.read_json, sha=io.sha,
        copy_partition=lambda r: entry.copy_partition(modules, r, load=factory.load,
            directory_record=io.directory_record, saved=prepared['historical_copies']))
    require(same(state.copy_state['references'], prepared['historical_copies'])
            and set(state.copy_state['historical_files']) == set(io.historical),
            'independently rebuilt historical partition differs')
    retired = entry.retirement_qualification(modules, plan['copy_retirement'], state.copy_state,
        read_json=io.read_json, sha=io.sha)
    require(set(io.historical) <= set(prepared['absent_paths'])
            and all(not os.path.lexists(name) for name in io.historical),
            'all actually retired copies must be real prepared absences')
    qualified = state.check(full=True)
    require(same(qualified, plan['qualified_prerequisites']), 'complete current prerequisite summary differs')
    controls52 = entry.runtime_qualification(state)
    controls70 = entry.catalog_qualification(state)
    require(same(controls52, plan['runtime_adapter_qualification'])
            and same(controls70, plan['catalog_qualification']), 'actual producer/helper qualification differs')
    state.reader.snapshot_qualification()
    catalog = factory.load('completed_catalog', entry.CATALOG_SOURCE, io.file)
    snapshots = factory.load('qualified_snapshots', modules.stage.SNAPSHOT_SOURCE, io.file)
    # This returns None for the first preflight; only later installation is
    # allowed to require the prior preflight's already published independent audit.
    previous = entry.preflight_catalog_owner(modules, plan,
        read_json=io.read_json, read_bytes=io.read_bytes, sha=io.sha)
    require(phase != 'preflight' or previous is None, 'first preflight cannot require its own audit')
    lineage = entry.completed_catalog(modules, state, catalog, snapshots, plan['evidence_roots'],
        read_json=io.read_json, read_bytes=io.read_bytes, sha=io.sha, file_record=io.record,
        directory_record=io.directory_record, guard=guard, preflight_owner=previous)
    require(same(lineage, plan['snapshot_reuse']), 'complete actual runtime snapshot ancestry differs')
    snapshot_proof = reader.snapshot_readback(plan=plan, freeze=prepared, packet=packet, work=work,
        terminal=terminal, snapshot=snapshot, manifest=io.read_json(work/'source-snapshots.json'),
        lineage=lineage, catalog=catalog, snapshots=snapshots, read_json=io.read_json,
        sha=io.sha, identity=io.identity, directory_record=io.directory_record, guard=guard)

    specification = io.read_json(plan['specification']['path'])
    require(plan['specification']['path'] == str(packet/'specification.json')
            and io.sha(packet/'specification.json') == plan['specification']['sha256'], 'actual specification binding differs')
    if phase == 'preflight':
        desired = recipe.preflight_commands(modules.q, specification, R, work/'source-probe', plan['environment'])
    else:
        key, sysroot, desired = recipe.installation_commands(modules.q, specification, R, work, plan['environment'])
        require(key == plan['runtime_key'] and str(sysroot) == plan['sysroot'], 'actual final keyed prefix differs')
    history = reader.child_history(plan, terminal, desired=desired,
        read_json=io.read_json, read_bytes=io.read_bytes, sha=io.sha)
    validator = preflight if phase == 'preflight' else final_runtime
    phase_proof = validator.validate(plan=plan, spec=specification, terminal=terminal,
        children=history['children'], runtime=modules.q.runtime, q=modules.q, recipe=recipe,
        read_json=io.read_json, read_bytes=io.read_bytes, sha=io.sha, identity=io.identity,
        inventory=io.inventory, guard=guard)

    result = io.read_json(work/'source-probe/result.json')
    members = {work/'receipt.json', work/'snapshot-plan.json', work/'source-snapshots.json',
               work/'source-probe/source.rs', work/'source-probe/result.json'}
    for child in desired:
        members.update(Path(child['output'])/name for name in ['receipt.json','stdout','stderr'])
    members.update(Path(row['path']) for row in result['retained_sources'].values())
    for row in io.read_json(work/'source-snapshots.json')['storage'].values():
        if row['kind'] == 'stored':
            members.add(Path(row['path']))
    output_proof = exact_output_tree(io, work, members, empty_directories=['tmp'])
    packet_proof = exact_output_tree(io, packet, [packet/name for name in
        ['source-policy-proof.json','specification.json','plan.json','inputs.json',
         'snapshot-plan.json','metadata-preflight.json','launch.json']])
    outer_proof = exact_output_tree(io, outer,
        [outer/name for name in ['plan.json','status.json','command.log']])
    launcher_proof = exact_output_tree(io, launcher_root,
        [launcher_root/name for name in ['record.json','stdout','stderr','launcher.py']])
    require(launcher['retained_launcher_source'] == str(launcher_root/'launcher.py')
            and io.sha(launcher_root/'launcher.py') == launcher['launcher_source_sha256'],
            'retained actual standalone launcher source differs')
    preparation_root = Path(expected['preparation']['path']).parent
    preparation_proof = exact_output_tree(io, preparation_root, [preparation_root/name for name in
        ['record.json','stdout','stderr','launcher.py','invocation.json','source-rows.json','child-observation.json']])
    preparation_record = io.read_json(expected['preparation']['path'])
    require(io.sha(preparation_root/'invocation.json') == preparation_record['invocation']['sha256'],
            'retained actual preparation invocation differs')
    for name in ['stdout','stderr']:
        require(io.sha(preparation_root/name) == preparation_record[name+'_sha256'],
                'actual preparation raw differs')
    require(not io.read_bytes(preparation_root/'stderr'), 'successful preparation emitted stderr')
    source_rows = io.read_json(preparation_root/'source-rows.json')
    require(type(source_rows) is dict and 0 < len(source_rows) <= 512
        and sum(row['size'] for row in source_rows.values()) <= 8*2**20,
        'bounded actual preparation source union required')
    for name,row in source_rows.items():
        require(name in io.files and same(row,io.files[name]), 'actual preparation source omitted or relabeled')
    current_guard(inspection['value'], io, guard, full=True)
    io.recheck(full=True)
    require(all(not os.path.lexists(name) for name in io.historical), 'retired names reappeared during audit')
    return dict(status='verified', phase=phase, started_at=started, finished_at=time.time(),
        receipt_sha256=io.sha(work/'receipt.json'), result_sha256=io.sha(work/'source-probe/result.json'),
        inputs_sha256=expected['inputs'], plan_sha256=io.sha(packet/'plan.json'),
        snapshot_plan_sha256=expected['snapshot_plan'], outer_sha256=expected['outer'],
        launcher_record_sha256=expected['launcher_record_sha256'],
        actual_children=len(desired), original_prepared_files=len(prepared['files']),
        inspection_union=copy.deepcopy(inspection['report']), historical_copy_retirement=retired,
        actual53=controls53, phase45=controls45, producer52=controls52, continuation70=controls70,
        startup39=controls39, startup_environment=copy.deepcopy(plan['startup_environment']),
        preparation=copy.deepcopy(expected['preparation']), preparation_launcher=copy.deepcopy(expected['preparation_launcher']),
        preparation_membership=preparation_proof,
        qualified_prerequisites=qualified, full_current_input_rehash=True,
        snapshots=snapshot_proof, phase_result=phase_proof, output_membership=output_proof,
        packet_membership=packet_proof, outer_membership=outer_proof,
        launcher_membership=launcher_proof, process_identities=history['identities'],
        unavailable_contemporaneous_cwd=history['unavailable_contemporaneous_cwd'],
        first_preflight_has_no_circular_audit=phase == 'preflight',
        compiler_calls=0, provider_probes=0, application_qualified=False,
        performance_measurement=False, exporter_qualified=False, std_mir_prepared=False)
