"""Qualify vmmap label compatibility with contracts and retained mapping reports."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
RUN = 'vmmap-label-compatibility-01'


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        failed = ROOT / 'results/adopted-current-runtime-sampling-01'
        summary = json.loads((failed / 'summary.json').read_text())
        closure = json.loads((failed / 'closure.json').read_text())
        assert summary['status'] == 'capture-failed' and summary['usable_sample_windows'] == 0
        assert summary['unstarted_cases'] == ['exhaustive'] and closure['status'] == 'closed'
        assert sha(failed / 'summary.json') == closure['summary_sha256']
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        paths = [ROOT / p for p in subprocess.check_output(['git', 'ls-files', 'scripts', 'tests', 'crates',
            'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'], cwd=ROOT, text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
        for directory in ['scalar-runtime-sampling', 'scalar-private-transfers', 'operation-map']:
            paths += list((ROOT / 'benchmarks/experiments' / directory).glob('*.py'))
        paths += [failed / n for n in ['summary.json', 'closure.json', 'terminal.json']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        raw = ROOT / '.work' / RUN
        raw.mkdir(exist_ok=False)
        commands = [('python', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], ROOT),
            ('attribution', [sys.executable, '-m', 'unittest', 'test_attribution', '-v'],
             ROOT / 'benchmarks/experiments/scalar-runtime-sampling'),
            ('retained-maps', [sys.executable, str(Path(__file__).with_name('replay.py'))], ROOT)]
        write(raw / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
            commands=[dict(label=label, command=command, cwd=str(cwd)) for label, command, cwd in commands],
            initial_gib=12, minimum_child_gib=8, guest_commands=0, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_'))
               and k not in ['RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        env['PYTHONPATH'] = os.pathsep.join(str(ROOT / 'benchmarks/experiments' / d) for d in
            ['scalar-runtime-sampling', 'scalar-private-transfers', 'operation-map']) + os.pathsep + str(ROOT / 'scripts')
        records, counts = [], {}
        for label, command, cwd in commands:
            require_space(ROOT, 8)
            child, out, err = capture(command, cwd=cwd, env=env, receipt_path=raw / 'active.json', receipt=dict(stage=label))
            for stream, text in [('stdout', out), ('stderr', err)]:
                (raw / (label + '.' + stream)).write_text(text)
            records.append(dict(label=label, command=command, cwd=str(cwd), pid=child.pid, returncode=child.returncode,
                stdout_sha256=sha(raw / (label + '.stdout')), stderr_sha256=sha(raw / (label + '.stderr'))))
            write(raw / 'records.json', records)
            assert child.returncode == 0, (out + err)[-5000:]
            if label in ['python', 'attribution']:
                count, = re.findall(r'Ran (\d+) tests? in ', err)
                skipped, = re.findall(r'^OK(?: \(skipped=(\d+)\))?$', err, re.M)
                counts[label] = dict(discovered=int(count), skipped=int(skipped or 0))
                if label == 'python':
                    assert int(count) >= 449 and int(skipped or 0) == 22
                    assert err.count('test_vmmap_ranges.VmmapRanges.') == 6
                else:
                    assert int(count) == 9 and not skipped
            else:
                replay = json.loads(out)
                assert replay['status'] == 'passed' and replay['reports'] == 14 and replay['guest_commands'] == 0
                assert replay['every_original_emitted_arena_contained']
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, 'passed', flush=True)
        out = ROOT / 'results' / RUN
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', commands=3, guest_commands=0,
            python=counts['python'], attribution_tests=9, retained_reports=14,
            current_reports=12, historical_reports=2, all_emitted_arenas_contained=True,
            source_revision=revision, raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw / 'plan.json'), records_sha256=sha(raw / 'records.json'),
            frozen_inputs=len(frozen), performance_measurement=False))


if __name__ == '__main__':
    main()
