import hashlib
import json
from pathlib import Path
import re

root = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
source = root/'experiments/hir-options-hash-prerequisite-controls-01'
work = root/'.work/hir-options-hash-prerequisite-controls-01'
outer = root/'.work/experiments/hir-options-hash-prerequisite-controls-supervisor-01'
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    return json.loads(Path(path).read_bytes())

freeze = read(source/'inputs.json')
launch = read(source/'launch.json')
terminal = read(work/'receipt.json')
child = read(work/'command/receipt.json')
status = read(outer/'status.json')
plan = read(outer/'plan.json')
result = read(work/'result.json')
assert sha(source/'inputs.json') == launch['inputs_sha256'] == terminal['inputs_sha256'] == '931aa31b59e0945d100a3b2c15eefe36fb1794cad77faca718e04c9a075e0aee'
for name, row in freeze['files'].items():
    path = Path(name)
    before = path.lstat()
    assert path.resolve(strict=True) == path and path.is_file() and sha(path) == row['sha256']
    after = path.lstat()
    keys = ['dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink']
    assert [getattr(before, 'st_'+k) for k in keys] == row['stamp'] == [getattr(after, 'st_'+k) for k in keys]
for name, resolved in freeze['routes'].items():
    assert str(Path(name).resolve(strict=True)) == resolved
assert status['status'] == 'finished' and status['returncode'] == 0
assert status['owner'] == plan['owner'] == status['cwd'] == str(root)
assert status['command'] == plan['command'] == launch['command'][launch['command'].index('--')+1:]
assert sha(outer/'plan.json') == status['plan_sha256']
assert plan['supervisor_sha256'] == sha(root/'scripts/supervise_experiment.py')
assert terminal['status'] == 'passed' and terminal['controls_passed'] == result['tests_run'] == 9
assert terminal['pid'] == status['child_pid'] == child['supervisor_pid']
assert terminal['parent_pid'] == status['supervisor_pid'] == child['parent_pid']
assert terminal['commands'] == [dict(path=str(work/'command/receipt.json'), sha256=sha(work/'command/receipt.json'), pid=child['pid'])]
assert child['status'] == 'finished' and child['returncode'] == 0
assert child['command'] == freeze['command'] and child['environment'] == freeze['environment']
assert child['cwd'] == str(root/'experiments/hir-options-hash-driver-stage')
assert status['started_at'] <= status['child_started_at'] <= terminal['started_at'] <= terminal['admitted_at'] <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'] <= status['finished_at']
identity = child['identity']
fields = identity['ps'].split(None, 9)
assert identity['ps_returncode'] == identity['cwd_returncode'] == 0
assert fields[:3] == list(map(str, [child['pid'], terminal['pid'], child['pid']]))
assert fields[8] == '??' and fields[9] == ' '.join(child['command'])
assert identity['cwd'].splitlines() == [f'p{child["pid"]}', 'fcwd', 'n'+child['cwd']]
for name in ['stdout', 'stderr']:
    assert sha(work/'command'/name) == child[name+'_sha256']
assert sha(work/'result.json') == terminal['result_sha256']
assert sha(outer/'command.log') == status['log_sha256']
assert result['status'] == 'passed' and result['expected_names'] == freeze['expected_names']
assert all(result[k] == 0 for k in ['failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes', 'child_processes', 'compiler_calls'])
stderr = (work/'command/stderr').read_text()
names = re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$', stderr, re.M)
assert sorted(names) == freeze['expected_names'] and re.search(r'^Ran 9 tests in [0-9.]+s\n\nOK\n$', stderr, re.M)
assert not (work/'command/stdout').read_bytes() and not list((work/'tmp').iterdir())
proof = dict(status='verified', tests=9, input_files=len(freeze['files']), freeze_sha256=sha(source/'inputs.json'),
    terminal_sha256=sha(work/'receipt.json'), child_receipt_sha256=sha(work/'command/receipt.json'),
    supervisor_status_sha256=sha(outer/'status.json'), result_sha256=sha(work/'result.json'),
    actual_compiler_calls=0, actual_provider_probes=0, actual_signals=0,
    read_only_auditor_correction='Initial inline verifier used argv[5:] including separator; corrected from actual supervisor CLI/source to argv after --. No workload repeated.',
    interpretation='Nine in-memory predecessor command-chain controls only; native raw readback and complete hash-driver stage remain unqualified.')
destination = root/'.work/root-prerequisite-controls-actual-verification-01.json'
with destination.open('x') as stream:
    json.dump(proof, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps(dict(status='verified', audit_sha256=sha(destination), tests=9)))
