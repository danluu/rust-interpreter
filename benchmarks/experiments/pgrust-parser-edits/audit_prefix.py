"""Retain the two successful commands preceding a Cargo progress-label mismatch."""
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
from workflow_io import write_json as write
from states import native_outcomes
from bench_e2e_workflow import build_metrics
from workflow_controls import exporter_seconds


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        work = ROOT / '.work/pgrust-parser-edits-repository-01'
        outer = ROOT / '.work/experiments/pgrust-parser-edits-repository-01'
        terminal = json.loads((outer / 'status.json').read_text())
        assert terminal['status'] == 'finished' and terminal['returncode'] == 1
        assert sha(outer / 'command.log') == terminal['log_sha256']
        assert "selected custom source was not checked" in (outer / 'command.log').read_text()
        plan = json.loads((work / 'plan.json').read_text())
        rows = json.loads((work / 'records.json').read_text())
        assert [(r['index'], r['mode'], r['returncode']) for r in rows] == [(0, 'native', 0), (1, 'custom-a', 0)]
        assert all(fingerprint(ROOT / p) == h for p, h in plan['frozen'].items())
        source = ROOT / '.work/sources/pgrust/crates/backend/parser/gram_core/src/parse.rs'
        assert sha(source) == plan['original_source_sha256']
        names = native_inventory((ROOT / '.work/pgrust-parser-support-01/native.stdout').read_text())
        for row in rows:
            index = row['index']
            for stream in ['stdout', 'stderr']:
                assert sha(work / f'{index}.{stream}') == row[stream + '_sha256']
            assert row['source_sha256'] == plan['original_source_sha256']
            assert {k: row[k] for k in plan['schedule'][index]} == plan['schedule'][index]
        assert sha(ROOT / rows[0]['executable']['path']) == rows[0]['executable']['sha256']
        rows[0]['outcomes'] = native_outcomes((work / '0.stdout').read_text(), names, True)
        err = (work / '1.stderr').read_text()
        assert '\n   Compiling gram_core v' in err
        launch, = [json.loads(l.split(': ', 1)[1]) for l in err.splitlines() if l.startswith('rust-interp-launch: ')]
        assert launch['tool_key'] == plan['tool_key'] and launch['borrowck_cache'] == 'off'
        assert len([l for l in err.splitlines() if l.startswith('rust-interp-export: ')]) == 1
        report, digest = read_report(work / '1-suite.json', launch['suite_report_sha256'])
        outcomes = validate_report(report, names, 'prepared', True)
        assert outcomes == rows[0]['outcomes'] and len(outcomes) == 114
        validate_runtime_limits(report, 100000000000, 150000, required=True)
        assert report['workers'] == report['requested_workers'] == 2
        rows[1].update(outcomes=outcomes, suite_sha256=digest, launch=launch,
                       build=build_metrics(launch), stages=exporter_seconds(err))
        for kind, suffix in [('artifact', 'rbc'), ('entry_catalog', 'json')]:
            path = Path(launch[kind + '_path']); digest = launch[kind + '_sha256']
            assert sha(path) == digest
            saved = work / 'artifacts' / (digest + '.' + suffix)
            if not saved.exists(): shutil.copy2(path, saved)
            assert sha(saved) == digest
            rows[1][kind] = dict(path=str(saved.relative_to(ROOT)), sha256=digest)
        write(work / 'audited-prefix.json', rows)
        result = ROOT / 'results/pgrust-parser-edits-repository-01-failure'; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='two-command prefix verified; validator mismatch retained',
            commands=2, edited_commands=0, native_tests=114, custom_tests=114, source_restored=True,
            frozen_inputs_verified=len(plan['frozen']), raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), original_records_sha256=sha(work / 'records.json'),
            audited_prefix_sha256=sha(work / 'audited-prefix.json'), terminal=terminal,
            no_speedup_claim=True, continuation_requires_new_plan=True))
        print('PASS: two original-state commands retained; no edited observations or repeated commands', flush=True)


if __name__ == '__main__':
    main()
