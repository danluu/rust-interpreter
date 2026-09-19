"""Authenticate the actual pure-control history before loading new readers."""
import ast
from pathlib import Path
import re

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
CATALOG = ROOT/'experiments/completed-proof-snapshot-catalog-02/catalog.py'
PLAN = ROOT/'experiments/hir-options-hash-driver-stage-03/plan_reference.py'
TESTS = [CATALOG.with_name('test_catalog.py'), CATALOG.with_name('test_failed_catalog.py'),
         PLAN.with_name('test_plan_reference.py')]
SOURCE = ROOT/'experiments/hash-continuation-controls-01'
WORK = ROOT/'.work/hash-continuation-controls-01'
AUDIT = ROOT/'.work/hash-continuation-controls-independent-verification-01.json'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def qualify(*, read_json, read_bytes, sha, file_record):
    inputs = read_json(SOURCE/'inputs.json')
    launch = read_json(SOURCE/'launch.json')
    terminal = read_json(WORK/'receipt.json')
    result = read_json(WORK/'result.json')
    child = read_json(WORK/'command/receipt.json')
    audit = read_json(AUDIT)
    for path in [CATALOG, PLAN, *TESTS]:
        require(str(path) in inputs['files'], 'tested helper or test is missing')
    for name, row in inputs['files'].items():
        current = file_record(name)
        require(current['sha256'] == row['sha256'] and [current['identity'][k] for k in
                ['dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink']] == row['stamp'],
                'complete actual control input identity and bytes')
    for name, target in inputs['routes'].items():
        require(str(Path(name).resolve(strict=True)) == target and target in inputs['files'],
                'actual control executable route changed')
    names = []
    for test in TESTS:
        for cls in ast.parse(read_bytes(test), filename=str(test)).body:
            if isinstance(cls, ast.ClassDef):
                names.extend(test.stem+'.'+cls.name+'.'+method.name for method in cls.body
                             if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'))
    names = sorted(names)
    require(len(names) == len(set(names)) == 70 and names == inputs['expected_names']
            == result['expected_names'] == sorted(audit['exact_names']), 'complete 70-control identities')
    require(terminal['status'] == result['status'] == 'passed' and audit['status'] == 'verified'
            and terminal['controls_passed'] == result['tests_run'] == audit['controls'] == launch['controls'] == 70
            and terminal['inputs_sha256'] == launch['inputs_sha256'] == sha(SOURCE/'inputs.json')
            and terminal['result_sha256'] == audit['result_sha256'] == sha(WORK/'result.json')
            and audit['receipt_sha256'] == sha(WORK/'receipt.json'), 'actual audited control completion')
    require(all(type(result[k]) is int and result[k] == 0 for k in
                ['failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes',
                 'child_processes', 'compiler_calls'])
            and all(type(terminal[k]) is int and terminal[k] == 0 for k in
                    ['compiler_calls', 'provider_probes', 'B3_compositions']), 'no omitted tests or workloads')
    require(child['status'] == 'finished' and child['returncode'] == 0
            and child['command'] == inputs['command'] and child['environment'] == inputs['environment']
            and child['cwd'] == str(CATALOG.parent) and child['supervisor_pid'] == terminal['pid']
            and child['parent_pid'] == terminal['parent_pid']
            and terminal['started_at'] <= terminal['admitted_at'] <= child['started_at']
            <= child['finished_at'] <= terminal['finished_at']
            and terminal['commands'] == [dict(path=str(WORK/'command/receipt.json'), pid=child['pid'],
                                              sha256=sha(WORK/'command/receipt.json'))],
            'actual single control child association')
    for stream in ['stdout', 'stderr']:
        require(sha(WORK/'command'/stream) == child[stream+'_sha256'] == audit['raw_sha256'][stream],
                'actual control raw changed')
    stderr = read_bytes(WORK/'command/stderr').decode('utf-8')
    actual = re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$', stderr, re.M)
    require(not read_bytes(WORK/'command/stdout') and sorted(actual) == names
            and re.search(r'^Ran 70 tests in [0-9.]+s\n\nOK\n$', stderr, re.M), 'all actual raw test outcomes')
    return dict(controls=70, audit=dict(path=str(AUDIT), sha256=sha(AUDIT)),
                inputs=dict(path=str(SOURCE/'inputs.json'), sha256=sha(SOURCE/'inputs.json')),
                receipt=dict(path=str(WORK/'receipt.json'), sha256=sha(WORK/'receipt.json')),
                result=dict(path=str(WORK/'result.json'), sha256=sha(WORK/'result.json')),
                sources={str(p): sha(p) for p in [CATALOG, PLAN, *TESTS]})
