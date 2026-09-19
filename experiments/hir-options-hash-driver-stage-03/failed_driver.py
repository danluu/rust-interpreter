"""Read the exact failed first driver attempt without qualifying its workload."""
import hashlib
from pathlib import Path

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE = ROOT/'experiments/hir-options-hash-driver-stage-02'
WORK = ROOT/'.work/hir-options-hash-driver-01'
OUTER = ROOT/'.work/experiments/hir-options-hash-driver-supervisor-01'
DISPATCH = ROOT/'.work/hash-driver-launch-execution-01'
ARTIFACTS = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/hash-driver-01')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def validate(owner, terminal, audit, *, read_json, read_bytes, sha, check_absent, directory_record):
    require(owner['role'] == 'failed-hash-driver-01' and owner['source'] == str(SOURCE)
            and owner['evidence'] == str(WORK), 'exact failed driver owner')
    require(terminal == read_json(WORK/'receipt.json') and audit == read_json(owner['audit']['path'])
            and sha(owner['audit']['path']) == owner['audit']['sha256'], 'original failed owner/audit changed')
    require(terminal['status'] == 'failed' and audit['status'] == 'verified-retained-failure'
            and audit['receipt_sha256'] == sha(WORK/'receipt.json')
            and terminal['error'] == "AssertionError('unexpected compiler-stage return code')",
            'closed failed driver compiler history required')
    require(all(terminal[k] is False for k in ['hash_driver_qualified', 'application_qualified',
                                              'performance_measurement', 'runtime_installation']),
            'failed owner cannot qualify a driver or application')
    require(audit['source'] == str(SOURCE) and audit['evidence'] == str(WORK)
            and audit['owner_status'] == 'failed' and audit['actual_children'] == audit['actual_compiler_children'] == 1
            and audit['actual_driver_processes'] == audit['qualified_hash_driver_processes'] == 0
            and audit['hash_driver_qualified'] is audit['application_qualified'] is audit['performance_measurement'] is False
            and audit['complete_failed_raw_history'] is audit['full_snapshot_selection']
            is audit['retained_snapshot_owner_only'] is audit['compiler_failure_preserved'] is True,
            'actual audited failure scope')
    plan = read_json(SOURCE/'plan.json')
    launch = read_json(SOURCE/'launch.json')
    outer = read_json(OUTER/'status.json')
    dispatch = read_json(DISPATCH/'record.json')
    child = read_json(WORK/'compile/receipt.json')
    wanted = plan['children'][0]
    require(len(plan['children']) == 3 and child['status'] == 'failed' and child['returncode'] == 1
            and child['expected'] == [0] and child['error'] == terminal['error']
            and child['command'] == wanted['argv'] and child['cwd'] == wanted['cwd']
            and child['environment'] == wanted['environment']
            and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
            and terminal['started_at'] <= terminal['admitted_at'] <= child['started_at']
            <= child['finished_at'] <= terminal['finished_at'], 'only first failed compiler child')
    stderr = read_bytes(WORK/'compile/stderr')
    stdout = read_bytes(WORK/'compile/stdout')
    require(stdout == b'' and hashlib.sha256(stdout).hexdigest() == child['stdout_sha256']
            and hashlib.sha256(stderr).hexdigest() == child['stderr_sha256']
            == '789be46bc0f46a221859863de9fa28103a928ba8c4d5b51bd83e101dde06698f',
            'exact retained E0277 diagnostic')
    require(outer['status'] == 'finished' and outer['returncode'] == 1
            and outer['child_pid'] == terminal['pid'] and outer['supervisor_pid'] == terminal['parent_pid']
            and outer['command'] == launch['command'][6:] and outer['cwd'] == str(ROOT)
            and outer['plan_sha256'] == sha(OUTER/'plan.json')
            and outer['log_sha256'] == sha(OUTER/'command.log')
            and outer['child_started_at'] <= terminal['started_at']
            and terminal['finished_at'] <= outer['finished_at'], 'failed supervisor closure')
    require(dispatch['status'] == 'terminal-observed' and dispatch['returncode'] == 1
            and dispatch['launcher_returncode'] == 0 and dispatch['outer_sha256'] == sha(OUTER/'status.json')
            and dispatch['supervisor_pid'] == outer['supervisor_pid'] and dispatch['controller_pid'] == terminal['pid']
            and dispatch['command'] == launch['command'] and dispatch['cwd'] == str(ROOT)
            and dispatch['environment'] == launch['environment']
            and dispatch['launch_sha256'] == sha(SOURCE/'launch.json')
            and sha(dispatch['launcher_source_path']) == dispatch['launcher_source_sha256']
            and dispatch['started_at'] <= dispatch['launcher_finished_at'] <= dispatch['finished_at']
            and outer['finished_at'] <= dispatch['terminal_observed_at'] <= dispatch['finished_at'],
            'closed original launcher retains failure')
    for stream in ['stdout', 'stderr']:
        require(sha(DISPATCH/stream) == dispatch[stream+'_sha256'], 'launcher raw differs')
    handoff = read_json(DISPATCH/'stdout')
    require(handoff == dispatch['supervisor_handoff'] and handoff['directory'] == str(OUTER)
            and handoff['supervisor_pid'] == outer['supervisor_pid'], 'original supervisor handoff')
    require(launch['inputs_sha256'] == terminal['inputs_sha256'] == sha(SOURCE/'inputs.json')
            and launch['plan_sha256'] == sha(SOURCE/'plan.json')
            and launch['snapshot_plan_sha256'] == terminal['snapshot_plan_sha256']
            == sha(SOURCE/'snapshot-plan.json'), 'failed source packet binding')
    require(audit['compile_receipt_sha256'] == sha(WORK/'compile/receipt.json')
            and audit['closure']['outer_sha256'] == sha(OUTER/'status.json')
            and audit['closure']['launcher_record_sha256'] == sha(DISPATCH/'record.json')
            and audit['closure']['actual_outer_closed'] is audit['closure']['actual_wrapper_closed'] is True,
            'actual independent raw and closure references')
    absent = [WORK/'result.json', WORK/'serial', WORK/'parallel', WORK/'linker-command.json',
              WORK/'driver-loader-closure.json', ARTIFACTS/'hash-control-driver']
    require(audit['absent_outputs'] == list(map(str, absent)), 'all skipped outputs remain explicit')
    for path in absent:
        require(check_absent(path) is True, 'a failed-owner skipped output appeared')
    require(sha(ARTIFACTS/'fixture.rs') == audit['artifacts']['fixture.rs']['sha256'],
            'retained failed-owner fixture bytes changed')
    for directory, names in [(WORK, ['receipt.json', 'compile', 'source-snapshots', 'source-snapshots.json', 'snapshot-plan.json']),
                              (WORK/'compile', ['receipt.json', 'stdout', 'stderr']),
                              (ARTIFACTS, ['fixture.rs', 'serial', 'parallel', 'tmp']),
                              *[(ARTIFACTS/name, []) for name in ['serial', 'parallel', 'tmp']]]:
        require(directory_record(directory)['children'] == sorted(names), 'failed-owner exact directory membership')
    return True
