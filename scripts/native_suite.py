#!/usr/bin/env python3
"""Build a native library test target once, then run each exact test in its own process."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

from interpreter import TOOLCHAIN
from workflow_controls import native_command
from workflow_io import capture


def test_status(name, returncode, stdout):
    """Zero matches, ignored bodies and abnormal exits cannot satisfy an assertion control."""
    summaries = re.findall(r'^test result: (ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored;', stdout, re.M)
    if summaries == [('ok', '1', '0', '0')] and returncode == 0 and f'test {name} ... ok' in stdout.splitlines():
        return 'passed'
    if summaries == [('FAILED', '0', '1', '0')] and returncode != 0 and f'test {name} ... FAILED' in stdout.splitlines():
        return 'failed'
    raise RuntimeError('native command did not execute exactly the requested test: ' + name)


def selected_executable(stdout, target):
    candidates = []
    for line in stdout.splitlines():
        event = json.loads(line)
        if (event.get('reason') == 'compiler-artifact' and event.get('profile', {}).get('test')
                and 'lib' in event.get('target', {}).get('kind', []) and event.get('executable')):
            candidates.append(Path(event['executable']))
    if len(candidates) != 1:
        raise RuntimeError('Cargo must report exactly one library test executable')
    path = candidates[0]
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(target.resolve()):
        raise RuntimeError('native test executable is outside the requested target')
    return path.resolve()


def execute(args, report):
    started = time.perf_counter()
    command = native_command(TOOLCHAIN, args.manifest_path, args.package, args.target_dir,
                             args.jobs, '1', [], timings=args.timings)
    command = command[:command.index('--')] + ['--no-run', '--message-format=json-render-diagnostics']
    receipt = args.suite_report.with_suffix('.active.json')
    before = time.perf_counter()
    child, stdout, stderr = capture(command, cwd=Path.cwd(), env=os.environ.copy(),
        receipt_path=receipt, receipt=dict(mode='native-suite-build'))
    report['build'] = dict(command=command, seconds=time.perf_counter()-before,
                           returncode=child.returncode, stdout=stdout, stderr=stderr)
    sys.stderr.write(stderr)
    if child.returncode:
        report['status'] = 'build-failed'
        return child.returncode
    executable = selected_executable(stdout, args.target_dir)
    report['executable'] = str(executable)
    for name in args.entry:
        command = [str(executable), '--exact', name, '--test-threads=1']
        before = time.perf_counter()
        child, stdout, stderr = capture(command, cwd=Path.cwd(), env=os.environ.copy(),
            receipt_path=receipt, receipt=dict(mode='native-suite-test', test=name))
        row = dict(name=name, command=command, seconds=time.perf_counter()-before,
                   returncode=child.returncode, stdout=stdout, stderr=stderr)
        report['tests'].append(row)
        sys.stdout.write(stdout); sys.stderr.write(stderr)
        row['status'] = test_status(name, child.returncode, stdout)
    failures = sum(t['status'] == 'failed' for t in report['tests'])
    report.update(status='failed' if failures else 'passed', passed=len(args.entry)-failures,
                  failed=failures, seconds_before_report_write=time.perf_counter()-started)
    return int(failures != 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-path', required=True, type=Path)
    parser.add_argument('--package', required=True)
    parser.add_argument('--target-dir', required=True, type=Path)
    parser.add_argument('--jobs', required=True, type=int, choices=range(1, 257))
    parser.add_argument('--test-threads', choices=['1'], default='1')
    parser.add_argument('--entry', action='append', required=True)
    parser.add_argument('--timings', action='store_true')
    parser.add_argument('--suite-report', required=True, type=Path)
    args = parser.parse_args()
    if not 1 <= len(args.entry) <= 10_000 or len(set(args.entry)) != len(args.entry) or any(not n or n.startswith('-') for n in args.entry):
        parser.error('entries must be distinct nonempty test names')
    report = dict(schema_version=1, mode='native', status='error', tests=[],
                  isolation='one native process per test', scope='explicit exact library test names')
    # Reserve before Cargo; preserve earlier evidence, including dangling links.
    with args.suite_report.open('x') as output:
        try:
            return execute(args, report)
        except Exception as error:
            report.update(status='error', error=str(error))
            raise
        finally:
            json.dump(report, output, indent=2)
            output.write('\n')


if __name__ == '__main__':
    sys.exit(main())
