"""Seal the completed original parser support proof without rerunning a guest."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'pgrust-parser-probe'))
from compare_saved_runtime import acquire_lock, sha
from probe import fingerprint, native_inventory
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        result = ROOT / 'results/pgrust-parser-support-04'
        summary = json.loads((result / 'summary.json').read_text())
        assert summary['status'] == 'passed' and summary['custom_tests_passed'] == 114
        work = ROOT / summary['raw']
        outer = ROOT / '.work/experiments/pgrust-parser-support-04-admission-02'
        terminal = json.loads((outer / 'status.json').read_text())
        assert terminal['status'] == 'finished' and terminal['returncode'] == 0
        assert sha(outer / 'command.log') == terminal['log_sha256']
        assert sha(outer / 'plan.json') == terminal['plan_sha256']
        for name in ['plan', 'records']:
            assert sha(work / (name + '.json')) == summary[name + '_sha256']
        plan = json.loads((work / 'plan.json').read_text())
        row, = json.loads((work / 'records.json').read_text())
        assert row['returncode'] == 0 and row['command'] == plan['command']
        for stream in ['stdout', 'stderr']:
            assert sha(work / ('custom.' + stream)) == row[stream + '_sha256']
        assert all(fingerprint(ROOT / p) == h for p, h in plan['frozen'].items())
        names = native_inventory((ROOT / '.work/pgrust-parser-support-01/native.stdout').read_text())
        report, digest = read_report(work / 'suite.json', summary['suite_sha256'])
        assert len(validate_report(report, names, 'prepared', True)) == 114
        validate_runtime_limits(report, 100000000000, 150000, required=True)
        assert report['workers'] == report['requested_workers'] == 2
        for artifact in summary['artifacts'].values():
            assert sha(ROOT / artifact['path']) == artifact['sha256']
        write(result / 'final-audit.json', dict(status='passed', guest_commands=0,
            original_tests=114, original_assertions_unchanged=True,
            exact_native_test_set=True, prepared_workers=2,
            frozen_inputs_verified=len(plan['frozen']), suite_sha256=digest,
            terminal_receipt=str((outer / 'status.json').relative_to(ROOT)),
            terminal_receipt_sha256=sha(outer / 'status.json'),
            prior_controller_pid=terminal['child_pid'], prior_guest_command_pid=row['pid'],
            performance_measurement=False))
        print('PASS: terminal receipt, 114 original outcomes, artifacts and frozen inputs', flush=True)


if __name__ == '__main__':
    main()
