"""Read-only native03 evidence replay for a separately admitted reconciliation.

Requires the exact failed terminal and finished outer supervisor. No result or native qualification is inferred. Reads actual retained
streams, complete frozen sources/providers and compressed snapshots. No command,
controller, compiler, provider probe or signal is invoked. Pure observation
modules are loaded only from already rehashed source bytes.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from types import ModuleType

A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HERE = A/'experiments/hir-options-hash-native-controls-03'
WORK = A/'.work/hir-options-hash-native-controls-03'
OUTER = A/'.work/experiments/hir-options-hash-native-controls-supervisor-03'
LAUNCHER = A/'.work/native-controls-launch-execution-03'
OUT = A/'.work/native-controls-failure-verification-03.json'
BETA_SOURCE = A/'experiments/hir-options-hash-beta-composition-08'
BETA_WORK = A/'.work/hir-options-hash-beta-composition-08'
N = X/'.work/hir-options-hash-compiler-01'
S = N/'source'
EXPECTED_LAUNCH = '4bbbdc02a5fcd623f866c074b69902f49ad3e7cf5d5a48e0d2b9c661f2cf486e'
EXPECTED_INPUTS = '8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d'
EXPECTED_PLAN = '37828597c866453a0beba3f22875cea63d03cf1d8a577f93b5987d1bb86bdf49'
EXPECTED_PROJECTION = '81fab53745a96fb9ff9694f9c03f66539c027594d6179fee093e37e0a3a68d0a'
EXPECTED_DISPATCHER = '03525570cec92cd9ee3e057fd942405c6482da96fbbf263dae5f6fa47d60850f'
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
checked = {}
_capacity_guard = None


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def unique(pairs):
    value = {}
    for name, row in pairs:
        require(name not in value, 'duplicate JSON key')
        value[name] = row
    return value


def read(path):
    path = Path(path)
    require(path.stat().st_size <= 64*2**20, 'bounded JSON input required')
    return json.loads(path.read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()


def identity(path):
    info = Path(path).lstat()
    return {key:getattr(info, 'st_'+key) for key in FIELDS}


def stamp(path):
    s = identity(path)
    return [s[k] for k in ('dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink')]


def sha(path):
    require(callable(_capacity_guard), 'explicit reconciliation resource guard required')
    _capacity_guard()
    path = Path(path); before = identity(path)
    require(path.resolve(strict=True) == path and stat.S_ISREG(before['mode']), 'ordinary input required: '+str(path))
    if str(path) in checked and checked[str(path)]['identity'] == before:
        return checked[str(path)]['sha256']
    require(before['size'] <= 2*2**30, 'finite ordinary file bound')
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        require({k:getattr(os.fstat(stream.fileno()), 'st_'+k) for k in FIELDS} == before, 'open identity differs')
        hasher = hashlib.sha256()
        while chunk := stream.read(2**20):
            _capacity_guard(); hasher.update(chunk)
        value = hasher.hexdigest()
        require({k:getattr(os.fstat(stream.fileno()), 'st_'+k) for k in FIELDS} == before, 'read identity changed')
    require(identity(path) == before, 'input changed while hashed')
    checked[str(path)] = dict(identity=before, sha256=value)
    return value


def frozen(path, freeze):
    path = Path(path); row = freeze['files'][str(path)]
    require(identity(path) == row['identity'] and sha(path) == row['sha256']
            and path.stat().st_size == row['size'], 'frozen input changed: '+str(path))
    return path


def names(root):
    root = Path(root); require(root.resolve(strict=True) == root and root.is_dir(), 'ordinary tree root required')
    found = {}
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs+files:
            path = Path(parent)/name; info = path.lstat()
            require(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode), 'special tree entry')
            found[str(path.relative_to(root))] = path
            require(len(found) <= 150000, 'bounded inventory required')
    return found


def verify_snapshots(freeze, receipt, projection_plan):
    projection = projection_plan['projection']; manifest = read(WORK/'source-snapshots.json')
    require(sha(WORK/'source-snapshots.json') == receipt['source_snapshots_sha256']
            and sha(WORK/'snapshot-plan.json') == receipt['snapshot_plan_sha256'] == sha(HERE/'snapshot-plan.json'), 'snapshot manifest/projection binding differs')
    require(manifest['policy'] == projection['policy'] == 'bounded-gzip-proof-snapshots-v1'
            and manifest['projection_sha256'] == hashlib.sha256(encoded(projection)).hexdigest()
            and manifest['blobs'] == projection['blobs']
            and manifest['full_logical_readback'] is True and manifest['full_gzip_eof'] is True, 'snapshot policy/projection differs')
    expected_names = set(freeze['snapshot_inputs']) | {str(HERE/'inputs.json')}
    require(set(projection['files']) == set(manifest['files']) == expected_names, 'snapshot logical member set differs')
    root = WORK/'source-snapshots'
    require(set(p.name for p in root.iterdir()) == {row['filename'] for row in projection['blobs'].values()}, 'snapshot physical membership differs')
    compressed_total = 0
    for digest, row in projection['blobs'].items():
        require(row['filename'] == digest+'.gz' and row['logical_sha256'] == digest, 'snapshot blob route differs')
        path = root/row['filename']; before = identity(path)
        require(before['nlink'] == 1 and before['size'] == row['compressed_bytes'] and sha(path) == row['sha256'], 'snapshot compressed bytes differ')
        total = 0; h = hashlib.sha256()
        with gzip.open(path, 'rb') as stream:
            while chunk := stream.read(min(2**20, row['logical_bytes']-total+1)):
                _capacity_guard()
                total += len(chunk); require(total <= row['logical_bytes'], 'snapshot expansion exceeded exact bound'); h.update(chunk)
        require(total == row['logical_bytes'] and h.hexdigest() == digest and identity(path) == before, 'full snapshot logical/gzipEOF readback differs')
        compressed_total += before['size']
    for name, row in projection['files'].items():
        require(sha(name) == row['sha256'] and identity(name) == row['identity'] and Path(name).stat().st_size == row['size'], 'snapshot original changed')
        require(manifest['files'][name] == dict(path=str(root/(row['sha256']+'.gz')), sha256=row['sha256'], size=row['size'], encoding='gzip'), 'logical snapshot route differs')
    require(compressed_total == projection['compressed_bytes'] == manifest['compressed_bytes'], 'snapshot compressed total differs')
    return dict(logical_files=len(expected_names), physical_blobs=len(projection['blobs']), compressed_bytes=compressed_total,
                full_logical_hashes=True, full_gzip_eof_crc=True, exact_projection=True)


def pure_module(name, path, freeze, dependencies=None):
    """Execute only the admitted parser/recipe source, avoiding stale pyc bytes."""
    path = frozen(path, freeze)
    require(path.stat().st_size <= 2*2**20, 'bounded pure source required')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == freeze['files'][str(path)]['sha256'], 'pure source changed')
    module = ModuleType(name); module.__file__ = str(path); module.__package__ = None
    missing = object(); replacements = dict(dependencies or {}, **{name: module})
    old = {key:sys.modules.get(key, missing) for key in replacements}; old_path = list(sys.path)
    try:
        sys.modules.update(replacements)
        exec(compile(raw, str(path), 'exec'), module.__dict__)
    finally:
        sys.path[:] = old_path
        for key, value in old.items():
            if value is missing: sys.modules.pop(key, None)
            else: sys.modules[key] = value
    return module


def exact_file(row):
    path = Path(row['path'])
    require(identity(path) == row['identity'] and path.stat().st_size == row['size']
            and sha(path) == row['sha256'], 'actual artifact identity or bytes differ')
    return path


def b3_prerequisite(plan, freeze):
    reference = plan['assembly']
    require(reference['source'] == str(BETA_SOURCE) and reference['evidence'] == str(BETA_WORK), 'wrong actual B308 route')
    terminal = read(frozen(BETA_WORK/'receipt.json', freeze))
    audit_ref = reference['audit']; audit = read(frozen(audit_ref['path'], freeze))
    require(terminal['status'] == 'passed' and terminal['assembly_and_auxiliary_strip_qualified'] is True
            and len(terminal['commands']) == 19 and sha(BETA_WORK/'receipt.json') == reference['receipt_sha256'],
            'successful actual B3 prerequisite required')
    require(audit['status'] == 'verified' and audit['receipt_sha256'] == reference['receipt_sha256']
            and sha(audit_ref['path']) == audit_ref['sha256'], 'actual independent B3 audit differs')
    beta_freeze = read(frozen(BETA_SOURCE/'inputs.json', freeze))
    beta_plan = read(frozen(BETA_SOURCE/'plan.json', freeze))
    require(sha(BETA_SOURCE/'inputs.json') == reference['inputs_sha256'] == terminal['inputs_sha256']
            and sha(BETA_SOURCE/'plan.json') == beta_freeze['plan_sha256'], 'B3 plan/freeze differs')
    require(all(freeze['files'].get(name) == row for name, row in beta_freeze['files'].items())
            and all(freeze['links'].get(name) == row for name, row in beta_freeze['links'].items())
            and set(beta_freeze['absent_paths']) <= set(freeze['absent_paths']), 'complete B3 closure omitted')
    require(sha(frozen(BETA_SOURCE/'snapshot-plan.json', freeze))
            == sha(frozen(BETA_WORK/'snapshot-plan.json', freeze)) == terminal['snapshot_plan_sha256']
            and sha(frozen(BETA_WORK/'source-snapshots.json', freeze)) == terminal['source_snapshots_sha256'],
            'qualified B3 compressed proof binding differs')
    previous = terminal['admitted_at']
    for index, (ref, wanted) in enumerate(zip(terminal['commands'], beta_plan['children'], strict=True)):
        path = BETA_WORK/'commands'/f'{index:03}'/'receipt.json'
        child = read(frozen(path, freeze))
        require(ref['path'] == str(path) and sha(path) == ref['sha256'] and ref['pid'] == child['pid']
                and child['status'] == 'finished' and child['returncode'] == 0 and child['expected'] == [0]
                and child['command'] == ref['command'] == wanted['argv']
                and child['environment'] == wanted['environment'] and child['cwd'] == wanted['cwd'] == str(S)
                and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                and previous <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                'B3 actual child association differs')
        previous = child['finished_at']
        for stream in ['stdout', 'stderr']:
            require(sha(frozen(path.parent/stream, freeze)) == child[stream+'_sha256'], 'B3 retained raw differs')
    inventory = read(frozen(BETA_WORK/'assembly/output-inventory.json', freeze))
    require(sha(BETA_WORK/'assembly/output-inventory.json') == terminal['assembly']['output_inventory_sha256'], 'B3 inventory hash differs')
    current = {name:path for name, path in names(N/'beta-sysroot').items() if not path.is_dir() or path.is_symlink()}
    require(set(current) == set(inventory) and len(inventory) == 335, 'complete B3 payload membership differs')
    for name, row in inventory.items():
        path = current[name]
        require(not path.is_symlink() and identity(path) == row['identity'] and sha(path) == row['sha256']
                and path.stat().st_size == row['size'] and stat.S_IMODE(path.stat().st_mode) == row['mode'], 'B3 payload changed')
    require(plan['ordered_driver_destinations'] == terminal['producer_proof']['ordered_driver_destinations']
            and plan['compiler'] == beta_plan['actual_build']
            and sha(frozen(BETA_WORK/'strip-proof.json', freeze)) == terminal['strip_proof_sha256'], 'B3 role/provenance/strip proof differs')
    compiled = read(frozen(Path(plan['compiler']['evidence'])/'compiled.json', freeze))
    compiler_audit = read(frozen(plan['compiler']['audit']['path'], freeze))
    require(compiled['source_identity'] == plan['source_identity']
            and compiled['candidate_revision'] == plan['candidate_revision']
            and compiler_audit['status'] == 'verified'
            and sha(plan['compiler']['audit']['path']) == plan['compiler']['audit']['sha256']
            and compiler_audit['compiled_sha256'] == sha(Path(plan['compiler']['evidence'])/'compiled.json'),
            'actual compiler prerequisite differs')
    require([compiler_audit[key] for key in ['children','saved_children','saved_actual_children',
                'combined_children','combined_actual_children']] == [3,22,23,25,26], 'compiler failure/success scope differs')
    return dict(receipt_sha256=sha(BETA_WORK/'receipt.json'), independent_audit=audit_ref,
                current_B3_files=len(inventory), actual_B3_children=19, compiler_logical_children=25,
                compiler_actual_children=26)



def successor_proof(plan, freeze, receipt, paths):
    control_module = pure_module('_native03_audit_stock_controls', HERE/'stock_controls.py', freeze)
    controls = control_module.validate(lambda path: frozen(path, freeze), freeze['files'])
    require(controls == plan['stock_source_controls'] and controls['controls'] == 4,
            'exact actual private-source derivation controls differ')
    loader_controls = loader_control_proof(plan, freeze)
    prior_module = pure_module('_native03_audit_previous_attempt', HERE/'previous_attempt.py', freeze)
    priors = prior_module.validate(lambda path: frozen(path, freeze), freeze['files'])
    require(priors == plan['prior_failed_attempts']
            and type(priors) is list and len(priors) == 2
            and [row['actual_children'] for row in priors] == [5,6]
            and all(row['qualified_children'] == 0 and row['status'] == 'verified-retained-failure' for row in priors),
            'ordered old failed eleven children were changed or relabeled')
    historical_missing_cwd = []; old_membership = {}
    for index, prior in enumerate(priors):
        old_root = N/('native-controls' if index == 0 else 'native-controls-02')
        members = {'smoke-rustc'} if index == 0 else {'smoke-rustc','stock-main.rs'}
        require(set(path.name for path in old_root.iterdir()) == members
                and exact_file(prior['unqualified_stock']) == old_root/'smoke-rustc'
                and prior['unqualified_stock']['qualified'] is False,
                'old failed root/stock changed')
        old_audit = read(frozen(prior['audit']['path'], freeze))
        require(old_audit['status'] == 'verified-retained-failure' and old_audit['children'] == [5,6][index],
                'old actual failure audit association differs')
        historical_missing_cwd.append(dict(evidence=prior['evidence'], observations=old_audit['unavailable_contemporaneous_cwd']))
        old_membership[str(old_root)] = sorted(members)
    source = frozen(S/'compiler/rustc/src/main.rs', freeze)
    derive = pure_module('_native03_audit_stock_source', HERE/'stock_source.py', freeze)
    derived, proof = derive.derive(source.read_bytes(), source, paths['stock_source'])
    require(proof == plan['stock_source_derivation'] == receipt['stock_source_derivation'] and proof['removed_line'] == 4
            and proof['original_sha256'] == 'bfa21d3eced1a7ae4de80cb17e7f8840be640bfdfa96bff32fd6c63282d2c2ab'
            and proof['derived_sha256'] == '2830149bab94db375ec164229320f060096bd5c1ba2576045148bfc090fdcd68',
            'exact remove-only Cargo expectation derivation differs')
    source_path = exact_file(receipt['stock_source'])
    require(source_path == paths['stock_source']
            and source_path.read_bytes() == derived and identity(source_path)['nlink'] == 1
            and (identity(source_path)['dev'],identity(source_path)['ino']) != (identity(source)['dev'],identity(source)['ino']),
            'independent private stock source changed')
    return dict(prior_failed_attempts=priors, stock_source_controls=controls, loader_route_controls=loader_controls,
                historical_failed_children=11, qualified_children=0, total_actual_children=31,
                exact_old_root_membership=old_membership, stock_source_derivation=proof,
                stock_source=receipt['stock_source'], historical_missing_cwd=historical_missing_cwd)


def loader_control_proof(plan, freeze):
    module = pure_module('_native03_audit_loader_controls', HERE/'loader_controls.py', freeze)
    proof = module.validate(lambda path: frozen(path, freeze), freeze['files'])
    require(proof == plan['loader_route_controls']
            and proof['controls'] == 9
            and proof['audit'] == dict(path=str(A/'.work/native-loader-route-controls-independent-verification-01.json'),
                sha256='2aa407e52e482c97949d0ff533a9c27024c895c84ce29a3b0ae522ac3e9d761d'),
            'exact actual nine loader-route controls differ')
    return proof



def qualification_membership(paths):
    root = paths['root']
    require(root == N/'native-controls-03', 'fresh qualification root differs')
    directories = {'fixture','wrong-role','incremental-ordinary','incremental-reuse'}
    require(set(p.name for p in root.iterdir()) == directories | {'smoke-rustc','stock-main.rs'},
            'new native qualification root membership differs')
    for name in directories:
        require((root/name).is_dir() and not (root/name).is_symlink(), 'native output directory is indirect')
    require(set(p.name for p in paths['wrong_source'].parent.iterdir()) == {'main.rs'}, 'wrong-role directory membership differs')
    fixture_names = set(p.name for p in paths['fixture'].parent.iterdir())
    # Darwin may retain the packed debug bundle alongside the explicit program.
    # It is observed as compiler output, never a future executable/provider route.
    require({'main.rs','program'} <= fixture_names <= {'main.rs','program','program.dSYM'},
            'fixture output membership differs')
    if 'program.dSYM' in fixture_names:
        debug = paths['program'].with_name('program.dSYM')
        require(debug.is_dir() and not debug.is_symlink(), 'debug bundle is indirect')
    rows = names(root); inventory = {}
    for name,path in rows.items():
        info = identity(path)
        require(not path.is_symlink() and (stat.S_ISDIR(info['mode']) or stat.S_ISREG(info['mode'])),
                'qualification output contains indirect/special entry')
        inventory[name] = dict(kind='directory' if stat.S_ISDIR(info['mode']) else 'file',identity=info)
    return dict(root=str(root), entries=len(inventory), members=inventory,
                scope='Fresh native03 qualification and its compiler debug/incremental outputs only; hash-driver uses a separate sibling root.')


def readback(capacity_guard):
    global _capacity_guard
    require(_capacity_guard is None and callable(capacity_guard), 'one explicit readback per process required')
    _capacity_guard = capacity_guard
    require(all(isinstance(value,str) and re.fullmatch(r'[a-f0-9]{64}',value) for value in [EXPECTED_LAUNCH,EXPECTED_INPUTS,EXPECTED_PLAN,EXPECTED_PROJECTION,EXPECTED_DISPATCHER]), 'unbound source-only verifier; exact reviewed native03 packet required')
    require(sys.dont_write_bytecode and not sys.flags.optimize, 'explicit unoptimized Python -B required')
    require(sha(OUT) == '1058d64e64d75748a3da12115a8400a01daa5cd499b39b09c8d29520eaab4f24'
            and read(OUT)['status'] == 'verified-retained-failure', 'accepted independent original failure audit required')
    started = time.time()
    prior_execution = A/'.work/native-controls-failure-verification-execution-03'
    prior_audit = read(prior_execution/'record.json')
    require(prior_audit['status'] == 'finished' and prior_audit['returncode'] == 1
            and prior_audit['source_sha256'] == sha(A/'.work/verify_native_controls_failure_03.py')
                == '046f175276f15c48864ed4588b1265bcd0f6b9e73f8c7e7e7874faeb3724594f'
            and prior_audit['command'] == ['/opt/homebrew/bin/python3','-B',str(A/'.work/verify_native_controls_failure_03.py')]
            and prior_audit['cwd'] == str(A) and prior_audit['started_at'] <= prior_audit['finished_at'] <= started,
            'original failed read-only audit association differs')
    for stream in ['stdout','stderr']:
        require((prior_execution/stream).stat().st_size <= 2**20
                and sha(prior_execution/stream) == prior_audit[stream+'_sha256'], 'original failed audit raw differs')
    require(not (prior_execution/'stdout').read_bytes()
            and (prior_execution/'stderr').read_bytes().endswith(b'RuntimeError: distinct native child identities required\n'),
            'original failed audit outcome differs')
    launch = read(HERE/'launch.json'); freeze = read(HERE/'inputs.json'); plan = read(HERE/'plan.json')
    receipt = read(WORK/'receipt.json'); outer = read(OUTER/'status.json')
    require(not (WORK/'native-controls.json').exists() and not (WORK/'native-controls.json').is_symlink(), 'failed attempt unexpectedly published result')
    require(sha(HERE/'launch.json') == EXPECTED_LAUNCH
            and sha(HERE/'inputs.json') == EXPECTED_INPUTS == launch['inputs_sha256'] == receipt['inputs_sha256']
            and sha(HERE/'plan.json') == EXPECTED_PLAN == freeze['plan_sha256']
            and sha(HERE/'snapshot-plan.json') == EXPECTED_PROJECTION == launch['snapshot_plan_sha256'] == receipt['snapshot_plan_sha256'],
            'exact reviewed native launch/freeze/plan/projection required')
    expected_error = "ValueError('wrong-B3 failure is not compiler metadata incompatibility')"
    require(receipt['status'] == 'failed' and receipt['error'] == expected_error
            and receipt['source_restored'] is True
            and 'native_roles_and_behavior_qualified' not in receipt and 'result_sha256' not in receipt
            and 'wrong_B3' not in receipt
            and sha(WORK/'receipt.json') == '76fe70afd8eb6486b445e39366de2dd1ffd52ed9578e63203dc7cf74a679a272',
            'exact failed terminal/restoration differs')
    require(all(receipt[key] is False for key in ['hash_driver_qualified','application_qualified','runtime_installation','benchmark']),
            'failed attempt scope changed')
    require(outer['status'] == 'finished' and outer['returncode'] == 1
            and outer['child_pid'] == receipt['pid'] and outer['supervisor_pid'] == receipt['parent_pid']
            and outer['cwd'] == str(A) and outer['command'] == launch['command'][6:]
            and outer['log_sha256'] == sha(OUTER/'command.log') and outer['plan_sha256'] == sha(OUTER/'plan.json')
            and outer['started_at'] <= outer['child_started_at'] <= receipt['started_at'] <= receipt['admitted_at']
                <= receipt['finished_at'] <= outer['finished_at'], 'actual native outer association differs')
    dispatch = read(LAUNCHER/'record.json')
    require(dispatch['status'] == 'terminal-observed' and dispatch['returncode'] == 1
            and dispatch['outer_status'] == 'finished' and dispatch['launcher_returncode'] == 0
            and dispatch['command'] == launch['command'] and dispatch['cwd'] == launch['owner'] == str(A)
            and dispatch['environment'] == launch['environment'] and dispatch['launch_sha256'] == EXPECTED_LAUNCH
            and dispatch['started_at'] <= outer['started_at']
            and outer['finished_at'] <= dispatch['terminal_observed_at'] == dispatch['finished_at']
            and dispatch['started_at'] <= dispatch['launcher_finished_at'] <= dispatch['terminal_observed_at']
            and dispatch['outer_sha256'] == sha(OUTER/'status.json')
            and dispatch['controller_pid'] == receipt['pid'] and dispatch['supervisor_pid'] == outer['supervisor_pid']
            and Path(dispatch['launcher_source_path']) == A/'.work/launch_native_controls_03.py'
            and sha(dispatch['launcher_source_path']) == dispatch['launcher_source_sha256']
                == EXPECTED_DISPATCHER,
            'explicit bounded native launcher differs')
    require(dispatch['entry_free_bytes'] >= 24*2**30 and dispatch['maximum_wrapper_seconds'] == 30
            and dispatch['maximum_observation_seconds'] == 1800
            and dispatch['wrapper_identity_limitation'] == 'Popen PID retained; no separate contemporaneous wrapper ps/cwd probe.'
            and dispatch['launcher_identity']['source'] == 'in-process observation'
            and dispatch['launcher_identity']['pid'] == dispatch['launcher_pid']
            and dispatch['launcher_identity']['parent_pid'] == dispatch['launcher_parent_pid']
            and dispatch['launcher_identity']['cwd'] == str(A), 'launcher admission/observation contract differs')
    for stream in ['stdout','stderr']:
        require(sha(LAUNCHER/stream) == dispatch[stream+'_sha256'], 'launcher raw differs')
    handoff = read(LAUNCHER/'stdout')
    require(handoff == dispatch['supervisor_handoff'] and handoff['supervisor_pid'] == outer['supervisor_pid'] and handoff['directory'] == str(OUTER), 'launcher supervisor handoff differs')
    outer_plan = read(OUTER/'plan.json')
    require(outer_plan['owner'] == str(A) and outer_plan['command'] == launch['command'][6:]
            and outer_plan['supervisor_sha256'] == sha(frozen(A/'scripts/supervise_experiment.py',freeze)),
            'actual outer source/command binding differs')
    require(plan['capacity'] == dict(entry_gib=24,stop_gib=9,floor_gib=8,
        namespace_bytes=14*2**30,evidence_bytes=256*2**20), 'native capacity contract differs')
    for name in freeze['files']: frozen(name, freeze)
    for name, row in freeze['links'].items():
        path = Path(name)
        require(path.is_symlink() and stamp(path) == row['stamp'] and os.readlink(path) == row['target']
                and str(path.resolve(strict=True)) == row['resolved'], 'frozen provider route differs')
    for name in freeze['absent_paths']:
        require(not Path(name).exists() and not Path(name).is_symlink(), 'frozen absence changed')
    for name, resolved in plan['executor_routes'].items():
        require(str(Path(name).resolve(strict=True)) == resolved, 'native executor route differs')
    recipe = pure_module('_native_audit_recipe', HERE/'recipe.py', freeze)
    observed = pure_module('_native_audit_observations', HERE/'observations.py', freeze)
    require(plan['children'] == recipe.desired_commands(plan), 'native exact twenty-call recipe differs')
    paths = recipe.paths(N)
    successor = successor_proof(plan,freeze,receipt,paths)
    rows = []; previous = receipt['admitted_at']; missing_cwd = []
    require(len(receipt['commands']) == len(plan['children']) == 20, 'twenty actual native children required')
    for index, (ref, wanted) in enumerate(zip(receipt['commands'], plan['children'], strict=True)):
        path = WORK/'commands'/f'{index:03}'/'receipt.json'; child = read(path)
        require(ref['path'] == str(path) and sha(path) == ref['sha256'] and ref['pid'] == child['pid']
                and ref['command'] == child['command'] == wanted['argv'] and ref['role'] == wanted['role']
                and child['status'] == 'finished' and child['returncode'] in wanted['expected']
                and child['expected'] == wanted['expected'] and child['environment'] == wanted['environment']
                and child['cwd'] == wanted['cwd'] == str(S), 'actual native child argv/environment/role/return differs')
        require(child['supervisor_pid'] == receipt['pid'] and child['parent_pid'] == receipt['parent_pid']
                and previous <= child['started_at'] <= child['finished_at'] <= receipt['finished_at'], 'native parent/time association differs')
        previous = child['finished_at']; obs = child['identity']
        require(obs['ps_returncode'] == 0 and obs['ps'].strip(), 'missing actual native PS observation')
        fields = obs['ps'].split()
        require(list(map(int,fields[:3])) == [child['pid'],receipt['pid'],child['pid']]
                and len(fields) > 9 and fields[8] == '??' and obs['ps'].endswith(' '.join(wanted['argv'])), 'native actual PID/parent/group/start/command differs')
        time.strptime(' '.join(fields[3:8]), '%a %b %d %H:%M:%S %Y')
        if obs['cwd_returncode'] == 0:
            require(obs['cwd'] == 'p'+str(child['pid'])+'\nfcwd\nn'+str(S)+'\n', 'native contemporaneous cwd differs')
        else:
            require(obs['cwd_returncode'] == 1 and obs['cwd'] == '', 'unexpected native cwd probe failure')
            missing_cwd.append(dict(index=index,pid=child['pid'],requested_cwd=str(S),
                limitation='Contemporaneous cwd unavailable for fast child; requested/recorded cwd retained, no success inferred.'))
        for stream in ['stdout','stderr']:
            require((path.parent/stream).stat().st_size <= 8*2**20
                    and sha(path.parent/stream) == child[stream+'_sha256'], 'bounded native raw stream differs')
        rows.append(dict(child=child,stdout=(path.parent/'stdout').read_bytes(),stderr=(path.parent/'stderr').read_bytes()))
    process_identities = [(row['child']['pid'], ' '.join(row['child']['identity']['ps'].split()[3:8])) for row in rows]
    require(len(set(process_identities)) == 20, 'distinct actual PID/start identities required')
    reused_numeric_pids = {}
    for index, row in enumerate(rows):
        pid = row['child']['pid']
        if sum(item['child']['pid'] == pid for item in rows) > 1:
            reused_numeric_pids.setdefault(str(pid), []).append(dict(index=index,
                observed_ps_start=process_identities[index][1], parent_pid=row['child']['supervisor_pid'],
                argv=row['child']['command'], requested_cwd=row['child']['cwd'],
                cwd_observation=row['child']['identity']['cwd'], cwd_returncode=row['child']['identity']['cwd_returncode'],
                started_at=row['child']['started_at'], finished_at=row['child']['finished_at']))
    for group in reused_numeric_pids.values():
        require(all(first['finished_at'] <= second['started_at'] and first['observed_ps_start'] != second['observed_ps_start']
                    for first, second in zip(group, group[1:])), 'reused PID process intervals overlap or start is ambiguous')

    for index, expected in enumerate([plan['build_version'],str(paths['build'])+'\n',plan['runtime_version'],str(paths['runtime'])+'\n']):
        require(rows[index]['stdout'].decode() == expected and not rows[index]['stderr'], 'native compiler version/sysroot observation differs')
    require(not rows[4]['stderr'] and not rows[5]['stderr'] and rows[6]['stdout'].decode() == plan['runtime_version'], 'stock compiler identity differs')
    stock = exact_file(receipt['stock']); require(stock == paths['stock'], 'stock output binding differs')
    linker = observed.link_command(rows[4]['stdout'],clang=plan['clang'],output=stock,runtime_lib=paths['runtime']/'lib')
    static = observed.stock_macho(stock.read_bytes(),rows[5]['stdout'],stock=stock,driver=plan['runtime_driver']['path'],
        runtime_lib=paths['runtime']/'lib',qualified_private=plan['runtime_closure']['libraries'])
    require(linker == receipt['linker'] and static == receipt['static_loader'], 'actual stock linker/static loader proof differs')
    loader_base = ROOT/'experiments/hir-driver-observations'
    shared_observed = pure_module('_native_audit_shared_observations',loader_base/'observations.py',freeze)
    trace = pure_module('_native_audit_loader_trace',loader_base/'loader_trace.py',freeze,{'observations':shared_observed})
    actual_loader = trace.parse(rows[6]['stderr'],pid=rows[6]['child']['pid'],
        allowed_private={str(stock),*[row['resolved'] for row in plan['runtime_closure']['libraries']]})
    require(actual_loader == receipt['actual_loader'], 'actual stock private loader proof differs')
    for row in plan['runtime_closure']['libraries']:
        require(sha(frozen(row['resolved'],freeze)) == row['sha256'], 'runtime loaded provider changed')
    for path, present in plan['runtime_closure']['searches'].items():
        require((Path(path).exists() or Path(path).is_symlink()) == present, 'runtime loader search changed')
    platform = os.uname()
    require(plan['runtime_closure']['platform'] == dict(system=platform.sysname,release=platform.release,
        version=platform.version,machine=platform.machine), 'runtime loader platform changed')
    for index in [7,9,11,13,14,15,16]: observed.clean(rows[index]['stderr'])
    hits = [observed.hit(rows[index]['stderr'],cold=index==9) for index in [9,11,15,16]]
    raw_pair = lambda index: (rows[index]['stdout'], rows[index]['stderr'])
    error_pair = observed.error_pair(raw_pair(13),raw_pair(14),'E0308')
    wrong_parity = observed.error_pair(raw_pair(18),raw_pair(19),'E0514')
    require([row['message'] for row in wrong_parity['errors']] == [
        'found crate `std` compiled by an incompatible version of rustc',
        'found crate `compiler_builtins` compiled by an incompatible version of rustc'],
        'actual wrong-role coded diagnostic set differs')
    try:
        observed.wrong_pair(raw_pair(18),raw_pair(19),plan['beta_std_paths'])
    except ValueError as error:
        require(repr(error) == expected_error, 'frozen parser rejection differs')
    else:
        raise RuntimeError('frozen parser no longer reproduces actual rejection')
    require(hits == receipt['hits'] and error_pair == receipt['uncalled_error'],
            'native reuse/error evidence differs')
    expected_compiles = [dict(index=index,source_sha256=hashlib.sha256(recipe.ERROR if index in [13,14,15] else recipe.ORIGINAL).hexdigest())
        for index in [7,9,11,13,14,15,16]]
    require(receipt['fixture_compilations'] == expected_compiles, 'all original/error/restored compilations not retained')
    require(paths['fixture'].read_bytes() == recipe.ORIGINAL and paths['wrong_source'].read_bytes() == recipe.WRONG
            and not paths['wrong_output'].exists() and not paths['wrong_output'].is_symlink(), 'final fixture/negative output differs')
    for name, data in [('original',recipe.ORIGINAL),('error',recipe.ERROR),('restored',recipe.ORIGINAL)]:
        require((WORK/(name+'.rs')).read_bytes() == data, 'retained fixture state differs')
    executed = receipt['native_executions']
    require([row['index'] for row in executed] == [8,10,12,17], 'four actual native outputs required')
    for row in executed:
        index = row['index']; copy = Path(row['retained']); original = row['artifact']
        require(copy == WORK/'artifacts'/(str(index)+'.bin') and original['path'] == str(paths['program'])
                and copy.stat().st_size == original['size'] and sha(copy) == original['sha256']
                and identity(copy)['nlink'] == 1
                and (identity(copy)['dev'],identity(copy)['ino']) != (original['identity']['dev'],original['identity']['ino'])
                and rows[index]['stdout'] == b'42\n' and not rows[index]['stderr'], 'executed native output/retained artifact differs')
    exact_file(executed[-1]['artifact'])
    require(plan['candidate_revision'] == receipt['candidate_revision'] and receipt['source_restored'] is True,
            'failed attempt candidate/restoration differs')
    require(set(p.name for p in (WORK/'commands').iterdir()) == {f'{index:03}' for index in range(20)}, 'complete fresh command membership differs')
    require(set(p.name for p in (WORK/'artifacts').iterdir()) == {str(index)+'.bin' for index in [8,10,12,17]}, 'retained execution artifact membership differs')
    membership = qualification_membership(paths)
    beta = b3_prerequisite(plan,freeze)
    projection_plan = read(HERE/'snapshot-plan.json')
    require(projection_plan['inputs_sha256'] == EXPECTED_INPUTS
            and projection_plan['evidence_cap_bytes'] == 256*2**20
            and projection_plan['remaining_evidence_reservation_bytes'] == 32*2**20
            and projection_plan['limits'] == dict(maximum_files=1024,maximum_file_bytes=64*2**20,
                maximum_logical_bytes=512*2**20,maximum_compressed_bytes=128*2**20,maximum_manifest_bytes=4*2**20)
            and projection_plan['helper'] == dict(path=str(ROOT/'experiments/bounded-proof-snapshots/proof_snapshots.py'),
                sha256=freeze['files'][str(ROOT/'experiments/bounded-proof-snapshots/proof_snapshots.py')]['sha256']),
            'snapshot admission policy differs')
    snapshots = verify_snapshots(freeze,receipt,projection_plan)
    reserve = projection_plan['projection']['compressed_bytes']+4096*len(projection_plan['projection']['files'])+8*2**20+32*2**20
    require(projection_plan['projected_reservation_bytes'] == reserve
            and receipt['snapshot_admission']['projected_reservation_bytes'] == reserve
            and receipt['snapshot_admission']['evidence_cap_bytes'] == 256*2**20
            and receipt['snapshot_admission']['existing_evidence_bytes']+reserve <= 256*2**20, 'actual compressed evidence reservation differs')
    for path, row in checked.items(): require(identity(path) == row['identity'], 'audited input changed before completion')
    report = dict(status='verified-retained-failure',receipt_sha256=sha(WORK/'receipt.json'),
        failure=receipt['error'],result_absent=True,frozen_parser_rejection_reproduced=True,
        retained_wrong_role_error_parity=wrong_parity,distinct_observed_process_identities=20,numeric_pid_reuse=reused_numeric_pids,
        prior_readonly_audit_attempt=dict(source=str(A/'.work/verify_native_controls_failure_03.py'),
            source_sha256='046f175276f15c48864ed4588b1265bcd0f6b9e73f8c7e7e7874faeb3724594f',
            execution=str(A/'.work/native-controls-failure-verification-execution-03'),
            record_sha256=sha(prior_execution/'record.json'),
            stdout_sha256=prior_audit['stdout_sha256'],stderr_sha256=prior_audit['stderr_sha256'],
            outcome='failed before report publication on numeric-PID uniqueness assumption'),
        launch_sha256=EXPECTED_LAUNCH,inputs_sha256=EXPECTED_INPUTS,plan_sha256=EXPECTED_PLAN,snapshot_plan_sha256=EXPECTED_PROJECTION,
        children=20,historical_failed_children=11,total_actual_native_children=31,qualified_native_children=0,
        successor=successor,qualification_membership=membership,original_history_children=18,wrong_B3_children=2,fixture_compilations=7,native_executions=4,
        reuse_observations=4,expected_compile_failures=5,source_restored=True,source_identity=plan['source_identity'],
        candidate_revision=plan['candidate_revision'],frozen_files=len(freeze['files']),frozen_bytes=sum(r['size'] for r in freeze['files'].values()),
        frozen_links=len(freeze['links']),full_current_input_hashes=True,actual_linker_static_and_dynamic_loader_replayed=True,
        exact_twenty_call_recipe_and_diagnostic_parity=True,retained_executed_artifacts=4,
        unavailable_contemporaneous_cwd=missing_cwd,wrapper_identity_limitation=dispatch['wrapper_identity_limitation'],B3=beta,snapshots=snapshots,
        native_roles_and_behavior_qualified=False,hash_driver_qualified=False,application_qualified=False,performance_measurement=False,
        admitted_at=receipt['admitted_at'],released_at=outer['finished_at'],started_at=started,finished_at=time.time(),
        verifier_sha256=sha(Path(__file__).resolve()),
        execution='Saved actual/current-byte reads and frozen pure parser calls only; no process/compiler/provider probes or controller import.')
    return report, dict(plan=plan, freeze=freeze, receipt=receipt, paths=paths, rows=rows,
                        observed=observed, recipe=recipe, successor=successor)
