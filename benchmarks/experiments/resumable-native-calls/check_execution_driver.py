#!/usr/bin/env python3
"""Check driver staging and reject mislabelled historical VM commands."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from qualify_native_execution import stage_validator, verify_vm_options, OPTIONS, sha, require, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    reference = ROOT / '.work/local-memory-forwarding-native-01/summary.json'
    old = json.loads(reference.read_text())
    tool = ROOT / '.work/interpreter-tools' / old['key']
    rows, evidence = [], {str(reference.relative_to(ROOT)): sha(reference)}
    for mode, run in old['runs'].items():
        path = ROOT / run['detail']['raw'] / 'commands.jsonl'
        options = dict.fromkeys(OPTIONS, False)
        counts = verify_vm_options(path, tool, options)
        bad = {**options, 'jit_resumable_calls': True, 'jit_persistent_registers': True}
        try:
            verify_vm_options(path, tool, bad)
        except RuntimeError as error:
            require(str(error) == 'captured VM option differs', 'unexpected rejection')
        else:
            raise RuntimeError('accepted historical commands as resumable')
        rows.append(dict(mode=mode, counts=counts, false_new_mode_rejected=True))
        evidence[str(path.relative_to(ROOT))] = sha(path)
    source = ROOT / 'scripts/validate_interpreter.py'
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    stages = []
    for flags in [[], ['--jit-resumable-calls', '--jit-persistent-registers'],
                  ['--jit-native-calls', '--jit-native-call-stubs', '--jit-persistent-registers']]:
        text, replacements = stage_validator(source, tool, flags)
        # stage_validator verifies every existing Assert AST is unchanged;
        # the complete real execution will qualify positive flag propagation.
        stages.append(dict(flags=flags, replacements=replacements, assertions_unchanged=True))
    paths = [Path(__file__), source, ROOT / 'scripts/qualify_native_execution.py',
             ROOT / 'scripts/audit_validation_counts.py', ROOT / 'scripts/interpreter.py']
    write(out / 'summary.json', dict(status='passed', historical=rows, staging=stages,
        frozen={str(p.relative_to(ROOT)): sha(p) for p in paths}, evidence=evidence,
        performance_measurement=False, full_validator_executed=False))
    print(json.dumps(dict(status='passed', historical_modes=len(rows), staged_modes=len(stages))))


if __name__ == '__main__':
    main()
