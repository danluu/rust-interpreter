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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from summarize_owned_sample import summarize, require, runtime_options
from attribute_generated_sample import attribute, dump_options


def canonical(value):
    # JSON records encode Python tuple address ranges as arrays.
    return json.loads(json.dumps(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ('.', '..'), 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    rows, evidence = [], {}
    for name in ['native-code-folded-sample-01', 'native-code-token-sample-02',
                 'persistent-folded-sample-01', 'persistent-token-sample-01']:
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
            bad_plan['jit_resumable_calls'] = True
            bad_dump['resumable_calls'] = True
            for check in [lambda: runtime_options(bad_plan, [command]),
                          lambda: dump_options(bad_dump, command),
                          lambda: runtime_options(plan, [command + ['--jit-resumable-calls']]),
                          lambda: dump_options(dump, command + ['--jit-resumable-calls'])]:
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
        false_option_checks=48, incompatible_range_checks=range_checks, cli_checks=cli_checks,
        frozen={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        performance_measurement=False), indent=2) + '\n')
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
