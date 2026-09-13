"""Qualify the prospective schedule and timing verdict before any benchmark."""
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
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert Path(args.run_id).name == args.run_id and args.run_id.startswith('parser-jit-capacity-protocol-')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        paths = list(Path(__file__).parent.glob('*.py')) + [Path(__file__).with_name('PLAN.md')]
        paths += [ROOT / 'scripts/workflow_measurements.py', ROOT / 'scripts/workflow_io.py',
                  ROOT / 'scripts/compare_saved_runtime.py', Path(__file__).parent.parent / 'pgrust-parser-edits/states.py']
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'inputs.json', frozen)
        command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(Path(__file__).parent), '-p', 'test_protocol.py', '-v']
        child, out, err = capture(command, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                                 receipt_path=work / 'active.json', receipt=dict(label='capacity protocol'))
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        assert child.returncode == 0 and re.search(r'Ran 9 tests', err) and err.strip().endswith('OK'), err
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', tests=9, commands=1, guest_commands=0,
            raw=str(work.relative_to(ROOT)), inputs_sha256=sha(work / 'inputs.json'),
            command=command, pid=child.pid, stdout_sha256=sha(work / 'stdout'), stderr_sha256=sha(work / 'stderr')))
        print('PASS: nine schedule/noise/control/CPU/statistics/prefix tests', flush=True)


if __name__ == '__main__': main()
