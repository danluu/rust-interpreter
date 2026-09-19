"""Read-only preflight05 saved-evidence orchestration, awaiting source review.

This module has no CLI and publishes nothing. A separately reviewed bounded
entry must authenticate its own source, actual53/45 qualification, the complete
expanded packet and supplemental source manifest before importing this module.
The function below rechecks those associations and returns a report only after
the actual owner's complete saved evidence has passed. It never constructs a
Controller, RuntimeCompiler or final-validator factory.
"""
import ast
import copy
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import stat
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
HERE = ROOT/'experiments/hir-options-hash-runtime-audit-10'
QUALIFIED_AUDIT = ROOT/'experiments/hir-options-hash-runtime-audit-05'
ATTEMPT = ROOT/'experiments/runtime-preflight-retry-05'
ROUTES_PATH = ATTEMPT/'routes.json'
ROUTES_SHA = '893d6102741b5206a829e2f5e130614667140b1eacc09d0c55616f7311f82e6a'
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
RETRY_CONTROL = ROOT/'experiments/runtime-preflight-retry-controls-05'
RETRY_WORK = ROOT/'.work/runtime-preflight-retry-controls-05'
RETRY_AUDIT = ROOT/'.work/runtime-preflight-retry-controls-independent-verification-05.json'
RETRY_COUNT = 33  # Source-derived count; separate actual frozen qualification is still required.
RETRY_FILES = ('entry.py','controller.py','audit_owner.py','routes.json','prepare.py','prepare_once.py','launch.py')
LINK_SOURCE = ROOT/'experiments/runtime-frozen-link-reader-01'
LINK_CONTROL = ROOT/'experiments/runtime-frozen-link-controls-01'
LINK_RESULT = ROOT/'results/runtime-frozen-link-controls-01/result.json'
LINK_COUNT = 24  # Source-derived; actual result/record/manifest must be independently bound.
LINK_PROOF = {'result_sha256': 'cfb7577f2345147a9c5f4d44b7c562d7e92e61bdcc91e7b95fbba48c8ac22497', 'record_sha256': 'a2acb45bb98cb6c3b44bddbb7b2f43331281f38aa219a14aa56ac7bddf06441c', 'manifest_sha256': 'a4380c58427d256f7e7c450752e6d724d20d528f45a6d9766f876cc6d1ebab80'}
FAILED_LINK_AUDIT = dict(path=str(ROOT/'.work/runtime06-saved-audit-preflight-execution-01/record.json'),
    sha256='4b7e57aa4a1aa0bf09a6725dd47056497cd7a5ef56b0f3a36f2a77fce60fdb2b')
FAILED_COMPLETED_AUDIT = dict(path=str(ROOT/'.work/runtime08-saved-audit-preflight-execution-01/record.json'),
    sha256='71c59ba889fa71da8ea326b1f04723a472db7e1f580b545a13071dcbee12975c')
FAILED_AUDIT = dict(path=str(ROOT/'.work/runtime09-saved-audit-preflight-execution-01/record.json'),
    sha256='23786949ac2f542f28aefc95f1a8d03a0ba680322cbf8dd765530c8f57ee1b42')
FAILED_REVIEW = dict(path=str(ROOT/'results/runtime04-preflight-capacity-failure-01/review.json'),
    sha256='3d29955a0512ba66dd86da9f50c18c93a013cbb0e648f5a25ae378eaaf1afaa3')
HASH_PLAN = dict(path=str(HASH/'plan.json'),
    sha256='24faa0611eacda26748727e443bef844c695c3ed362cda75b5aa60223e4d6055')

COMPLETED_READER_SHA = '4a3d78ece513e77a3d1f79723c26f0b30183111c626ecbadfb37e67227a3ed4e'


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


