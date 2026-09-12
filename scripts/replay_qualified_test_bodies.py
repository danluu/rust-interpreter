#!/usr/bin/env python3
"""Replay a complete qualified public test list through the existing survey."""
import argparse
from collections import Counter
import os
from pathlib import Path
import subprocess
import sys
import time

from interpreter import ROOT, installed_tools
from qualify_test_bodies import OPTIONS, read, require, sha, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualification', type=Path, required=True)
    parser.add_argument('--vm-tool-key', required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    parent_path = args.qualification.resolve()
    parent = read(parent_path)
    require(parent['status'] == 'passed' and parent['strict_frontend'], 'parent qualification did not pass')
    require(parent['project'] in ['pgrust', 'fre', 'nushell', 'ruff'], 'expected a public corpus qualification')
    require(parent['original_sources_and_tests_unchanged'], 'parent source changed')
    require(not parent['failures'] and not parent['outcome_changes'], 'parent has unresolved outcomes')
    tools, key = installed_tools(args.vm_tool_key)
    binaries = read(tools / 'ready.json')
    for name in ['rust-interp-mir-export', 'rust-interp-rustc-wrapper']:
        require(binaries[name] == parent['tool_binaries'][name], 'replay requires the same qualified frontend')
    previous = read(ROOT / parent['raw'] / 'results.json')
    require(len(previous) == parent['selected'] == parent['discovered'], 'parent selection incomplete')
    by_entry = {r['entry']: r for r in previous}
    require(len(by_entry) == len(previous), 'duplicate parent entries')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    paths = [Path(__file__), ROOT / 'scripts/survey_audit_execution.py', ROOT / 'scripts/qualify_test_bodies.py',
             ROOT / 'scripts/interpreter.py', parent_path, ROOT / parent['raw'] / 'results.json', tools / 'ready.json']
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    # Parent records bind collection summaries, exact reports, prior outcomes,
    # original native control, selected names and command archives by hash.
    for batch in parent['records']:
        for path, digest in batch['evidence'].items():
            require(path not in frozen or frozen[path] == digest, 'conflicting parent evidence')
            frozen[path] = digest
    write(work / 'plan.json', dict(parent=str(parent_path.relative_to(ROOT)), parent_tool=parent['tool_key'],
        candidate_tool=key, binaries=binaries, frozen=frozen, runtime_options=parent['runtime_options'],
        instruction_limit=parent['instruction_limit'], allocation_limit=parent['allocation_limit'],
        fresh_exports=False, fresh_native_processes=True, performance_measurement=False))

    def verify():
        require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'qualified evidence changed')
        installed_tools(key)

    status = dict(status='starting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), completed=[])
    write(work / 'status.json', status)
    results, batches = [], []
    try:
        verify()
        for batch in parent['records']:
            index = batch['index']
            run = args.run_id + '-batch-' + str(index).zfill(3)
            report_path = work / 'reports' / str(index).zfill(3) / 'summary.json'
            command = [sys.executable, str(ROOT / 'scripts/survey_audit_execution.py'),
                '--run-id', run, '--collection', str(ROOT / batch['collection']), '--vm-tool-key', key,
                '--native-control-provenance', str(ROOT / batch['native_control']),
                '--instruction-limit', str(parent['instruction_limit']), '--allocation-limit', str(parent['allocation_limit']),
                '--lock-wait-seconds', '45', '--report-directory', str(report_path.parent)]
            command += ['--' + name.replace('_', '-') for name in OPTIONS if parent['runtime_options'][name]]
            with (work / (str(index).zfill(3) + '.log')).open('x') as output:
                child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
                status.update(status='running', batch=index, child_pid=child.pid, command=command, child_started_at=time.time(),
                    child_identity=subprocess.run(['ps', '-p', str(child.pid), '-o', 'pid,ppid,lstart,tty,command'],
                        capture_output=True, text=True).stdout)
                write(work / 'status.json', status)
                print('START', index, child.pid, flush=True)
                code = child.wait()
            status.update(child_returncode=code, child_finished_at=time.time())
            write(work / 'status.json', status)
            require(code == 0, 'replay child failed; log retained')
            report = read(report_path)
            rows_path = ROOT / report['raw'] / 'results.json'
            rows = read(rows_path)
            original_rows = read(ROOT / read(ROOT / batch['replay'])['raw'] / 'results.json')
            require(sorted(r['entry'] for r in rows) == sorted(r['entry'] for r in original_rows), 'batch selection differs')
            for row in rows:
                old = by_entry[row['entry']]
                require(row['status'] == old['status'], 'test outcome changed: ' + row['entry'])
                require(row.get('artifact_sha256') == old.get('artifact_sha256'), 'executed artifact changed')
            require(report['tool_key'] == key and report['tool_binaries'] == binaries, 'VM identity differs')
            require(report['runtime_options'] == parent['runtime_options'], 'runtime options differ')
            require(report['native_binary_sha256'] == batch['native_binary_sha256'], 'native control differs')
            results.extend(rows)
            batches.append(dict(index=index, report=str(report_path.relative_to(ROOT)),
                evidence={str(p.relative_to(ROOT)): sha(p) for p in [report_path, rows_path, ROOT / report['raw'] / 'commands.jsonl']}))
            write(work / 'results.json', results)
            write(work / 'batches.json', batches)
            status['completed'].append(index)
            write(work / 'status.json', status)
            verify()
            print('PASS', index, dict(Counter(r['status'] for r in rows)), flush=True)
        require(sorted(r['entry'] for r in results) == sorted(by_entry), 'complete selection differs')
        require(dict(Counter(r['status'] for r in results)) == parent['counts'], 'complete outcome counts differ')
        summary = dict(status='passed', tool_key=key, binaries=binaries, project=parent['project'],
            revision=parent['revision'], counts=parent['counts'], selected=len(results), batches=batches,
            raw=str(work.relative_to(ROOT)), fresh_exports=False, fresh_native_processes=parent['counts'].get('passed', 0),
            unchanged_artifacts=True, outcome_changes=[], performance_measurement=False,
            scope='Original qualified bytecode and assertions with a new VM; fresh native processes using the verified same-pin executable. Body coverage, not full libtest semantics.',
            evidence={str(p.relative_to(ROOT)): sha(p) for p in [work / 'plan.json', work / 'results.json', work / 'batches.json']})
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', summary)
        status.update(status='finished', returncode=0, finished_at=time.time())
        write(work / 'status.json', status)
    except Exception as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__':
    main()
