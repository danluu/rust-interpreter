"""Analyze two retained owned samples; never start or repeat a guest execution."""
import argparse
import os
import sys
from common import ROOT, KEY, VM, read, verify, terminal, run_name, acquire_lock, sha, require_space, write
from workflow_io import capture
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/scalar-runtime-sampling'))
from attribute import attribute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True, type=run_name)
    parser.add_argument('--block-supervisor')
    parser.add_argument('--exhaustive-supervisor')
    args = parser.parse_args()
    supervisors = dict(block=args.block_supervisor, exhaustive=args.exhaustive_supervisor)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        raw = ROOT / '.work' / args.run_id
        plan = read(raw / 'plan.json')
        assert plan['tool_key'] == KEY and plan['vm_sha256'] == VM
        assert plan['guest_commands'] == 2 and plan['reused_controls'] == 9
        verify(plan)
        assert sha(ROOT / plan['archived_vm_sources']) == plan['archived_vm_sources_sha256']
        evidence = {}
        rows, reports = [], []
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        assert not (raw / 'analysis-records.json').exists()
        for case in plan['cases']:
            name = case['run_id']
            supervisor = supervisors[case['label']] or name
            assert supervisor == name or supervisor.startswith(name + '-admission-')
            outer, _ = terminal(supervisor, case['command'])
            for file in ['status.json', 'plan.json', 'command.log']:
                path = outer / file
                evidence[str(path.relative_to(ROOT))] = sha(path)
            sample = ROOT / '.work' / name
            sampled_plan, sampled_summary = read(sample / 'plan.json'), read(sample / 'summary.json')
            assert sampled_plan['tool_key'] == sampled_summary['tool_key'] == KEY
            assert sampled_plan['vm_sha256'] == sampled_summary['vm_sha256'] == VM
            assert sampled_plan['repetitions'] == 1 and sampled_plan['sample_seconds'] == 3
            assert sampled_plan['expected_jit_declines'] == 0
            assert sampled_plan['selection']['name'] == case['test']
            assert all(sampled_plan[k] is True for k in ['jit_persistent_registers', 'jit_resumable_calls', 'jit_scalar_calls', 'jit_operation_map', 'dump_code'])
            record, = read(sample / 'records.json')
            assert record['identity']['status'] == 'finished' and record['identity']['returncode'] == 0
            command = record['identity']['command']
            assert '--profile' not in command and '--profile-test' not in command and '--jit-indirect-calls' not in command
            assert record['statistics']['jit_declined_functions'] == 0
            assert len(sampled_summary['records']) == 1 and sampled_summary['source_unchanged']
            assert all(sha(sample / '0' / p) == h for p, h in record['files'].items())
            for file in ['plan.json', 'summary.json', 'records.json', '0/record.json']:
                path = sample / file
                evidence[str(path.relative_to(ROOT))] = sha(path)
            # Summary and attribution consume retained data only, under this lock.
            require_space(ROOT, 8)
            child, out, err = capture(case['summary_command'], cwd=ROOT, env=env,
                receipt_path=raw / 'active-analysis.json', receipt=dict(stage=case['label'] + ' summary'))
            label = case['label']
            (raw / (label + '.stdout')).write_text(out)
            (raw / (label + '.stderr')).write_text(err)
            rows.append(dict(label=label, command=case['summary_command'], pid=child.pid,
                returncode=child.returncode, stdout_sha256=sha(raw / (label + '.stdout')),
                stderr_sha256=sha(raw / (label + '.stderr'))))
            write(raw / 'analysis-records.json', rows)
            assert child.returncode == 0, err
            assert sha(ROOT / case['profile']) == case['profile_sha256']
            report = attribute(name, ROOT / case['profile'], VM)
            reports.append(dict(case=label, run_id=name, **report))
            verify(plan)
            print(label, report['by_label'], flush=True)
        write(raw / 'sample-evidence.json', evidence)
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', tool_key=KEY, vm_sha256=VM,
            guest_commands=2, new_guests_during_analysis=0, summary_commands=2,
            reused_controls=9, cases=reports, raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw / 'plan.json'), records_sha256=sha(raw / 'analysis-records.json'),
            sample_evidence_sha256=sha(raw / 'sample-evidence.json'),
            archived_vm_sources_sha256=plan['archived_vm_sources_sha256'],
            all_frozen_inputs_verified=True, ordinary_entropy=True,
            profile_used_for_static_identity_only=True, performance_measurement=False))


if __name__ == '__main__':
    main()