def frozen_link_controls(reference, *, read_json, read_bytes, sha, identity):
    """Authenticate the direct real-filesystem controls, not reader.controls."""
    require(type(LINK_COUNT) is int and LINK_COUNT == 24
        and all(type(value) is str and re.fullmatch('[a-f0-9]{64}', value)
                for value in LINK_PROOF.values()), 'actual frozen-link controls remain unbound')
    output = LINK_RESULT.parent
    require(same(reference, dict(path=str(LINK_RESULT), sha256=LINK_PROOF['result_sha256']))
        and sha(LINK_RESULT) == reference['sha256'], 'exact actual frozen-link result required')
    result = read_json(LINK_RESULT)
    require(result['status'] == 'verified-frozen-link-controls' and type(result['tests']) is int
        and result['tests'] == LINK_COUNT and result['source_unchanged'] is True
        and type(result['compiler_calls']) is int and result['compiler_calls'] == 0
        and all(result[key] is False for key in ['network','provider_writes','canonical_lock_access','runtime_audit_qualified'])
        and type(result['owned_bytes']) is int and 0 <= result['owned_bytes'] <= 8*2**20,
        'complete successful direct control result required')
    def check_row(path, row):
        require(type(row) is dict and set(row) == {'bytes','sha256','identity'}
            and type(row['bytes']) is int and 0 <= row['bytes'] <= 64*2**20
            and type(row['identity']) is dict and set(row['identity']) ==
                {'dev','ino','mode','nlink','size','mtime_ns','ctime_ns'}
            and all(type(v) is int for v in row['identity'].values())
            and sha(path) == row['sha256'] and same(identity(path), row['identity'])
            and row['bytes'] == row['identity']['size'], 'actual control byte/identity row differs')
    refs = dict(record=output/'record.json',source_before=output/'source-before.json',
        source_after=output/'source-after.json',stdout=output/'stdout',stderr=output/'stderr',plan=LINK_CONTROL/'plan.json')
    for key,path in refs.items():
        require(type(result[key]) is dict and set(result[key]) == {'path','sha256'}
            and result[key]['path'] == str(path) and sha(path) == result[key]['sha256'],
            'exact direct control closure reference differs')
    require(result['record']['sha256'] == LINK_PROOF['record_sha256']
        and sha(output/'manifest.json') == LINK_PROOF['manifest_sha256'], 'actual direct control closure anchors differ')
    manifest = read_json(output/'manifest.json')
    members = {'run_once.py','child.py','plan.json','started.json','record.json','source-before.json',
               'source-after.json','stdout','stderr','result.json'}
    require(set(manifest) == members and {p.name for p in output.iterdir()} == members|{'manifest.json','tmp'}
        and stat.S_ISDIR((output/'tmp').lstat().st_mode) and not list((output/'tmp').iterdir()),
        'complete direct control output membership differs')
    for name,row in manifest.items(): check_row(output/name,row)
    record = read_json(output/'record.json'); started = read_json(output/'started.json')
    plan = read_json(LINK_CONTROL/'plan.json')
    before = read_json(output/'source-before.json'); after = read_json(output/'source-after.json')
    require(same(before,after) and same(before,result['sources']), 'control sources changed before/after')
    python = str(Path('/opt/homebrew/bin/python3').resolve(strict=True))
    expected_sources = {str(LINK_SOURCE/'links.py'),str(LINK_SOURCE/'test_links.py'),
        str(LINK_CONTROL/'run_once.py'),str(LINK_CONTROL/'child.py'),str(LINK_CONTROL/'plan.json'),python}
    require(set(before) == expected_sources and plan['python_resolved'] == python,
        'complete direct-control implementation/test/runner/interpreter source set differs')
    for name,row in before.items(): check_row(name,row)
    for name in ['run_once.py','child.py','plan.json']:
        require(sha(output/name) == sha(LINK_CONTROL/name), 'retained direct-control source differs')
    require(plan['policy'] == 'owned-temp-frozen-link-controls-v1' and plan['actual_result'] is None
        and plan['source_root'] == str(LINK_SOURCE) and plan['control_source'] == str(LINK_CONTROL)
        and plan['future_output'] == str(output) and plan['cwd'] == str(LINK_SOURCE)
        and plan['command'] == ['/opt/homebrew/bin/python3','-B',str(LINK_CONTROL/'child.py')]
        and plan['canonical_lock_access'] is False and plan['provider_writes'] is False
        and plan['network'] is False and type(plan['compiler_calls']) is int and plan['compiler_calls'] == 0
        and same(plan['bounds'],dict(cpu_seconds=30,entry_free_bytes=256*2**20,file_bytes=256*1024,
            observer_seconds=60,owned_bytes=8*2**20,stop_free_bytes=128*2**20)), 'direct-control plan/bounds differ')
    for key,names in [('sources',[LINK_CONTROL/'child.py',LINK_SOURCE/'links.py',LINK_SOURCE/'test_links.py']),
                      ('test_sources',[LINK_SOURCE/'links.py',LINK_SOURCE/'test_links.py'])]:
        require(same(plan[key],{str(name):before[str(name)] for name in names}), 'source-bound direct control plan differs')
    names = sorted('test_links.'+cls.name+'.'+method.name
        for cls in ast.parse(read_bytes(LINK_SOURCE/'test_links.py')).body if isinstance(cls,ast.ClassDef)
        for method in cls.body if isinstance(method,ast.FunctionDef) and method.name.startswith('test_'))
    require(len(names) == len(set(names)) == LINK_COUNT and type(plan['tests']) is int and plan['tests'] == LINK_COUNT
        and same(names,plan['test_names']) and same(names,result['test_names']), 'source-derived actual link test names differ')
    environment = dict(PATH='/usr/bin:/bin:/opt/homebrew/bin',LANG='C',LC_ALL='C',TMPDIR=str(output/'tmp'),
        PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONHASHSEED='0')
    require(record['status'] == 'closed' and type(record['returncode']) is int and record['returncode'] == 0
        and record['may_be_live'] is False and record['observation_errors'] == []
        and record['command'] == plan['command'] and record['cwd'] == str(LINK_SOURCE)
        and same(record['environment'],environment) and record['plan_sha256'] == result['plan']['sha256']
        and all(type(record[key]) is int and record[key] > 0 for key in ['pid','parent_pid','parent_parent_pid'])
        and record['started_at'] <= record['spawned_at'] <= record['observation_finished_at'] <= record['finished_at']
        and record['finished_at']-record['spawned_at'] <= 60
        and record['cpu_seconds'] == 30 and record['observer_seconds'] == 60
        and record['file_bytes'] == 256*1024 and record['namespace_bytes'] == 8*2**20
        and record['canonical_lock_access'] is False and type(record['compiler_calls']) is int and record['compiler_calls'] == 0
        and type(record['retries']) is int and record['retries'] == 0 and record['signals'] == []
        and not any(key in record for key in ['execution_error','publication_error']),
        'actual direct-control child closure/identity/limits differ')
    require(started['status'] == 'running' and started['may_be_live'] is True
        and all(same(started[key],record[key]) for key in ['command','cwd','environment','pid','parent_pid',
            'parent_parent_pid','started_at','spawned_at','plan_sha256']), 'retained started child association differs')
    for key in ['stdout','stderr']: check_row(output/key,record[key])
    raw = read_bytes(output/'stdout').decode(); require(read_bytes(output/'stderr') == b'', 'direct controls emitted stderr')
    lines = raw.splitlines(); footer = [line for line in lines if line.startswith('FROZEN_LINK_CONTROL_RESULT ')]
    require(len(footer) == 1 and [line for line in lines if line.startswith('test_')] ==
        [name.rsplit('.',1)[1]+' ('+name+') ... ok' for name in names], 'complete actual24 raw names differ')
    proof = json.loads(footer[0].split(' ',1)[1])
    require(same(proof,result['child_proof']) and proof['status'] == 'passed'
        and type(proof['tests']) is int and proof['tests'] == LINK_COUNT and same(proof['test_names'],names)
        and proof['child_pid'] == record['pid'] and proof['parent_pid'] == record['parent_pid']
        and proof['cwd'] == str(LINK_SOURCE) and same(proof['test_sources'],plan['test_sources'])
        and all(type(proof[key]) is int and proof[key] == 0 for key in ['skipped','failures','errors']),
        'actual direct-control child result differs')
    observed = proof['observed_environment']
    require(same(observed,environment) or same(observed,dict(environment,__CF_USER_TEXT_ENCODING='0x1F5:0x0:0x52')),
        'passed/observed startup environments differ beyond explicit validated CF addition')
    policy = proof['io_policy']
    require(policy['owned_tmp'] == str(output/'tmp') and policy['temporary_members_after'] == []
        and policy['denied_events'] == [] and type(policy['mutation_events']) is int and 0 <= policy['mutation_events'] <= 1024
        and all(policy[key] is False for key in ['provider_writes','subprocess_calls','network_calls','signal_calls']),
        'actual temporary-filesystem controls escaped their policy')
    return dict(status='verified-frozen-link-controls',tests=LINK_COUNT,test_names=names,result=dict(reference),
        record=dict(result['record']),manifest=dict(path=str(output/'manifest.json'),sha256=LINK_PROOF['manifest_sha256']),
        source_before=dict(result['source_before']),source_after=dict(result['source_after']),
        stdout=dict(result['stdout']),stderr=dict(result['stderr']),sources=before,
        passed_environment=environment,observed_environment=observed,
        controls_are_separate_from_actual53=True,compiler_calls=0)


