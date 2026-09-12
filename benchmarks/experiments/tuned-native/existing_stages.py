#!/usr/bin/env python3
"""Recover coarse native stages from the retained histories, without rerunning."""
import fcntl
import hashlib
import json
from pathlib import Path
import statistics
import sys

from native_results import libtest_summary, residual_seconds

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from workflow_io import write_json


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT / 'results/native-existing-stages-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = read(ROOT / 'benchmarks/current-status.json')
        results = []
        for group in ['primary', 'heldout']:
            for case in read(ROOT / manifest[group])['cases']:
                report_path = ROOT / 'results' / case['run_id'] / 'summary.json'
                report = read(report_path)
                records_path = ROOT / report['raw'] / 'records.json'
                rows = read(records_path)
                native = [r for r in rows if r['mode'] == 'native' and r['state'] > 0]
                custom = {(r['cycle'], r['state']): r for r in rows
                          if r['mode'] == 'candidate' and r['state'] > 0}
                if len(native) != 15 or len(custom) != 15:
                    raise RuntimeError('incomplete retained history')
                samples = []
                for row in native:
                    peer = custom[row['cycle'], row['state']]
                    if row['source_sha256'] != peer['source_sha256'] or len(row['calls']) != 1:
                        raise RuntimeError('unmatched source or multiple native calls')
                    call = row['calls'][0]
                    if call['returncode']:
                        raise RuntimeError('failed edited native command')
                    suite = libtest_summary(call['stdout'], selected=len(row['tests']))
                    launches = [c['launch'] for c in peer['calls']]
                    samples.append(dict(cycle=row['cycle'], state=row['state'],
                        native_seconds=row['seconds'], suite=suite,
                        non_libtest=residual_seconds(row['seconds'], suite),
                        custom_seconds=peer['seconds'],
                        custom_cargo_seconds=sum(c['cargo_seconds'] for c in launches),
                        custom_execution_seconds=sum(c['execution_seconds'] for c in launches)))
                median = lambda name: statistics.median(s[name] for s in samples)
                result = dict(label=case['label'], edited_samples=len(samples),
                    harnesses=sorted({s['suite']['harness'] for s in samples}),
                    median_native_seconds=median('native_seconds'),
                    median_suite_rounded_seconds=statistics.median(s['suite']['rounded_seconds'] for s in samples),
                    median_non_libtest_bounds={k: statistics.median(s['non_libtest'][k] for s in samples)
                                              for k in ['lower', 'upper']},
                    median_custom_seconds=median('custom_seconds'),
                    median_custom_cargo_seconds=median('custom_cargo_seconds'),
                    median_custom_execution_seconds=median('custom_execution_seconds'),
                    source_report=str(report_path.relative_to(ROOT)), source_report_sha256=sha(report_path),
                    source_records_sha256=sha(records_path))
                results.append(result)
        out.mkdir(exist_ok=False)
        write_json(out / 'summary.json', dict(status='passed', cases=results,
            native_commands=135, new_commands=0,
            parser_sha256=sha(Path(__file__).with_name('native_results.py')),
            note='Suite intervals reflect two-decimal display rounding. Residual includes Cargo, compilation, link, process startup and harness overhead. Custom execution has a different scope and includes VM startup/JIT compilation. Private names/source/raw output remain local.'))
        lines = ['# Native stage attribution from retained commands', '',
            'Parsed the original stdout for all 135 successful edited native commands. No builds or tests were rerun. These are the same histories as STATUS, with each row retaining its own controls.', '',
            '| Workflow | Native command | Native suite | Outside suite | Custom Cargo | Custom execution |',
            '| --- | ---: | ---: | ---: | ---: | ---: |']
        for r in results:
            bounds = r['median_non_libtest_bounds']
            lines.append(f"| {r['label']} | {r['median_native_seconds']:.3f}s | {r['median_suite_rounded_seconds']:.2f}s | {bounds['lower']:.3f}–{bounds['upper']:.3f}s | {r['median_custom_cargo_seconds']:.3f}s | {r['median_custom_execution_seconds']:.3f}s |")
        lines += ['',
            'The native harnesses report rounded suite duration; 0.00s means an interval from zero to about 5ms. Nushell type-relations uses a grouped harness; the other rows use libtest. Outside-suite time is a residual, not pure compile time. Custom execution includes VM startup and JIT compilation, so these execution columns are not identical scopes. Per-stage medians need not sum to command medians.', '',
            'This narrows the hybrid question to Cargo targets. Selecting native tests still requires compiling their library-test executable. A per-test runtime threshold that omits that cost is not a valid command-time estimate. The current batch records do not contain per-test guest times or a qualified shared native/export compilation path, so they cannot establish a mixed-test policy or a never-slower guarantee.', '']
        (out / 'assessment.md').write_text('\n'.join(lines))
        print('\n'.join(lines))


if __name__ == '__main__':
    main()
