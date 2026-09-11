#!/usr/bin/env python3
"""Recheck saved generated-code reports without overwriting historical evidence."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from summarize_owned_sample import summarize, require
from attribute_generated_sample import attribute


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
        rows.append(dict(run_id=name, windows=3, sample_counts_unchanged=True, attribution_unchanged=True))
        for path in [summary, attribution]:
            evidence[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    paths = [Path(__file__), ROOT / 'scripts/summarize_owned_sample.py', ROOT / 'scripts/attribute_generated_sample.py']
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    (out / 'summary.json').write_text(json.dumps(dict(status='passed', checks=rows, evidence=evidence,
        frozen={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        performance_measurement=False), indent=2) + '\n')
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
