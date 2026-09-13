"""Run the original complete gram_core native target and the same custom bodies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import capture, require_space, write_json as write

PIN = '38d2517d3e09168a8fe222837730d435238ff358'
KEY = 'c743a75d335da063a645c24af93336b345e5329b83005a2a7c8dcb0e49915b8f'


def native_inventory(stdout, count=114):
    rows = re.findall(r'^test (\S+) \.\.\. (ok|FAILED|ignored)(?:,.*)?$', stdout, re.M)
    assert len(rows) == count and len(dict(rows)) == count, 'incomplete or duplicate native inventory'
    assert all(status == 'ok' for _, status in rows), 'native target did not pass every test'
    summaries = re.findall(r'^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out;', stdout, re.M)
    assert summaries == [('ok', str(count), '0', '0', '0', '0')], 'native target was filtered or not fully successful'
    assert re.findall(r'^running (\d+) tests?$', stdout, re.M) == [str(count)]
    return sorted(name for name, _ in rows)


def native_target(stdout, source_path):
    selected = []
    for line in stdout.splitlines():
        if not line.startswith('{'): continue
        try: row = json.loads(line)
        except json.JSONDecodeError: continue
        if not isinstance(row, dict) or row.get('reason') != 'compiler-artifact': continue
        target = row.get('target', {})
        if target.get('name') == 'gram_core' and row.get('profile', {}).get('test'):
            assert target['kind'] == ['lib'] and target['src_path'] == str(source_path)
            assert isinstance(row.get('executable'), str) and row['executable']
            selected.append(row['executable'])
    assert len(selected) == 1, 'missing or ambiguous selected native executable'
    return Path(selected[0])


def fingerprint(path):
    if path.is_symlink():
        return dict(kind='symlink', sha256=hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest())
    return dict(kind='file', sha256=sha(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'pgrust-parser-support-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 16)
        source = ROOT / '.work/sources/pgrust'
        marker = source / '.rust-interp-owned.json'
        owner = json.loads(marker.read_text())
        assert owner['owner'] == str(ROOT) and owner['revision'] == PIN
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == PIN
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        proof_path = ROOT / 'results/guarded-ranges-main-qualification-01/summary.json'
        proof = json.loads(proof_path.read_text())
        assert proof['status'] == 'passed' and proof['complete_tool_qualified'] and proof['commands'] == 263
        assert proof['tool_key'] == KEY
        tools, _ = installed_tools(KEY)
        binaries = json.loads((tools / 'ready.json').read_text())
        harness_path = ROOT / 'results/pgrust-parser-probe-tests-01/summary.json'
        harness = json.loads(harness_path.read_text())
        assert harness['status'] == 'passed' and harness['tests'] == 6
        inputs = ROOT / harness['raw'] / 'inputs.json'
        assert sha(inputs) == harness['inputs_sha256']
        for name, digest in json.loads(inputs.read_text()).items(): assert sha(ROOT / name) == digest
        paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), proof_path, harness_path, inputs, marker]
        paths += [source / name for name in subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0') if name]
        paths += list((ROOT / 'scripts').glob('*.py')) + [tools / name for name in binaries]
        frozen = {str(p.relative_to(ROOT)): fingerprint(p) for p in paths}
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR',
                             'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1')
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), revision=PIN, tool_key=KEY, binaries=binaries,
              frozen=frozen, package='gram_core', target='lib', expected_tests=114, maximum_commands=2,
              cargo_jobs=2, custom_workers=2, native_threads='libtest default', profile='project defaults; incremental=false',
              minimum_command_free_gib=8, admitted_free_bytes=shutil.disk_usage(ROOT).free,
              source_edits=0, performance_measurement=False))
        records = []

        def run(label, command, selected_env):
            assert all(fingerprint(ROOT / p) == digest for p, digest in frozen.items())
            require_space(ROOT, 8)
            child, out, err = capture(command, cwd=source, env=selected_env,
                receipt_path=work / 'active.json', receipt=dict(stage=label))
            for suffix, contents in [('stdout', out), ('stderr', err)]: (work / (label + '.' + suffix)).write_text(contents)
            records.append(dict(stage=label, command=command, pid=child.pid, returncode=child.returncode,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', records)
            assert child.returncode == 0, label + ' failed; retained full logs'
            return out, err

        native = ['cargo', '+nightly-2026-09-08', 'test', '--manifest-path', str(source / 'Cargo.toml'),
                  '--package', 'gram_core', '--lib', '--locked', '--offline', '--jobs', '2',
                  '--target-dir', str(work / 'native'), '--message-format=json', '--timings']
        out, _ = run('native', native, env)
        names = native_inventory(out)
        executable = native_target(out, source / 'crates/backend/parser/gram_core/src/lib.rs').resolve(strict=True)
        assert executable.is_relative_to((work / 'native').resolve())
        records[-1].update(tests=len(names), executable=str(executable.relative_to(ROOT)), executable_sha256=sha(executable))
        write(work / 'native-tests.json', names)
        write(work / 'records.json', records)
        suite = work / 'suite.json'
        command = [sys.executable, str(ROOT / 'scripts/interpreter.py'), '--manifest-path', str(source / 'Cargo.toml'),
                   '--package', 'gram_core', '--test-body', '--std-mir', '--engine', 'jit', '--tool-key', KEY,
                   '--jit-resumable-calls', '--jit-persistent-registers', '--isolated-batch', 'prepared',
                   '--suite-workers', '2', '--jobs', '2', '--function-cache', 'auto', '--toolchain-lookup', 'cached',
                   '--inline-leaves', '--trap-unsupported-calls', '--run-try-callbacks',
                   '--instruction-limit', '100000000000', '--allocation-limit', '150000',
                   '--suite-report', str(suite), '--cache-namespace', args.run_id]
        for name in names: command += ['--entry', name]
        _, err = run('custom', command, dict(env, RUST_INTERP_LAUNCH_STATS='1'))
        launch, = [json.loads(line.split(': ', 1)[1]) for line in err.splitlines() if line.startswith('rust-interp-launch: ')]
        assert launch['tool_key'] == KEY and launch['borrowck_cache'] == 'off'
        report, digest = read_report(suite, launch['suite_report_sha256'])
        outcomes = validate_report(report, names, 'prepared', True)
        assert len(outcomes) == 114 and sorted(name for name, _ in outcomes) == names
        validate_runtime_limits(report, 100000000000, 150000, required=True)
        assert report['workers'] == report['requested_workers'] == 2
        artifacts = {}
        for kind, suffix in [('artifact', 'rbc'), ('entry_catalog', 'json')]:
            path = Path(launch[kind + '_path'])
            assert sha(path) == launch[kind + '_sha256']
            saved = work / (kind + '.' + suffix)
            shutil.copy2(path, saved)
            artifacts[kind] = dict(path=str(saved.relative_to(ROOT)), sha256=sha(saved))
        records[-1].update(tests=114, suite_sha256=digest, artifacts=artifacts)
        write(work / 'records.json', records)
        assert all(fingerprint(ROOT / p) == digest for p, digest in frozen.items())
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        result = ROOT / 'results' / args.run_id
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=2, tests=114, package='gram_core', target='lib',
              tool_key=KEY, source_unchanged=True, original_assertions_unchanged=True, exact_native_test_set=True,
              prepared_isolation=True, performance_measurement=False, raw=str(work.relative_to(ROOT)),
              plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
              test_names_sha256=sha(work / 'native-tests.json'), suite_sha256=digest))
        print('PASS: complete original native target and114 custom test bodies', flush=True)


if __name__ == '__main__':
    main()
