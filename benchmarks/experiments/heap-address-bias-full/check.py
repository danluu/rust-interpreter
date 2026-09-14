"""Freeze and check the full comparison protocol without running guests."""
import argparse
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
    assert re.fullmatch(r'heap-address-full-protocol-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        directory = Path(__file__).parent
        paths = [p for p in directory.iterdir() if p.suffix in ['.py', '.md']]
        paths += [ROOT / 'benchmarks/experiments/heap-address-bias' / name for name in ['screen.py', 'real_controls.py', 'FULL-CONTROLS.md']]
        paths += list((ROOT / 'scripts').glob('*.py'))
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        write(work / 'inputs.json', frozen)
        child, out, err = capture([sys.executable, '-m', 'unittest', 'test_full', 'test_large',
            'test_full_controller', 'test_prerequisites', '-v'], cwd=directory,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), receipt_path=work / 'active.json',
            receipt=dict(stage='full protocol controls'))
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        assert child.returncode == 0 and 'Ran 23 tests' in err and err.rstrip().endswith('OK')
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        from prerequisites import load
        load()  # Bind the actual retained controls as well as the synthetic negatives.
        result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', tests=23, guest_commands=0, commands=1,
            raw=str(work.relative_to(ROOT)), inputs_sha256=sha(work / 'inputs.json'), performance_measurement=False))
        print('PASS: 23 full comparison controls', flush=True)


if __name__ == '__main__': main()
