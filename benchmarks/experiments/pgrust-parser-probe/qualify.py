"""Qualify complete-native-target inventory parsing before the support probe."""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    run = 'pgrust-parser-probe-tests-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        paths = [p for p in Path(__file__).parent.iterdir() if p.is_file()]
        paths += list((ROOT / 'scripts').glob('*.py'))
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        write(work / 'inputs.json', frozen)
        command = [sys.executable, '-m', 'unittest', 'discover', '-s',
                   'benchmarks/experiments/pgrust-parser-probe', '-p', 'test_*.py', '-v']
        child, out, err = capture(command, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work / 'active.json', receipt=dict(stage='inventory tests'))
        for suffix, text in [('stdout', out), ('stderr', err)]: (work / suffix).write_text(text)
        write(work / 'records.json', [dict(command=command, pid=child.pid, returncode=child.returncode,
              stdout_sha256=sha(work / 'stdout'), stderr_sha256=sha(work / 'stderr'))])
        assert child.returncode == 0 and re.search(r'Ran 6 tests in', err) and 'skipped' not in err
        assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
        result = ROOT / 'results' / run
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', tests=6, guest_commands=0,
              raw=str(work.relative_to(ROOT)), inputs_sha256=sha(work / 'inputs.json'),
              records_sha256=sha(work / 'records.json'), performance_measurement=False))
        print('PASS: six native inventory/target rejection checks', flush=True)


if __name__ == '__main__':
    main()
