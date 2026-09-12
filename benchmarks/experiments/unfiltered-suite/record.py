#!/usr/bin/env python3
"""Preserve the native baseline failure and identify the actual target gap."""
from collections import Counter
import fcntl
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/tuned-native'))
from timing import read, require, sha
from native_results import SUMMARY, libtest_summary
from workflow_io import write_json as write


def main():
    work = ROOT / '.work/fre-unfiltered-native-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        supervisor = ROOT / '.work/experiments/fre-unfiltered-native-01'
        terminal = read(supervisor / 'status.json')
        require(terminal['status'] == 'finished' and terminal['returncode'] == 1 and
                sha(supervisor / 'command.log') == terminal['log_sha256'], 'supervisor is not verified terminal')
        plan = read(work / 'plan.json')
        require(all(sha(ROOT / p) == h for p, h in plan['frozen'].items()), 'frozen inputs changed')
        require(sha(ROOT / '.work/sources/fre/crates/fre-kernels/src/token_phrase.rs') == sha(work / 'original.rs'), 'source not restored')
        rows = read(work / 'records.json')
        require(len(rows) == 1 and rows[0]['state'] == 0 and rows[0]['returncode'] == 101, 'unexpected failure phase')
        row = rows[0]
        for stream in ['stdout', 'stderr']:
            require(sha(ROOT / row[stream]) == row[stream + '_sha256'], 'native output changed')
        stdout, stderr = [(ROOT / row[stream]).read_text() for stream in ['stdout', 'stderr']]
        matches = list(SUMMARY.finditer(stdout))
        targets = re.findall(r'^\s*(?:Running (.*?) \([^\n]*\)|Doc-tests (\S+))\s*$', stderr, re.M)
        require(len(matches) == len(targets) == 12, 'unexpected target inventory')
        inventory = []
        previous = 0
        for match, (target, doc) in zip(matches, targets):
            summary = libtest_summary(match.group(0), success=match.group(1) == 'ok')
            names = dict(re.findall(r'^test (\S+) \.\.\. (ok|FAILED|ignored)(?:,.*)?$', stdout[previous:match.start()], re.M))
            inventory.append(dict(target=target or ('Doc-tests ' + doc), kind='doc' if doc else 'unit' if target.startswith('unittests') else 'integration',
                                  summary=summary, names=names))
            previous = match.end()
        require(all(i['summary']['failed'] == 0 for i in inventory[:-1]) and inventory[-1]['summary']['failed'] == 1,
                'failure is not confined to the doc test')
        require('Some expected error codes were not found: ["E0451"]' in stdout, 'doc diagnostic differs')
        history_path = ROOT / 'results/aggregate-relocation-fre-01/summary.json'
        history = read(history_path)
        bodies = {}
        for batch in history['records']:
            replay = read(ROOT / batch['replay'])
            path = ROOT / replay['raw'] / 'results.json'
            require(sha(path) == batch['evidence'][str(path.relative_to(ROOT))], 'old replay outcomes changed')
            for result in read(path):
                require(result['entry'] not in bodies, 'duplicate replay body')
                bodies[result['entry']] = result['status']
        require(set(bodies) == set(inventory[0]['names']), 'library inventory changed')
        require(dict(Counter(bodies.values())) == {'passed': 382, 'ignored': 7}, 'historical coverage changed')
        require(all(inventory[0]['names'][n] == ('ok' if outcome == 'passed' else 'ignored') for n, outcome in bodies.items()), 'library outcome differs')
        write(work / 'inventory.json', dict(native=inventory, historical_custom=bodies))
        counts = {key: sum(i['summary'][key] for i in inventory) for key in ['passed', 'failed', 'ignored', 'filtered']}
        out = ROOT / 'results/fre-unfiltered-native-01'
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='native-baseline-failed', raw=str(work.relative_to(ROOT)),
            native_commands=1, real_edit_commands=0, returncode=101, source_restored=True,
            all_processes_terminal=True, counts=counts, command_seconds=row['seconds'], cpu=row['cpu'],
            inventory_sha256=sha(work / 'inventory.json'), records_sha256=sha(work / 'records.json'),
            targets=[{k: v for k, v in i.items() if k != 'names'} for i in inventory],
            custom_library_inventory_exact=True, historical_custom_report=str(history_path.relative_to(ROOT)),
            historical_custom_counts=history['counts'], unqualified_integration_tests=52, unqualified_doc_tests=3,
            failure='Compile-fail doctest rejected its Rust code, but the pinned nightly omitted the expected E0451 diagnostic code.',
            note='Unfiltered Cargo command failed on original source; wrong and valid edit commands were not started. Its 9.615s duration is failure latency, not a successful edit-to-suite benchmark. The historical custom replay covers exactly the library target, excluding ten integration targets and doc tests.'))
        (out / 'assessment.md').write_text('''# Unfiltered fre baseline exposes target and doc-test gaps

The actual `cargo test -p fre-kernels` command failed on the original source.
It passed **382 unit tests and 52 integration tests**, with seven ignored unit
tests. Two doc tests passed; the third failed. Total: 436 passed, one failed,
seven ignored, zero filtered. The controller stopped before either production
edit and restored source; all processes are terminal.

The failed compile-fail doc test expects `E0451`. Rustc rejected its private-field
construction, but this pinned nightly omitted that error code. Rustdoc therefore
correctly reports that the expected diagnostic was missing. Original assertions
and test attributes remain untouched. This is a native baseline incompatibility,
not an engine regression. The 9.615s command duration is failure latency, not a
successful edit-to-suite measurement.

The native library inventory exactly matches all 389 names in the retained
custom replay: 382 passed and seven ignored. But the unfiltered command also
runs **ten integration-test executables containing 52 tests**, plus three doc
tests. Those are outside the custom replay. The historical body result therefore
does not establish whole-crate coverage, even before libtest/thread semantics.

Priority: add explicit Cargo integration-test target selection to the exporter/
launcher, then qualify those actual assertions. Handle doc-test compilation as
a separate rustdoc/compiler workflow with its original expected-error rules.
Keep this baseline failure visible. Do not remove the expected code, skip docs,
or describe a library-only command as the complete suite. Cached JIT and shared
multi-entry exports remain useful, but target selection comes first for this
concrete coverage gap.
''')
        print(counts, 'integration gap: 52 tests / 10 targets; doc gap: 3 tests')


if __name__ == '__main__':
    main()
