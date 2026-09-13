"""Native baseline and exact boxed-FnOnce old/new exporter regression."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'pgrust-parser-probe'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from probe import native_inventory
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import capture, require_space, write_json as write

CONTROL = 'c743a75d335da063a645c24af93336b345e5329b83005a2a7c8dcb0e49915b8f'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['before', 'after'], required=True)
    parser.add_argument('--key', default=CONTROL)
    args = parser.parse_args()
    run = 'boxed-fnonce-' + args.phase + '-01'
    fixture = Path(__file__).parent / 'fixture'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        tool, _ = installed_tools(args.key)
        binaries = json.loads((tool / 'ready.json').read_text())
        paths = [p for p in fixture.rglob('*') if p.is_file()]
        paths += [Path(__file__), Path(__file__).with_name('PLAN.md')]
        paths += list((ROOT / 'scripts').glob('*.py')) + [tool / p for p in binaries]
        paths += [Path(__file__).parent.parent / 'pgrust-parser-probe/probe.py']
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, tool_key=args.key,
              binaries=binaries, phase=args.phase, expected_tests=6, performance_measurement=False))
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                             'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1')
        rows = []

        def run_command(label, command, expected=0):
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            require_space(ROOT, 8)
            child, out, err = capture(command, cwd=ROOT, env=env,
                receipt_path=work / 'active.json', receipt=dict(stage=label))
            for stream, contents in [('stdout', out), ('stderr', err)]:
                (work / (label + '.' + stream)).write_text(contents)
            rows.append(dict(stage=label, command=command, pid=child.pid, returncode=child.returncode,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', rows)
            assert child.returncode == expected, err
            return out, err

        if args.phase == 'before':
            assert args.key == CONTROL
            command = ['cargo', '+nightly-2026-09-08', 'test', '--manifest-path', str(fixture / 'Cargo.toml'),
                '--lib', '--locked', '--offline', '--jobs', '2', '--target-dir', str(work / 'native'), '--message-format=json']
            out, _ = run_command('native', command)
            names = native_inventory(out, count=6)
            targets = [json.loads(line) for line in out.splitlines() if line.startswith('{')]
            targets = [r for r in targets if r.get('reason') == 'compiler-artifact' and r.get('executable')]
            target, = targets
            assert target['target']['name'] == 'boxed_fnonce_regression' and target['profile']['test']
            executable = Path(target['executable']).resolve(strict=True)
            assert executable.is_relative_to(work / 'native')
            write(work / 'native.json', dict(names=names, executable=str(executable.relative_to(ROOT)),
                  executable_sha256=sha(executable), fixture={str(p.relative_to(ROOT)): sha(p) for p in fixture.rglob('*') if p.is_file()}))
            modes = [('jit', ['--engine', 'jit'], 101)]
        else:
            before = ROOT / '.work/boxed-fnonce-before-01'
            proof = json.loads((ROOT / 'results/boxed-fnonce-before-01/summary.json').read_text())
            assert proof['status'] == 'expected lowering failure verified'
            assert sha(before / 'native.json') == proof['native_sha256']
            native = json.loads((before / 'native.json').read_text())
            assert all(sha(ROOT / p) == h for p, h in native['fixture'].items())
            assert sha(ROOT / native['executable']) == native['executable_sha256']
            names = native['names']
            modes = [('interpreter', ['--engine', 'interpreter'], 0),
                     ('jit', ['--engine', 'jit'], 0),
                     ('resumable', ['--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers'], 0)]
        for mode, flags, expected in modes:
            suite = work / (mode + '.suite.json')
            command = [sys.executable, str(ROOT / 'scripts/interpreter.py'), '--manifest-path', str(fixture / 'Cargo.toml'),
                '--package', 'boxed-fnonce-regression', '--test-body', '--std-mir', '--tool-key', args.key,
                '--isolated-batch', 'prepared', '--suite-workers', '2', '--jobs', '2', '--function-cache', 'auto',
                '--toolchain-lookup', 'cached', '--inline-leaves', '--trap-unsupported-calls', '--run-try-callbacks',
                '--instruction-limit', '10000000', '--allocation-limit', '150000', '--suite-report', str(suite),
                '--cache-namespace', run + ':' + mode, *flags]
            for name in names: command += ['--entry', name]
            _, err = run_command(mode, command, expected)
            if expected:
                assert 'virtual call requires a fat-pointer receiver' in err
                assert not suite.exists()
            else:
                report, digest = read_report(suite)
                outcomes = validate_report(report, names, 'prepared', True)
                assert len(outcomes) == 6
                validate_runtime_limits(report, 10000000, 150000, required=True)
                rows[-1]['suite_sha256'] = digest
                write(work / 'records.json', rows)
            print(mode, 'verified', flush=True)
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / run
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='expected lowering failure verified' if args.phase == 'before' else 'passed',
              commands=len(rows), native_tests=6, guest_tests=0 if args.phase == 'before' else 18,
              tool_key=args.key, raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
              records_sha256=sha(work / 'records.json'), performance_measurement=False,
              native_sha256=sha((work if args.phase == 'before' else ROOT / '.work/boxed-fnonce-before-01') / 'native.json')))


if __name__ == '__main__':
    main()