def current_guard(freeze, io, guard, frozen_links, *, full):
    for name in freeze['files']:
        guard()
        if full:
            io.file(name)
        else:
            io.identity(name)
    require(same(frozen_links.rows, freeze['links']), 'complete original frozen-link rows differ')
    for name in freeze['links']:
        guard(); frozen_links.verify(name)
    require(set(frozen_links.checked) == set(freeze['links']), 'every declared frozen link must be checked')
    for name in freeze['absent_paths']:
        require(not os.path.lexists(name), 'actual prepared absence changed')
    for name, resolved in freeze['executor_routes'].items():
        require(str(Path(name).resolve(strict=True)) == resolved, 'actual executor route changed')
    for module in list(sys.modules.values()):
        source = getattr(module, '__file__', None)
        if source and source.startswith('/Users/danluu/dev/'):
            require(str(Path(source).resolve(strict=True)) in io.files,
                    'unqualified imported audit/producer source is outside inspection union')


def frozen_link_observations(frozen_links):
    """Bind all observations; retain plain deduplicated current ancestor routes."""
    directories = {}; links = {}; endpoints = set(); digest = hashlib.sha256()
    for name in sorted(frozen_links.checked):
        observation = frozen_links.checked[name]
        require(observation['path'] == name and same(observation['frozen_row'], frozen_links.rows[name])
            and observation['ancestors_were_in_original_freeze'] is False,
            'explicit original/current link association differs')
        digest.update(encoded(dict(path=name, observation=observation)))
        for row in observation['current_ancestor_observations']['directories']:
            path = row['path']; identity = row['identity']
            require(path not in directories or same(directories[path], identity), 'ancestor directory changed across links')
            directories.setdefault(path, copy.deepcopy(identity))
        for row in observation['current_ancestor_observations']['links']:
            # The declared leaf is already retained verbatim in the original
            # frozen table and complete digest above; only current ancestor
            # observations need an additional plain row in this report.
            if row['frozen_leaf']:
                continue
            path = row['path']; value = dict(identity=row['identity'], target=row['target'])
            require(path not in links or same(links[path], value), 'ancestor link changed across links')
            links.setdefault(path, copy.deepcopy(value))
        if stat.S_ISDIR(observation['resolved_identity']['mode']):
            path = observation['frozen_row']['resolved']; identity = observation['resolved_identity']
            require(set(identity) == {'dev','ino','mode'} and path in directories
                and same(directories[path], identity), 'directory endpoint/held route differs')
            endpoints.add(path)
    return dict(policy='complete-frozen-links-current-observations-v1', count=len(frozen_links.checked),
        frozen_rows_sha256=hashlib.sha256(encoded(frozen_links.rows)).hexdigest(),
        complete_observations_sha256=digest.hexdigest(),
        complete_observations_encoding='sorted per-name canonical JSON {path,observation}, each newline terminated',
        current_directories=dict(sorted(directories.items())), current_ancestor_links=dict(sorted(links.items())),
        directory_endpoint_count=len(endpoints),
        directory_endpoint_paths_sha256=hashlib.sha256(encoded(sorted(endpoints))).hexdigest(),
        original_frozen_leaf_rows_repeated=False, ancestor_observations_are_original_frozen_rows=False)


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


