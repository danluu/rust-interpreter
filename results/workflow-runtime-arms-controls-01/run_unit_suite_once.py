"""One ordinary isolated unit-suite invocation; no benchmark/provider imports."""
from pathlib import Path
import ast, hashlib, json, os, subprocess, time

HERE = Path(__file__).resolve().parent
SOURCE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/workflow-runtime-arms-01')
PYTHON = '/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14'
EXPECTED = {
    'workflow_runtime_arms.py': '57c7b2e1d5127a90d39599a9910bbac18c51c679a57656eff16556c621758822',
    'test_workflow_runtime_arms.py': 'b639c6b15c3a18fab23b940f123bc23e9229bce70c05a993e0d5e20090a7f57e',
}
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value):
    with (HERE/name).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True); f.write('\n')

assert sha(Path(PYTHON)) == '87d4df53fd91304be5bac391fb204643c36b7df2023c04a0953bcbc7d4fdf634'
assert not (HERE/'record.json').exists()
originals = json.loads((SOURCE/'base-sources.json').read_text())['sources']
for path, row in originals.items():
    assert sha(Path(path)) == row['sha256']
for name, expected in EXPECTED.items():
    path = SOURCE/'proposed'/name
    assert sha(path) == expected
    with (HERE/name).open('xb') as output:
        output.write(path.read_bytes())
    assert sha(HERE/name) == expected
suite = ast.parse((SOURCE/'proposed/test_workflow_runtime_arms.py').read_text())
methods = sorted(n.name for n in ast.walk(suite) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_'))
assert len(methods) == 35
command = [PYTHON, '-I', '-B', '-m', 'unittest', 'discover', '-s', str(SOURCE/'proposed'), '-p', 'test_workflow_runtime_arms.py', '-v']
environment = {'PATH':'/usr/bin:/bin', 'LANG':'C', 'LC_ALL':'C'}
record = dict(status='starting', command=command, cwd=str(SOURCE/'proposed'), environment=environment,
              parent_pid=os.getpid(), parent_parent_pid=os.getppid(), started_at=time.time(),
              source_sha256=EXPECTED, runner_sha256=sha(Path(__file__)), test_methods=methods)
with (HERE/'stdout.txt').open('xb') as stdout, (HERE/'stderr.txt').open('xb') as stderr:
    child = subprocess.Popen(command, cwd=record['cwd'], env=environment, stdout=stdout, stderr=stderr)
    record.update(pid=child.pid, spawned_at=time.time())
    write('started.json', record)
    try:
        record['returncode'] = child.wait(timeout=60)
    except subprocess.TimeoutExpired:
        record.update(status='wait-timeout-unclosed', observed_at=time.time())
        write('record.json', record)
        raise
record.update(status='closed', finished_at=time.time(), stdout_sha256=sha(HERE/'stdout.txt'), stderr_sha256=sha(HERE/'stderr.txt'))
write('record.json', record)
assert record['returncode'] == 0
assert (HERE/'stdout.txt').stat().st_size <= 262144 and (HERE/'stderr.txt').stat().st_size <= 262144
text = (HERE/'stderr.txt').read_text()
assert 'Ran 35 tests in ' in text and text.rstrip().endswith('OK')
assert all(text.count(name+' (') == 1 for name in methods)
for name, expected in EXPECTED.items():
    assert sha(SOURCE/'proposed'/name) == sha(HERE/name) == expected
for path, row in originals.items():
    assert sha(Path(path)) == row['sha256']
write('result.json', dict(status='passed', tests_run=35, tests_passed=35, record_sha256=sha(HERE/'record.json'),
    source_sha256=EXPECTED, originals_unchanged=originals, target='pure in-memory helper fixture suite',
    provider_or_benchmark_integration=False, stdout_sha256=record['stdout_sha256'], stderr_sha256=record['stderr_sha256']))
print(json.dumps(dict(status='passed', tests=35, pid=child.pid, record_sha256=sha(HERE/'record.json'), result_sha256=sha(HERE/'result.json'))))
