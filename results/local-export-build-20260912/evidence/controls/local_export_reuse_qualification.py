"""Adapt actual future core results to unchanged, self-locking cache checkers.

Never invoke through run_locked.py. Preparation is source-only; `freeze` and
the three checker modes are for root to execute after core qualification.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time
import traceback


ROOT = Path('/Users/danluu/dev/rust-interp-perf-20260912')
B = ROOT / '.work/build-general-20260912'
HERE = ROOT / 'benchmarks/experiments/export-costs'
SCRIPT = B / 'local_export_reuse_qualification.py'
INPUTS = B / 'local-export-reuse-inputs.json'
BUILD = B / 'local-export-reuse-build-schema.json'
CANDIDATE = '14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75'
BASELINE = 'eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d'
SHARED_LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
RUNS = {'reuse': 'export-reuse-fixtures-71',
        'dependency': 'export-dependency-fixture-71', 'cache': 'export-cache-fixture-71'}
COUNTS = {'reuse': 337, 'dependency': 293, 'cache': 98}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    path = Path(path)
    require(path.is_relative_to(ROOT) and path.resolve(strict=True) == path,
            'noncanonical or unowned proof path: ' + str(path))
    require(stat.S_ISREG(path.lstat().st_mode), 'nonregular proof: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for data in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(data)
    return digest.hexdigest()


def read(path):
    sha(path)
    return json.loads(Path(path).read_text())


def write_new(path, value):
    with Path(path).open('x') as target:
        json.dump(value, target, indent=2, allow_nan=False)
        target.write('\n')
        target.flush()
        os.fsync(target.fileno())


def bind(proofs, path, expected=None):
    path = Path(path)
    name = str(path.relative_to(ROOT))
    digest = sha(path)
    require(expected is None or digest == expected, 'proof hash differs: ' + name)
    require(name not in proofs or proofs[name] == digest, 'proof changed: ' + name)
    proofs[name] = digest


def verify(proofs):
    for name, digest in proofs.items():
        require(sha(ROOT / name) == digest, 'frozen input changed: ' + name)


def static_inputs():
    inputs = read(INPUTS)
    require(inputs['candidate_tool_key'] == CANDIDATE and inputs['baseline_tool_key'] == BASELINE,
            'wrong static tool identities')
    require(inputs['runs'] == RUNS and inputs['expected_commands'] == COUNTS, 'run plan changed')
    proofs = dict(inputs['files'])
    verify(proofs)
    bind(proofs, INPUTS)
    return proofs


def freeze():
    require(not os.path.lexists(BUILD), 'build-schema receipt already exists')
    proofs = static_inputs()
    core_path = B / 'local-export-qualification.json'
    core = read(core_path)
    require(core['qualification_pass'] is True and core['tool_key'] == CANDIDATE,
            'candidate core qualification did not pass')
    require(core['baseline_tool_key'] == BASELINE and core['frozen_baseline_runtime'] is True,
            'core baseline changed')
    expected_tests = {mode: {'passed': 408, 'failed': 0, 'ignored': 1} for mode in ['debug', 'release']}
    require(core['tests'] == expected_tests and core['full_validation']['completed_commands'] == 23727,
            'actual core test results differ')
    for name, digest in core['proofs'].items():
        bind(proofs, ROOT / name, digest)
    bind(proofs, core_path)
    bundles = {}
    for key, filename in [(CANDIDATE, 'local-export-tools.json'), (BASELINE, 'owned-analysis-tools.json')]:
        tools_path = B / filename
        tools = read(tools_path)
        directory = ROOT / '.work/interpreter-tools' / key
        require(tools['tool_key'] == key and Path(tools['directory']) == directory, 'wrong tool bundle')
        require(set(tools['binaries']) == {'rust-interp-mir-export', 'rust-interp-vm', 'rust-interp-rustc-wrapper'},
                'unexpected tool binary set')
        require(read(directory / 'ready.json') == tools['binaries'], 'bundle readiness changed')
        caps = read(directory / 'capabilities.json')
        require(caps['tool_key'] == key and caps['exporter_sha256'] == tools['binaries']['rust-interp-mir-export'],
                'bundle capabilities changed')
        for name, digest in tools['binaries'].items():
            bind(proofs, directory / name, digest)
        for path in [tools_path, directory / 'ready.json', directory / 'capabilities.json']:
            bind(proofs, path)
        bundles[key] = tools['binaries']
    for name in ['rust-interp-vm', 'rust-interp-rustc-wrapper']:
        require(bundles[CANDIDATE][name] == bundles[BASELINE][name], 'candidate runtime or wrapper drift')
    for run in RUNS.values():
        require(not os.path.lexists(ROOT / '.work' / run)
                and not os.path.lexists(ROOT / 'results' / run), 'run identity already exists: ' + run)
    verify(proofs)
    write_new(BUILD, dict(status='passed', kind='derived-build-schema-adapter',
        explanation='Flattened actual 408-test whole-workspace core results; the historical exporter-only build script was not executed.',
        source_commit=core['source_commit'], tool_key=CANDIDATE, baseline_tool_key=BASELINE,
        tests={'test-debug': 408, 'test-release': 408}, actual_workspace_tests=core['tests'],
        binaries=bundles[CANDIDATE], core_qualification=str(core_path.relative_to(ROOT)),
        core_qualification_sha256=sha(core_path), proofs=proofs, created_at=time.time(),
        new_build_performed=False, historical_results_substituted=False, performance_measurement=False))
    print(json.dumps({'status': 'passed', 'derived_receipt': str(BUILD)}, indent=2))


def summary_path(mode):
    return ROOT / 'results' / RUNS[mode] / 'summary.json'


def passed_path(mode):
    return B / ('local-export-' + mode + '-passed.json')


def argv_for(mode):
    argv = [str(HERE / (mode + '_check.py')), '--run-id', RUNS[mode], '--build', str(BUILD)]
    if mode == 'reuse':
        return argv + ['--typed-relocations', '--binding-replay', '--function-reuse', '--expected-tests', '408']
    if mode == 'dependency':
        return argv + ['--binding-replay-qualification', str(summary_path('reuse')), '--persistent-cache', '--function-reuse']
    return argv + ['--qualification', str(summary_path('dependency')), '--function-reuse']


def validate_result(mode, proofs):
    result_path = summary_path(mode)
    result = read(result_path)
    work = ROOT / '.work' / RUNS[mode]
    require(result['status'] == ('completed diagnostic' if mode == 'dependency' else 'passed'),
            'original checker did not complete successfully')
    require(result['tool_key'] == CANDIDATE and result['commands'] == COUNTS[mode]
            and result['function_reuse'] is True and result['performance_measurement'] is False
            and result['all_artifact_hashes_identical'] is True, 'checker result differs')
    require(ROOT / result['raw'] == work and work.resolve(strict=True) == work, 'wrong raw run directory')
    if mode == 'reuse':
        require(result['typed_relocations'] is True and result['binding_replay'] is True, 'reuse flags differ')
    else:
        require(result['source_restored'] is True and result['original_assertions_unchanged'] is True,
                'original source/assertions were not preserved')
    if mode == 'dependency':
        require(result['binding_replay'] is True and result['persistent_cache'] is True
                and result['candidate_dependency_boundary_supported'] is True
                and result['all_lowering_executed'] is True
                and result['green_functions'] > 0 and result['changed_green_templates'] == 0
                and result['unknown_green'] == 0 and result['strict_invalid_source_rejected'] is True,
                'dependency boundary qualification failed')
        bind(proofs, work / 'observations.json', result['observations_sha256'])
    if mode == 'cache':
        require(all(result[key] is True for key in ['checksum_namespace_missing_controls',
            'both_policy_namespaces_and_nodes_invalidated', 'failed_publication_after_staging_published_no_session',
            'cache_recovery']) and result['all_original_lowering_executed'] is False, 'cache controls failed')
    bind(proofs, result_path)
    bind(proofs, work / 'records.json', result['records_sha256'])
    records = read(work / 'records.json')
    require(len(records) == COUNTS[mode], 'raw command count differs')
    for row in records:
        for stream in ['stdout', 'stderr']:
            path = ROOT / row[stream]
            require(path.is_relative_to(work), 'raw stream outside owned run')
            bind(proofs, path, row[stream + '_sha256'])
    for name, digest in result['frozen'].items():
        bind(proofs, ROOT / name, digest)
    # Bind completed evidence, not mutable compiler incremental generations.
    for path in sorted(work.iterdir()):
        if path.suffix in {'.json', '.jsonl', '.rbc', '.bin', '.stdout', '.stderr', '.rs'}:
            bind(proofs, path)
    if mode != 'reuse':
        for name in ['main.rs', 'model.rs', '.rust-interp-owned.json']:
            bind(proofs, work / 'source' / name)
        for name in ['main.rs', 'model.rs']:
            require(sha(work / 'source' / name) == sha(HERE / 'dependency_fixture' / name), 'source copy not restored')
    return result


def run(mode, attempt):
    require(1 <= attempt <= 99, 'attempt must be 1..99')
    proofs = static_inputs()
    build = read(BUILD)
    require(build['kind'] == 'derived-build-schema-adapter' and build['status'] == 'passed'
            and build['tool_key'] == CANDIDATE and build['baseline_tool_key'] == BASELINE,
            'missing actual core-derived build receipt')
    verify(build['proofs'])
    proofs.update(build['proofs'])
    bind(proofs, BUILD)
    if mode != 'reuse':
        previous = 'reuse' if mode == 'dependency' else 'dependency'
        receipt = read(passed_path(previous))
        require(receipt['status'] == 'passed' and receipt['tool_key'] == CANDIDATE
                and receipt['mode'] == previous and receipt['run_id'] == RUNS[previous], 'prior adapter did not pass')
        verify(receipt['proofs'])
        proofs.update(receipt['proofs'])
        bind(proofs, passed_path(previous))
        validate_result(previous, proofs)
    work = ROOT / '.work' / RUNS[mode]
    results = ROOT / 'results' / RUNS[mode]
    require(not os.path.lexists(work) and not os.path.lexists(results)
            and not os.path.lexists(passed_path(mode)), 'existing run evidence forbids launch')
    if attempt > 1:
        previous = read(B / f'local-export-{mode}-attempt-{attempt - 1:02}.json')
        require(previous['status'] == 'unstarted-lock-timeout' and previous['run_id'] == RUNS[mode]
                and previous['module_argv'] == argv_for(mode), 'only an unstarted lock timeout may retry')
    require((ROOT / '.work/benchmark.lock').resolve(strict=True) == SHARED_LOCK,
            'workspace lock does not identify the established shared lock')
    stem = B / f'local-export-{mode}-attempt-{attempt:02}'
    receipt_path, log_path = stem.with_suffix('.json'), stem.with_suffix('.log')
    require(not os.path.lexists(receipt_path) and not os.path.lexists(log_path), 'attempt already recorded')
    record = dict(status='running', mode=mode, run_id=RUNS[mode], tool_key=CANDIDATE,
        argv=[sys.executable, *sys.argv], module_argv=argv_for(mode), cwd=str(Path.cwd()),
        controller_pid=os.getpid(), started_at=time.time(), self_lock_seconds=45,
        outer_lock_acquired=False, baseline_override=BASELINE)
    write_new(receipt_path, record)
    old_argv = sys.argv
    success = False
    with log_path.open('x') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        try:
            sys.path.insert(0, str(HERE))
            spec = importlib.util.spec_from_file_location('local_export_' + mode + '_checker', HERE / (mode + '_check.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            require(module.ROOT == ROOT, 'checker imported from another workspace')
            module.CONTROL = BASELINE
            sys.argv = argv_for(mode)
            module.main()
            result = validate_result(mode, proofs)
            verify(proofs)
            record.update(status='passed', original_summary_status=result['status'])
            success = True
        except BaseException as error:
            expected = f'timed out after 45s waiting for benchmark lock {ROOT / ".work/benchmark.lock"}'
            unstarted = isinstance(error, TimeoutError) and str(error) == expected
            unstarted = unstarted and not os.path.lexists(work) and not os.path.lexists(results)
            record.update(status='unstarted-lock-timeout' if unstarted else 'failed', error=repr(error))
            traceback.print_exc()
        finally:
            sys.argv = old_argv
            record['finished_at'] = time.time()
    # Updating this attempt's own receipt never replaces prior attempts/evidence.
    receipt_path.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
    if success:
        bind(proofs, receipt_path)
        bind(proofs, log_path)
        write_new(passed_path(mode), dict(status='passed', tool_key=CANDIDATE,
            baseline_tool_key=BASELINE, mode=mode, run_id=RUNS[mode], commands=COUNTS[mode],
            original_summary=str(summary_path(mode).relative_to(ROOT)),
            original_summary_status=record['original_summary_status'], proofs=proofs,
            performance_measurement=False, completed_at=time.time()))
    print(json.dumps({'status': record['status'], 'receipt': str(receipt_path)}, indent=2))
    return 0 if success else 1


def main():
    require(Path(__file__).resolve(strict=True) == SCRIPT, 'wrong adapter source location')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['freeze', 'reuse', 'dependency', 'cache'])
    parser.add_argument('--attempt', type=int, default=1)
    args = parser.parse_args()
    if args.mode == 'freeze':
        freeze()
        return 0
    return run(args.mode, args.attempt)


if __name__ == '__main__':
    raise SystemExit(main())
