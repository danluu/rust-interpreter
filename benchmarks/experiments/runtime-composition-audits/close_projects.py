"""Close completed project evidence while parser qualification remains pending."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/runtime-composition-full'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write
from full import CASES, audit_cases, next_case


def read(path):
    return json.loads(path.read_text())


def main():
    supervisor, revision = sys.argv[1:3]
    assert supervisor.startswith('runtime-composition-full-nushell-') and Path(supervisor).name == supervisor
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        raw = ROOT / '.work/runtime-composition-full-02'
        out = ROOT / 'results/runtime-composition-full-02'
        outer = ROOT / '.work/experiments' / supervisor
        terminal, summary = read(outer / 'status.json'), read(out / 'summary.json')
        assert terminal['status'] == 'finished' and terminal['returncode'] == 0
        assert terminal['owner'] == terminal['cwd'] == str(ROOT)
        assert sha(outer / 'plan.json') == terminal['plan_sha256']
        assert sha(outer / 'command.log') == terminal['log_sha256']
        assert summary['completed_cases'] == CASES and not summary['unstarted_cases']
        assert summary['commands'] == 726 and summary['final_source_and_input_audit_passed']
        passed = summary['all_five_gates_passed']
        assert summary['status'] == ('passed' if passed else 'rejected')
        cases = [read(ROOT / 'results' / ('runtime-composition-edit-' + case + '-02') / 'summary.json') for case in CASES]
        assert next_case(cases) is None and passed == all(case['gate_passed'] for case in cases)
        for file, key in [('plan.json', 'plan_sha256'), ('records.json', 'records_sha256'),
                          (summary['final_audit_path'], 'final_audit_sha256')]:
            assert sha(raw / file) == summary[key]
        audit = read(raw / summary['final_audit_path'])
        assert audit_cases(CASES) == audit
        evidence, sources = {}, {}

        def bind(path, expected=None):
            digest = sha(path)
            assert expected is None or digest == expected, path
            evidence[str(path.relative_to(ROOT))] = digest

        def source(path, digest, commit):
            assert sha(ROOT / path) == digest
            assert hashlib.sha256(subprocess.check_output(['git', 'show', commit + ':' + path])).hexdigest() == digest
            sources[path] = dict(revision=commit, sha256=digest)

        for path, digest in read(raw / 'plan.json')['frozen'].items():
            if path.startswith(('.work/', 'results/')):
                bind(ROOT / path, digest)
            else:
                source(path, digest, revision)
        records = read(raw / 'records.json')
        assert [row['case'] for row in records] == CASES
        for row in records:
            assert row['returncode'] == 0
            for stream in ['stdout', 'stderr']:
                bind(raw / (row['case'] + '.' + stream), row[stream + '_sha256'])
            bind(ROOT / 'results' / ('runtime-composition-edit-' + row['case'] + '-02') / 'summary.json', row['summary_sha256'])
        if 'audit_recovery' in summary:
            assert summary['audit_recovery'] == supervisor
            recovery_path = ROOT / 'results' / supervisor / 'summary.json'
            recovery = read(recovery_path)
            assert recovery['status'] == 'passed' and recovery['new_guest_commands'] == recovery['repeated_commands'] == 0
            assert recovery['final_summary_sha256'] == sha(out / 'summary.json')
            plan_path = ROOT / recovery['raw'] / 'plan.json'
            bind(recovery_path)
            bind(plan_path, recovery['plan_sha256'])
            plan = read(plan_path)
            for path, digest in plan['evidence'].items():
                bind(ROOT / path, digest)
            source(plan['script'], plan['script_sha256'], plan['source_revision'])
        else:
            assert supervisor == 'runtime-composition-full-nushell-02'
        helper_revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        helper_path = str(Path(__file__).relative_to(ROOT))
        source(helper_path, sha(Path(__file__)), helper_revision)
        snapshot = raw / 'closed-projects'
        snapshot.mkdir(exist_ok=False)
        for file in ['plan.json', 'records.json', summary['final_audit_path']]:
            (snapshot / file).write_bytes((raw / file).read_bytes())
            bind(snapshot / file)
        write(snapshot / 'sources.json', sources)
        write(snapshot / 'evidence.json', evidence)
        (out / 'project-terminal.json').write_bytes((outer / 'status.json').read_bytes())
        receipt = dict(status='closed', commands=726, completed_cases=CASES,
            closure_source_revision=helper_revision,
            project_gates_passed=passed, parser_guards_complete=False, runtime_adopted=False,
            snapshot=str(snapshot.relative_to(ROOT)), sources_sha256=sha(snapshot / 'sources.json'),
            evidence_sha256=sha(snapshot / 'evidence.json'), frozen_sources=len(sources),
            unique_frozen_inputs=audit['unique_frozen_inputs'], all_retained_artifacts_and_sources_verified=True,
            summary_sha256=sha(out / 'summary.json'), terminal_sha256=sha(out / 'project-terminal.json'))
        assert not (out / 'project-closure.json').exists()
        write(out / 'project-closure.json', receipt)
        nu = ROOT / 'results/runtime-composition-edit-nushell-02'
        (nu / 'project-terminal.json').write_bytes((outer / 'status.json').read_bytes())
        write(nu / 'project-closure.json', dict(status='closed', commands=132,
            project_gates_passed=passed, parser_guards_complete=False, runtime_adopted=False,
            full_project_closure=str((out / 'project-closure.json').relative_to(ROOT)),
            full_project_closure_sha256=sha(out / 'project-closure.json'),
            summary_sha256=sha(nu / 'summary.json'), terminal_sha256=sha(nu / 'project-terminal.json'),
            all_retained_artifacts_and_sources_verified=True))
        print('Closed726 project commands; project gates', passed, '; parser guards still pending', flush=True)


if __name__ == '__main__':
    main()
