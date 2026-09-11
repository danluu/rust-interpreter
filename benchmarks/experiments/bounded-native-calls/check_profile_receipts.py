#!/usr/bin/env python3
"""Recheck saved generated-code reports without overwriting historical evidence."""
import argparse
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import struct

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from summarize_owned_sample import summarize, require, runtime_options
from attribute_generated_sample import (attribute, dump_options, classify_words,
    ZERO_BULK, ZERO_BULK_PREFIX, ZERO_RANGE)


def canonical(value):
    # JSON records encode Python tuple address ranges as arrays.
    return json.loads(json.dumps(value))


def check_bulk_pattern():
    def classify(words, enabled=True):
        return classify_words(struct.pack('<' + 'I' * len(words), *words), resumable=enabled)

    classes, counts = classify(ZERO_BULK)
    require(classes == ['native_zero_bulk'] * len(ZERO_BULK_PREFIX) +
            ['native_zero_range'] * len(ZERO_RANGE), 'bulk/tail categories overlap or miss words')
    require(counts == {'native_zero_bulk': 1, 'native_zero_range': 1}, 'incorrect exact loop counts')
    classes, counts = classify(ZERO_BULK, enabled=False)
    require('native_zero_bulk' not in classes and 'native_zero_bulk' not in counts,
            'bulk recognized outside resumable ABI')
    rejected = 0
    for index in range(len(ZERO_BULK)):
        for bit in range(32):
            changed = list(ZERO_BULK)
            changed[index] ^= 1 << bit
            classes, counts = classify(changed)
            require('native_zero_bulk' not in classes and 'native_zero_bulk' not in counts,
                    'inexact bulk sequence classified')
            rejected += 1
    for size in range(len(ZERO_BULK)):
        classes, counts = classify(ZERO_BULK[:size])
        require('native_zero_bulk' not in classes and 'native_zero_bulk' not in counts,
                'truncated bulk sequence classified')
        rejected += 1
    padding = (0xd503201f,)
    words = padding + ZERO_BULK + padding + ZERO_BULK + padding
    classes, counts = classify(words)
    require(counts == {'native_zero_bulk': 2, 'native_zero_range': 2}, 'adjacent sequences miscounted')
    require(all(classes[i] == 'other_generated' for i in [0, 21, 42]), 'padding reclassified')
    return dict(exact_sequences=2, mutated_or_truncated_rejections=rejected,
                non_resumable_rejection=True, disjoint_tail=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ('.', '..'), 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    bulk_pattern_checks = check_bulk_pattern()
    rows, evidence = [], {}
    for name in ['native-code-folded-sample-01', 'native-code-token-sample-02',
                 'persistent-folded-sample-01', 'persistent-token-sample-01',
                 'resumable-folded-sample-01', 'resumable-token-sample-01']:
        summary = ROOT / 'results' / name / 'summary.json'
        attribution = summary.with_name('generated-attribution.json')
        old = json.loads(summary.read_text())
        generated = json.loads(attribution.read_text())
        require(len(old['samples']) == len(generated['samples']) == 3, 'missing windows')
        for sample, previous in zip(old['samples'], generated['samples']):
            folder = ROOT / '.work' / name / str(sample['index'])
            current = summarize(folder)
            require(canonical(current) == sample, 'saved sample counts changed')
            require(canonical(attribute(folder, current)) == previous, 'saved attribution changed')
            plan = json.loads((folder.parent / 'plan.json').read_text())
            command = json.loads((folder / 'record.json').read_text())['identity']['command']
            runtime_options(plan, [command])
            dump = json.loads((folder / 'jit-code/map.json').read_text())
            bad_plan, bad_dump = copy.deepcopy(plan), copy.deepcopy(dump)
            enabled = '--jit-resumable-calls' in command
            bad_plan['jit_resumable_calls'] = not enabled
            bad_dump['resumable_calls'] = not enabled
            bad_command = ([word for word in command if word != '--jit-resumable-calls'] if enabled
                           else command + ['--jit-resumable-calls'])
            for check in [lambda: runtime_options(bad_plan, [command]),
                          lambda: dump_options(bad_dump, command),
                          lambda: runtime_options(plan, [bad_command]),
                          lambda: dump_options(dump, bad_command)]:
                try:
                    check()
                except RuntimeError:
                    pass
                else:
                    raise RuntimeError('accepted false resumable option')
        rows.append(dict(run_id=name, windows=3, sample_counts_unchanged=True, attribution_unchanged=True))
        for path in [summary, attribution]:
            evidence[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    # Validate the new mode without fabricating process evidence. Full positive
    # code/PC checks happen on the subsequent actual process captures.
    command = ['--jit-resumable-calls', '--jit-persistent-registers']
    plan = dict(jit_resumable_calls=True, jit_persistent_registers=True)
    dump = dict(resumable_calls=True, persistent_registers=True,
                ranges=[dict(kind=k) for k in ['resumable_region', 'resumable_call', 'resumable_return']])
    require(runtime_options(plan, [command])['jit_resumable_calls'], 'resumable flag missing')
    require(dump_options(dump, command), 'resumable dump flag missing')
    range_checks = 0
    for kind in ['ordinary_region', 'call_stub', 'native_tree', 'unknown']:
        bad = copy.deepcopy(dump)
        bad['ranges'].append(dict(kind=kind))
        try:
            dump_options(bad, command)
        except RuntimeError:
            range_checks += 1
        else:
            raise RuntimeError('accepted incompatible code range')
    sampler = ROOT / 'scripts/sample_owned_vm.py'
    cli_checks = []
    for extra in [[], ['--jit-native-calls'], ['--jit-native-call-stubs']]:
        argv = [sys.executable, str(sampler)]
        if not extra:
            argv += ['--help']
        else:
            argv += ['--tool-key', 'unused', '--artifact', 'unused', '--artifact-sha256', 'unused',
                     '--run-id', 'unused', '--jit-resumable-calls', *extra]
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=30)
        expected = 'cannot be combined' if extra else '--jit-resumable-calls'
        require(result.returncode == (2 if extra else 0) and expected in result.stdout + result.stderr,
                'sampler CLI did not enforce mode')
        cli_checks.append(dict(command=argv, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    paths = [Path(__file__), sampler, ROOT / 'scripts/summarize_owned_sample.py', ROOT / 'scripts/attribute_generated_sample.py']
    for path in paths:
        compile(path.read_text(), str(path), 'exec')
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    (out / 'summary.json').write_text(json.dumps(dict(status='passed', checks=rows, evidence=evidence,
        false_option_checks=len(rows) * 3 * 4, incompatible_range_checks=range_checks,
        bulk_pattern_checks=bulk_pattern_checks, cli_checks=cli_checks,
        frozen={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        performance_measurement=False), indent=2) + '\n')
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
