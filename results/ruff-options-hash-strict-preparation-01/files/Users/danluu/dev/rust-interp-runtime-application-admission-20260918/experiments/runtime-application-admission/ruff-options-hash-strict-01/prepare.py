#!/usr/bin/env python3
"""Prepare the unchanged strict Ruff history from actual published prerequisites.

No subprocess or application execution. A separate reviewed binding supplies the
future exporter publication and exact preparation environment. Project imports
occur only after the finite source manifest and all proof references are checked.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time
import tomllib

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[2]
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
NAME = 'ruff-options-hash-strict-01'
WORK = OWNER / '.work' / NAME
DESTINATION = HERE / 'plan'
OUTER = OWNER / '.work/experiments/ruff-options-hash-strict-supervisor-01'
RUNTIME_KEY = 'f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70'
STD_KEY = 'f6366b5873636f47cdc3e9941a9b24ef612f94432baecb5d75ed5c4c54911928'
PER_FILE = 32 * 2**20
TOTAL = 96 * 2**20
SOURCES_POLICY = 'ruff-options-hash-strict-sources-v1'
BINDING_POLICY = 'reviewed-ruff-options-hash-strict-preparation-v1'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stamp(path):
    s = Path(path).lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def data(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path, 'indirect input: ' + str(path))
    before = stamp(path)
    require(stat.S_ISREG(before[2]) and before[3] <= PER_FILE, 'unbounded input: ' + str(path))
    payload = path.read_bytes()
    require(len(payload) == before[3] and stamp(path) == before, 'input changed: ' + str(path))
    return payload


def reference(path):
    return dict(path=str(path), sha256=hashlib.sha256(data(path)).hexdigest())


def pinned(ref, checked, *, json_value=True):
    require(type(ref) is dict and set(ref) == {'path', 'sha256'} and type(ref['path']) is str
            and type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}', ref['sha256']),
            'unbound or malformed proof reference')
    payload = data(ref['path'])
    require(hashlib.sha256(payload).hexdigest() == ref['sha256'], 'proof changed: ' + ref['path'])
    require(ref['path'] not in checked or checked[ref['path']] == ref['sha256'], 'unequal proof overlap')
    checked[ref['path']] = ref['sha256']
    return json.loads(payload) if json_value else payload


def write(path, value):
    payload = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    require(len(payload) <= PER_FILE, 'packet output exceeds file bound')
    with path.open('xb') as stream:
        stream.write(payload)


def floor():
    free = shutil.disk_usage(OWNER).free
    require(free >= 9 * 2**30, 'read-only preparation free-space floor')
    return free


def prerequisite_records(binding, checked):
    refs = binding['proofs']
    require(set(refs) == {'runtime', 'std', 'history', 'exporter'}, 'proof groups differ')
    expected = {
        'runtime': {'ready', 'admission', 'qualification', 'receipt', 'audit', 'audit_execution'},
        'std': {'ready', 'result', 'receipt', 'launch_execution', 'independent_readback'},
        'history': {'strict_plan', 'strict_freeze', 'diagnostic_plan', 'diagnostic_receipt',
                    'diagnostic_records', 'source_inventory', 'source_acquisition', 'original_source',
                    'strict_independent_audit', 'strict_summary'},
        'exporter': {'publication', 'published_tools'},
    }
    records = {}
    for group, names in expected.items():
        require(set(refs[group]) == names, 'proof fields differ: ' + group)
        records[group] = {name: pinned(refs[group][name], checked,
                            json_value=not (group == 'history' and name == 'original_source'))
                          for name in sorted(names)}
    r, s, h, e = [records[name] for name in ['runtime', 'std', 'history', 'exporter']]
    audit, execution = r['audit'], r['audit_execution']
    require(audit['status'] == 'verified' and audit['phase'] == 'installation'
            and audit['phase_result']['runtime_key'] == RUNTIME_KEY,
            'actual installation audit required')
    require(execution['status'] == 'finished' and execution['returncode'] == 0
            and execution['may_be_live'] is False and not execution['observation_errors']
            and execution['report'] == refs['runtime']['audit']['path']
            and execution['result_sha256'] == refs['runtime']['audit']['sha256']
            and execution['child_started_at'] <= audit['started_at'] <= audit['finished_at']
                <= execution['finished_at'] <= execution['canonical_released_at'],
            'installation audit is not a closed successful observation')
    for channel in ['stdout', 'stderr']:
        path = Path(refs['runtime']['audit_execution']['path']).parent / channel
        pinned(dict(path=str(path), sha256=execution[channel + '_sha256']), checked, json_value=False)
    runtime = R / '.work/runtime-compilers' / RUNTIME_KEY
    for name in ['ready', 'admission', 'qualification']:
        require(refs['runtime'][name]['path'] == str(runtime / (name + '.json'))
                and audit['phase_result'][name + '_sha256'] == refs['runtime'][name]['sha256'],
                'installation phase proof association differs')
    require(r['receipt']['status'] == 'passed'
            and audit['receipt_sha256'] == refs['runtime']['receipt']['sha256']
            and r['ready']['key'] == RUNTIME_KEY and r['ready']['status'] == 'installed'
            and set(r['admission']) == {'identity', 'snapshots'}
            and r['ready']['identity'] == r['admission']['identity']
            and r['ready']['identity']['admission']['loader_probe'] == {
                'policy': 'darwin-native-loader-probe-v1', 'host': 'aarch64-apple-darwin',
                'architecture': 'arm64'}, 'qualified native runtime proof differs')
    readback, launch = s['independent_readback'], s['launch_execution']
    require(readback['status'] == 'verified' and readback['runtime_key'] == RUNTIME_KEY
            and readback['std_key'] == STD_KEY and readback['ready'] == refs['std']['ready']
            and readback['result_sha256'] == refs['std']['result']['sha256']
            and readback['receipt_sha256'] == refs['std']['receipt']['sha256']
            and readback['launch_execution_sha256'] == refs['std']['launch_execution']['sha256']
            and readback['source_and_output_unchanged'] is True,
            'independently checked actual std07 proof differs')
    require(launch['status'] == 'terminal-observed' and launch['returncode'] == 0
            and launch['controller_may_be_live'] is False and launch['wrapper_may_be_live'] is False
            and s['receipt']['status'] == 'passed' and s['result']['status'] == 'passed'
            and s['result']['commands'] == 7 and s['result']['key'] == STD_KEY
            and s['ready']['key'] == STD_KEY
            and refs['std']['ready']['path'] == str(R / '.work/std-mir' / STD_KEY / 'ready.json'),
            'ordinary seven-command std closure differs')
    require(h['diagnostic_receipt']['status'] == 'passed'
            and h['strict_independent_audit']['status'] == 'verified'
            and h['strict_independent_audit']['complete_commands'] == 16
            and h['strict_summary']['status'] == 'passed'
            and h['strict_summary']['wrong_edit_rejected_in_both_modes'] is True,
            'retained historical source/assertion schedule is not qualified')
    key = binding['tool_key']
    require(type(key) is str and re.fullmatch('[0-9a-f]{64}', key), 'future exporter key remains unbound')
    publication, published = e['publication'], e['published_tools']
    require(publication['status'] == 'passed' and publication['runtime_key'] == RUNTIME_KEY
            and publication['tool_key'] == key and publication['frontend_qualified'] is True
            and publication['published_tools_sha256'] == refs['exporter']['published_tools']['sha256']
            and published['tool_key'] == key
            and published['directory'] == str(R / '.work/interpreter-tools' / key),
            'actual qualified new exporter publication required')
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--binding-sha256', required=True)
    args = parser.parse_args()
    require(Path.cwd() == OWNER and sys.dont_write_bytecode and not sys.flags.optimize,
            'fixed owner and unoptimized Python -B required')
    checked = {}
    binding = pinned(dict(path=str(args.binding), sha256=args.binding_sha256), checked)
    require(set(binding) == {'policy', 'owner', 'name', 'source_manifest', 'preparation_environment',
                            'tool_key', 'proofs'} and binding['policy'] == BINDING_POLICY
            and binding['owner'] == str(OWNER) and binding['name'] == NAME,
            'binding schema or ownership differs')
    require(type(binding['preparation_environment']) is dict
            and dict(os.environ) == binding['preparation_environment'], 'exact preparation environment differs')
    observed_environment = dict(os.environ)
    require(type(observed_environment.get('__CF_USER_TEXT_ENCODING')) is str
            and observed_environment['__CF_USER_TEXT_ENCODING'], 'actual startup environment observation missing')
    sources = pinned(binding['source_manifest'], checked)
    require(set(sources) == {'policy', 'files', 'runtime_script_paths'}
            and sources['policy'] == SOURCES_POLICY, 'source manifest schema differs')
    runtime_paths = sorted(str(p) for p in (R / 'scripts').glob('*.py'))
    helper_paths = [HERE / name for name in ['run.py', 'prepare.py', 'README.md', 'PREPARATION.md']]
    helper_paths += [HERE.parent / name for name in [
        'runtime_admission_v3.py', 'runtime_platform.py', 'run_ruff_diagnostic.py',
        'ruff-profile-02/profile_helpers.py']]
    helper_paths += [OWNER/'experiments/stable-cgu/owned_stage.py', OWNER/'scripts/supervise_experiment.py',
                    ROOT/'experiments/runtime-native-loader-probes-01/runtime_compiler.py']
    require(runtime_paths == sources['runtime_script_paths'] and len(runtime_paths) == 112
            and set(sources['files']) == set(runtime_paths) | set(map(str, helper_paths)),
            'finite strict source closure differs')
    require(len(sources['files']) <= 128, 'source closure exceeds declared finite scope')
    for name, digest in sources['files'].items():
        pinned(dict(path=name, sha256=digest), checked, json_value=False)
    records = prerequisite_records(binding, checked)
    for path in [DESTINATION, WORK, OUTER]:
        require(not path.exists() and not path.is_symlink(), 'preparation or workload namespace is not fresh')
    floor()
    sys.path.insert(0, str(HERE))
    import run as a
    import runtime_platform
    from runtime_compiler import load_runtime_compiler
    from runtime_tools import validate_tool_runtime
    from interpreter import installed_tools
    from std_mir_source_paths import load as load_std, namespace_for
    require(a.NAME == NAME and a.OWNER == OWNER and a.WORK == WORK
            and a.RUNTIME_KEY == RUNTIME_KEY and a.STD_KEY == STD_KEY,
            'controller source constants differ')
    require(dict(os.environ) == observed_environment, 'environment changed during project import')
    old = records['history']['strict_plan']
    historical = records['history']['diagnostic_plan']
    refs = binding['proofs']
    for key in ['source_inventory', 'source_acquisition', 'prior_records', 'prior_diagnostic']:
        name = {'prior_records': 'diagnostic_records', 'prior_diagnostic': 'diagnostic_receipt'}.get(key, key)
        require(old[key] == refs['history'][name], 'historical reference association differs: ' + key)
    original = records['history']['original_source']
    source = a.source_file(a.SOURCE, a.WORKFLOWS['ruff'])
    inventory = records['history']['source_inventory']
    original_sha = hashlib.sha256(original).hexdigest()
    require(source == a.SOURCE / a.WORKFLOWS['ruff']['file'] and data(source) == original
            and original_sha == inventory[a.WORKFLOWS['ruff']['file']]['sha256']
            == records['history']['strict_freeze']['files'][str(source)], 'original source or live path differs')
    states, schedule = a.history(original)
    prior_rows = [row for row in records['history']['diagnostic_records'] if row['mode'] != 'native']
    require(schedule == old['history'] and len(schedule) == len(prior_rows) == 16, 'strict history differs')
    for spec, prior in zip(schedule, prior_rows, strict=True):
        require(all(spec[k] == prior[k] for k in ['state', 'phase', 'mode', 'source_sha256'])
                and prior['tests'] == a.WORKFLOWS['ruff']['tests'], 'diagnostic source/test/order differs')
    compiler = load_runtime_compiler(R, RUNTIME_KEY)
    tools, key = installed_tools(binding['tool_key'])
    require(key == binding['tool_key'], 'ordinary installed-tools selection differs')
    validate_tool_runtime(tools, key, compiler)
    composition = json.loads(data(tools / 'compiler.json'))
    capabilities = json.loads(data(tools / 'capabilities.json'))
    published = records['exporter']['published_tools']
    require(published['composition'] == composition and published['capabilities'] == capabilities,
            'publication and ordinary installed tools differ')
    a.TOOL_KEY = key  # Only after the actual ordinary reader and runtime association succeed.
    for name in ['ready.json', 'compiler.json', 'capabilities.json']:
        ref = reference(tools / name)
        pinned(ref, checked)
    environment = dict(old['child_environment'], TMPDIR=str(WORK / 'tmp') + '/',
                       __CF_USER_TEXT_ENCODING=observed_environment['__CF_USER_TEXT_ENCODING'])
    require(not any(name in environment for name in a.FORBIDDEN), 'compatibility policy in strict environment')
    observed = list(os.uname())
    require(runtime_platform.identity(observed) == old['platform_identity'], 'kernel/machine identity changed')
    configuration = {}
    config_paths = set(map(Path, historical['configuration']))
    for root in [WORK, WORK/'tmp', WORK/'cache', WORK/'cache/baseline', WORK/'cache/candidate', WORK/'compiler-argv']:
        config_paths.update(parent/'.cargo'/name for parent in [root, *root.parents]
                            for name in ['config', 'config.toml'])
    for path in sorted(config_paths):
        require(not path.is_symlink() and all(not p.is_symlink() for p in path.parents), 'indirect configuration')
        row = dict(exists=path.exists())
        if row['exists']:
            payload = data(path)
            row['sha256'] = hashlib.sha256(payload).hexdigest()
            checked[str(path)] = row['sha256']
            if path.name in ['config', 'config.toml'] and path.parent.name == '.cargo':
                require(not any(k in tomllib.loads(payload.decode()).get('env', {}) for k in a.FORBIDDEN),
                        'Cargo config enables compatibility policy')
        if str(path) in historical['configuration']:
            require(row == historical['configuration'][str(path)], 'historical source/configuration changed')
        else:
            require(not row['exists'], 'unexpected new configuration')
        configuration[str(path)] = row
    providers = {name: a.provider(name) for name in old['providers']}
    executors = {name: a.provider(name) for name in old['executor_routes']}
    require(providers == old['providers'] and executors == old['executor_routes'], 'provider/executor changed')
    python = Path(old['python'])
    require(str(Path(sys.executable).resolve()) == executors[str(python)]['resolved'], 'preparation Python differs')
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(environment)
    try:
        standard = load_std(R, STD_KEY, compiler, namespace_for('source-paths-v2-shared', 'unused-shared-policy'), rehash=True)
    finally:
        os.environ.clear()
        os.environ.update(saved)
    commands = [dict(label=spec['label'], command=a.command(str(python), spec), cwd=str(R),
                     expected_returncode=1 if spec['state'] == -1 else 0) for spec in schedule]
    for command, previous in zip(commands, old['commands'], strict=True):
        replacements = {old['runtime_key']: RUNTIME_KEY, old['std_key']: STD_KEY, old['tool_key']: key,
                        old['name']: NAME}
        argv = previous['command']
        for before, after in replacements.items():
            argv = [arg.replace(before, after) for arg in argv]
        require(command == dict(previous, command=argv), 'strict command delta exceeds names and actual keys')
    plan = dict(schema_version=1, status='unexecuted', name=NAME, policy=a.POLICY, owner=str(OWNER),
        runtime_owner=str(R), runtime_key=RUNTIME_KEY, std_key=STD_KEY, tool_key=key,
        runtime_composition=composition, tool_publication=refs['exporter']['publication'],
        published_tools=refs['exporter']['published_tools'], source_inventory=refs['history']['source_inventory'],
        source_acquisition=refs['history']['source_acquisition'], prior_diagnostic=refs['history']['diagnostic_receipt'],
        prior_records=refs['history']['diagnostic_records'], historical_plan=refs['history']['strict_plan'],
        prerequisite_proofs=refs, preparation_binding=reference(args.binding), source_manifest=binding['source_manifest'],
        python=str(python), launch_environment=environment, child_environment=environment,
        platform=observed, platform_identity=runtime_platform.identity(observed), executor_routes=executors,
        providers=providers, provider_directories=old['provider_directories'], configuration=configuration,
        producer_sources=sources['files'], canonical_lock=old['canonical_lock'], wait_seconds=600,
        history=schedule, commands=commands, allocated_byte_limit=6*2**30, bounds=old['bounds'],
        editable_source=dict(path=str(source), relative_path=a.WORKFLOWS['ruff']['file'], original_sha256=original_sha,
            original_snapshot=refs['history']['original_source'],
            state_sha256=[dict(state=s['state'], sha256=hashlib.sha256(s['source']).hexdigest()) for s in states],
            policy='Live mutable path excluded from immutable inputs; exact state checked before and after every call.'),
        changes_from_strict03=['Fresh namespaces and actual runtime07/std07/published exporter keys.',
            'Replace live immutable registry freeze with retained original and exact per-state digest.',
            'Finite current imported-source/proof closure; no recursive historical input union.'],
        scope='Full strict JIT six-test history, sixteen new calls, eight off/on RBC pairs; correctness only.',
        performance_qualified=False, benchmark=False, no_new_native_application_baseline=True)
    require(plan['bounds'] == dict(entry_free_gib=16, active_child_stop_gib=9, running_floor_gib=8,
            retained_inputs_bytes=TOTAL, retained_input_file_bytes=PER_FILE), 'original resource policy differs')
    require(str(source) not in checked, 'live mutable source included in immutable closure')
    # Reserve the exact serialized plan size before creating any packet output.
    plan_bytes = (json.dumps(plan, sort_keys=True, indent=2) + '\n').encode()
    total = sum(Path(name).stat().st_size for name in checked) + len(plan_bytes)
    require(total <= TOTAL and len(plan_bytes) <= PER_FILE, 'finite input closure exceeds unchanged budget')
    DESTINATION.mkdir()
    write(DESTINATION/'plan.json', plan)
    checked[str(DESTINATION/'plan.json')] = sha(DESTINATION/'plan.json')
    frozen = dict(schema_version=1, owner=str(OWNER),
        python=dict(resolved=str(python.resolve()), sha256=sha(python)), files=dict(sorted(checked.items())))
    write(DESTINATION/'inputs.json', frozen)
    probe = a.Admission.__new__(a.Admission)
    probe.plan_path, probe.freeze_path = DESTINATION/'plan.json', DESTINATION/'inputs.json'
    probe.freeze_sha = sha(probe.freeze_path)
    probe.plan, probe.freeze, probe.source_files = plan, frozen, plan['producer_sources']
    probe.compiler, probe.tools, probe.key, probe.standard = compiler, tools, key, standard
    probe.environment = environment
    started = time.time()
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(environment)
    try:
        probe.guard()
        probe.full_artifacts()
        source_proof = a.source_inventory(a.SOURCE, inventory, floor)
    finally:
        os.environ.clear()
        os.environ.update(saved)
    require(dict(os.environ) == observed_environment, 'preparation environment was not restored')
    write(DESTINATION/'metadata-preflight.json', dict(status='passed', started_at=started, finished_at=time.time(),
        pid=os.getpid(), parent_pid=os.getppid(), source_freeze_sha256=probe.freeze_sha,
        workload_children=0, work_directory_created=False, source_inventory=source_proof,
        full_runtime_and_std_rehashed=True, full_ready_tools_rehashed=True,
        ordinary_read_only_guard_passed=True, live_mutable_source_excluded=True,
        input_files=len(checked), input_bytes=total, observed_preparation_environment=observed_environment,
        launch_environment=environment, free_bytes_after=floor()))
    launch = dict(owner=str(OWNER), cwd=str(OWNER), environment=environment, helper=reference(HERE/'run.py'),
        plan=reference(probe.plan_path), source_freeze=reference(probe.freeze_path),
        command=[str(python), '-B', str(OWNER/'scripts/supervise_experiment.py'), '--run-id',
            'ruff-options-hash-strict-supervisor-01', '--', str(python), '-B', str(HERE/'run.py'),
            '--plan', str(probe.plan_path), '--freeze', str(probe.freeze_path), '--freeze-sha256', probe.freeze_sha],
        canonical_lock=plan['canonical_lock'], wait_seconds=600, bounds=plan['bounds'], expected_children=16,
        review_required_before_launch=True)
    write(DESTINATION/'launch.json', launch)
    print(json.dumps(dict(launch=reference(DESTINATION/'launch.json'), plan=reference(probe.plan_path),
        freeze=reference(probe.freeze_path), input_files=len(checked), input_bytes=total), indent=2))


if __name__ == '__main__':
    main()
