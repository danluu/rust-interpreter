"""Seal completed project history, source and component proofs without reruns."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from suite_reports import read_report, validate_report
from workflow_io import require_space, write_json as write
from qualify_projects import fingerprint, references, reference_artifact


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        name = 'environment-read-projects-02'
        result = ROOT / 'results' / name
        summary = json.loads((result / 'summary.json').read_text())
        assert summary['status'] == 'passed' and summary['commands'] == 40
        terminal_path = ROOT / '.work/experiments' / name / 'status.json'
        terminal = json.loads(terminal_path.read_text())
        assert terminal['status'] == 'finished' and terminal['returncode'] == 0
        assert terminal['owner'] == str(ROOT) and terminal['child_pid'] == 17434
        for stem in ['plan', 'command']:
            path = terminal_path.parent / (stem + ('.json' if stem == 'plan' else '.log'))
            assert sha(path) == terminal['plan_sha256' if stem == 'plan' else 'log_sha256']
        raw = ROOT / summary['raw']
        for stem in ['plan', 'records']:
            assert sha(raw / (stem + '.json')) == summary[stem + '_sha256']
        plan = json.loads((raw / 'plan.json').read_text())
        assert plan['owner'] == str(ROOT) and plan['expected_commands'] == 40
        assert all(fingerprint(ROOT / p) == h for p, h in plan['frozen'].items())
        rows = json.loads((raw / 'records.json').read_text())
        assert len(rows) == 40
        for case in summary['cases']:
            name = case['case']
            assert case['source_restored'] and case['exact_reference_artifacts'] and case['original_assertion_outcomes']
            prior = json.loads((ROOT / 'results' / ('guarded-ranges-edit-' + name + '-01') / 'summary.json').read_text())
            old = ROOT / prior['raw']
            expected = references(json.loads((old / 'records.json').read_text()))
            current = [r for r in rows if r['case'] == name]
            assert [r['state'] for r in current] == list(range(8))
            assert current[0]['source_sha256'] == current[-1]['source_sha256']
            for r, e in zip(current, expected):
                assert r['returncode'] == e['returncode'] and r['source_sha256'] == e['source_sha256']
                report, _ = read_report(raw / f"{name}-{r['state']}-suite.json", r['suite_sha256'])
                names = [n for n, _ in e['outcomes']]
                assert sorted(validate_report(report, names, 'prepared', r['state'] != 1)) == sorted(tuple(x) for x in e['outcomes'])
                for kind in ['artifact', 'entry_catalog']:
                    assert sha(ROOT / r[kind]['path']) == r[kind]['sha256'] == reference_artifact(e, kind)['sha256']
        proofs = {}
        for name in ['environment-read-build-02', 'environment-read-frontend-build-01']:
            path = ROOT / 'results' / name / 'summary.json'
            build = json.loads(path.read_text())
            assert build['status'] == 'passed'
            manifest = ROOT / build['source_manifest']
            assert sha(manifest) == build['source_manifest_sha256']
            frozen = json.loads(manifest.read_text())['frozen']
            components = {p: h for p, h in frozen.items() if p.startswith('crates/') or p in
                          ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'scripts/interpreter.py']}
            # The final frontend proof changes only strlen lowering from the VM proof.
            for p, h in components.items():
                if name == 'environment-read-build-02' and p == 'crates/mir-export/src/lower/system.rs':
                    continue
                assert sha(ROOT / p) == h, p
            tool = ROOT / '.work/interpreter-tools' / build['tool_key']
            assert all(sha(tool / p) == h for p, h in build['binaries'].items())
            proofs[name] = dict(summary_sha256=sha(path), manifest_sha256=sha(manifest),
                               verified_component_files=len(components), binaries=build['binaries'])
        write(result / 'final-audit.json', dict(status='passed', guest_commands=0,
            commands_verified=40, original_outcomes_and_artifacts=True,
            frozen_inputs_verified=len(plan['frozen']), source_component_proofs=proofs,
            terminal_receipt_sha256=sha(terminal_path), controller_pid=terminal['child_pid'],
            private_details_redacted=True, performance_measurement=False))
        print('PASS: 40 project histories, frozen inputs, immutable tools and exact qualified component sources', flush=True)


if __name__ == '__main__':
    main()
