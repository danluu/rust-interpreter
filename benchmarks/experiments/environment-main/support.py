"""Probe the complete original parser with qualified environment reads and C strings."""
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'pgrust-parser-probe'))
from probe import ROOT, PIN, fingerprint, native_inventory
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import capture, require_space, write_json as write


def main():
    run = 'environment-main-parser-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 16)
        proof_paths = [ROOT / 'results' / name / 'summary.json' for name in
            ['pgrust-parser-support-01-failure', 'environment-main-build-01',
             'environment-read-build-02', 'environment-main-qualification-01']]
        failure, build, targeted, broader = [json.loads(p.read_text()) for p in proof_paths]
        assert failure['status'] == 'custom lowering failed' and failure['native_tests_passed'] == 114
        assert build['status'] == targeted['status'] == broader['status'] == 'passed'
        key = build['tool_key']
        assert broader['tool_key'] == key
        assert build['composition']['kind'] == 'environment-main-compiler'
        assert targeted['binaries']['rust-interp-vm'] == build['binaries']['rust-interp-vm']
        assert build['tests']['test-debug'] == build['tests']['test-release'] >= 89
        assert targeted['tests'] == {'test-debug': 484, 'test-release': 484}
        assert broader['commands'] == 119
        tool, _ = installed_tools(key)
        binaries = json.loads((tool / 'ready.json').read_text())
        assert binaries == build['binaries']
        before = ROOT / failure['raw']
        for name in ['plan', 'records']:
            assert sha(before / (name + '.json')) == failure[name + '_sha256']
        old = json.loads((before / 'plan.json').read_text())
        records = json.loads((before / 'records.json').read_text())
        assert [(r['stage'], r['returncode']) for r in records] == [('native', 0), ('custom', 101)]
        for row in records:
            for stream in ['stdout', 'stderr']:
                assert sha(before / (row['stage'] + '.' + stream)) == row[stream + '_sha256']
        assert sha(ROOT / records[0]['executable']) == records[0]['executable_sha256']
        names = native_inventory((before / 'native.stdout').read_text())
        source = ROOT / '.work/sources/pgrust'
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == PIN
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        source_inputs = {p: h for p, h in old['frozen'].items() if p.startswith('.work/sources/pgrust/')}
        assert source_inputs and all(fingerprint(ROOT / p) == h for p, h in source_inputs.items())
        paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), Path(__file__).parent.parent / 'pgrust-parser-probe/probe.py',
                 before / 'plan.json', before / 'records.json', *proof_paths]
        paths += list((ROOT / 'scripts').glob('*.py')) + [tool / name for name in binaries]
        frozen = dict(source_inputs, **{str(p.relative_to(ROOT)): fingerprint(p) for p in paths})
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        suite = work / 'suite.json'
        command = records[1]['command'].copy()
        assert [command[i + 1] for i, item in enumerate(command) if item == '--entry'] == names
        for option, value in [('--tool-key', key), ('--suite-report', str(suite)), ('--cache-namespace', run)]:
            assert command.count(option) == 1
            command[command.index(option) + 1] = value
        write(work / 'plan.json', dict(owner=str(ROOT), revision=PIN, frozen=frozen, tool_key=key,
              binaries=binaries, command=command, native_tests_reused=114, source_edits=0,
              maximum_new_commands=1, performance_measurement=False))
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                             'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1', RUST_INTERP_LAUNCH_STATS='1')
        require_space(ROOT, 8)
        child, out, err = capture(command, cwd=source, env=env, receipt_path=work / 'active.json',
                                  receipt=dict(stage='complete parser with environment reads and checked C strings'))
        (work / 'custom.stdout').write_text(out)
        (work / 'custom.stderr').write_text(err)
        write(work / 'records.json', [dict(command=command, pid=child.pid, returncode=child.returncode,
              stdout_sha256=sha(work / 'custom.stdout'), stderr_sha256=sha(work / 'custom.stderr'))])
        assert all(fingerprint(ROOT / p) == h for p, h in frozen.items())
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        result = ROOT / 'results' / run
        result.mkdir(exist_ok=False)
        summary = dict(status='custom command failed', commands=1, native_tests_reused=114,
              expected_custom_tests=114, returncode=child.returncode, source_unchanged=True,
              frozen_inputs_verified=len(frozen), tool_key=key, raw=str(work.relative_to(ROOT)),
              plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
              suite_present=suite.exists(), performance_measurement=False)
        if child.returncode == 0:
            launch, = [json.loads(line.split(': ', 1)[1]) for line in err.splitlines() if line.startswith('rust-interp-launch: ')]
            assert launch['tool_key'] == key and launch['borrowck_cache'] == 'off'
            report, digest = read_report(suite, launch['suite_report_sha256'])
            assert len(validate_report(report, names, 'prepared', True)) == 114
            validate_runtime_limits(report, 100000000000, 150000, required=True)
            import shutil
            artifacts = {}
            for kind, suffix in [('artifact', 'rbc'), ('entry_catalog', 'json')]:
                path = Path(launch[kind + '_path'])
                assert sha(path) == launch[kind + '_sha256']
                saved = work / (kind + '.' + suffix)
                shutil.copy2(path, saved)
                artifacts[kind] = dict(path=str(saved.relative_to(ROOT)), sha256=sha(saved))
            summary.update(status='passed', custom_tests_passed=114, suite_sha256=digest, artifacts=artifacts)
        write(result / 'summary.json', summary)
        print(summary['status'], 'source and inputs verified', flush=True)
        raise SystemExit(int(child.returncode != 0))


if __name__ == '__main__':
    main()
