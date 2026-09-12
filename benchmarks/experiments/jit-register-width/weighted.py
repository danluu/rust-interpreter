#!/usr/bin/env python3
"""Bind historical whole-run counters to their exact typed programs and census."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    run = 'jit-register-width-weighted-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build_path = ROOT / 'results/jit-register-width-build-02/summary.json'
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed'
        assert all(c == dict(passed=337, ignored=1) for c in build['tests'].values())
        build_work = ROOT / build['raw']
        build_plan = json.loads((build_work / 'plan.json').read_text())
        assert sha(build_work / 'plan.json') == build['source_manifest_sha256']
        status_path = ROOT / '.work/experiments/jit-register-width-build-02/status.json'
        status = json.loads(status_path.read_text())
        assert status['status'] == 'finished' and status['returncode'] == 0
        assert sha(status_path.with_name('command.log')) == status['log_sha256']
        assert all(sha(ROOT / p) == h for p, h in build_plan['frozen'].items())
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        binary = work / 'rust-interp-register-census'
        original_binary = Path(build_plan['target']) / 'release' / binary.name
        shutil.copy2(original_binary, binary)
        assert sha(binary) == sha(original_binary)
        frozen_paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), build_path,
                        build_work / 'plan.json', build_work / 'commands.json', status_path,
                        status_path.with_name('command.log'), binary]
        inputs = []
        for case in ['token', 'folded']:
            summary_path = ROOT / 'results' / ('resumable-bulk-' + case + '-transitions-01') / 'summary.json'
            summary = json.loads(summary_path.read_text())
            assert summary['status'] == 'passed' and not summary['performance_measurement']
            assert summary['options']['jit_resumable_calls'] and summary['options']['jit_persistent_registers']
            process = summary['process']
            assert process['status'] == 'finished' and process['returncode'] == 0 and process['cwd'] == str(ROOT)
            command = process['command']
            artifact = Path(command[-1])
            profile = Path(command[command.index('--profile') + 1])
            assert sha(artifact) == summary['artifact_sha256'] and sha(Path(command[0])) == summary['vm_sha256']
            assert str(profile.relative_to(ROOT)) in summary['evidence']
            assert all(sha(ROOT / p) == h for p, h in summary['evidence'].items())
            frozen_paths += [summary_path, artifact, Path(command[0])] + [ROOT / p for p in summary['evidence']]
            inputs.append(dict(case=case, artifact=str(artifact.relative_to(ROOT)),
                artifact_sha256=sha(artifact), profile=str(profile.relative_to(ROOT)), profile_sha256=sha(profile),
                producer_vm_sha256=summary['vm_sha256'], statistics=summary['statistics']))
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in frozen_paths}
        write(work / 'plan.json', dict(owner=str(ROOT), source_commit=build['source_commit'],
            controller_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            binary_sha256=sha(binary), frozen=frozen, inputs=inputs,
            scope='offline feasibility using exact older programs and their instrumented profiles, not the expanded twelve-test token suite or current runtime timing'))
        records, summaries = [], []
        for item in inputs:
            require_space(ROOT, 8)
            report_path = work / (item['case'] + '.json')
            command = [str(binary), str(ROOT / item['artifact']), str(report_path), str(ROOT / item['profile'])]
            child, stdout, stderr = capture(command, cwd=ROOT, env=os.environ.copy(),
                receipt_path=work / 'active.json', receipt=dict(case=item['case']))
            records.append(dict(case=item['case'], command=command, pid=child.pid,
                                returncode=child.returncode, stdout=stdout, stderr=stderr))
            write(work / 'records.json', records)
            assert child.returncode == 0, stderr
            report = json.loads(report_path.read_text())
            assert report['artifact_sha256'] == item['artifact_sha256'] and report['profile_sha256'] == item['profile_sha256']
            functions = report['functions']
            totals = {key:sum(f.get(key, 0) for f in functions) for key in [
                'native_operation_executions', 'interpreted_operation_executions', 'native_read_operands',
                'baseline_native_read_operands', 'packed_native_read_operands',
                'baseline_live_native_block_entries', 'packed_live_native_block_entries']}
            assert totals['native_operation_executions'] == item['statistics']['jit_instructions']
            assert totals['native_operation_executions'] + totals['interpreted_operation_executions'] == item['statistics']['instructions']
            extra = totals['packed_native_read_operands'] - totals['baseline_native_read_operands']
            ranked = sorted((f for f in functions if f.get('packed_native_read_operands', 0) > f.get('baseline_native_read_operands', 0)),
                            key=lambda f:f['packed_native_read_operands']-f['baseline_native_read_operands'], reverse=True)
            top = [dict(function=f['function'], name=f['name'], baseline=f['baseline'], packed=f['packed'],
                        extra_read_operands=f['packed_native_read_operands']-f['baseline_native_read_operands']) for f in ranked[:12]]
            summary = dict(case=item['case'], artifact_sha256=item['artifact_sha256'], profile_sha256=item['profile_sha256'],
                totals=totals, additional_native_read_operands=extra,
                additional_fraction_of_all_native_reads=extra/totals['native_read_operands'],
                extra_assignment_hot_functions=len(ranked), top_extra_functions=top, report_sha256=sha(report_path))
            summaries.append(summary)
            print(item['case'], 'additional read fraction', summary['additional_fraction_of_all_native_reads'], flush=True)
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / run
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', cases=summaries, commands=len(records),
            source_commit=build['source_commit'], binary_sha256=sha(binary), performance_measurement=False,
            limitation='Historical whole-run operand counts do not model the existing block cache, generated instruction cost, or the expanded token suite. Block-entry liveness includes internal native edges, not just spills.',
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json')))


if __name__ == '__main__':
    main()
