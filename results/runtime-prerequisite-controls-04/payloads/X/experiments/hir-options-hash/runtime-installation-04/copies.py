"""Explicit closed proof-copy partition; no filesystem identities are virtualized.

The enclosing reader supplies strict current-file callbacks. Bootstrap replays
only the previously qualified beta/native/failed-hash catalog, before the
successful hash Reader.check and its later mandatory completed-owner extension.
No function here grants retirement, runtime admission, or missing-file access.
"""
import copy
import json
from pathlib import Path

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
SOURCE = ROOT/'experiments/retained-proof-copy-references-01'
CONTROLS = ROOT/'experiments/retained-proof-copy-controls-01'
CONTROL_WORK = ROOT/'.work/retained-proof-copy-controls-01'
CONTROL_AUDIT = ROOT/'.work/retained-proof-copy-controls-independent-verification-01.json'
CONTROL_AUDIT_SHA256 = 'c803f6e6e663c3fc8a081829e3c07deb9098692206a91269c36b2fe6fc08290a'
PROPOSAL = X/'.work/runtime04-retained-copy-retirement-proposal-01.json'
PROPOSAL_SHA256 = 'e0599d87ab842b9e18932fddb54bb63aaf850cd2366279f67507e875731b3481'
COPY_ROOT = O/'.work/hir-options-hash-run-make-01/retained'
ORIGINAL_INPUTS_SHA256 = 'c06e016829f0c98e579aace635ded04858ac8890ebe43bb6014d1f4df52aa010'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def same(left, right):
    return encoded(left) == encoded(right)


def selection(original, *, read_json, sha):
    """Only an explicit reviewed proposal can nominate historical copy rows."""
    require(sha(PROPOSAL) == PROPOSAL_SHA256, 'exact reviewed copy selection required')
    proposal = read_json(PROPOSAL)
    require(proposal['status'] == 'source-only-prospective-retirement-not-prepared'
            and proposal['target_root'] == str(COPY_ROOT)
            and type(proposal['selection_count']) is int and proposal['selection_count'] == 21
            and proposal['selected'] == sorted(set(proposal['selected'])), 'copy proposal scope differs')
    rows = {row['path']: row for row in proposal['recovery']}
    names = sorted(str(COPY_ROOT/name) for name in proposal['selected'])
    require(len(rows) == len(names) == 21 and set(rows) == set(names), 'complete 21-copy recovery map required')
    for name in names:
        require(Path(name).parent == COPY_ROOT and name in original['files']
                and same(rows[name]['original_record'], original['files'][name]), 'original historical copy row differs')
    require(not set(names) & set(original['snapshot_inputs']), 'selected hash snapshot input cannot be historical')
    return names


def retained_owner(stage, plan, original, *, read_json, sha):
    """Authenticate the closed owner's full 61-row retention mapping.

    The ordinary full Stage.prerequisites check is still mandatory later.
    This bootstrap never substitutes an archive check for current provider work.
    """
    work, source = stage.RECIPE_WORK, stage.RECIPE_SOURCE
    receipt = read_json(work/'receipt.json'); result = read_json(work/'result.json')
    reference = plan['independent_audits']['run_make']; audit = read_json(reference['path'])
    retention = read_json(work/'retained-inputs.json')
    require(sha(reference['path']) == reference['sha256'] and audit['status'] == 'verified'
            and audit['receipt_sha256'] == sha(work/'receipt.json')
            and receipt['status'] == result['status'] == 'passed'
            and receipt['result_sha256'] == sha(work/'result.json')
            and result['retained_inputs_sha256'] == sha(work/'retained-inputs.json')
            and receipt['native_recipe_qualified'] is result['native_recipe_qualified'] is True,
            'actual completed run-make retention owner required')
    for item in [receipt, result]:
        require(all(type(item[key]) is int and item[key] == value for key, value in
                    dict(recipe_compilations=1, recipe_executions=1, nested_commands=230).items())
                and all(item[key] is False for key in
                        ['hash_driver_qualified', 'application_qualified', 'performance_measurement']),
                'original recipe scope differs')
    recipe_plan = read_json(source/'plan.json')
    require(result['plan_sha256'] == sha(source/'plan.json')
            and result['inputs_sha256'] == sha(source/'inputs.json')
            and same(result['actual_commands'], receipt['commands'])
            and same(result['source_identity'], plan['source_identity']), 'closed retention source/commands differ')
    expected = {name: dict(sha256=row['sha256'], bytes=row['stamp'][3])
                for name, row in recipe_plan['retained_selection'].items()}
    for name in [str(source/'plan.json'), str(source/'inputs.json')]:
        row = original['files'][name]
        require(name not in expected, 'retained own packet appears twice')
        expected[name] = dict(sha256=row['sha256'], bytes=row['size'])
    rows = retention['files']
    require(len(expected) == len(rows) == 61
            and same({row['source']: dict(sha256=row['sha256'], bytes=row['bytes']) for row in rows}, expected)
            and len({row['retained'] for row in rows}) == 61
            and retention['status'] == 'retained', 'complete original 61-entry retained selection differs')
    for index, name in enumerate(sorted(expected)):
        row = rows[index]
        require(row['source'] == name and row['retained'] == str(COPY_ROOT/(f'{index:04d}-'+Path(name).name)),
                'original retained-copy alias/order differs')
    owner = dict(source=str(source), evidence=str(work),
        receipt=dict(path=str(work/'receipt.json'), sha256=sha(work/'receipt.json')),
        audit=copy.deepcopy(reference), retention=dict(path=str(work/'retained-inputs.json'), sha256=sha(work/'retained-inputs.json')))
    return owner, retention


