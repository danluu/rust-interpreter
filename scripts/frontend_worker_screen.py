"""Prepared screen interface for a worker build plus external qualification.

The public publisher supplies build identity under BUILD_POLICY. This consumer
additionally requires the external actual 30-command worker qualification. No compiler/fixture is executed by these helpers.
"""
import importlib
import json
import math
from pathlib import Path

from custom_compiler import require, valid_key
from frontend_workers import receipt, require_capability

BUILD_POLICY = 'frontend-workers-public-build-v1'
QUALIFICATION_POLICY = 'frontend-workers-qualification-v1'
COUNTS = dict(baseline=1, candidate=2, duplicate=1)
ERROR_BODIES = {
    'type': 'fn unused() { let _: u32 = false; }\n',
    'borrow': 'fn unused() { let x = vec![1]; let y = &x; drop(x); println!("{:?}", y); }\n',
    'constant': 'const UNUSED: u32 = panic!("must be checked");\n',
}


def public_build(tool, key, read_bytes):
    """Explicit shared-policy boundary; never fall back to macro proof."""
    try:
        api = importlib.import_module('qualified_public_tools')
    except ImportError as error:
        raise RuntimeError('prepare typed worker public-build publication first') from error
    require(BUILD_POLICY in getattr(api, 'SUPPORTED_QUALIFICATION_POLICIES', ()),
            'shared public publisher does not yet support typed worker builds')
    validated = api.validate_public_tool(tool, key, read_bytes, qualification_policy=BUILD_POLICY)
    require(validated['composition']['qualification_policy'] == BUILD_POLICY
            and validated['qualification_scope'] == 'public-build-only',
            'worker public-build scope differs')
    require_capability(tool, validated['capability'], validated['composition']['binaries'])
    return validated


def standard_binding(validated, std):
    public = validated['composition']['public_compiler']
    shared = validated['correctness']['shared_std']
    require(std['rustc'] == public['rustc_path'] and std['rustc_sha256'] == public['rustc_sha256']
            and std['target'] == public['target'] and std['compiler'] == shared['identity']['compiler']
            and std['key'] == shared['key'] and std['sha256'] == shared['ready_sha256']
            and std['sysroot'] == shared['sysroot'], 'worker screen public compiler/std differs')


def qualification_labels():
    result = ['compiler-path', 'compiler-version']
    result += [phase + '-' + str(n) for phase in ['cold', 'edited', 'restored'] for n in [1, 2]]
    for error in ['type', 'borrow', 'constant']:
        result += [phase + '-' + str(n) for phase in [error, error + '-restored', error + '-native-diagnostic']
                   for n in [1, 2]]
    result += [phase + '-' + str(n) for phase in ['assembly-rejection', 'assembly-restored'] for n in [1, 2]]
    return result


