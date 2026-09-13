"""Recover a wholly unstarted observations-off protocol after admission timeout.

Root must review these recovery controls before execution. The original freeze
is retained unchanged. Each unchanged
harness/verifier acquires the shared lock itself; do not use run_locked.py.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import traceback

ROOT = Path('/Users/danluu/dev/rust-interp-perf-20260912')
B = ROOT / '.work/build-general-20260912'
INPUTS = B / 'local-export-adoption-inputs.json'
COMMANDS = B / 'local-export-adoption-commands.json'
FROZEN = B / 'local-export-adoption-frozen.json'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
RECOVERY = B / 'local-export-adoption-recovery-01'
RECOVERY_MANIFEST = RECOVERY / 'recovery.json'
BASELINE = 'eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d'
CANDIDATE = '14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75'
STD_KEY = 'bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'
VM_SHA = '03d401c1df926f99941cdd5325c2d58848d25e3b774ffa7f27db20b448c65a20'
WRAPPER_SHA = '56fec5a315571ba8308f5c2b637aff8b8be200ba84cde1ba7c606f61e47606d3'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path
            and stat.S_ISREG(path.lstat().st_mode), 'noncanonical/nonregular proof: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(data)
    return digest.hexdigest()


def read(path):
    sha(path)
    return json.loads(Path(path).read_text())


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def bind(proofs, path, expected=None):
    path = Path(path)
    digest = sha(path)
    require(expected is None or digest == expected, 'proof hash differs: ' + str(path))
    require(str(path) not in proofs or proofs[str(path)] == digest, 'conflicting proof: ' + str(path))
    proofs[str(path)] = digest


def verify(proofs):
    for path, digest in proofs.items():
        require(sha(path) == digest, 'frozen input changed: ' + path)


def recovery_proofs():
    manifest = read(RECOVERY_MANIFEST)
    require(manifest['kind'] == 'wholly-unstarted-admission-timeout'
            and manifest['admission_wait_seconds'] == 3600
            and manifest['workload_commands_changed'] is False
            and manifest['original_frozen_sha256'] == 'a54ddd20bb73748a1243ca48eceaf672f91c72ae55095f636aa371604dc0f54c'
            and manifest['original_stopped_controller_sha256'] == 'ad0668a39b0ba0b3219562264152a4370bdd907c8651baee264f4d98651551b7',
            'recovery must bind the exact wholly unstarted protocol')
    proofs = dict(manifest['files'])
    verify(proofs)
    require(sha(FROZEN) == manifest['original_frozen_sha256'], 'original frozen protocol differs')
    original = B / 'local-export-adoption-screen-controller.json'
    require(sha(original) == manifest['original_stopped_controller_sha256'], 'original stopped receipt differs')
    stopped, frozen = read(original), read(FROZEN)
    require(stopped['status'] == 'stopped' and stopped['calls'] == [] and stopped['admissions'] == []
            and stopped['phase'] == 'screen' and stopped['frozen_sha256'] == sha(FROZEN)
            and stopped['planned_commands'] == frozen['commands']['screen']
            and stopped['error'].rstrip().endswith('RuntimeError: admission lock unavailable; no workload launched'),
            'original attempt is not a wholly unstarted admission timeout')
    paths = [str(path) for case in frozen['cases'] for path in [
        ROOT / '.work/runs' / case['run_id'], ROOT / 'results' / case['run_id'],
        *map(Path, case['cache_workspaces'].values())]]
    require(len(paths) == len(set(paths)) == 32 and manifest['absent_workload_paths'] == paths,
            'recovery must cover every original raw/report/custom workspace')
    bind(proofs, RECOVERY_MANIFEST)
    return proofs


def qualification(proofs, filename):
    path = B / filename
    result = read(path)
    for name, digest in result['proofs'].items():
        bind(proofs, ROOT / name, digest)
    bind(proofs, path)
    require(result.get('tool_key', result.get('candidate_tool_key')) == CANDIDATE
            and result['baseline_tool_key'] == BASELINE, 'qualification tool identity differs')
    return result


def source_check(case, git):
    directory = ROOT / '.work/sources' / case['project']
    require(directory.resolve(strict=True) == directory and not directory.is_symlink(), 'source is not owned directory')
    marker = read(directory / '.rust-interp-owned.json')
    require(marker['owner'] == str(ROOT) and marker['revision'] == case['revision'], 'source ownership/pin differs')
    revision = subprocess.check_output([git, 'rev-parse', 'HEAD'], cwd=directory, text=True).strip()
    changed = subprocess.check_output([git, 'diff', '--name-only', 'HEAD'], cwd=directory, text=True).strip()
    require(revision == case['revision'] and not changed, 'source must be the clean pinned original')
    require(sha(directory / case['production_file']) == case['original_source_sha256'], 'original production/tests differ')
    return {str(p): sha(p) for p in [directory / '.rust-interp-owned.json', directory / 'Cargo.toml',
                                    directory / 'Cargo.lock', directory / case['production_file']]}


def fresh(case):
    for path in [ROOT / '.work/runs' / case['run_id'], ROOT / 'results' / case['run_id'],
                 *map(Path, case['cache_workspaces'].values())]:
        require(not os.path.lexists(path), 'planned namespace is not fresh: ' + str(path))


def clean_environment():
    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or name in [
                'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                'CARGO_BUILD_TARGET', 'RUSTC_BOOTSTRAP', 'PYTHONPATH']:
            env.pop(name)
    env['CARGO_TERM_COLOR'] = 'never'
    return env


def freeze():
    require(not os.path.lexists(FROZEN), 'adoption inputs already frozen')
    inputs, plan = read(INPUTS), read(COMMANDS)
    require(plan['baseline_tool_key'] == BASELINE and plan['candidate_tool_key'] == CANDIDATE,
            'wrong adoption keys')
    proofs = dict(inputs['files'])
    verify(proofs)
    bind(proofs, INPUTS)
    core = qualification(proofs, 'local-export-qualification.json')
    require(core['qualification_pass'] is True and core['frozen_baseline_runtime'] is True
            and core['tests'] == {p: dict(passed=408, failed=0, ignored=1) for p in ['debug', 'release']}
            and core['full_validation']['completed_commands'] == 23727
            and core['raw_validation_records'] == 23727, 'incomplete core qualification')
    for mode, count in [('reuse', 337), ('dependency', 293), ('cache', 98)]:
        receipt = qualification(proofs, 'local-export-' + mode + '-passed.json')
        require(receipt['status'] == 'passed' and receipt['mode'] == mode and receipt['commands'] == count,
                'reuse/dependency/cache qualification incomplete')
    audit = qualification(proofs, 'local-export-audit-inline-passed.json')
    require(audit['status'] == 'passed'
            and all(check['status'] == 'passed' for check in audit['checks'].values())
            and audit['checks']['audit-artifacts']['commands'] == 79
            and type(audit['optional_legacy_exporter_check']) is bool
            and audit['checks']['leaf-inline']['commands'] == 23 + int(audit['optional_legacy_exporter_check'])
            and audit['checks']['audit-parity']['commands'] == 8
            and audit['checks']['audit-parity']['retained_artifact_pairs'] == 8
            and audit['completed_commands'] == sum(c['commands'] for c in audit['checks'].values()),
            'audit/inline qualification incomplete')
    failure_path = B / 'local-export-panic-coverage-failure.json'
    failure_sha = '9a957ecd4af45cd659c288e13d16f73ad6618ccebc38e1921bbc48789c23f525'
    bind(proofs, failure_path, failure_sha)
    failure = read(failure_path)
    require(failure['status'] == 'failed structural coverage' and failure['coverage_pass'] is False
            and failure['qualification_pass'] is False and failure['completed_commands'] == 90
            and failure['candidate_tool_key'] == CANDIDATE and failure['baseline_tool_key'] == BASELINE,
            'original failed panic coverage must remain preserved')
    for name, digest in failure['proofs'].items():
        bind(proofs, ROOT / name, digest)
    require(not os.path.lexists(B / 'local-export-panic-passed.json'),
            'original failed panic run must not acquire a passing receipt')
    panic = qualification(proofs, 'local-export-panic-late-passed.json')
    require(panic['status'] == 'passed' and panic['completed_commands'] == 90
            and panic['actual_mir_and_argument_directed_store_before_trap'] is True
            and panic['unary_not_64_store_8_verified'] is True
            and panic['stored_value_relation'] == 'bitwise-not-u64(second_argument)'
            and panic['expected_decimal_outputs'] == {
                '0': '18446744073709551615', '1': '18446744073709551614',
                '9223372036854775808': '9223372036854775807', '18446744073709551615': '0'}
            and panic['original_coverage_failure'] == dict(path=str(failure_path), sha256=failure_sha)
            and panic['bytecode_and_error_parity'] is True, 'actual late-panic complement-store coverage incomplete')
    source = read(B / 'local-export-prebuild-source/source.json')
    require(source['tool_key'] == CANDIDATE and len(source['files']) == 146, 'wrong frozen source')
    for name, row in source['files'].items():
        bind(proofs, ROOT / name, row['sha256'])
    for name, digest in source['common_files'].items():
        bind(proofs, ROOT / name, digest)
    bundles = {}
    for arm, filename, key in [('baseline', 'owned-analysis-tools.json', BASELINE),
                               ('candidate', 'local-export-tools.json', CANDIDATE)]:
        bundle = read(B / filename)
        require(bundle['tool_key'] == key and bundle['binaries']['rust-interp-vm'] == VM_SHA
                and bundle['binaries']['rust-interp-rustc-wrapper'] == WRAPPER_SHA, 'selected bundle differs')
        bind(proofs, B / filename)
        for name, digest in bundle['binaries'].items():
            bind(proofs, Path(bundle['directory']) / name, digest)
        bind(proofs, Path(bundle['directory']) / 'ready.json')
        bundles[arm] = bundle
    # The copied ready file has owner/stamps specific to this workspace. Keep
    # the original copy receipt's source_ready_sha256 as original provenance.
    std_path = B / 'std-mir-diagnostic-local-ready.json'
    std = read(std_path)
    bind(proofs, std_path)
    for field in ['copy_receipt', 'local_binding_script']:
        bind(proofs, std[field]['path'], std[field]['sha256'])
    copied = read(std['copy_receipt']['path'])
    require(all(std[k] == copied[k] for k in ['source', 'owner', 'artifacts', 'source_ready_sha256']),
            'std-MIR original provenance differs')
    ready = ROOT / '.work/std-mir' / STD_KEY / 'ready.json'
    require(std['owner'] == str(ROOT) and std['local_ready_path'] == str(ready)
            and len(std['artifacts']) == 26, 'wrong owned std-MIR identity')
    bind(proofs, ready, std['local_ready_sha256'])
    for name, row in std['artifacts'].items():
        path = ready.parent / name
        require(path.stat().st_size == row['bytes'], 'std-MIR size differs')
        bind(proofs, path, row['sha256'])
    python = str(Path(sys.executable).resolve(strict=True))
    executables = {'python': python}
    for name in ['git', 'cargo', 'rustc']:
        executable = shutil.which(name)
        require(executable is not None, 'missing executable: ' + name)
        executables[name] = str(Path(executable).resolve(strict=True))
    for executable in set(executables.values()):
        bind(proofs, executable)
    sources = {}
    for case in plan['cases']:
        fresh(case)
        sources.update(source_check(case, executables['git']))
    proofs.update(sources)
    commands = {phase: [dict(item, command=[python, *item['command'][1:]]) for item in plan[phase]]
                for phase in ['screen', 'confirmation']}
    verify(proofs)
    write_new(FROZEN, dict(schema_version=1, status='frozen; no adoption workload executed',
              frozen_at=time.time(), cwd=str(ROOT), baseline_tool_key=BASELINE, candidate_tool_key=CANDIDATE,
              bundles=bundles, commands=commands, cases=plan['cases'], proofs=proofs,
              executables=executables, compiler_observations=False, launcher_build_metrics=True,
              source_proofs=sources, std_mir_key=STD_KEY))


def run(phase):
    recovery_bindings = recovery_proofs()
    if phase == 'screen':
        for path in read(RECOVERY_MANIFEST)['absent_workload_paths']:
            require(not os.path.lexists(path), 'wholly unstarted recovery namespace now exists: ' + path)
    frozen = read(FROZEN)
    verify(frozen['proofs'])
    require(str(Path(sys.executable).resolve(strict=True)) == frozen['executables']['python'], 'Python differs')
    for name in ['git', 'cargo', 'rustc']:
        require(str(Path(shutil.which(name)).resolve(strict=True)) == frozen['executables'][name],
                'PATH selects a different executable: ' + name)
    require((ROOT / '.work/benchmark.lock').resolve(strict=True) == LOCK, 'shared-lock alias differs')
    if phase == 'confirmation':
        screen = read(RECOVERY / 'screen-assessment.json')
        require(screen['screen_pass'] is True and screen['all_planned_runs_included'] is True,
                'complete passing screen required')
        verify(screen['proofs'])
    receipt = RECOVERY / (phase + '-controller.json')
    require(not receipt.exists(), 'controller already started; preserve it, do not restart')
    state = dict(owner='build-general-20260912', phase=phase, controller_pid=os.getpid(),
                 controller_ppid=os.getppid(), cwd=str(ROOT), started_at=time.time(),
                 frozen_sha256=sha(FROZEN), planned_commands=frozen['commands'][phase],
                 recovery_manifest_sha256=sha(RECOVERY_MANIFEST), recovery_proofs=recovery_bindings,
                 admission_wait_seconds=3600,
                 calls=[], admissions=[], status='running')
    write_new(receipt, state)

    def save():
        receipt.write_text(json.dumps(state, indent=2, allow_nan=False) + '\n')

    try:
        for item in state['planned_commands']:
            label, command = item['label'], item['command']
            admission = None
            if item['kind'] == 'history':
                case = next(c for c in frozen['cases'] if c['run_id'] == label)
                admission = LOCK.open('r+b')
                wait_started, deadline = time.time(), time.monotonic() + 3600
                try:
                    while True:
                        try:
                            fcntl.flock(admission, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            break
                        except BlockingIOError:
                            if time.monotonic() >= deadline:
                                raise RuntimeError('admission lock unavailable; no workload launched')
                            time.sleep(1)
                    held, named = os.fstat(admission.fileno()), os.stat(LOCK)
                    require(stat.S_ISREG(held.st_mode) and (held.st_dev, held.st_ino) == (named.st_dev, named.st_ino),
                            'shared-lock identity differs')
                    verify(frozen['proofs'])
                    verify(recovery_bindings)
                    fresh(case)
                    source_check(case, frozen['executables']['git'])
                    free = shutil.disk_usage(ROOT).free
                    state['admissions'].append(dict(label=label, minimum_gib=case['minimum_admission_gib'],
                        free_bytes=free, lock_wait_started=wait_started, time=time.time(),
                        lock_identity=[held.st_dev, held.st_ino]))
                    save()
                    require(free >= case['minimum_admission_gib'] * 2**30, 'fixed capacity admission failed')
                except BaseException:
                    admission.close()
                    raise
            log_path = RECOVERY / (label + '-controller.log')
            try:
                with log_path.open('x') as log:
                    started = time.time()
                    try:
                        child = subprocess.Popen(command, cwd=ROOT, env=clean_environment(),
                                  stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                    finally:
                        # The child independently acquires the same shared lock.
                        # Release this admission lock before waiting for output.
                        if admission is not None:
                            admission.close()
                            state['admissions'][-1]['lock_released_at'] = time.time()
                    row = dict(label=label, command=command, kind=item['kind'], child_pid=child.pid,
                               started_at=started, status='running')
                    state['calls'].append(row)
                    save()
                    print('START', label, child.pid, flush=True)
                    try:
                        code = child.wait()
                    except BaseException:
                        child.wait()  # wait for this exact owned child/restoration; never signal
                        raise
                    row.update(returncode=code, finished_at=time.time(),
                               status='complete' if code == 0 else 'failed', log_sha256=sha(log_path))
                    save()
                    print('END', label, code, flush=True)
                    require(code == 0, 'history/verifier failed: ' + label)
            finally:
                if admission is not None:
                    admission.close()
        verify(frozen['proofs'])
        verify(recovery_bindings)
        state.update(status='complete', finished_at=time.time())
        save()
    except BaseException:
        state.update(status='stopped', error=traceback.format_exc(), finished_at=time.time())
        save()
        raise


def main():
    require(__debug__, 'do not use Python -O')
    require(Path.cwd() == ROOT, 'run from isolated root worktree')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['screen', 'confirmation'])
    args = parser.parse_args()
    run(args.mode)


if __name__ == '__main__':
    main()
