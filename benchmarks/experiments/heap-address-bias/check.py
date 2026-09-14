"""Run protocol controls and freeze experiment inputs before benchmarks."""
import argparse
import json
import screen
import re
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
    parser.add_argument('--reuse-launcher-from',choices=['heap-address-screen-protocol-01'])
    args = parser.parse_args()
    assert args.run_id.startswith('heap-address-screen-protocol-') and Path(args.run_id).name == args.run_id
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
        child, out, err = capture([sys.executable, '-m', 'unittest', 'test_screen', 'test_mechanism', '-v'],
            cwd=Path(__file__).parent, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=work / 'active.json', receipt=dict(stage='heap address bias screen protocol'))
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        assert child.returncode == 0 and 'Ran 18 tests' in err and err.rstrip().endswith('OK')
        if args.reuse_launcher_from:
            prior=ROOT/'.work'/args.reuse_launcher_from
            summary=json.loads((ROOT/'results'/args.reuse_launcher_from/'summary.json').read_text())
            assert summary['status']=='passed' and summary['launcher_tests']==414 and summary['launcher_skipped']==22
            assert sha(prior/'inputs.json')==summary['inputs_sha256']
            previous=json.loads((prior/'inputs.json').read_text())
            assert all(previous[str(p.relative_to(ROOT))]==sha(p) for p in paths if p.parent in [ROOT/'scripts',ROOT/'tests'])
            terminal=ROOT/'results'/args.reuse_launcher_from/'terminal.json'
            final=json.loads(terminal.read_text());assert final['status']=='finished' and final['returncode']==0
            assert sha(ROOT/'.work/experiments'/args.reuse_launcher_from/'command.log')==final['log_sha256']
            launcher_out=(prior/'launcher.stdout').read_text();launcher_err=(prior/'launcher.stderr').read_text()
            for stream in ['stdout','stderr']:assert sha(prior/('launcher.'+stream))==summary['launcher_'+stream+'_sha256']
            from types import SimpleNamespace
            child=SimpleNamespace(returncode=0)
            write(work/'launcher-reuse.json',dict(prior=args.reuse_launcher_from,source_hashes_match=True,
                summary_sha256=sha(ROOT/'results'/args.reuse_launcher_from/'summary.json'),terminal_sha256=sha(terminal)))
        else:
            child,launcher_out,launcher_err=capture([sys.executable,'-m','unittest','discover','-s','tests','-v'],
                cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
                receipt_path=work/'launcher-active.json',receipt=dict(stage='current main launcher controls'))
        (work/'launcher.stdout').write_text(launcher_out);(work/'launcher.stderr').write_text(launcher_err)
        assert child.returncode==0 and launcher_err.rstrip().endswith('OK (skipped=22)'),launcher_err[-3000:]
        (launcher_count,)=map(int,re.findall(r'Ran (\d+) tests',launcher_err));assert launcher_count>=336
        assert all(sha(ROOT / p) == h for p, h in hashes.items())
        result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',tests=13,mechanism_controls=5,launcher_tests=launcher_count,launcher_skipped=22,
            commands=1 if args.reuse_launcher_from else 2,launcher_commands_reused=int(bool(args.reuse_launcher_from)),raw=str(work.relative_to(ROOT)),inputs_sha256=sha(work/'inputs.json'),
            stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr'),
            launcher_stdout_sha256=sha(work/'launcher.stdout'),launcher_stderr_sha256=sha(work/'launcher.stderr'),
            guest_commands=0,performance_measurement=False))
        print('PASS: thirteen screen/five code-partition controls and',launcher_count,'current launcher controls',flush=True)



if __name__ == '__main__':
    main()
