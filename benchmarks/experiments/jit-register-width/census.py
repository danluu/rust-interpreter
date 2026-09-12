#!/usr/bin/env python3
"""Run the tested offline width census on qualified, restored real programs."""
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
    run = 'jit-register-width-census-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build_path = ROOT / 'results/jit-register-width-build-01/summary.json'
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed'
        assert all(c == dict(passed=334, ignored=1) for c in build['tests'].values())
        build_work = ROOT / build['raw']
        build_plan = json.loads((build_work / 'plan.json').read_text())
        assert sha(build_work / 'plan.json') == build['source_manifest_sha256']
        status_path = ROOT / '.work/experiments/jit-register-width-build-01/status.json'
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
        for case, reference in [('pgrust', 'filtered-workflow-pgrust-01'),
                                ('folded', 'filtered-workflow-folded-01'),
                                ('token', 'filtered-workflow-token-02')]:
            summary_path = ROOT / 'results' / reference / 'summary.json'
            summary = json.loads(summary_path.read_text())
            assert summary['status'] == 'passed' and summary['source_restored']
            records_path = ROOT / summary['raw'] / 'records.json'
            assert sha(records_path) == summary['records_sha256']
            rows = json.loads(records_path.read_text())
            matches = [r for r in rows if r['state'] == 6 and r['mode'] == 'automatic']
            assert len(matches) == 1 and matches[0]['returncode'] == 0
            row = matches[0]
            artifact = ROOT / row['artifact_path']
            assert sha(artifact) == row['artifact_sha256']
            frozen_paths += [summary_path, records_path, artifact]
            inputs.append(dict(case=case, artifact=str(artifact.relative_to(ROOT)),
                               artifact_sha256=sha(artifact), test_count=summary['test_count']))
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in frozen_paths}
        write(work / 'plan.json', dict(owner=str(ROOT), source_commit=build['source_commit'],
            controller_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            binary_sha256=sha(binary), frozen=frozen, inputs=inputs,
            scope='offline static feasibility; no guest execution or timing comparison'))
        records, summaries = [], []
        for item in inputs:
            require_space(ROOT, 8)
            report_path = work / (item['case'] + '.json')
            command = [str(binary), str(ROOT / item['artifact']), str(report_path)]
            child, stdout, stderr = capture(command, cwd=ROOT, env=os.environ.copy(),
                receipt_path=work / 'active.json', receipt=dict(case=item['case']))
            records.append(dict(case=item['case'], command=command, pid=child.pid,
                                returncode=child.returncode, stdout=stdout, stderr=stderr))
            write(work / 'records.json', records)
            assert child.returncode == 0, stderr
            report = json.loads(report_path.read_text())
            assert report['artifact_sha256'] == item['artifact_sha256']
            functions = report['functions']
            admitted = [f for f in functions if 'declined' not in f]
            extra = [f for f in admitted if len(f['packed']) > len(f['baseline'])]
            summary = dict(**item, functions=len(functions), admitted=len(admitted),
                declined=len(functions)-len(admitted), extra_assignment_functions=len(extra),
                baseline_assignments=sum(len(f['baseline']) for f in admitted),
                packed_assignments=sum(len(f['packed']) for f in admitted),
                baseline_static_reads=sum(f['baseline_static_reads'] for f in admitted),
                packed_static_reads=sum(f['packed_static_reads'] for f in admitted),
                report_sha256=sha(report_path))
            summaries.append(summary)
            print(json.dumps(summary), flush=True)
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / run
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', cases=summaries, commands=len(records),
            source_commit=build['source_commit'], binary_sha256=sha(binary), performance_measurement=False,
            limitation='Static operand counts are not dynamic traffic or a speedup estimate.',
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json')))


if __name__ == '__main__':
    main()
