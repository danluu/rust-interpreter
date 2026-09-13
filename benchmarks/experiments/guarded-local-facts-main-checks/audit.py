"""Close all current-compiler qualification receipts without executing guests."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from component import ROOT, require_build
from compare_saved_runtime import acquire_lock, sha
from qualify_projects import fingerprint, CASES
from suite_reports import read_report, validate_report
from workflow_io import require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        names = ['build', 'remapping', 'qualification', 'projects', 'parser']
        paths = [ROOT / 'results' / ('guarded-local-facts-main-' + n + '-01') / 'summary.json' for n in names]
        proofs = [json.loads(p.read_text()) for p in paths]
        build, remap, strict, projects, parser = proofs
        require_build(build)
        assert all(p['status'] == 'passed' and p['tool_key'] == build['tool_key'] for p in proofs)
        assert build['tests']['test-debug'] == dict(passed=513, ignored=5)
        assert (remap['tests'], remap['internal_commands'], remap['harness_commands']) == (2, 130, 1)
        assert strict['commands'] == 119 and projects['commands'] == 40
        assert parser['commands'] == 1 and parser['custom_tests_passed'] == parser['native_tests_reused'] == 114
        evidence, inputs, artifact_identity = {}, {}, []
        for name, path, proof in zip(names, paths, proofs):
            evidence[str(path.relative_to(ROOT))] = sha(path)
            outer_name = 'guarded-local-facts-main-' + name + '-01'
            if name == 'remapping': outer_name = 'guarded-local-facts-main-remapping-admission-02'
            terminal_path = ROOT / '.work/experiments' / outer_name / 'status.json'
            terminal = json.loads(terminal_path.read_text())
            assert terminal['owner'] == terminal['cwd'] == str(ROOT)
            assert terminal['status'] == 'finished' and terminal['returncode'] == 0
            for file, field in [('command.log', 'log_sha256'), ('plan.json', 'plan_sha256')]:
                assert sha(terminal_path.with_name(file)) == terminal[field]
            evidence[str(terminal_path.relative_to(ROOT))] = sha(terminal_path)
            raw = ROOT / proof['raw']
            assert raw.parent == ROOT / '.work'
            assert sha(raw / 'plan.json') == proof['plan_sha256']
            plan = json.loads((raw / 'plan.json').read_text())
            assert plan['owner'] == str(ROOT)
            for file, digest in plan['frozen'].items():
                value = fingerprint(ROOT / file) if isinstance(digest, dict) else sha(ROOT / file)
                assert value == digest, (name, file)
                if file in inputs: assert inputs[file] == fingerprint(ROOT / file)
                inputs[file] = fingerprint(ROOT / file)
            if name == 'remapping':
                assert sha(raw / 'record.json') == proof['record_sha256']
                assert sha(raw / 'artifacts.json') == proof['artifacts_sha256']
                inventory = json.loads((raw / 'artifacts.json').read_text())
                assert all(sha(raw / p) == h for p, h in inventory.items())
                assert len(list(raw.glob('trap-*/command-*/receipt.json'))) == 130
                continue
            assert sha(raw / 'records.json') == proof['records_sha256']
            rows = json.loads((raw / 'records.json').read_text())
            if name == 'build':
                assert len(rows) == 6
                for row in rows:
                    assert row['returncode'] == 0
                    for stream in ['stdout', 'stderr']:
                        assert sha(raw / (row['label'] + '.' + stream)) == row[stream + '_sha256']
            elif name == 'qualification':
                assert len(rows) == 119
                for row in rows:
                    for stream in ['stdout', 'stderr']: assert sha(ROOT / row[stream]) == row[stream + '_sha256']
            elif name == 'projects':
                assert len(rows) == 40 and [c['case'] for c in proof['cases']] == CASES
                assert all(c['source_restored'] and c['original_assertion_outcomes'] for c in proof['cases'])
                for row in rows:
                    report, _ = read_report(raw / f"{row['case']}-{row['state']}-suite.json", row['suite_sha256'])
                    assert len(report['tests']) > 0
                    for kind in ['artifact', 'entry_catalog']:
                        saved = row[kind]
                        assert sha(ROOT / saved['path']) == saved['sha256']
                        assert saved['identical_to_reference'] == (saved['sha256'] == saved['reference_sha256'])
                artifact_identity = [dict(case=c['case'], exact=c['exact_reference_artifacts']) for c in proof['cases']]
            elif name == 'parser':
                report, _ = read_report(raw / 'suite.json', proof['suite_sha256'])
                original_path = ROOT / 'results/guarded-local-facts-parser-01/summary.json'
                original = json.loads(original_path.read_text())
                before, _ = read_report(ROOT / original['raw'] / 'suite.json', original['suite_sha256'])
                assert len(validate_report(report, [r['name'] for r in before['tests']], 'prepared', True)) == 114
                for artifact in proof['artifacts'].values():
                    assert sha(ROOT / artifact['path']) == artifact['sha256']
        harness_path = ROOT / 'results/guarded-local-facts-main-project-tests-01/summary.json'
        harness = json.loads(harness_path.read_text())
        assert harness['status'] == 'passed' and harness['tests'] == 6
        hashes = ROOT / harness['raw'] / 'inputs.json'
        assert sha(hashes) == harness['inputs_sha256']
        assert all(sha(ROOT / p) == h for p, h in json.loads(hashes.read_text()).items())
        evidence[str(harness_path.relative_to(ROOT))] = sha(harness_path)
        source_revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        source_bindings = []
        for path, identity in sorted(inputs.items()):
            prefix = '.work/publication-main/'
            revision = build['source_commit'] if path.startswith(prefix) else source_revision
            relative = path[len(prefix):] if path.startswith(prefix) else path
            if not (relative.startswith(('crates/', 'scripts/', 'tests/', 'benchmarks/experiments/'))
                    or relative in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml']):
                continue
            spec = revision + ':' + relative
            blob = subprocess.check_output(['git', 'show', spec], cwd=ROOT)
            assert hashlib.sha256(blob).hexdigest() == identity['sha256'], path
            source_bindings.append(dict(path=path, git_source=spec, sha256=identity['sha256']))
        result = ROOT / 'results/guarded-local-facts-main-final-audit-01'
        result.mkdir(exist_ok=False)
        write(result / 'source-bindings.json', source_bindings)
        write(result / 'summary.json', dict(status='passed', guest_commands=0, tool_key=build['tool_key'],
            binaries=build['binaries'], workspace_tests_per_profile=513, ordinary_ignored_tests=5,
            explicit_remap_tests=2, remap_internal_commands=130, strict_commands=119,
            project_commands=40, complete_parser_tests=114, unique_frozen_inputs=len(inputs),
            project_artifact_identity=artifact_identity, evidence=evidence,
            qualification_source_revision=source_revision, git_bound_source_files=len(source_bindings),
            source_bindings_sha256=sha(result / 'source-bindings.json'), auditor_sha256=sha(Path(__file__)),
            all_frozen_inputs_verified=True, private_details_redacted=True, performance_measurement=False))
        print('PASS: source/tool/evidence audit,130 remap and159 strict/project controls;114 parser tests', flush=True)


if __name__ == '__main__': main()