def validate_qualification(result_path, key, public, std, read_bytes):
    """Verify actual saved 30-command evidence, bound to a final published key.

    This receipt is external to the keyed composition: its commands contain the
    final tool key. Putting it inside that composition would be self-referential.
    read_bytes may read live files at admission or exact archive bytes later.
    """
    import hashlib
    def sha(data):return hashlib.sha256(data).hexdigest()
    result_path = Path(result_path)
    run = result_path.parent
    require(result_path.is_absolute() and result_path.name == 'result.json'
            and '..' not in result_path.parts, 'invalid worker qualification path')
    read_paths = {}
    def read(path):
        data = read_bytes(path)
        require(isinstance(data, bytes), 'worker qualification reader must return bytes')
        read_paths[str(path)] = sha(data)
        return data
    def load(path):return json.loads(read(path))
    result, plan = load(result_path), load(run / 'plan.json')
    require(result['status'] == 'passed' and result['policy'] == QUALIFICATION_POLICY
            and plan['policy'] == QUALIFICATION_POLICY and result['commands'] == 30
            and result['tool_key'] == plan['tool_key'] == key == public['tool_key'],
            'missing actual typed 30-command worker qualification')
    owner = Path(plan['owner'])
    lock = Path(plan['lock'])
    require(lock.is_absolute() and '..' not in lock.parts, 'worker qualification lock is not explicit')
    require(owner.is_absolute() and run.is_relative_to(owner / '.work')
            and plan['tools'] == public['composition']['binaries']
            and plan['capability'] == public['capability'] and plan['jobs'] == 2,
            'worker qualification tools/owner differ')
    require_capability(Path(public['tool']), plan['capability'], plan['tools'])
    require(plan['rustc'] == std['rustc'] and plan['rustc_sha256'] == std['rustc_sha256']
            and plan['std_key'] == std['key'] and plan['std_ready_sha256'] == std['sha256'],
            'worker qualification compiler/std differs')
    from qualified_public_tools import validate_input_guard
    require(set(result.get('public_input_guards', {})) == {'before','after'}, 'worker qualification lacks public input guards')
    for name, expected in result['public_input_guards'].items():
        data = read(run / ('public-' + name + '.json'))
        require(sha(data) == expected, 'worker public input guard changed')
        guard = json.loads(data)
        require(guard['validation'] == 'sha256', 'worker qualification requires full input guards')
        validate_input_guard(public, guard)
    sources = public['composition']['source']['files']
    required = {name: value for name, value in sources.items() if name.startswith(('crates/', '.cargo/'))
                or name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml']}
    require(required and all(plan['frozen'].get(str(owner / name)) == value
                             for name, value in required.items()), 'worker qualification source inventory differs')
    # Bind all qualification source/fixture/harness bytes, rather than trusting
    # a summary hash map. Readers archive these exact bytes for later review.
    for name, expected in plan['frozen'].items():
        path = Path(name)
        require(path.is_absolute() and path.is_relative_to(owner) and '..' not in path.parts
                and valid_key(expected) and sha(read(path)) == expected, 'worker frozen input differs')
    labels = qualification_labels()
    expected_logs = {'logs/' + label + suffix for label in labels for suffix in ['.json', '-process.json']}
    require(set(result['logs']) == expected_logs, 'worker qualification log set differs')
    logs = {}
    for name, expected in result['logs'].items():
        payload = read(run / name)
        require(sha(payload) == expected, 'worker qualification log bytes differ')
        logs[name] = json.loads(payload)
    cache_paths, native_errors, artifacts = {}, {}, {}
    project = run / 'fixture'
    original_guest = read(owner / 'experiments/frontend-workers/fixture/src/lib.rs')
    error_codes = dict(type='E0308', borrow='E0505', constant='E0080')
    previous_end = 0
    for label in labels:
        row = logs['logs/' + label + '.json']
        child = logs['logs/' + label + '-process.json']
        command = row['command']
        require(row['label'] == child['label'] == label and child['status'] == 'finished'
                and child['command'] == command and child['cwd'] == str(run)
                and child['returncode'] == row['returncode']
                and type(child['pid']) is int and child['pid'] > 0
                and all(type(child[k]) in (int, float) and math.isfinite(child[k]) for k in ['started_at', 'finished_at'])
                and child['finished_at'] >= child['started_at'] >= previous_end
                and child['sources'] == row['sources'], 'worker child receipt differs')
        previous_end = child['finished_at']
        env = child['environment']
        allowed_policy_env = {'RUST_INTERP_LAUNCH_STATS': '1'}
        if '-native-diagnostic-' in label:
            allowed_policy_env['RUST_INTERP_FRONTEND_WORKERS'] = label.rsplit('-', 1)[1]
        require(all(k in allowed_policy_env and v == allowed_policy_env[k] for k, v in env.items()
                    if k.startswith('RUST_INTERP_')), 'worker qualification contains another interpreter policy')
        require(not any(v and (k.endswith('RUSTFLAGS') or k.startswith('CARGO_PROFILE_') or k in
                ['RUSTC', 'CARGO_BUILD_RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                 'CARGO_INCREMENTAL', 'CARGO_BUILD_TARGET', 'CARGO_TARGET_DIR']) for k, v in env.items()),
                'worker qualification overrides normal compiler/profile policy')
        if label == 'compiler-path':
            require(command == ['rustup', 'which', '--toolchain', 'nightly-2026-09-08', 'rustc']
                    and row['returncode'] == 0 and row['stdout'].strip() == std['rustc'], 'worker compiler lookup differs')
            require(row['sources'] == {}, 'compiler identity probe unexpectedly consumes fixture')
            continue
        if label == 'compiler-version':
            require(command == [std['rustc'], '-vV'] and row['returncode'] == 0
                    and row['stdout'] == std['compiler'], 'worker compiler version differs')
            require(row['sources'] == {}, 'compiler identity probe unexpectedly consumes fixture')
            continue
        phase, count = label.rsplit('-', 1)
        count = int(count)
        error = error_codes.get(phase)
        source_expected = {'fixture/shared/src/lib.rs': sha(
            ('pub fn value() -> u64 { ' + ('7' if phase == 'edited' else '3') + ' }\n').encode()),
            'fixture/src/lib.rs': sha(original_guest + ERROR_BODIES.get(phase, '').encode())}
        if phase.endswith('-native-diagnostic'):
            kind = phase.removesuffix('-native-diagnostic')
            source_expected['diagnostic.rs'] = sha(('pub fn good() -> u32 { 1 }\n' + ERROR_BODIES[kind]).encode())
            require(row['sources'] == source_expected, 'worker direct diagnostic source differs')
            expected = [str(Path(public['tool']) / 'rust-interp-rustc-wrapper'), std['rustc'],
                '--crate-name', 'diagnostic', '--crate-type', 'rlib', '--emit=metadata', '--error-format=json',
                '-Cincremental=' + str(run / ('diagnostic-' + str(count))), '-o',
                str(run / ('diagnostic-' + str(count) + '.rmeta')), str(run / 'diagnostic.rs')]
            require(command == expected and env.get('RUST_INTERP_FRONTEND_WORKERS') == str(count)
                    and row['returncode'] != 0 and not row['stdout'] and error_codes[kind] in row['stderr'],
                    'worker direct diagnostic control differs')
            messages = [json.loads(line) for line in row['stderr'].splitlines() if line.startswith('{')]
            messages = [{k: v for k, v in message.items() if k != 'rendered'} for message in messages
                        if message.get('$message_type') == 'diagnostic']
            require(messages and any((m.get('code') or {}).get('code') == error_codes[kind] for m in messages),
                    'missing actual worker diagnostic records')
            native_errors[kind, count] = sorted(json.dumps(m, sort_keys=True) for m in messages)
            continue
        entry = 'assembly' if phase == 'assembly-rejection' else 'answer'
        require(row['sources'] == source_expected, 'worker edit/error/restoration source differs')
        expected = [str(owner / 'scripts/interpreter.py'), '--manifest-path', str(project / 'Cargo.toml'),
            '--package', 'frontend-worker-fixture', '--tool-key', key, '--std-mir', '--jobs', '2',
            '--function-cache', 'auto', '--frontend-workers', str(count), '--workspace-cache-root',
            str(run / 'cache'), '--entry', entry]
        require(command and Path(command[0]).is_absolute() and command[1:] == expected,
                'worker launcher qualification command differs')
        reports = [json.loads(line.removeprefix('rust-interp-launch: ')) for line in row['stderr'].splitlines()
                   if line.startswith('rust-interp-launch: ')]
        if error or phase == 'assembly-rejection':
            expected_error = error or 'unsupported terminator InlineAsm'
            require(row['returncode'] != 0 and row['stdout'] == '' and not reports
                    and expected_error in row['stderr'], 'worker error control accepted or executed')
            continue
        expected_value = 32 if phase == 'edited' else 20
        require(row['returncode'] == 0 and row['stdout'] == str(expected_value) + '\n' and len(reports) == 1,
                'worker executed a wrong or stale result')
        report = reports[0]
        require(report['tool_key'] == key and report['frontend_workers'] == receipt(count, plan['capability'])
                and report['std_mir'] == {k: std[k] for k in ['key', 'sysroot', 'target']}
                and 'custom_compiler' not in report and 'custom_cargo' not in report,
                'worker launch provenance differs')
        path = Path(report['workspace_path'])
        require(path.is_absolute() and path.is_relative_to(run / 'cache') and '..' not in path.parts
                and cache_paths.setdefault(count, path) == path, 'worker cache identity differs')
        artifact = Path(report['artifact_path'])
        require(artifact.is_relative_to(path / 'target') and '..' not in artifact.parts,
                'worker artifact escapes its cache')
        data = read(run / 'artifacts' / (label + '.rbc'))
        require(sha(data) == report['artifact_sha256'], 'worker executed artifact differs')
        artifacts[phase, count] = data
    require(cache_paths[1] != cache_paths[2] and result['workspaces'] == {str(k): str(v) for k, v in cache_paths.items()},
            'worker policies share a cache')
    original = artifacts['cold', 1]
    require(sha(original) == result['original_artifact_sha256'], 'worker original artifact differs')
    for (phase, count), data in artifacts.items():
        require(data == artifacts[phase, 3 - count] and (data != original if phase == 'edited' else data == original),
                'worker edit/restoration or pair bytecode differs')
    require(all(native_errors[kind, 1] == native_errors[kind, 2] for kind in error_codes),
            'worker raw diagnostic comparison differs')
    for relative in ['shared/src/lib.rs', 'src/lib.rs']:
        original_path = owner / 'experiments/frontend-workers/fixture' / relative
        require(read(project / relative) == read(original_path), 'worker fixture was not restored')
    return dict(policy=QUALIFICATION_POLICY, result_path=str(result_path), result_sha256=read_paths[str(result_path)],
                plan_sha256=read_paths[str(run / 'plan.json')], tool_key=key, commands=30,
                compiler_sha256=std['rustc_sha256'], std_key=std['key'], files=read_paths,
                workload_lock=str(lock),
                qualification='passed', timing_claim=False)
