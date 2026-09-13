"""Run protocol controls and freeze experiment inputs before benchmarks."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id.startswith('guarded-local-facts-protocol-') and Path(args.run_id).name == args.run_id
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        paths = list(Path(__file__).parent.glob('*.py')) + [Path(__file__).with_name(name) for name in ['PLAN.md','QUALIFICATION.md','SCREEN-REPAIR.md']]
        paths += list((ROOT / 'scripts').glob('*.py'))
        hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'inputs.json', hashes)
        child, out, err = capture([sys.executable, '-m', 'unittest', 'test_screen', '-v'],
            cwd=Path(__file__).parent, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work / 'active.json', receipt=dict(stage='local-fact screen protocol'))
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        assert child.returncode == 0 and 'Ran 12 tests' in err and err.rstrip().endswith('OK')
        assert all(sha(ROOT / p) == h for p, h in hashes.items())
        result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', tests=12, commands=1,
            raw=str(work.relative_to(ROOT)), inputs_sha256=sha(work / 'inputs.json'),
            guest_commands=0, performance_measurement=False))
        print('PASS: twelve current-baseline and native-artifact screen controls', flush=True)


if __name__ == '__main__':
    main()
