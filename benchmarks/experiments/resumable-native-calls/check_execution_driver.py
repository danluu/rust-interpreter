#!/usr/bin/env python3
"""Check driver staging and reject mislabelled historical VM commands."""
import argparse
import copy
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from qualify_native_execution import stage_validator, verify_vm_options, verify_binary_provenance, OPTIONS, sha, require, write


def check_binary_provenance(tool):
    vm, exporter, wrapper = 'rust-interp-vm', 'rust-interp-mir-export', 'rust-interp-rustc-wrapper'
    binaries = {vm: '1' * 64, exporter: '2' * 64, wrapper: '3' * 64}
    rows = [dict(command=[str(tool / name)]) for name in [vm, exporter]]
    inputs = {str((tool / name).relative_to(ROOT)): binaries[name] for name in [vm, exporter]}
    for manifest in [binaries, {name: binaries[name] for name in [vm, exporter]}]:
        result = verify_binary_provenance(rows, tool, manifest, inputs)
        require(result['directly_invoked_binaries'] == {name: binaries[name] for name in [vm, exporter]} and
                result['other_installed_binaries'] == ({wrapper: binaries[wrapper]} if wrapper in manifest else {}),
                'legacy/current binary provenance classification differs')
    with_wrapper = [*rows, dict(command=[str(tool / wrapper)])]
    wrapper_inputs = {**inputs, str((tool / wrapper).relative_to(ROOT)): binaries[wrapper]}
    result = verify_binary_provenance(with_wrapper, tool, binaries, wrapper_inputs)
    require(result['directly_invoked_binaries'] == binaries and not result['other_installed_binaries'],
            'an actually invoked and recorded wrapper was not verified')
    rejected = []
    cases = []
    for name in [vm, exporter]:
        key = str((tool / name).relative_to(ROOT))
        cases.append(('missing-' + name, rows, binaries, {p: h for p, h in inputs.items() if p != key}))
        cases.append(('wrong-hash-' + name, rows, binaries, {**inputs, key: '0' * 64}))
        changed = copy.deepcopy(rows)
        changed[[vm, exporter].index(name)]['command'][0] = str(tool.parent / 'wrong-tool' / name)
        cases.append(('wrong-directory-' + name, changed, binaries, inputs))
    cases += [
        ('unused-wrapper-labelled-as-invoked', rows, binaries, wrapper_inputs),
        ('invoked-wrapper-not-recorded', with_wrapper, binaries, inputs),
        ('invoked-wrapper-not-installed', with_wrapper, {vm: binaries[vm], exporter: binaries[exporter]}, wrapper_inputs),
        ('unknown-tool-invoked', [*rows, dict(command=[str(tool / 'unexpected-binary')])], binaries, inputs),
        ('missing-exporter-execution', rows[:1], binaries, inputs),
        ('missing-vm-execution', rows[1:], binaries, inputs),
    ]
    for label, commands, manifest, recorded in cases:
        try:
            verify_binary_provenance(commands, tool, manifest, recorded)
        except RuntimeError:
            rejected.append(label)
        else:
            raise RuntimeError('accepted false provenance: ' + label)
    return dict(positive_configurations=3, rejected=rejected)


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
        manifest = json.loads((tool / 'ready.json').read_text())
        with path.open() as commands:
            provenance = verify_binary_provenance((json.loads(line) for line in commands),
                tool, manifest, run['detail']['inputs_sha256'])
        bad = {**options, 'jit_resumable_calls': True, 'jit_persistent_registers': True}
        try:
            verify_vm_options(path, tool, bad)
        except RuntimeError as error:
            require(str(error) == 'captured VM option differs', 'unexpected rejection')
        else:
            raise RuntimeError('accepted historical commands as resumable')
        rows.append(dict(mode=mode, counts=counts, binary_provenance=provenance, false_new_mode_rejected=True))
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
    provenance_checks = check_binary_provenance(tool)
    write(out / 'summary.json', dict(status='passed', historical=rows, staging=stages,
        binary_provenance_checks=provenance_checks,
        frozen={str(p.relative_to(ROOT)): sha(p) for p in paths}, evidence=evidence,
        performance_measurement=False, full_validator_executed=False))
    print(json.dumps(dict(status='passed', historical_modes=len(rows), staged_modes=len(stages))))


if __name__ == '__main__':
    main()