def bootstrap(stage, modules, original, plan, current_files, evidence_roots, helper, snapshots, *,
              helper_qualification, read_json, read_bytes, sha, file_record, directory_record, check_absent, guard,
              saved=None):
    """Rebuild the qualified prior catalog before any successful-owner callback.

    All IO callbacks remain strict physical reads. The fixed validation context
    is the original complete table minus the explicit 21 copies. New runtime
    source/packet files receive independent normal physical guards.
    """
    require(sha(stage.HERE/'inputs.json') == ORIGINAL_INPUTS_SHA256,
            'exact original completed hash input table required')
    require(type(helper_qualification['controls']) is int and helper_qualification['controls'] == 40
            and helper_qualification['audit'] == dict(path=str(CONTROL_AUDIT), sha256=CONTROL_AUDIT_SHA256)
            and sha(CONTROL_AUDIT) == CONTROL_AUDIT_SHA256,
            'actual qualified reference helper required before partition')
    approved = selection(original, read_json=read_json, sha=sha)
    historical = set(approved)
    require(historical.isdisjoint(current_files), 'copy cannot be represented as current and historical')
    def physical(callback):
        def checked(path, *args, **kwargs):
            require(str(path) not in historical, 'no physical read API for historical copy')
            return callback(path, *args, **kwargs)
        return checked
    read_json, read_bytes, sha = map(physical, [read_json, read_bytes, sha])
    context = {name: current_files[name] for name in original['files'] if name not in historical}
    require(len(original['files']) == 109343 and len(context) == 109322
            and all(same(row, original['files'][name]) for name, row in context.items()),
            'fixed original current context changed')
    def physical_record(path):
        require(str(path) not in historical, 'no physical file API for historical copy')
        return file_record(path)
    catalog = stage.continued_catalog(modules, dict(files=context, absent_paths=original['absent_paths']),
        modules['comp'], plan['independent_audits'], evidence_roots, snapshots,
        read_json=read_json, read_bytes=read_bytes, sha=sha, file_record=physical_record,
        directory_record=directory_record, check_absent=check_absent, guard=guard)
    require(same(catalog, plan['snapshot_reuse']) and len(catalog['records']) == 464,
            'complete qualified prior witness catalog differs')
    require(all(row['path'] in context for row in catalog['records']), 'witness must remain an original current input')
    owner, retention = retained_owner(stage, plan, original, read_json=read_json, sha=sha)
    base = read_json(stage.FILE_TABLE_BASE['path'])
    metadata = read_json(X/'experiments/hir-options-hash/compiler-metadata-03/inputs.json')
    live = set(base['files']) | set(metadata['files']) | set(original['snapshot_inputs'])
    live.update(row['source'] for row in retention['files'])
    for ancestor in catalog['predecessors']:
        manifest = ancestor['manifest']; require(sha(manifest['path']) == manifest['sha256'], 'historical manifest changed')
        live.update(read_json(manifest['path'])['files'])
    # Every required live path is still part of the fixed original context;
    # owner-input table files selected by old snapshots are included as well.
    require(historical.isdisjoint(live) and live <= set(context),
            'live selected/base/metadata/source input cannot be historical or omitted')
    def owner_check(given, rows):
        now_owner, now_rows = retained_owner(stage, plan, original, read_json=read_json, sha=sha)
        require(same(given, owner) and same(now_owner, owner) and same(rows, retention)
                and same(now_rows, retention), 'closed retention callback changed')
        return True
    def catalog_check(given):
        require(same(given, catalog), 'bootstrap catalog callback changed')
        return True
    arguments = dict(retention=retention, historical_files=original['files'], current_files=context,
        qualified_catalog=catalog, approved_copies=approved, required_live=sorted(live), copy_root=str(COPY_ROOT),
        owner=owner, validate_owner=owner_check, validate_catalog=catalog_check)
    proof = helper.build(**arguments)
    if saved is not None:
        require(same(saved, proof), 'saved historical-copy reference differs')
    parts = helper.partition(proof, **arguments)
    require(same(parts['current_files'], context)
            and set(parts['historical_files']) == historical, 'complete physical/historical partition differs')
    return dict(references=proof, historical_files=parts['historical_files'],
        current_context_files=len(context), prior_catalog=catalog,
        bootstrap_policy='continued-catalog-before-reader', runtime_admitted=False, retirement_authorized=False)
