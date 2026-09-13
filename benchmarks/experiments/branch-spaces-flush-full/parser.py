"""Replay all original parser tests with the candidate and exact qualified compiler output."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/pgrust-parser-probe'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from probe import PIN, fingerprint, native_inventory
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import capture, require_space, write_json as write
from prerequisites import load as load_prerequisites


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'branch-spaces-flush-parser-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 10)
        baseline, build, paths = load_prerequisites()
        tool, key = installed_tools(build['tool_key'])
        assert all(sha(tool / name) == h for name, h in build['binaries'].items())
        prior_path = ROOT / 'results/guarded-local-facts-main-parser-01/summary.json'
        prior = json.loads(prior_path.read_text())
        assert prior['status'] == 'passed' and prior['tool_key'] == baseline['tool_key']
        assert prior['custom_tests_passed'] == prior['native_tests_reused'] == 114 and prior['source_unchanged']
        final_path = ROOT / 'results/guarded-local-facts-main-final-audit-01/summary.json'
        final = json.loads(final_path.read_text())
        assert final['status'] == 'passed' and final['complete_parser_tests'] == 114
        assert sha(prior_path) == final['evidence'][str(prior_path.relative_to(ROOT))]
        prior_raw = ROOT / prior['raw']
        for name in ['plan', 'records']:
            path = prior_raw / (name + '.json'); assert sha(path) == prior[name + '_sha256']; paths.append(path)
        paths += [prior_path, final_path, prior_raw / 'suite.json', Path(__file__),
                  Path(__file__).with_name('prerequisites.py'), Path(__file__).with_name('FULL.md'),
                  ROOT / 'benchmarks/experiments/branch-spaces-flush/screen.py',
                  ROOT / 'benchmarks/experiments/pgrust-parser-probe/probe.py']
        artifacts = {}
        for name in ['artifact', 'entry_catalog']:
            item = prior['artifacts'][name]; path = ROOT / item['path']
            assert sha(path) == item['sha256']; artifacts[name] = path; paths.append(path)
        catalog = json.loads(artifacts['entry_catalog'].read_text())
        names = [entry['name'] for entry in catalog['entries']]
        assert len(names) == len(set(names)) == 114
        old_suite, _ = read_report(prior_raw / 'suite.json', prior['suite_sha256'])
        validate_report(old_suite, names, 'prepared', True)
        native_proof_path = ROOT / 'results/pgrust-parser-support-01-failure/summary.json'
        native_proof = json.loads(native_proof_path.read_text()); native_raw = ROOT / native_proof['raw']
        assert native_proof['native_tests_passed'] == 114
        assert sha(native_raw / 'records.json') == native_proof['records_sha256']
        native_row, = [r for r in json.loads((native_raw / 'records.json').read_text()) if r['stage'] == 'native']
        assert native_row['returncode'] == 0
        assert sha(native_raw / 'native.stdout') == native_row['stdout_sha256']
        assert names == native_inventory((native_raw / 'native.stdout').read_text())
        assert sha(ROOT / native_row['executable']) == native_row['executable_sha256']
        paths += [native_proof_path, native_raw / 'records.json', native_raw / 'native.stdout', ROOT / native_row['executable']]
        source = ROOT / '.work/sources/pgrust'
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == PIN
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        source_inputs = {p: h for p, h in json.loads((prior_raw / 'plan.json').read_text())['frozen'].items()
                         if p.startswith('.work/sources/pgrust/')}
        assert source_inputs and all(fingerprint(ROOT / p) == h for p, h in source_inputs.items())
        paths += [tool / name for name in build['binaries']] + list((ROOT / 'scripts').glob('*.py'))
        frozen = dict(source_inputs, **{str(p.relative_to(ROOT)): fingerprint(p) for p in paths})
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        suite_path = work / 'suite.json'
        command = list(map(str, [tool / 'rust-interp-vm', '--engine', 'jit', '--jit-resumable-calls',
            '--jit-persistent-registers', '--isolated-batch', 'prepared', '--suite-workers', '2',
            '--suite-report', suite_path, '--suite-catalog', artifacts['entry_catalog'],
            '--instruction-limit', '100000000000', '--allocation-limit', '150000', artifacts['artifact']]))
        write(work / 'plan.json', dict(owner=str(ROOT), tool_key=key, command=command, frozen=frozen,
            revision=PIN, native_tests_reused=114, compiler_output_reused_from=baseline['tool_key'],
            commands=1, source_edits=0, initial_gib=10, minimum_child_gib=8, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env['RUST_INTERP_VM_STATS'] = '1'
        require_space(ROOT, 8)
        child, out, err = capture(command, cwd=ROOT, env=env, receipt_path=work / 'active.json', receipt=dict(stage='complete parser compatibility'))
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        write(work / 'records.json', [dict(command=command, pid=child.pid, returncode=child.returncode,
            stdout_sha256=sha(work / 'stdout'), stderr_sha256=sha(work / 'stderr'))])
        assert child.returncode == 0 and out == '0\n', err
        suite, digest = read_report(suite_path)
        assert len(validate_report(suite, names, 'prepared', True)) == 114
        validate_runtime_limits(suite, 100000000000, 150000, required=True)
        assert suite['workers'] == suite['requested_workers'] == 2
        assert all(t['jit_bytes'] <= 16 * 1024**2 for t in suite['tests'])
        assert all(fingerprint(ROOT / p) == h for p, h in frozen.items())
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
        result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=1, custom_tests_passed=114,
            native_tests_reused=114, source_unchanged=True, original_assertions_match=True,
            tool_key=key, vm_sha256=sha(tool / 'rust-interp-vm'), suite_sha256=digest,
            artifacts=prior['artifacts'], frozen_inputs_verified=len(frozen), raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'), performance_measurement=False))
        print('PASS: all 114 original parser tests', flush=True)


if __name__ == '__main__': main()
