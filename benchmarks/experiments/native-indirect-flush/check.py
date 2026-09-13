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
    assert args.run_id.startswith('native-indirect-flush-protocol-') and Path(args.run_id).name == args.run_id
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
        previous_path=ROOT/'results/native-indirect-protocol-01/summary.json'
        previous=json.loads(previous_path.read_text());prior_raw=ROOT/previous['raw']
        assert previous['status']=='passed' and previous['launcher_tests']==384 and previous['launcher_skipped']==16
        assert sha(prior_raw/'inputs.json')==previous['inputs_sha256']
        prior_inputs=json.loads((prior_raw/'inputs.json').read_text())
        launcher_inputs=[p for p in paths if p.parent in [ROOT/'scripts',ROOT/'tests']]
        assert launcher_inputs and all(prior_inputs[str(p.relative_to(ROOT))]==sha(p) for p in launcher_inputs)
        prior_terminal=ROOT/'results/native-indirect-protocol-01/terminal.json'
        terminal=json.loads(prior_terminal.read_text());outer=ROOT/'.work/experiments/native-indirect-protocol-01'
        assert terminal['status']=='finished' and terminal['returncode']==0
        assert sha(outer/'command.log')==terminal['log_sha256'] and sha(outer/'plan.json')==terminal['plan_sha256']
        assert 'Ran 384 tests' in (prior_raw/'launcher-stderr').read_text()
        assert (prior_raw/'launcher-stderr').read_text().rstrip().endswith('OK (skipped=16)')
        closure_path=ROOT/'results/native-indirect-screen-token-01/closure.json'
        closure=json.loads(closure_path.read_text());assert closure['status']=='passed'
        for path in [previous_path,prior_terminal,prior_raw/'inputs.json',prior_raw/'launcher-stdout',
                     prior_raw/'launcher-stderr',prior_raw/'launcher-active.json']:
            assert sha(path)==closure['evidence'][str(path.relative_to(ROOT))]
        paths.append(closure_path)
        paths += [previous_path,prior_terminal,outer/'command.log',outer/'plan.json',prior_raw/'inputs.json',
                  prior_raw/'launcher-stdout',prior_raw/'launcher-stderr',prior_raw/'launcher-active.json']
        hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'inputs.json', hashes)
        child, out, err = capture([sys.executable, '-m', 'unittest', 'test_screen', '-v'],
            cwd=Path(__file__).parent, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work / 'active.json', receipt=dict(stage='combined indirect and flush screen protocol'))
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        assert child.returncode == 0 and 'Ran 13 tests' in err and err.rstrip().endswith('OK')
        assert all(sha(ROOT / p) == h for p, h in hashes.items())
        result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', tests=13, launcher_tests=384,launcher_skipped=16,commands=1,
            launcher_commands_reused=1,launcher_proof=str(previous_path.relative_to(ROOT)),
            launcher_source_hashes_match=True,
            raw=str(work.relative_to(ROOT)), inputs_sha256=sha(work / 'inputs.json'),
            guest_commands=0, performance_measurement=False))
        print('PASS: thirteen adopted-baseline and native-artifact screen controls', flush=True)


if __name__ == '__main__':
    main()
