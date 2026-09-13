"""Retain the failing cache regression, then verify the complete fixed harness."""
import argparse
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', required=True, choices=['before', 'after'])
    args = parser.parse_args()
    name = 'toolchain-cache-' + args.phase + '-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        paths = [p for base in ['scripts', 'tests'] for p in (ROOT / base).rglob('*.py')]
        paths += [p for p in Path(__file__).parent.iterdir() if p.is_file()]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / name
        work.mkdir(exist_ok=False)
        write(work / 'inputs.json', frozen)
        pattern = 'test_interpreter_tools.py' if args.phase == 'before' else 'test_*.py'
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v']
        child, out, err = capture(command, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work / 'active.json', receipt=dict(phase=args.phase))
        for suffix, text in [('stdout', out), ('stderr', err)]: (work / suffix).write_text(text)
        row = dict(command=command, pid=child.pid, returncode=child.returncode,
                   stdout_sha256=sha(work / 'stdout'), stderr_sha256=sha(work / 'stderr'))
        write(work / 'records.json', [row])
        count, = re.findall(r'Ran (\d+) tests? in', err)
        if args.phase == 'before':
            assert child.returncode == 1 and count == '5' and 'FAILED (failures=1)' in err
            failed = re.findall(r'^FAIL: (\w+) ', err, re.M)
            assert failed == ['test_changing_selected_toolchain_rebuilds_in_a_distinct_namespace']
            status, passed, skipped = 'expected regression failure', 4, 0
        else:
            assert child.returncode == 0 and count == '133' and 'OK (skipped=10)' in err
            status, passed, skipped = 'passed', 123, 10
        assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
        result = ROOT / 'results' / name
        result.mkdir(exist_ok=False)
        summary = dict(status=status, tests=int(count), passed=passed, skipped=skipped,
                       compiler_builds=0, guest_commands=0, performance_measurement=False,
                       raw=str(work.relative_to(ROOT)), inputs_sha256=sha(work / 'inputs.json'),
                       records_sha256=sha(work / 'records.json'))
        write(result / 'summary.json', summary)
        print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