def supervisor_output_readback(io, outer, launch, supervisor, *, source):
    """Retain both owned streams without relabeling the command-log digest."""
    outer, source = Path(outer), Path(source)
    plan = io.read_json(outer/'plan.json')
    require(set(plan) == {'owner','command','supervisor_sha256'}
        and plan['owner'] == supervisor['cwd']
        and launch['command'][1:6] == ['-B',str(source),'--run-id',outer.name,'--']
        and same(plan['command'], launch['command'][6:])
        and same(plan['command'], supervisor['command'])
        and io.sha(outer/'plan.json') == supervisor['plan_sha256']
        and io.sha(source) == plan['supervisor_sha256'],
        'actual supervisor writer/owner/command source association differs')
    membership = exact_output_tree(io, outer, [outer/name for name in
        ['plan.json','status.json','command.log','supervisor.log']])
    command = io.record(outer/'command.log')
    raw = io.record(outer/'supervisor.log')
    require(command['sha256'] == supervisor['log_sha256'],
        'saved child-command stream digest differs')
    return dict(membership=membership, writer=dict(path=str(source),sha256=io.sha(source)),
        command_stream=command, supervisor_stream=raw,
        supervisor_stream_observation='current full raw readback; no historical stream hash was recorded')


def preparation_source_equality(source_rows, files):
    """Check the whole retained preparation table, including nonpacket sources."""
    require(type(source_rows) is dict and 0 < len(source_rows) <= 512
        and sum(row['size'] for row in source_rows.values()) <= 8*2**20,
        'bounded actual preparation source union required')
    for name, row in source_rows.items():
        require(name in files and same(row, files[name]),
            'actual preparation source omitted or relabeled')
    return dict(files=len(source_rows), logical_bytes=sum(row['size'] for row in source_rows.values()),
        table_sha256=hashlib.sha256(encoded(source_rows)).hexdigest(), complete_typed_equality=True)


