"""Preserve five completed controls after missing failed-test statistics."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'pgrust-parser-probe'))
from compare_saved_runtime import acquire_lock, sha
from probe import fingerprint, native_inventory
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import require_space, write_json as write
from workflow_controls import exporter_seconds
from bench_e2e_workflow import build_metrics
from protocol import LIMITS
from states import native_outcomes, custom_export_ran


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        old = ROOT / '.work/parser-jit-capacity-screen-01'
        outer = ROOT / '.work/experiments/parser-jit-capacity-screen-01'
        terminal = json.loads((outer / 'status.json').read_text())
        assert terminal['status'] == 'finished' and terminal['returncode'] == 1
        assert sha(outer / 'command.log') == terminal['log_sha256']
        assert "KeyError: 'jit_bytes'" in (outer / 'command.log').read_text()
        plan = json.loads((old / 'plan.json').read_text())
        rows = json.loads((old / 'records.json').read_text())
        assert len(rows) == 5 and rows[-1]['mode'] == 'custom-32' and rows[-1]['state'] == -1
        assert all(fingerprint(ROOT / p) == h for p, h in plan['frozen'].items())
        source = ROOT / '.work/sources/pgrust/crates/backend/parser/gram_core/src/parse.rs'
        assert sha(source) == plan['original_source_sha256']
        work = ROOT / '.work/parser-jit-capacity-prefix-audit-01'; work.mkdir(exist_ok=False)
        artifacts = work / 'artifacts'; artifacts.mkdir()
        names = native_inventory((ROOT / '.work/pgrust-parser-support-01/native.stdout').read_text())
        for index, row in enumerate(rows):
            assert row['index'] == index and {k: row[k] for k in plan['schedule'][index]} == plan['schedule'][index]
            assert row['returncode'] == (1 if index == 4 else 0)
            row['log_raw'] = str(old.relative_to(ROOT))
            for stream in ['stdout', 'stderr']:
                assert sha(old / f'{index}.{stream}') == row[stream + '_sha256']
            if row['mode'] == 'native':
                row['outcomes'] = native_outcomes((old / f'{index}.stdout').read_text(), names, True)
                assert sha(ROOT / row['executable']['path']) == row['executable']['sha256']
                continue
            err = (old / f'{index}.stderr').read_text()
            launch, = [json.loads(l.split(': ', 1)[1]) for l in err.splitlines() if l.startswith('rust-interp-launch: ')]
            assert launch['tool_key'] == plan['tool_key'] and launch['borrowck_cache'] == 'off'
            assert launch['function_cache'] == 'auto' and launch['toolchain_lookup']['mode'] == 'cached'
            assert launch['jit_code_limit_bytes'] == LIMITS[row['mode']]
            assert launch['suite_workers'] == launch['suite_workers_requested'] == 2 and custom_export_ran(err)
            report, digest = read_report(old / f'{index}-suite.json', launch['suite_report_sha256'])
            outcomes = validate_report(report, names, 'prepared', index != 4)
            validate_runtime_limits(report, 100000000000, 150000, jit_code_limit=LIMITS[row['mode']], required=True)
            assert report['workers'] == report['requested_workers'] == 2
            successful = [t for t in report['tests'] if t['status'] == 'passed']
            peak = max((t['jit_bytes'] for t in successful), default=None)
            assert peak is None or peak <= LIMITS[row['mode']]
            row.update(outcomes=outcomes, suite_sha256=digest, launch=launch, stages=exporter_seconds(err), build=build_metrics(launch),
                maximum_owner_code_bytes=peak, maximum_owner_declines=max((t['jit_declined_functions'] for t in successful), default=None),
                statistics_tests_available=len(successful), statistics_tests_unavailable=report['failed'],
                statistics_scope='successful test receipts; failures do not expose runtime counters')
            if index != 4: assert row['outcomes'] == rows[0]['outcomes']
            for kind, suffix in [('artifact', 'rbc'), ('entry_catalog', 'json')]:
                path = Path(launch[kind + '_path']); digest = launch[kind + '_sha256']
                # The original custom32 artifact has already been replaced by
                # its wrong-source build; prefer the retained content-addressed copy.
                if kind in row: path = ROOT / row[kind]['path']
                assert sha(path) == digest
                saved = artifacts / (digest + '.' + suffix)
                if not saved.exists(): shutil.copy2(path, saved)
                assert sha(saved) == digest
                row[kind] = dict(path=str(saved.relative_to(ROOT)), sha256=digest)
        for kind in ['artifact', 'entry_catalog']:
            assert len({r[kind]['sha256'] for r in rows[1:4]}) == 1
        assert all(fingerprint(ROOT / p) == h for p, h in plan['frozen'].items()) and sha(source) == plan['original_source_sha256']
        write(work / 'records.json', rows)
        result = ROOT / 'results/parser-jit-capacity-screen-01-failure'; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='five-command prefix verified; harness failure retained',
            commands=5, edited_timing_commands=0, source_restored=True, frozen_inputs_verified=len(plan['frozen']),
            old_raw=str(old.relative_to(ROOT)), raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(old / 'plan.json'), original_records_sha256=sha(old / 'records.json'),
            audited_records_sha256=sha(work / 'records.json'), audit_source_sha256=sha(Path(__file__)), terminal=terminal,
            wrong_control=dict(passed=8, failed=106, native_comparison_pending=True),
            no_performance_verdict=True, continuation_requires_new_plan=True))
        print('PASS: five controls retained, zero valid edited timings; wrong native comparison remains pending', flush=True)


if __name__ == '__main__': main()
