"""Run protocol controls and freeze experiment inputs before benchmarks."""
import argparse
import json
import screen
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
    assert args.run_id.startswith('native-indirect-protocol-') and Path(args.run_id).name == args.run_id
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        paths = list(Path(__file__).parent.glob('*.py')) + [Path(__file__).with_name(name) for name in ['PLAN.md','QUALIFICATION.md']]
        paths += list((ROOT / 'scripts').glob('*.py'))
        paths += list((ROOT / 'tests').glob('*.py'))
        controls = [ROOT/'results'/name/'summary.json' for name in ['guarded-local-facts-main-build-01',
            'guarded-local-facts-main-final-audit-01','guarded-local-facts-main-qualification-01',
            'guarded-local-facts-main-projects-01','guarded-local-facts-main-parser-01']]
        assert screen.validate_baseline(*[json.loads(p.read_text()) for p in controls])
        paths += controls
        hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'inputs.json', hashes)
        child, out, err = capture([sys.executable, '-m', 'unittest', 'test_screen', '-v'],
            cwd=Path(__file__).parent, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work / 'active.json', receipt=dict(stage='native indirect screen protocol'))
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        assert child.returncode == 0 and 'Ran 13 tests' in err and err.rstrip().endswith('OK')
        child,out,err=capture([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py','-v'],
            cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work/'launcher-active.json',receipt=dict(stage='launcher contracts'))
        (work/'launcher-stdout').write_text(out);(work/'launcher-stderr').write_text(err)
        import re
        count,=re.findall(r'Ran (\d+) tests',err)
        assert child.returncode==0 and int(count)>=336 and err.rstrip().endswith('OK (skipped=16)'),err[-4000:]
        for name in ['test_native_indirect_option_reaches_only_vm_and_is_reported',
                     'test_native_indirect_requires_compatible_execution_before_tools']:
            assert name in err
        assert all(sha(ROOT / p) == h for p, h in hashes.items())
        result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', tests=13, launcher_tests=int(count),launcher_skipped=16,commands=2,
            raw=str(work.relative_to(ROOT)), inputs_sha256=sha(work / 'inputs.json'),
            guest_commands=0, performance_measurement=False))
        print('PASS: thirteen adopted-baseline and native-artifact screen controls', flush=True)


if __name__ == '__main__':
    main()
