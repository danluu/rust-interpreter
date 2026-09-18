"""Apply the predeclared component-screen rule without selecting observations."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def assess(path):
    payload = path.read_bytes()
    receipt = json.loads(payload)
    if receipt['status'] != 'passed' or len(receipt['children']) != 27:
        raise ValueError('complete successful control and comparison execution required')
    observations = receipt['observations']
    if len(observations) != 26 or sum(row['warmup'] for row in observations) != 2:
        raise ValueError('complete fixed observation history required')
    pairs = []
    for index in range(12):
        rows = [row for row in observations if not row['warmup'] and row['pair'] == index]
        if len(rows) != 2 or {row['mode'] for row in rows} != {'baseline', 'candidate'}:
            raise ValueError('missing or duplicate paired observation')
        rows.sort(key=lambda row: row['child_index'])
        expected = ['baseline', 'candidate'] if index % 2 == 0 else ['candidate', 'baseline']
        if [row['mode'] for row in rows] != expected:
            raise ValueError('execution order differs from alternating plan')
        baseline = next(row for row in rows if row['mode'] == 'baseline')
        candidate = next(row for row in rows if row['mode'] == 'candidate')
        for name in ['runtime_key', 'identity_digest', 'std_key', 'runtime_sysroot', 'std_sysroot']:
            if baseline[name] != candidate[name]:
                raise ValueError('paired installation identity differs')
        pairs.append(dict(pair=index, first=rows[0]['mode'],
            wall=candidate['lookup_seconds'] - baseline['lookup_seconds'],
            cpu=candidate['lookup_cpu_seconds'] - baseline['lookup_cpu_seconds']))
    metrics = {}
    for metric in ['wall', 'cpu']:
        differences = [pair[metric] for pair in pairs]
        order_medians = {first: statistics.median(pair[metric] for pair in pairs if pair['first'] == first)
                         for first in ['baseline', 'candidate']}
        metrics[metric] = dict(median_paired_difference_seconds=statistics.median(differences),
            faster_pairs=sum(value < 0 for value in differences), order_medians=order_medians)
    passed = all(row['median_paired_difference_seconds'] < 0 and row['faster_pairs'] >= 10
                 and all(value < 0 for value in row['order_medians'].values()) for row in metrics.values())
    return dict(receipt_sha256=hashlib.sha256(payload).hexdigest(), execution_status=receipt['status'],
        component_adoption_rule_passed=passed, metrics=metrics, pairs=pairs,
        application_performance_qualified=False, holdout_performance_qualified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.receipt), sort_keys=True, indent=2))
