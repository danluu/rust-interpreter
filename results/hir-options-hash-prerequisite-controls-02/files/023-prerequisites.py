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


def command_history(terminal, declarations, *, evidence, read_json, read_bytes):
    """Reconcile successful-stage children, including declared error controls.

    read_json/read_bytes must enforce the enclosing freeze before returning.
    A compiler expected to reject bad source still has a finished child with
    its exact nonzero expected return code; a failed controller cannot pass.
    Fast metadata children may lack an lsof cwd observation. Such cases remain
    explicit in the return value and are never presented as observed cwd.
    """
    evidence = Path(evidence)
    require(evidence.is_absolute() and '..' not in evidence.parts, 'absolute evidence root required')
    require(terminal['status'] == 'passed', 'successful predecessor required')
    for name in ['pid', 'parent_pid']:
        require(type(terminal[name]) is int and terminal[name] > 0, 'invalid predecessor owner')
    require(finite(terminal['admitted_at']) and finite(terminal['finished_at'])
            and terminal['admitted_at'] <= terminal['finished_at'], 'invalid predecessor interval')
    refs = terminal['commands']
    require(type(refs) is list and len(refs) == len(declarations) > 0, 'incomplete predecessor history')
    previous = terminal['admitted_at']
    output, unavailable_cwd = [], []
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


def native_wrapper(plan, terminal, result, *, paths, read_json, read_bytes):
    """Bind the private direct-rustc source and keep the failed attempt failed."""
    original_path = paths['source']/'compiler/rustc/src/main.rs'
    original = read_bytes(original_path)
    line = b'#![expect(unused_crate_dependencies)]\n'
    original_sha = 'bfa21d3eced1a7ae4de80cb17e7f8840be640bfdfa96bff32fd6c63282d2c2ab'
    derived_sha = '2830149bab94db375ec164229320f060096bd5c1ba2576045148bfc090fdcd68'
    require(len(original) == 2128 and digest(original) == original_sha
            and original.count(line) == 1 and original.splitlines(keepends=True)[3] == line,
            'exact original Cargo wrapper required')
    require(paths['stock_source'] == Path(plan['namespace'])/'native-controls-02/stock-main.rs',
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
    prior = result['prior_failed_attempt']
    owner = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
    old_work = owner/'.work/hir-options-hash-native-controls-01'
    old_audit = owner/'.work/native-controls-failure-verification-01.json'
    audit_sha = 'af25ceeda3cf32cf63d73b3fd2cee05726267166e0babd58587b884815256f3e'
    require(prior == plan['prior_failed_attempt'] and prior['evidence'] == str(old_work)
            and prior['source'] == str(owner/'experiments/hir-options-hash-native-controls-01')
            and prior['audit'] == dict(path=str(old_audit), sha256=audit_sha)
            and digest(read_bytes(old_audit)) == audit_sha, 'failed attempt audit association differs')
    audit = read_json(old_audit); old = read_json(old_work/'receipt.json')
    require(audit['status'] == 'verified-retained-failure' and audit['children'] == prior['actual_children'] == 5
            and prior['qualified_children'] == 0 and audit['native_roles_and_behavior_qualified'] is False
            and audit['fixture_never_created'] is prior['fixture_never_created'] is True
            and old['status'] == 'failed' and old['error'] == "ValueError('stock build emitted diagnostics')"
            and len(old['commands']) == 5 and digest(read_bytes(old_work/'receipt.json'))
                == audit['receipt_sha256'] == prior['receipt_sha256'], 'failed five-row history was relabeled')
    require(result['qualified_native_children'] == 20 and result['total_actual_native_children'] == 25,
            'twenty new children plus five failed-history children required')
    return dict(derived_sha256=derived_sha, prior_failed_children=5, qualified_children=20, total_actual_children=25)


def native_controls(plan, terminal, result, *, evidence, read_json, read_bytes,
                    recipe, observations, loader_trace):
    """Independently repeat all native role/behavior observations from raw data.

    The caller additionally verifies the B3/compiler transitive freeze, current
    inventories, provider routes, and independent predecessor audit. This
    function does not replace those checks or establish application performance.
    """
    require(result['status'] == 'native-roles-and-behavior-qualified'
            and terminal['native_roles_and_behavior_qualified'] is True,
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
    require(digest(read_bytes(Path(evidence)/'native-controls.json')) == terminal['result_sha256'],
            'native result bytes differ')
    declarations = recipe.desired_commands(plan)
    require(plan['children'] == declarations and len(declarations) == 20, 'native recipe differs')
    proof = command_history(terminal, declarations, evidence=evidence,
                            read_json=read_json, read_bytes=read_bytes)
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
        qualified_private={row['logical']: row['resolved'] for row in plan['runtime_closure']['libraries']})
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
    wrong = observations.wrong_pair(streams(18), streams(19), plan['beta_std_paths'])
    require(error == result['uncalled_error'] == terminal['uncalled_error']
            and wrong == result['wrong_B3'] == terminal['wrong_B3'], 'native raw error parity differs')
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
                unavailable_contemporaneous_cwd_children=proof['unavailable_contemporaneous_cwd_children'],
                application_qualified=False, performance_measurement=False)
