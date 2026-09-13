#!/usr/bin/env python3
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write

with (ROOT / '.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock, 45)
    require_space(ROOT, 8)
    work = ROOT / '.work/guarded-ranges-admission-tests-01'
    work.mkdir(exist_ok=False)
    paths = [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
    paths += list((ROOT / 'benchmarks/experiments/guarded-ranges').glob('*.py'))
    paths += list((ROOT / 'scripts').glob('*.py'))
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    write(work / 'inputs.json', frozen)
    child, out, err = capture([sys.executable, '-m', 'unittest', 'discover',
        '-s', 'benchmarks/experiments/guarded-ranges-admission', '-p', 'test_*.py'], cwd=ROOT,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), receipt_path=work / 'active.json',
        receipt=dict(stage='continuation eligibility tests'))
    (work / 'tests.stdout').write_text(out)
    (work / 'tests.stderr').write_text(err)
    write(work / 'records.json', dict(pid=child.pid, returncode=child.returncode,
        stdout_sha256=sha(work / 'tests.stdout'), stderr_sha256=sha(work / 'tests.stderr')))
    assert child.returncode == 0 and 'Ran 5 tests in' in err and '\nOK\n' in err, err
    assert all(sha(ROOT / name) == digest for name, digest in frozen.items())
    out = ROOT / 'results/guarded-ranges-admission-tests-01'
    out.mkdir(exist_ok=False)
    result = dict(status='passed', tests=5, guest_commands=0, raw=str(work.relative_to(ROOT)),
        inputs_sha256=sha(work / 'inputs.json'), records_sha256=sha(work / 'records.json'))
    write(out / 'summary.json', result)
    print(json.dumps(result), flush=True)