def preparation_invocation_readback(io, root, reference):
    """The retained file reserializes the pinned original JSON document."""
    require(type(reference) is dict and set(reference) == {'path','sha256'}
        and io.sha(reference['path']) == reference['sha256'],
        'exact original preparation invocation differs')
    retained = Path(root)/'invocation.json'
    require(same(io.read_json(reference['path']), io.read_json(retained)),
        'retained preparation invocation changed typed JSON values')
    return dict(original=copy.deepcopy(reference), retained=io.record(retained),
        complete_typed_equality=True, same_raw_bytes=io.sha(retained) == reference['sha256'])


def failed_predecessor(plan, routes, io):
    """Retain the exact published failed04 history without a success owner."""
    require(io.sha(FAILED_REVIEW['path']) == FAILED_REVIEW['sha256'], 'published failed04 review differs')
    review = io.read_json(FAILED_REVIEW['path'])
    require(review['status'] == 'closed-capacity-failure-before-compiler-probes'
        and review['qualification_passed'] is False and type(review['actual_compiler_children']) is int
        and review['actual_compiler_children'] == 0 and review['source_probe_directory_absent'] is True,
        'failed04 must remain an unqualified zero-child failure')
    for row in review['packet_references'].values():
        require(io.sha(row['path']) == row['sha256'] and io.files[row['path']]['size'] == row['bytes'],
            'complete original failed04 packet binding differs')
    for row in review['retained_records'].values():
        require(io.sha(row['original_path']) == row['sha256']
            and io.files[row['original_path']]['size'] == row['bytes'], 'failed04 retained source/raw binding differs')
    paths = routes['failed_predecessor']
    refs = {key: dict(path=str(Path(paths[role])/name), sha256=io.sha(Path(paths[role])/name))
        for key, role, name in [('receipt','work','receipt.json'),('outer','supervisor','status.json'),
                               ('launcher','launcher_execution','record.json')]}
    expected = dict(refs, phase='preflight', status='failed-before-admission', children=0, review=FAILED_REVIEW)
    require(same(plan['failed_predecessor'], expected), 'explicit failed04 predecessor association differs')
    require(not os.path.lexists(Path(paths['work'])/'source-probe'), 'failed04 cannot acquire later probe evidence')
    return copy.deepcopy(expected)


