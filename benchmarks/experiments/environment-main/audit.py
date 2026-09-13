"""Verify completed composition evidence and source identity before publication."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from suite_reports import read_report, validate_report
from workflow_io import require_space, write_json as write
from qualify_projects import fingerprint


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        names = ['environment-main-build-01', 'environment-main-qualification-01',
                 'environment-main-projects-01', 'environment-main-parser-01']
        proofs = [json.loads((ROOT / 'results' / n / 'summary.json').read_text()) for n in names]
        build, strict, projects, parser = proofs
        assert all(p['status'] == 'passed' and p['tool_key'] == build['tool_key'] for p in proofs)
        assert build['tests'] == {'test-debug': 98, 'test-release': 98}
        assert strict['commands'] == 119 and projects['commands'] == 40
        assert parser['custom_tests_passed'] == parser['native_tests_reused'] == 114
        documents = 'benchmarks/experiments/environment-main/PLAN.md'
        original_doc = subprocess.check_output(['git', 'show', build['source_commit'] + ':' + documents], cwd=ROOT)
        original_doc_hash = hashlib.sha256(original_doc).hexdigest()
        evidence, checked_inputs, revisions = {}, 0, []
        for name, proof in zip(names, proofs):
            result_path = ROOT / 'results' / name / 'summary.json'
            evidence[str(result_path.relative_to(ROOT))] = sha(result_path)
            terminal_path = ROOT / '.work/experiments' / name / 'status.json'
            terminal = json.loads(terminal_path.read_text())
            assert terminal['owner'] == str(ROOT) and terminal['status'] == 'finished' and terminal['returncode'] == 0
            assert sha(terminal_path.parent / 'command.log') == terminal['log_sha256']
            assert sha(terminal_path.parent / 'plan.json') == terminal['plan_sha256']
            evidence[str(terminal_path.relative_to(ROOT))] = sha(terminal_path)
            raw = ROOT / proof['raw']
            plan_path = raw / 'plan.json'
            expected = proof.get('plan_sha256', proof.get('source_manifest_sha256'))
            assert sha(plan_path) == expected
            plan = json.loads(plan_path.read_text())
            assert plan['owner'] == str(ROOT)
            for path, digest in plan['frozen'].items():
                actual = fingerprint(ROOT / path) if isinstance(digest, dict) else sha(ROOT / path)
                if actual != digest:
                    assert path == documents and digest == original_doc_hash, (name, path)
                    revisions.append(dict(proof=name, file=path, original_sha256=digest,
                        verified_git_source=build['source_commit'], reason='prospective cache admission paragraph added after this stage completed'))
                checked_inputs += 1
            if 'records_sha256' in proof:
                assert sha(raw / 'records.json') == proof['records_sha256']
            if name == 'environment-main-qualification-01':
                rows = json.loads((raw / 'records.json').read_text())
                assert len(rows) == 119
                for row in rows:
                    for stream in ['stdout', 'stderr']:
                        assert sha(ROOT / row[stream]) == row[stream + '_sha256']
            elif name == 'environment-main-projects-01':
                rows = json.loads((raw / 'records.json').read_text())
                assert len(rows) == 40 and all(c['source_restored'] and c['exact_reference_artifacts'] and c['original_assertion_outcomes'] for c in proof['cases'])
                for row in rows:
                    read_report(raw / f"{row['case']}-{row['state']}-suite.json", row['suite_sha256'])
                    for kind in ['artifact', 'entry_catalog']:
                        assert sha(ROOT / row[kind]['path']) == row[kind]['sha256'] == row[kind]['reference_sha256']
            elif name == 'environment-main-parser-01':
                report, _ = read_report(raw / 'suite.json', proof['suite_sha256'])
                original_path = ROOT / 'results/pgrust-parser-support-04/summary.json'
                original = json.loads(original_path.read_text())
                old, _ = read_report(ROOT / original['raw'] / 'suite.json', original['suite_sha256'])
                assert len(validate_report(report, [r['name'] for r in old['tests']], 'prepared', True)) == 114
                for kind, artifact in proof['artifacts'].items():
                    assert sha(ROOT / artifact['path']) == artifact['sha256'] == original['artifacts'][kind]['sha256']
        tools = ROOT / '.work/interpreter-tools' / build['tool_key']
        assert all(sha(tools / n) == h for n, h in build['binaries'].items())
        result = ROOT / 'results/environment-main-final-audit-01'; result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', guest_commands=0,
            strict_commands=119, project_commands=40, complete_parser_tests=114,
            exporter_tests_per_profile=98, tool_key=build['tool_key'], binaries=build['binaries'],
            exact_existing_and_parser_artifacts=True, checked_input_occurrences=checked_inputs,
            documented_post_stage_plan_revision=revisions, evidence=evidence,
            private_details_redacted=True, performance_measurement=False))
        print('PASS: complete source/tool/evidence audit,159 controls and114 original parser tests', flush=True)


if __name__ == '__main__':
    main()
