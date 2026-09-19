"""Pure readback of actual predecessor commands for the hash-driver stage.

The enclosing controller supplies readers that admit only frozen ordinary
files. Nothing here runs a process, infers an absent result, or changes a
predecessor. Status alone never establishes a completed command history.
"""
import hashlib
import math
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    require(type(raw) is bytes, 'raw predecessor bytes required')
    return hashlib.sha256(raw).hexdigest()


def finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def same_value(left, right):
    """JSON equality that never treats booleans, integers and floats as aliases."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(same_value(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(same_value(a, b) for a, b in zip(left, right, strict=True))
    return left == right


def command_history(terminal, declarations, *, evidence, read_json, read_bytes):
    """Reconcile successful-stage children, including declared error controls.

    read_json/read_bytes must enforce the enclosing freeze before returning.
    A compiler expected to reject bad source still has a finished child with
    its exact nonzero expected return code; a failed controller cannot pass.
    Fast metadata children may lack an lsof cwd observation. Such cases remain
    explicit in the return value and are never presented as observed cwd.
    """
    require(terminal['status'] == 'passed', 'successful predecessor required')
    return _command_history(terminal, declarations, evidence=evidence,
                            read_json=read_json, read_bytes=read_bytes)


def _command_history(terminal, declarations, *, evidence, read_json, read_bytes):
    """Raw checks shared only after the caller validates its owner contract."""
    evidence = Path(evidence)
    require(evidence.is_absolute() and '..' not in evidence.parts, 'absolute evidence root required')
    for name in ['pid', 'parent_pid']:
        require(type(terminal[name]) is int and terminal[name] > 0, 'invalid predecessor owner')
    require(finite(terminal['admitted_at']) and finite(terminal['finished_at'])
            and terminal['admitted_at'] <= terminal['finished_at'], 'invalid predecessor interval')
    refs = terminal['commands']
    require(type(refs) is list and len(refs) == len(declarations) > 0, 'incomplete predecessor history')
    previous = terminal['admitted_at']
    output, unavailable_cwd, identities = [], [], set()
    for index, (ref, wanted) in enumerate(zip(refs, declarations, strict=True)):
        directory = evidence/'commands'/f'{index:03}'
        receipt = directory/'receipt.json'
        require(ref['path'] == str(receipt) and digest(read_bytes(receipt)) == ref['sha256'],
                'predecessor child reference differs')
        child = read_json(receipt)
        expected = wanted.get('expected', [0])
        require(type(expected) is list and len(expected) == 1 and type(expected[0]) is int,
                'one exact child outcome required')
        require(child['status'] == 'finished' and type(child['returncode']) is int and child['returncode'] == expected[0]
                and child['expected'] == expected, 'child outcome differs from declared control')
        require(child['command'] == wanted['argv'] and child['environment'] == wanted['environment']
                and child['cwd'] == wanted['cwd'], 'actual predecessor invocation differs')
        require(type(child['pid']) is int and child['pid'] > 0 and child['pid'] == ref['pid']
                and child['supervisor_pid'] == terminal['pid']
                and child['parent_pid'] == terminal['parent_pid'], 'predecessor child ownership differs')
        if 'command' in ref:
            require(ref['command'] == wanted['argv'], 'child reference command differs')
        if 'role' in wanted:
            require(ref.get('role') == wanted['role'], 'child role differs')
        require(finite(child['started_at']) and finite(child['finished_at'])
                and previous <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                'predecessor children overlap or escape their owner interval')
        previous = child['finished_at']
        identity = child['identity']
        lines = identity['ps'].splitlines()
        fields = lines[0].split(None, 9) if len(lines) == 1 else []
        require(identity['ps_returncode'] == 0 and len(fields) == 10
                and fields[:3] == [str(child['pid']), str(terminal['pid']), str(child['pid'])]
                and fields[8] == '??' and fields[9] == ' '.join(wanted['argv']),
                'actual predecessor process identity differs')
        process_identity = (child['pid'], ' '.join(fields[3:8]))
        require(process_identity not in identities, 'predecessor process identity was reused')
        identities.add(process_identity)
        if identity['cwd_returncode'] == 0 and identity['cwd']:
            require(identity['cwd'].splitlines() == [f'p{child["pid"]}', 'fcwd', 'n'+wanted['cwd']],
                    'actual predecessor working directory differs')
        else:
            require(identity['cwd_returncode'] == 1 and not identity['cwd'], 'unrecognized cwd observation failure')
            unavailable_cwd.append(index)
        streams = []
        for name in ['stdout', 'stderr']:
            raw = read_bytes(directory/name)
            require(digest(raw) == child[name+'_sha256'], 'predecessor raw stream changed')
            streams.append(raw)
        output.append(dict(receipt=child, stdout=streams[0], stderr=streams[1]))
    return dict(rows=output, unavailable_contemporaneous_cwd_children=unavailable_cwd)


NATIVE_OWNER = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
NATIVE_SOURCE = NATIVE_OWNER/'experiments/hir-options-hash-native-controls-03'
NATIVE_EVIDENCE = NATIVE_OWNER/'.work/hir-options-hash-native-controls-03'
RECON_SOURCE = NATIVE_OWNER/'experiments/hir-options-hash-native-reconciliation-01'
RECON_EVIDENCE = NATIVE_OWNER/'.work/hir-options-hash-native-controls-reconciliation-01'
NATIVE_HASHES = dict(
    receipt='76fe70afd8eb6486b445e39366de2dd1ffd52ed9578e63203dc7cf74a679a272',
    inputs='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d',
    plan='37828597c866453a0beba3f22875cea63d03cf1d8a577f93b5987d1bb86bdf49',
    snapshot_plan='81fab53745a96fb9ff9694f9c03f66539c027594d6179fee093e37e0a3a68d0a',
    parser='5aea2b1b965ee9e95a67513120ca88ab4117c0488c28b320e70c7239aeed241c',
    audit='1058d64e64d75748a3da12115a8400a01daa5cd499b39b09c8d29520eaab4f24')
NATIVE_ERROR = "ValueError('wrong-B3 failure is not compiler metadata incompatibility')"
NATIVE_FAILURE_AUDIT = dict(path=str(NATIVE_OWNER/'.work/native-controls-failure-verification-03.json'),
                            sha256=NATIVE_HASHES['audit'])
NATIVE_BASE = dict(path=str(NATIVE_SOURCE/'inputs.json'), sha256=NATIVE_HASHES['inputs'])
PARSER_CONTROL_AUDIT = dict(path=str(NATIVE_OWNER/'.work/native-wrong-beta-controls-independent-verification-01.json'),
    sha256='b8d689dd8573ac4676ae4e43b0266d0af84fd10ac265854dfc00fa90a2f0d835')


def _reconciliation_records(plan, original_plan, terminal, qualification, result):
    """Pure record contract; byte/reference guards precede this in the reader.

    Kept separate so synthetic controls can exercise dishonest combinations
    without inventing actual receipts or rehashing the large base freeze.
    """
    additions = {'read_only_reconciliation', 'actual_workload_children', 'base_inputs',
                 'command_evidence', 'reconciliation', 'wrong_beta_providers',
                 'wrong_beta_lib', 'reconciliation_evidence_roots'}
    require(set(plan) == set(original_plan) | additions and not set(original_plan) & additions
            and all(same_value(plan[key], value) for key, value in original_plan.items()),
            'reconciliation changed or omitted an original native plan value')
    require(terminal['status'] == 'failed' and terminal['error'] == NATIVE_ERROR
            and terminal.get('native_roles_and_behavior_qualified', False) is False
            and 'result_sha256' not in terminal and 'wrong_B3' not in terminal,
            'original native failure was relabeled')
    require(type(terminal['commands']) is list and len(terminal['commands']) == 20
            and terminal['inputs_sha256'] == NATIVE_HASHES['inputs']
            and terminal['snapshot_plan_sha256'] == NATIVE_HASHES['snapshot_plan'],
            'complete original failed native history required')
    expected = dict(source=str(NATIVE_SOURCE), evidence=str(NATIVE_EVIDENCE),
        receipt_sha256=NATIVE_HASHES['receipt'], inputs_sha256=NATIVE_HASHES['inputs'],
        plan_sha256=NATIVE_HASHES['plan'], snapshot_plan_sha256=NATIVE_HASHES['snapshot_plan'],
        status='failed', error=NATIVE_ERROR, commands=terminal['commands'],
        failure_audit=NATIVE_FAILURE_AUDIT)
    require(plan['command_evidence'] == qualification['command_evidence']
            == result['command_evidence'] == expected, 'saved native command association differs')
    rec = plan['reconciliation']
    require(set(rec) == {'source', 'base_inputs', 'original_parser', 'parser', 'parser_controls', 'failure_audit'}
            and rec == qualification['reconciliation'] == result['reconciliation']
            and rec['source'] == str(RECON_SOURCE) and rec['base_inputs'] == plan['base_inputs'] == NATIVE_BASE
            and rec['original_parser'] == dict(path=str(NATIVE_SOURCE/'observations.py'), sha256=NATIVE_HASHES['parser'])
            and rec['parser']['path'] == str(RECON_SOURCE/'wrong_beta.py')
            and rec['failure_audit'] == NATIVE_FAILURE_AUDIT,
            'complete separate reconciliation provenance required')
    controls = rec['parser_controls']
    require(type(controls) is dict
            and set(controls) == {'source', 'evidence', 'receipt_sha256', 'result_sha256', 'controls', 'audit'}
            and controls['source'] == str(NATIVE_OWNER/'experiments/native-wrong-beta-controls-01')
            and controls['evidence'] == str(NATIVE_OWNER/'.work/native-wrong-beta-controls-01')
            and controls['audit'] == PARSER_CONTROL_AUDIT
            and type(controls['controls']) is int and controls['controls'] == 11,
            'complete corrected-parser qualification reference required')
    require(qualification['status'] == 'passed' and qualification.get('error') is None
            and qualification['commands'] == [] and qualification['native_roles_and_behavior_qualified'] is True
            and plan['read_only_reconciliation'] is qualification['read_only_reconciliation'] is True
            and type(plan['actual_workload_children']) is int and plan['actual_workload_children'] == 0,
            'only a completed read-only reconciliation can qualify saved commands')
    for name, count in [('actual_workload_children', 0), ('saved_actual_children', 20), ('historical_failed_children', 11)]:
        require(type(qualification[name]) is int and qualification[name] == count,
                'reconciliation workload accounting differs')
    for name in ['pid', 'parent_pid']:
        require(type(qualification[name]) is int and qualification[name] > 0, 'invalid reconciliation owner')
    require(all(finite(qualification[name]) for name in ['started_at', 'admitted_at', 'finished_at'])
            and terminal['finished_at'] <= qualification['started_at'] <= qualification['admitted_at']
            <= qualification['finished_at'], 'reconciliation interval does not follow the saved attempt')
    require(type(result['qualified_native_children']) is int and result['qualified_native_children'] == 20
            and type(result['total_actual_native_children']) is int and result['total_actual_native_children'] == 31
            and result['history'] == terminal['commands'][:18]
            and result['wrong_B3_commands'] == terminal['commands'][18:],
            'reconciliation omitted or replaced saved native commands')
    roots = plan['reconciliation_evidence_roots']
    require(type(roots) is list and all(type(root) is str and Path(root).is_absolute()
            and str(Path(root)) == root and '..' not in Path(root).parts for root in roots)
            and roots == sorted(set(original_plan['evidence_roots']) | {str(RECON_EVIDENCE)}),
            'reconciliation omitted an original or current evidence root')
    return rec


def reconciled_native_history(plan, terminal, result, *, evidence, qualification_terminal,
                              qualification_evidence, read_json, read_bytes):
    """Admit exactly the audited late native03 failure, never a generic failure.

    The enclosing frozen readers still revalidate the complete base/delta input
    closure and the independent successful reconciliation audit. No terminal is
    copied, patched, or presented as having succeeded under the old owner.
    """
    require(Path(evidence) == NATIVE_EVIDENCE and Path(qualification_evidence) == RECON_EVIDENCE,
            'exact command and reconciliation owners required')
    def reference(row):
        require(type(row) is dict and set(row) == {'path', 'sha256'}, 'exact proof reference required')
        path = Path(row['path'])
        require(path.is_absolute() and '..' not in path.parts and str(path) == row['path']
                and digest(read_bytes(path)) == row['sha256'], 'reconciliation proof bytes differ')
        return path
    for key, path in [('receipt', NATIVE_EVIDENCE/'receipt.json'), ('inputs', NATIVE_SOURCE/'inputs.json'),
                      ('plan', NATIVE_SOURCE/'plan.json'), ('snapshot_plan', NATIVE_SOURCE/'snapshot-plan.json')]:
        reference(dict(path=str(path), sha256=NATIVE_HASHES[key]))
    require(read_json(NATIVE_EVIDENCE/'receipt.json') == terminal
            and read_json(RECON_EVIDENCE/'receipt.json') == qualification_terminal
            and read_json(RECON_EVIDENCE/'native-controls.json') == result
            and read_json(RECON_SOURCE/'plan.json') == plan, 'supplied reconciliation records differ from saved bytes')
    rec = _reconciliation_records(plan, read_json(NATIVE_SOURCE/'plan.json'), terminal, qualification_terminal, result)
    freeze = read_json(RECON_SOURCE/'inputs.json')
    require(freeze['base_inputs'] == NATIVE_BASE and freeze['plan_sha256'] == digest(read_bytes(RECON_SOURCE/'plan.json'))
            == qualification_terminal['plan_sha256']
            and digest(read_bytes(RECON_SOURCE/'inputs.json')) == qualification_terminal['inputs_sha256']
            and digest(read_bytes(RECON_EVIDENCE/'native-controls.json')) == qualification_terminal['result_sha256'],
            'reconciliation delta/base freeze or result association differs')
    # A retained absence guard proves the old result has never been invented.
    require(str(NATIVE_EVIDENCE/'native-controls.json') in freeze['absent_paths'],
            'original failed result absence must remain a frozen guard')
    audit = read_json(reference(NATIVE_FAILURE_AUDIT))
    require(audit['status'] == 'verified-retained-failure' and audit['receipt_sha256'] == NATIVE_HASHES['receipt']
            and audit['inputs_sha256'] == NATIVE_HASHES['inputs'] and audit['plan_sha256'] == NATIVE_HASHES['plan']
            and audit['failure'] == NATIVE_ERROR and audit['children'] == 20
            and audit['historical_failed_children'] == 11 and audit['total_actual_native_children'] == 31
            and audit['native_roles_and_behavior_qualified'] is False
            and audit['full_current_input_hashes'] is True and audit['frozen_parser_rejection_reproduced'] is True,
            'exact independent retained-failure proof required')
    reference(rec['original_parser']); reference(rec['parser'])
    controls = rec['parser_controls']
    require(set(controls) == {'source', 'evidence', 'receipt_sha256', 'result_sha256', 'controls', 'audit'}
            and type(controls['controls']) is int and controls['controls'] > 0,
            'actual corrected-parser qualification required')
    control_work = Path(controls['evidence']); control_source = Path(controls['source'])
    require(control_work == NATIVE_OWNER/'.work/native-wrong-beta-controls-01'
            and control_source == NATIVE_OWNER/'experiments/native-wrong-beta-controls-01'
            and controls['controls'] == 11,
            'task-owned parser qualification routes required')
    control_receipt = read_json(reference(dict(path=str(control_work/'receipt.json'), sha256=controls['receipt_sha256'])))
    control_result = read_json(reference(dict(path=str(control_work/'result.json'), sha256=controls['result_sha256'])))
    control_audit = read_json(reference(controls['audit']))
    require(control_receipt['status'] == control_result['status'] == 'passed'
            and type(control_receipt['controls_passed']) is int and control_receipt['controls_passed'] == 11
            and type(control_result['tests_run']) is int and control_result['tests_run'] == 11
            and len(control_result['expected_names']) == len(set(control_result['expected_names'])) == 11
            and control_audit['status'] == 'verified' and control_audit['controls'] == controls['controls']
            and control_audit['receipt_sha256'] == controls['receipt_sha256']
            and control_audit['result_sha256'] == control_receipt['result_sha256'] == controls['result_sha256']
            and all(type(control_result[key]) is int and control_result[key] == 0 for key in
                    ['failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes',
                     'child_processes', 'compiler_calls']),
            'corrected-parser controls did not pass and receive an independent audit')
    control_freeze = read_json(control_source/'inputs.json')
    require(control_receipt['inputs_sha256'] == digest(read_bytes(control_source/'inputs.json'))
            and control_freeze['files'][rec['parser']['path']]['sha256'] == rec['parser']['sha256']
            and control_result['expected_names'] == control_freeze['expected_names'],
            'corrected parser was not the source qualified by those controls')
    return _command_history(terminal, plan['children'], evidence=evidence,
                            read_json=read_json, read_bytes=read_bytes)


def native_wrapper(plan, terminal, result, *, paths, read_json, read_bytes):
    """Bind the private direct-rustc source and both failed attempt histories."""
    original_path = paths['source']/'compiler/rustc/src/main.rs'
    original = read_bytes(original_path)
    line = b'#![expect(unused_crate_dependencies)]\n'
    original_sha = 'bfa21d3eced1a7ae4de80cb17e7f8840be640bfdfa96bff32fd6c63282d2c2ab'
    derived_sha = '2830149bab94db375ec164229320f060096bd5c1ba2576045148bfc090fdcd68'
    require(len(original) == 2128 and digest(original) == original_sha
            and original.count(line) == 1 and original.splitlines(keepends=True)[3] == line,
            'exact original Cargo wrapper required')
    require(paths['stock_source'] == Path(plan['namespace'])/'native-controls-03/stock-main.rs',
            'fresh private wrapper route required')
    derived = read_bytes(paths['stock_source'])
    require(derived == original.replace(line, b'', 1) and digest(derived) == derived_sha,
            'private wrapper changed more than the Cargo expectation')
    expected = dict(source=str(original_path), original_sha256=original_sha, original_size=len(original),
        destination=str(paths['stock_source']), derived_sha256=derived_sha, derived_size=len(derived),
        removed_line=4, removed_bytes=line.decode(), policy='remove-exact-cargo-unused-crate-expectation-v1')
    require(plan['stock_source_derivation'] == terminal['stock_source_derivation']
            == result['stock_source_derivation'] == expected, 'wrapper derivation association differs')
    require(result['stock_source'] == terminal['stock_source']
            and result['stock_source']['path'] == str(paths['stock_source'])
            and result['stock_source']['sha256'] == derived_sha
            and result['stock_source']['size'] == len(derived), 'actual retained wrapper differs')
    priors = result['prior_failed_attempts']
    owner = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
    histories = [
        ('01', 5, 'af25ceeda3cf32cf63d73b3fd2cee05726267166e0babd58587b884815256f3e',
         "ValueError('stock build emitted diagnostics')"),
        ('02', 6, 'c5f873179ed772de997771fd1c89f409876a79ca520d01ff5f8a288c2f6c879f',
         "ValueError('stock direct private edge is outside exact E2 closure')")]
    require(type(priors) is list and len(priors) == len(histories)
            and priors == plan['prior_failed_attempts'], 'both ordered failed histories required')
    for prior, (suffix, count, audit_sha, error) in zip(priors, histories, strict=True):
        old_work = owner/('.work/hir-options-hash-native-controls-' + suffix)
        old_audit = owner/('.work/native-controls-failure-verification-' + suffix + '.json')
        require(prior['evidence'] == str(old_work)
                and prior['source'] == str(owner/('experiments/hir-options-hash-native-controls-' + suffix))
                and prior['audit'] == dict(path=str(old_audit), sha256=audit_sha)
                and digest(read_bytes(old_audit)) == audit_sha, 'failed attempt audit association differs')
        audit = read_json(old_audit); old = read_json(old_work/'receipt.json')
        require(audit['status'] == prior['status'] == 'verified-retained-failure'
                and audit['children'] == prior['actual_children'] == count
                and prior['qualified_children'] == 0 and audit['native_roles_and_behavior_qualified'] is False
                and audit['fixture_never_created'] is prior['fixture_never_created'] is True
                and old['status'] == 'failed' and old['error'] == error
                and len(old['commands']) == count and digest(read_bytes(old_work/'receipt.json'))
                    == audit['receipt_sha256'] == prior['receipt_sha256'], 'failed native history was relabeled')
    require(result['qualified_native_children'] == 20 and result['total_actual_native_children'] == 31,
            'twenty new children plus eleven failed-history children required')
    return dict(derived_sha256=derived_sha, prior_failed_children=11, qualified_children=20, total_actual_children=31)


def native_controls(plan, terminal, result, *, evidence, qualification_terminal,
                    qualification_evidence, read_json, read_bytes, recipe,
                    observations, loader_trace, wrong_beta, beta_providers, verify_provider):
    """Independently repeat all native role/behavior observations from raw data.

    The caller additionally verifies the B3/compiler transitive freeze, current
    inventories, provider routes, and independent predecessor audit. This
    function does not replace those checks or establish application performance.
    """
    proof = reconciled_native_history(plan, terminal, result, evidence=evidence,
        qualification_terminal=qualification_terminal, qualification_evidence=qualification_evidence,
        read_json=read_json, read_bytes=read_bytes)
    require(result['status'] == 'native-roles-and-behavior-qualified'
            and qualification_terminal['native_roles_and_behavior_qualified'] is True,
            'native qualification did not complete')
    require(result['candidate_revision'] == terminal['candidate_revision'] == plan['candidate_revision']
            and result['source_identity'] == plan['source_identity'], 'native candidate identity differs')
    require(result['assembly'] == plan['assembly'] and result['compiler'] == plan['compiler']
            and result['runtime_closure'] == plan['runtime_closure']
            and result['ordered_driver_destinations'] == plan['ordered_driver_destinations'],
            'native compiler/provider association differs')
    require(result['source_restored'] is True and terminal['source_restored'] is True
            and all(result[name] is False for name in
                    ['hash_driver_qualified', 'run_make_qualified', 'application_qualified']),
            'native result incorrectly claims another qualification')
    declarations = recipe.desired_commands(plan)
    require(plan['children'] == declarations and len(declarations) == 20, 'native recipe differs')
    rows = proof['rows']
    require(result['history'] == terminal['commands'][:18]
            and result['wrong_B3_commands'] == terminal['commands'][18:], 'native history split differs')
    paths = recipe.paths(plan['namespace'])
    wrapper = native_wrapper(plan, terminal, result, paths=paths, read_json=read_json, read_bytes=read_bytes)
    for index, expected in enumerate([plan['build_version'], str(paths['build'])+'\n',
                                      plan['runtime_version'], str(paths['runtime'])+'\n']):
        require(rows[index]['stdout'].decode() == expected and not rows[index]['stderr'],
                'native compiler identity readback differs')
    require(not rows[4]['stderr'] and not rows[5]['stderr'], 'native build/static inspection emitted diagnostics')
    linker = observations.link_command(rows[4]['stdout'], clang=plan['clang'], output=paths['stock'],
                                       runtime_lib=paths['runtime']/'lib')
    require(linker == terminal['linker'], 'native linker readback differs')
    stock = read_bytes(paths['stock'])
    require(digest(stock) == result['stock']['sha256'] == terminal['stock']['sha256'], 'native stock binary changed')
    static = observations.stock_macho(stock, rows[5]['stdout'], stock=paths['stock'],
        driver=plan['runtime_driver']['path'], runtime_lib=paths['runtime']/'lib',
        qualified_private=plan['runtime_closure']['libraries'])
    require(static == result['static_loader'] == terminal['static_loader'], 'native static loader proof differs')
    require(rows[6]['stdout'].decode() == plan['runtime_version'], 'embedded compiler version differs')
    actual = loader_trace.parse(rows[6]['stderr'], pid=rows[6]['receipt']['pid'],
        allowed_private={str(paths['stock']), *[row['resolved'] for row in plan['runtime_closure']['libraries']]})
    require(actual == result['actual_loader'] == terminal['actual_loader'], 'native actual loader proof differs')
    hits = [observations.hit(rows[index]['stderr'], cold=index == 9) for index in [9, 11, 15, 16]]
    require(hits == result['hits'] == terminal['hits'], 'native cold/warm/error/restored HIR readback differs')
    def streams(index):
        return rows[index]['stdout'], rows[index]['stderr']
    error = observations.error_pair(streams(13), streams(14), 'E0308')
    require(beta_providers == plan['wrong_beta_providers']
            and plan['wrong_beta_lib'] == str(paths['beta']/'lib/rustlib/aarch64-apple-darwin/lib'),
            'corrected parser provider selection differs')
    wrong = wrong_beta.wrong_pair(streams(18), streams(19), observed=observations,
        beta_lib=plan['wrong_beta_lib'], beta_std_paths=plan['beta_std_paths'], providers=beta_providers,
        beta_version=plan['build_version'].splitlines()[0], native_version=plan['runtime_version'].splitlines()[0],
        verify_provider=verify_provider)
    require(error == result['uncalled_error'] == terminal['uncalled_error']
            and wrong == result['wrong_B3'], 'native raw error parity differs')
    expected_compilations = [dict(index=i, source_sha256=digest(recipe.ERROR if i in [13, 14, 15] else recipe.ORIGINAL))
                             for i in [7, 9, 11, 13, 14, 15, 16]]
    require(terminal['fixture_compilations'] == expected_compilations, 'native source edit history differs')
    executions = result['native_executions']
    require(executions == terminal['native_executions'] and [r['index'] for r in executions] == [8, 10, 12, 17],
            'native behavior history differs')
    for row in executions:
        require(row['retained'] == str(Path(evidence)/'artifacts'/(str(row['index'])+'.bin')),
                'retained native binary route differs')
        require(digest(read_bytes(Path(row['retained']))) == row['artifact']['sha256'],
                'executed native binary bytes changed')
        require(streams(row['index']) == (b'42\n', b''), 'native execution behavior differs')
    require(read_bytes(paths['fixture']) == recipe.ORIGINAL
            and read_bytes(paths['wrong_source']) == recipe.WRONG, 'native source restoration differs')
    return dict(status='native-predecessor-raw-readback-passed', commands=20, wrapper=wrapper,
                original_command_owner_status='failed', read_only_reconciliation=True,
                actual_reconciliation_workload_children=0,
                unavailable_contemporaneous_cwd_children=proof['unavailable_contemporaneous_cwd_children'],
                application_qualified=False, performance_measurement=False)
