"""Read the five closed pure-control histories and two failed read-only discoveries."""
import hashlib
import json
from pathlib import Path
import re

A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stages():
    rows = []
    for number, count, source in [('02', 63, '03'), ('03', 82, '04'), ('04', 93, '05'), ('05', 97, '06')]:
        failed = number == '04'
        rows.append(dict(packet=str(A/f'experiments/hir-options-hash-beta-controls-{number}'),
            work=str(A/f'.work/hir-options-hash-beta-controls-{number}'),
            outer=str(A/f'.work/experiments/hir-options-hash-beta-controls-supervisor-{number}'),
            launcher=str(A/f'.work/beta-controls-launch-execution-{number}'),
            source=str(A/f'experiments/hir-options-hash-beta-composition-{source}'),
            audit=str(A/f'.work/beta-controls-{"failure-" if failed else ""}independent-verification-{number}.json'),
            tests=count, errors=int(failed), failed=failed))
    rows.append(dict(packet=str(A/'experiments/hir-options-hash-sysroot-inventory-controls-01'),
        work=str(A/'.work/hir-options-hash-sysroot-inventory-controls-01'),
        outer=str(A/'.work/experiments/hir-options-hash-sysroot-inventory-controls-supervisor-01'),
        launcher=str(A/'.work/sysroot-inventory-controls-launch-execution-01'),
        source=str(A/'experiments/hir-options-hash-beta-composition-07'),
        audit=str(A/'.work/sysroot-inventory-controls-independent-verification-01.json'),
        tests=6, errors=0, failed=False))
    return rows


def validate(row):
    packet, work, outer, launcher = [Path(row[k]) for k in ['packet', 'work', 'outer', 'launcher']]
    f, launch = read(packet/'inputs.json'), read(packet/'launch.json')
    r, t, child = [read(work/name) for name in ['receipt.json', 'result.json', 'command/receipt.json']]
    o, l, audit = read(outer/'status.json'), read(launcher/'record.json'), read(row['audit'])
    code = int(row['failed'])
    assert l['status'] == 'finished' and l['returncode'] == 0
    assert l['command'] == launch['command'] and l['environment'] == launch['environment'] and l['cwd'] == str(A)
    assert l['launch_sha256'] == sha(packet/'launch.json')
    for stream in ['stdout', 'stderr']:
        assert l[stream+'_sha256'] == sha(launcher/stream)
    handoff = read(launcher/'stdout')
    assert handoff['supervisor_pid'] == o['supervisor_pid'] and handoff['directory'] == str(outer)
    assert o['status'] == 'finished' and o['returncode'] == code and o['command'] == launch['command'][6:]
    assert o['cwd'] == str(A) and o['plan_sha256'] == sha(outer/'plan.json') and o['log_sha256'] == sha(outer/'command.log')
    assert r['status'] == ('failed' if row['failed'] else 'passed')
    assert r['pid'] == o['child_pid'] and r['parent_pid'] == o['supervisor_pid']
    assert r['inputs_sha256'] == launch['inputs_sha256'] == sha(packet/'inputs.json')
    assert r['commands'] == [dict(path=str(work/'command/receipt.json'), pid=child['pid'], sha256=sha(work/'command/receipt.json'))]
    assert child['status'] == 'finished' and child['returncode'] == code
    assert child['command'] == f['command'] and child['cwd'] == row['source'] and child['environment'] == f['environment']
    assert child['supervisor_pid'] == r['pid'] and child['parent_pid'] == o['supervisor_pid']
    identity = child['identity']
    assert identity['ps_returncode'] == identity['cwd_returncode'] == 0
    assert list(map(int, identity['ps'].split()[:3])) == [child['pid'], r['pid'], child['pid']]
    assert identity['ps'].endswith(' '.join(child['command'])) and 'n'+child['cwd']+'\n' in identity['cwd']
    assert o['child_started_at'] <= r['started_at'] <= r['admitted_at'] <= child['started_at'] <= child['finished_at'] <= r['finished_at'] <= o['finished_at']
    for stream in ['stdout', 'stderr']:
        assert child[stream+'_sha256'] == sha(work/'command'/stream)
    assert not (work/'command/stdout').read_bytes()
    raw = (work/'command/stderr').read_text()
    observed = re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. (ok|ERROR)$', raw, re.M)
    assert sorted(name for name, _ in observed) == f['expected_names'] == t['expected_names']
    assert len(observed) == row['tests'] and sum(status == 'ERROR' for _, status in observed) == row['errors']
    assert t['tests_run'] == row['tests'] and t['errors'] == row['errors']
    assert all(t[k] == 0 for k in ['failures', 'skipped', 'expected_failures', 'unexpected_successes', 'child_processes', 'compiler_calls'])
    assert all(r[k] == 0 for k in ['compiler_calls', 'provider_probes', 'B3_compositions'])
    assert not list((work/'tmp').iterdir())
    assert audit['receipt_sha256'] == sha(work/'receipt.json') and audit['controls'] == row['tests']
    assert audit['status'] == ('verified-retained-failure' if row['failed'] else 'verified')
    if row['failed']:
        assert t['status'] == 'failed' and 'error' in r
        assert audit['passed'] == 92 and audit['errors'] == 1 and audit['result_sha256'] == sha(work/'result.json')
        assert re.search(r'^Ran 93 tests in [0-9.]+s\n\nFAILED \(errors=1\)$', raw, re.M)
        assert 'ValueError: require one compiler option: --crate-type' in raw
    else:
        assert t['status'] == 'passed' and r['controls_passed'] == row['tests'] and r['result_sha256'] == sha(work/'result.json')
        assert re.search(r'^Ran '+str(row['tests'])+r' tests in [0-9.]+s\n\nOK\n$', raw, re.M)
    return dict(tests=row['tests'], passed=row['tests']-row['errors'], errors=row['errors'],
        terminal_sha256=sha(work/'receipt.json'), result_sha256=sha(work/'result.json'),
        audit_sha256=sha(row['audit']), helper_pid=r['pid'], test_pid=child['pid'], supervisor_pid=o['supervisor_pid'])


def discovery(number):
    p = A/f'.work/beta-composition-discovery-failure-{number}.json'
    d = read(p)
    assert d['status'] == 'failed-read-only-discovery' and d['exit_code'] == 1 and d['compiler_calls'] == 0
    for stream in ['stdout', 'stderr']:
        assert d[stream+'_sha256'] == sha(A/f'.work/beta-composition-discovery-{number}.{stream}')
    assert not (A/f'.work/beta-composition-discovery-{number}.stdout').read_bytes()
    stderr = (A/f'.work/beta-composition-discovery-{number}.stderr').read_text()
    if number == '04':
        assert d['B3_composition'] is False and len(d['unexpected_output_command_forms']) == 49
        assert 'ValueError: one ordinary extra-filename required' in stderr
    else:
        assert d['B3_compositions'] == 0 and d['proposal_created'] is False and 'SDK link escapes frozen SDK' in stderr
    return dict(number=number, failure_sha256=sha(p), exit_code=1,
        limitation='Read-only tool execution with observed exit and raw streams; no supervised process-history receipt.')


def validate_all():
    return dict(controls=[validate(row) for row in stages()], discoveries=[discovery(n) for n in ['04', '06']],
        actual_control_processes=5, actual_compiler_calls=0, actual_B3_compositions=0,
        qualification='Pure controls and saved raw/source parsing only; no B3 or native qualification.')
