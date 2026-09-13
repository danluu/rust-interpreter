from pathlib import Path
import json, os, re, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, write_json as write, require_space

with (ROOT / '.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock, 45)
    require_space(ROOT, 8)
    work = ROOT / '.work/checked-addresses-python-tests-01'
    work.mkdir(exist_ok=False)
    frozen = {str(p.relative_to(ROOT)): sha(p)
              for base in ['scripts', 'tests']
              for p in (ROOT / base).rglob('*.py')}
    for p in (ROOT / 'benchmarks/experiments/checked-addresses').rglob('*'):
        if p.is_file(): frozen[str(p.relative_to(ROOT))] = sha(p)
    for name in ['operation-map/maps.py', 'composed-development/qualify_cache.py', 'parallel-suites/compare.py', 'selected-native-sampling/qualify.py']:
        path = ROOT / 'benchmarks/experiments' / name
        frozen[str(path.relative_to(ROOT))] = sha(path)
    frozen[str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
    write(work / 'inputs.json', frozen)
    records = []
    for label, folder, expected in [('existing', 'tests', 117),
            ('screen', 'benchmarks/experiments/checked-addresses', 14)]:
        child, out, err = capture([sys.executable, '-m', 'unittest', 'discover',
            '-s', folder, '-p', 'test_*.py'], cwd=ROOT,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work / 'active.json', receipt=dict(label=label))
        (work / (label + '.stdout')).write_text(out)
        (work / (label + '.stderr')).write_text(err)
        match = re.search(r'Ran (\d+) tests? in', err)
        skipped_match = re.search(r'OK \(skipped=(\d+)\)', err)
        skipped = int(skipped_match.group(1)) if skipped_match else 0
        records.append(dict(label=label, skipped=skipped, pid=child.pid, returncode=child.returncode,
            tests=int(match.group(1)) if match else None,
            stdout_sha256=sha(work / (label + '.stdout')),
            stderr_sha256=sha(work / (label + '.stderr'))))
        write(work / 'records.json', records)
        assert child.returncode == 0 and records[-1]['tests'] == expected and skipped == (10 if label == 'existing' else 0), err
    assert all(sha(ROOT / p) == h for p, h in frozen.items())
    destination = ROOT / 'results/checked-addresses-python-tests-01'
    destination.mkdir(exist_ok=False)
    result = dict(status='passed', tests=sum(r['tests'] - r['skipped'] for r in records), skipped=sum(r['skipped'] for r in records),
        raw=str(work.relative_to(ROOT)), inputs_sha256=sha(work / 'inputs.json'),
        records_sha256=sha(work / 'records.json'), performance_measurement=False)
    write(destination / 'summary.json', result)
    print(json.dumps(result), flush=True)
