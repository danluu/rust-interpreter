"""Finish a post-case audit after lock timeout; never execute a workload command."""
import argparse
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
from full import CASES, audit_cases, next_case, verify_manifest, validate_checkpoint



def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES[1:4], required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--failed-supervisor', required=True)
    args = parser.parse_args()
    COUNT = CASES.index(args.case) + 1
    NAME = args.run_id
    FAILED = args.failed_supervisor
    assert NAME.startswith('runtime-composition-full-' + args.case + '-audit-') and Path(NAME).name == NAME
    assert FAILED.startswith('runtime-composition-full-' + args.case + '-') and Path(FAILED).name == FAILED
    assert NAME != FAILED
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        raw = ROOT / '.work/runtime-composition-full-02'
        outer = ROOT / '.work/experiments' / FAILED
        terminal = read(outer / 'status.json')
        assert terminal['status'] == 'finished' and terminal['returncode'] == 1
        assert terminal['owner'] == terminal['cwd'] == str(ROOT)
        assert sha(outer / 'command.log') == terminal['log_sha256']
        assert sha(outer / 'plan.json') == terminal['plan_sha256']
        log = (outer / 'command.log').read_text()
        assert log.startswith(args.case + ' correctness passed; gate True\n')
        assert log.rstrip().endswith('TimeoutError: timed out after 45s waiting for benchmark lock ' + str(ROOT / '.work/benchmark.lock'))
        assert "acquire_lock(lock,45);require_space(ROOT,8)" in log
        assert terminal['command'][-3:] == ['--through', args.case, '--resume']
        assert not (raw / f'checkpoint-{COUNT}.json').exists()
        assert not (ROOT / 'results/runtime-composition-full-02/summary.json').exists()
        plan = read(raw / 'plan.json')
        assert plan['owner'] == str(ROOT) and plan['cases'] == CASES
        verify_manifest(plan['frozen'])
        rows = read(raw / 'records.json')
        assert [row['case'] for row in rows] == CASES[:COUNT]
        proofs = []
        evidence = {}

        def bind(path, digest=None):
            actual = sha(path)
            assert digest is None or actual == digest, path
            evidence[str(path.relative_to(ROOT))] = actual

        for path in ['status.json', 'plan.json', 'command.log']:
            bind(outer / path)
        for row in rows:
            assert row['returncode'] == 0
            for stream in ['stdout', 'stderr']:
                bind(raw / (row['case'] + '.' + stream), row[stream + '_sha256'])
            result = ROOT / 'results' / ('runtime-composition-edit-' + row['case'] + '-02') / 'summary.json'
            bind(result, row['summary_sha256'])
            proofs.append(read(result))
        assert next_case(proofs) == CASES[COUNT] and all(p['gate_passed'] for p in proofs)
        # The preceding closed checkpoint must remain the exact prefix.
        previous = raw / f'closed-checkpoint-{COUNT-1}'
        assert read(previous / 'records.json') == rows[:COUNT-1]
        assert read(previous / 'plan.json') == plan
        assert validate_checkpoint(read(previous / f'checkpoint-{COUNT-1}.json'),
            sha(previous / 'plan.json'), sha(previous / 'records.json'), proofs[:COUNT-1])
        for path in ['plan.json', 'records.json']:
            bind(raw / path)
        for path in ['plan.json', 'records.json', f'checkpoint-{COUNT-1}.json']:
            bind(previous / path)
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        script = str(Path(__file__).relative_to(ROOT))
        assert hashlib.sha256(subprocess.check_output(['git', 'show', revision + ':' + script], cwd=ROOT)).hexdigest() == sha(Path(__file__))
        work = ROOT / '.work' / NAME
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision,
            script=script, script_sha256=sha(Path(__file__)), evidence=evidence,
            completed_cases=CASES[:COUNT], guest_commands=0, repeat_completed_cases=False))
        audit = audit_cases(CASES[:COUNT])
        verify_manifest(plan['frozen'])
        assert all(sha(ROOT / p) == h for p, h in evidence.items())
        write(raw / f'audit-{COUNT}.json', audit)
        checkpoint = dict(status='paused-between-cases', completed_cases=CASES[:COUNT],
            next_case=CASES[COUNT], plan_sha256=sha(raw / 'plan.json'),
            records_sha256=sha(raw / 'records.json'), audit_path=f'audit-{COUNT}.json',
            audit_sha256=sha(raw / f'audit-{COUNT}.json'), audit_recovery=NAME)
        assert validate_checkpoint(checkpoint, sha(raw / 'plan.json'), sha(raw / 'records.json'), proofs)
        write(raw / f'checkpoint-{COUNT}.json', checkpoint)
        result = ROOT / 'results' / NAME
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), checkpoint_sha256=sha(raw / f'checkpoint-{COUNT}.json'),
            audit_sha256=sha(raw / f'audit-{COUNT}.json'), original_supervisor=FAILED,
            original_terminal_sha256=sha(outer / 'status.json'), completed_cases=CASES[:COUNT],
            completed_commands=sum(p['commands'] for p in proofs), new_guest_commands=0,
            repeated_commands=0, all_frozen_inputs_verified=True, performance_measurement=False))
        print('Recovered checkpoint', COUNT, ':', sum(p['commands'] for p in proofs), 'retained commands, zero commands repeated', flush=True)


if __name__ == '__main__':
    main()
