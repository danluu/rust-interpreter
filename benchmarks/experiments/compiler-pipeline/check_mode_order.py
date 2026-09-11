#!/usr/bin/env python3
"""Check balanced initial orders against the archived scheduler and real receipts."""
import argparse
from copy import deepcopy
import fcntl
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from workflow_measurements import initial_modes, source_states
from verify_repeated_workflow import verify


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    raw = ROOT / '.work/runs' / args.run_id
    out = ROOT / 'results' / args.run_id
    require(not raw.exists() and not out.exists(), 'run already exists')
    raw.mkdir()
    archive = raw / 'legacy_measurements.py'
    archive.write_bytes(subprocess.check_output(['git', 'show', 'b9091eb:scripts/workflow_measurements.py'], cwd=ROOT))
    spec = importlib.util.spec_from_file_location('legacy_measurements', archive)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    original = 'fn entry() -> u64 { 0 }\n#[cfg(test)]\nmod tests { }\n'
    case = dict(negative=['bad', '{ 0 }', '{ 999 }'],
                edits=[[str(i), '{ ' + str(i - 1) + ' }', '{ ' + str(i) + ' }'] for i in range(1, 6)])
    defaults = ['native', 'baseline', 'candidate']
    configurations = 0
    for paired in [False, True]:
        modes = defaults if paired else ['native', 'interpreter', 'jit']
        for permutation in itertools.permutations(modes):
            order = initial_modes(modes, list(permutation))
            for cycles in [1, 3, 6, 15]:
                generated = list(source_states(original, case, cycles, order, paired))
                require(generated == list(legacy.source_states(original, case, cycles, order, paired)), 'scheduler extraction changed old behavior')
                require(generated[0]['modes'] == list(permutation), 'cold order differs from request')
                if cycles % 3 == 0:
                    for state in range(1, 6):
                        edited = [s for s in generated if s['state'] == state]
                        for mode in modes:
                            require([sum(s['modes'].index(mode) == p for s in edited) for p in range(3)] == [cycles // 3] * 3,
                                    'warm mode positions are unbalanced')
                configurations += 1
    bad_inputs = [[], ['native'], ['native', 'baseline', 'baseline'], ['native', 'baseline', 'unknown'],
                  ['native', 'baseline', 'candidate', 'extra'], ['native', 'baseline', False],
                  ['native', 'baseline', []], 'native,baseline,candidate', {'native': 0}]
    for value in bad_inputs:
        try:
            initial_modes(defaults, value)
        except ValueError:
            pass
        else:
            raise RuntimeError('bad initial order accepted')
    corpus = json.loads((ROOT / 'results/native-controls-corpus-01/summary.json').read_text())
    reports = [ROOT / row['report'] for row in corpus['workflows']]
    for row, path in zip(corpus['workflows'], reports):
        require(sha(path) == row['report_sha256'], 'corpus report changed')
    reports += [ROOT / 'results' / name / 'summary.json' for name in [
        'interface-pgrust-repeated-01', 'interface-nushell-repeated-01',
        'lightweight-wrapper-pgrust-qualification-01', 'lightweight-wrapper-nushell-qualification-01']]
    histories = []
    for path in reports:
        report = json.loads(path.read_text())
        actual = verify(report)
        expected = json.loads(path.with_name('verification.json').read_text())
        require(all(actual[k] == expected[k] for k in actual if k != 'reference_bytecode'), 'historical verification changed')
        histories.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path), verification=actual))
    base = json.loads(reports[-1].read_text())
    for order in [list(reversed(defaults)), ['native', 'baseline', 'baseline']]:
        altered = deepcopy(base)
        altered['initial_mode_order'] = order
        try:
            verify(altered)
        except (RuntimeError, ValueError):
            pass
        else:
            raise RuntimeError('false mode-order claim accepted')
    cli_rejections = []
    for order in ['native,baseline,baseline', 'native,baseline', 'candidate,baseline,unknown']:
        command = [sys.executable, str(ROOT / 'scripts/bench_e2e_workflow.py'), '--baseline-tool-key', 'a' * 64,
                   '--initial-mode-order', order]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        require(result.returncode == 2 and 'initial mode order must contain' in result.stderr and not result.stdout,
                'CLI did not reject order before resolving tools/compiling')
        cli_rejections.append(dict(command=command, returncode=result.returncode, stderr=result.stderr))
    out.mkdir()
    paths = [Path(__file__), ROOT / 'scripts/workflow_measurements.py', ROOT / 'scripts/workflow_case_file.py',
             ROOT / 'scripts/bench_e2e_workflow.py', ROOT / 'scripts/verify_repeated_workflow.py']
    (out / 'summary.json').write_text(json.dumps(dict(status='passed', scheduler_configurations=configurations,
        malformed_order_inputs=len(bad_inputs), false_receipts_rejected=2, cli_rejections=cli_rejections,
        historical_reports=histories, archived_scheduler_sha256=sha(archive),
        source_hashes={str(p.relative_to(ROOT)): sha(p) for p in paths},
        project_compiled_or_executed=False, project_sources_mutated=False), indent=2) + '\n')
    print(json.dumps(dict(scheduler_configurations=configurations, historical_reports=len(histories),
                         malformed_orders=len(bad_inputs), false_receipts=2, cli_rejections=len(cli_rejections))))


if __name__ == '__main__':
    main()