def completed_directory_declarations(plan, files, *, read_json, read_bytes, sha):
    """Derive six metadata-only routes from the authenticated failed owner.

    This declares no subtree or file access and performs no directory syscall.
    The unchanged failed-owner reader still validates its full history later.
    """
    def document(reference):
        require(type(reference) is dict and set(reference) == {'path', 'sha256'},
                'exact completed-owner reference required')
        name = reference['path']
        require(name in files and files[name]['sha256'] == reference['sha256']
                and sha(name) == reference['sha256'], 'completed-owner source is not frozen')
        return read_json(name)

    wire = document(HASH_PLAN)
    require(set(wire) == {'policy','member','reference','remainder','integrity'}
            and wire['policy'] == 'external-json-member-v1' and wire['member'] == 'metadata_plan',
            'completed owner must come from original hash plan')
    owner = wire['remainder']['failed_driver']
    require(type(owner) is dict and set(owner) == {'role','source','evidence','audit'}
            and owner['role'] == 'failed-hash-driver-01'
            and owner['source'] == str(HASH.with_name('hir-options-hash-driver-stage-02')),
            'only the declared completed failed driver supplies directory access')
    associations = [row for row in plan['snapshot_reuse']['predecessors']
                    if row.get('role') == owner['role']]
    require(len(associations) == 1, 'exactly one original failed-owner association required')
    association = associations[0]
    require(association['completion'] == 'failed'
            and all(same(association[key], owner[key]) for key in ['role','source','evidence','audit'])
            and owner['evidence'] in plan['evidence_roots'], 'failed owner is not an accounted completed predecessor')
    work = Path(owner['evidence']); source = Path(owner['source'])
    require(work.is_absolute() and str(work) == owner['evidence'] and '..' not in work.parts,
            'canonical completed evidence route required')
    for key, expected in [('plan',source/'plan.json'),('receipt',work/'receipt.json'),
                          ('manifest',work/'source-snapshots.json'),('projection',source/'snapshot-plan.json'),
                          ('retained_projection',work/'snapshot-plan.json')]:
        require(association[key]['path'] == str(expected), 'completed-owner document route differs')
    original = document(association['plan']); terminal = document(association['receipt'])
    audit = document(owner['audit'])
    require(audit['status'] == 'verified-retained-failure' and terminal['status'] == 'failed'
            and audit['source'] == str(source) and audit['evidence'] == str(work)
            and audit['receipt_sha256'] == association['receipt']['sha256']
            and audit['plan_sha256'] == association['plan']['sha256']
            and audit['source_snapshots_sha256'] == association['manifest']['sha256']
            and audit['snapshot_plan_sha256'] == association['projection']['sha256']
            == association['retained_projection']['sha256']
            and audit['actual_compiler_children'] == 1 and audit['actual_driver_processes'] == 0
            and audit['hash_driver_qualified'] is False
            and audit['complete_failed_raw_history'] is audit['full_snapshot_selection'] is True,
            'closed audited failed-owner source binding required')
    authority = HASH/'failed_driver.py'
    require(str(authority) in files and files[str(authority)]['sha256'] == COMPLETED_READER_SHA
            and sha(authority) == COMPLETED_READER_SHA
            and hashlib.sha256(read_bytes(authority)).hexdigest() == COMPLETED_READER_SHA,
            'exact frozen failed-owner membership reader required')
    children = original['children']
    require(type(children) is list and len(children) == 3, 'original three-child recipe required')
    fixture = Path(children[1]['argv'][2]); artifacts = fixture.parent
    require(fixture.name == 'fixture.rs' and artifacts.is_absolute()
            and str(fixture) == children[1]['argv'][2] and '..' not in fixture.parts
            and children[2]['argv'][2] == str(fixture)
            and children[1]['argv'][3] == str(artifacts/'serial')
            and children[2]['argv'][3] == str(artifacts/'parallel')
            and children[0]['argv'][-2:] == ['-o',str(artifacts/'hash-control-driver')]
            and all(child['environment']['TMPDIR'] == str(artifacts/'tmp') for child in children),
            'completed artifact routes must come from the exact original recipe')
    require(set(audit['artifacts']) == {'fixture.rs','serial','parallel','tmp'}
            and audit['artifacts']['fixture.rs']['kind'] == 'file'
            and all(audit['artifacts'][name] == {'kind':'directory'} for name in ['serial','parallel','tmp'])
            and str(fixture) in files
            and files[str(fixture)]['sha256'] == audit['artifacts']['fixture.rs']['sha256'],
            'original failed artifact declarations differ')
    absent = [work/'result.json',work/'serial',work/'parallel',work/'linker-command.json',
              work/'driver-loader-closure.json',artifacts/'hash-control-driver']
    require(audit['absent_outputs'] == list(map(str,absent)), 'failed-owner absent outputs differ')
    root = str(work/'source-snapshots')
    require(association['snapshot_root'] == root and root in plan['snapshot_reuse']['evidence_roots'],
            'completed storage root must already have its own frozen declaration')
    memberships = {
        str(work):sorted(['receipt.json','compile','source-snapshots','source-snapshots.json','snapshot-plan.json']),
        str(work/'compile'):['receipt.json','stderr','stdout'],
        str(artifacts):['fixture.rs','parallel','serial','tmp'],
        **{str(artifacts/name):[] for name in ['serial','parallel','tmp']},
    }
    require(len(memberships) == 6 and not set(memberships).intersection(files),
            'exactly six distinct directory-only declarations required')
    for p in [work/'receipt.json',work/'source-snapshots.json',work/'snapshot-plan.json',
              work/'compile/receipt.json',work/'compile/stdout',work/'compile/stderr',fixture]:
        require(str(p) in files, 'completed directory cannot grant missing payload authorization')
    return dict(owner=copy.deepcopy(owner), hash_plan=dict(HASH_PLAN),
        membership_source=dict(path=str(authority),sha256=COMPLETED_READER_SHA),
        association=copy.deepcopy(association), directories=dict(sorted(memberships.items())))


def completed_directory_readback(declaration, io):
    """Use only qualified exact-entry directory APIs, never subtree authority."""
    result = {}
    require(type(declaration['directories']) is dict and len(declaration['directories']) == 6,
            'six completed-owner metadata declarations required')
    for name, children in declaration['directories'].items():
        require(name in io.entries and name not in io.files and name not in io.historical,
                'completed directory must have exact metadata-only authorization')
        row = io.directory_record(name)
        require(row['children'] == children, 'completed-owner exact directory membership differs')
        result[name] = row
    return result


