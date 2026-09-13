"""Check the retained project-controller boundaries and freeze current inputs."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        work = ROOT / '.work/guarded-local-facts-main-project-tests-01'
        work.mkdir(exist_ok=False)
        inputs = list((ROOT / 'scripts').glob('*.py')) + list(Path(__file__).parent.glob('*.py'))
        inputs += [Path(__file__).parent.parent / 'guarded-local-facts-main/inputs.py']
        inputs += [Path(__file__), Path(__file__).with_name('test_projects.py'),
                   Path(__file__).with_name('qualify_projects.py'), Path(__file__).with_name('PLAN.md')]
        hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
        write(work / 'inputs.json', hashes)
        import os
        child, out, err = capture([sys.executable, '-m', 'unittest', 'test_projects', '-v'],
            cwd=Path(__file__).parent, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work / 'active.json', receipt=dict(stage='controller tests'))
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        assert child.returncode == 0 and 'Ran 6 tests' in err and err.rstrip().endswith('OK')
        assert all(sha(ROOT / p) == h for p, h in hashes.items())
        result = ROOT / 'results/guarded-local-facts-main-project-tests-01'
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', tests=6, commands=1,
            raw=str(work.relative_to(ROOT)), inputs_sha256=sha(work / 'inputs.json'),
            performance_measurement=False))
        print('PASS: six project-controller boundaries', flush=True)


if __name__ == '__main__':
    main()