def verify(*, phase, expected, prepared, inspection, io, reader, recipe,
           preflight, final_runtime, factory, entry, actual53, startup_owner, actual39, actual_retry, link_reader, actual_links, failed_audit, completed_evidence, guard):
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
    require(phase in ['preflight'] and same(prepared, inspection['prepared'])
            and same(io.files, inspection['value']['files']), 'exact original/inspection distinction required')
    require(same({k:v for k,v in prepared.items() if k != 'files'},
                 {k:v for k,v in inspection['value'].items() if k != 'files'}),
            'inspection union changed original runtime metadata')
    source_identity(reader, io, QUALIFIED_AUDIT/'reader.py')
    source_identity(recipe, io, PHASE_SOURCE/'recipe.py')
    source_identity(preflight, io, PHASE_SOURCE/'preflight.py')
    source_identity(final_runtime, io, PHASE_SOURCE/'final_runtime.py')
    source_identity(factory, io, SOURCE/'imports.py')
    source_identity(entry, io, ATTEMPT/'entry.py')
    source_identity(startup_owner, io, ATTEMPT/'audit_owner.py')
    source_identity(startup_owner.environment, io, STARTUP_SOURCE/'environment.py')
    source_identity(link_reader, io, LINK_SOURCE/'links.py')
    require(actual53['path'] == str(CONTROL_AUDIT), 'exact actual53 control route required')
    controls53 = actual_controls(reader, io, actual53, source=CONTROL_SOURCE, work=CONTROL_WORK,
        modules=[QUALIFIED_AUDIT/'reader.py', QUALIFIED_AUDIT/'audit_io.py'],
        tests=[QUALIFIED_AUDIT/'test_reader.py', QUALIFIED_AUDIT/'test_audit_io.py'], count=53)
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
    require(type(RETRY_COUNT) is int and RETRY_COUNT > 0, 'retry qualification count remains unbound')
    require(actual_retry['path'] == str(RETRY_AUDIT), 'exact retry control route required')
    retry_controls = actual_controls(reader, io, actual_retry, source=RETRY_CONTROL, work=RETRY_WORK,
        modules=[ATTEMPT/name for name in RETRY_FILES], tests=[ATTEMPT/'test_retry.py'], count=RETRY_COUNT)
    retry_qualification = dict(retry_controls, source=str(RETRY_CONTROL), evidence=str(RETRY_WORK))
    require(type(LINK_COUNT) is int and LINK_COUNT > 0, 'frozen-link qualification count remains unbound')
    require(actual_links['path'] == str(LINK_RESULT), 'exact separately qualified frozen-link controls')
    link_controls = frozen_link_controls(actual_links, read_json=io.read_json,read_bytes=io.read_bytes,
        sha=io.sha,identity=io.identity)
    require(same(failed_audit, FAILED_AUDIT) and io.sha(failed_audit['path']) == failed_audit['sha256'],
        'exact closed failed09 audit provenance differs')
    prior_audit = io.read_json(failed_audit['path'])
    require(prior_audit['status'] == 'finished' and type(prior_audit['returncode']) is int
        and prior_audit['returncode'] == 1 and prior_audit['may_be_live'] is False
        and prior_audit['observation_errors'] == [] and prior_audit['mode'] == 'audit'
        and prior_audit['phase'] == phase, 'original failed09 must remain a closed failed audit')
    require(io.sha(FAILED_LINK_AUDIT['path']) == FAILED_LINK_AUDIT['sha256'],
        'original failed06 link audit must remain separately retained')
    require(io.sha(FAILED_COMPLETED_AUDIT['path']) == FAILED_COMPLETED_AUDIT['sha256'],
        'original failed08 completed-directory audit must remain separately retained')
    def strict_target_file(name):
        io.file(name)
        return copy.deepcopy(io.files[name])
    frozen_links = link_reader.FrozenLinks(prepared['links'], read_file=strict_target_file, guard=guard)
    require(io.sha(ROUTES_PATH) == ROUTES_SHA, 'exact reviewed attempt routes required')
    routes = io.read_json(ROUTES_PATH)
    require(routes['phase'] == phase and routes['qualified_source'] == str(SOURCE)
        and routes['attempt_source'] == str(ATTEMPT), 'separate qualified and attempt source owners')
    packet, work, outer = [Path(routes[k]) for k in ['packet','work','supervisor']]
    launcher_root = Path(routes['launcher_execution'])
    require(expected['launcher_record'] == str(launcher_root/'record.json'), 'exact standalone runtime launcher route')
    plan = io.read_json(packet/'plan.json'); launch = io.read_json(packet/'launch.json')
    require(same(plan['attempt'], dict(path=str(ROUTES_PATH), sha256=ROUTES_SHA)), 'actual plan route binding differs')
    declared = completed_directory_declarations(plan, io.files, read_json=io.read_json,
        read_bytes=io.read_bytes, sha=io.sha)
    require(same(declared, completed_evidence['declaration']), 'completed directory authority changed after bootstrap')
    completed_before = completed_directory_readback(declared, io)
    require(same(completed_before, completed_evidence['observed']), 'completed directories changed after bootstrap')
    require(same(plan['retry_qualification'], retry_qualification), 'separate actual retry qualification differs')
    prior_failure = failed_predecessor(plan, routes, io)
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
        validate_qualification=lambda given: same(given, startup_qualification),
        validate_retry_qualification=lambda given: same(given, retry_qualification))
    require(plan['hash_source'] == str(HASH) and same(plan['independent_audits']['hash'], HASH_AUDIT),
            'actual successful hash02 owner is required')

    # Authenticate the complete possible local Python closure before the
    # factory's transitive stage.dependencies imports. New audit and producer
    # rows are explicit physical rows in the inspection context.
    for name in io.files:
        if name.startswith('/Users/danluu/dev/') and name.endswith('.py'):
            io.file(name)
    current_guard(inspection['value'], io, guard, frozen_links, full=True)
    link_observations_before = frozen_link_observations(frozen_links)
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
    outer_proof = supervisor_output_readback(io, outer, launch, supervisor,
        source=R/'scripts/supervise_experiment.py')
    launcher_proof = exact_output_tree(io, launcher_root,
        [launcher_root/name for name in ['record.json','stdout','stderr','launcher.py']])
    require(launcher['retained_launcher_source'] == str(launcher_root/'launcher.py')
            and io.sha(launcher_root/'launcher.py') == launcher['launcher_source_sha256'],
            'retained actual standalone launcher source differs')
    preparation_root = Path(expected['preparation']['path']).parent
    preparation_proof = exact_output_tree(io, preparation_root, [preparation_root/name for name in
        ['record.json','stdout','stderr','launcher.py','invocation.json','source-rows.json','child-observation.json']])
    preparation_record = io.read_json(expected['preparation']['path'])
    invocation_proof = preparation_invocation_readback(io, preparation_root, preparation_record['invocation'])
    for name in ['stdout','stderr']:
        require(io.sha(preparation_root/name) == preparation_record[name+'_sha256'],
                'actual preparation raw differs')
    require(not io.read_bytes(preparation_root/'stderr'), 'successful preparation emitted stderr')
    source_rows = io.read_json(preparation_root/'source-rows.json')
    preparation_source_proof = preparation_source_equality(source_rows, io.files)
    current_guard(inspection['value'], io, guard, frozen_links, full=True)
    link_observations_after = frozen_link_observations(frozen_links)
    require(same(link_observations_before, link_observations_after), 'complete frozen-link routes changed during audit')
    completed_after = completed_directory_readback(declared, io)
    require(same(completed_before, completed_after), 'completed directories changed during audit')
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
        startup39=controls39, retry_controls=retry_controls, attempt=copy.deepcopy(plan['attempt']),
        failed_predecessor=prior_failure, failed_saved_audit=copy.deepcopy(failed_audit),
        saved_audit_source=str(HERE), prior_failed_saved_audit=dict(FAILED_LINK_AUDIT),
        prior_failed_completed_directory_audit=dict(FAILED_COMPLETED_AUDIT),
        completed_evidence_directories=dict(declaration=declared, observed=completed_after, before_after_equal=True),
        frozen_links_controls=link_controls,
        frozen_links=link_observations_after, frozen_links_before_after_equal=True,
        startup_environment=copy.deepcopy(plan['startup_environment']),
        preparation=copy.deepcopy(expected['preparation']), preparation_launcher=copy.deepcopy(expected['preparation_launcher']),
        preparation_membership=preparation_proof,
        preparation_source_table=preparation_source_proof, preparation_invocation=invocation_proof,
        qualified_prerequisites=qualified, full_current_input_rehash=True,
        snapshots=snapshot_proof, phase_result=phase_proof, output_membership=output_proof,
        packet_membership=packet_proof, outer_membership=outer_proof,
        launcher_membership=launcher_proof, process_identities=history['identities'],
        unavailable_contemporaneous_cwd=history['unavailable_contemporaneous_cwd'],
        first_preflight_has_no_circular_audit=phase == 'preflight',
        compiler_calls=0, provider_probes=0, application_qualified=False,
        performance_measurement=False, exporter_qualified=False, std_mir_prepared=False)
