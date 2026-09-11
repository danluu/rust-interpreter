#!/usr/bin/env python3
"""Verify repeated public edit measurements without assuming cross-cycle byte identity."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text())


def verify(report, reference=None):
    require(report['project'] != 'rg-aot', 'private runs need the private aggregate adapter')
    require(report['schema_version'] == 2, 'unsupported workflow schema')
    rows = read(ROOT / report['raw'] / 'records.json')
    transitions = read(ROOT / report['raw'] / 'source-transitions.json')
    cycles = report['cycles']
    edits = len(report['edits'])
    states = [0, -1, *range(1, edits + 1)]
    modes = ['native', 'baseline', 'candidate']
    expected = {(c, s, m) for c in range(cycles) for s in states for m in modes}
    actual = [(r['cycle'], r['state'], r['mode']) for r in rows]
    require(len(set(actual)) == len(actual) and set(actual) == expected, 'missing or duplicate samples')
    require(report['test_source_unchanged'] and report['wrong_production_edit_rejected'], 'source/test controls failed')
    require(len(transitions) == cycles * len(states), 'missing source transitions')
    require(all(t['content_changed'] for t in transitions if t['phase'] != 'cold'), 'unchanged warm sample')
    previous = dict.fromkeys(modes)
    artifacts = {}
    paths = set()
    for row in rows:
        cycle, state, mode = row['cycle'], row['state'], row['mode']
        phase = ('cold' if cycle == 0 else 'anchor') if state == 0 else ('wrong-edit' if state == -1 else 'edit')
        require(row['phase'] == phase, 'incorrect cold/anchor/edit label')
        require(row['previous_source_sha256'] == previous[mode], 'source history mismatch')
        if phase != 'cold':
            require(previous[mode] != row['source_sha256'], 'mode rebuilt unchanged source')
        previous[mode] = row['source_sha256']
        require(row['seconds'] > 0 and row['cpu_seconds'] > 0, 'invalid timing')
        cpu = sum(c['cpu']['user_seconds'] + c['cpu']['system_seconds'] for c in row['calls'])
        require(abs(cpu - row['cpu_seconds']) < 1e-8, 'CPU total does not match child calls')
        require(all((c['returncode'] == 0) == (state != -1) for c in row['calls']), 'unexpected command result')
        if mode != 'native':
            require(len(row['artifacts']) == 1, 'expected one batched artifact')
            artifact = row['artifacts'][0]
            path = artifact['path']
            require(path not in paths, 'repeated artifact path was overwritten')
            paths.add(path)
            digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            require(digest == artifact['sha256'], 'artifact hash mismatch')
            artifacts[cycle, state, mode] = digest
    for c in range(cycles):
        for s in states:
            selected = [r for r in rows if r['cycle'] == c and r['state'] == s]
            require(len({r['source_sha256'] for r in selected}) == 1, 'paired sources differ')
            require(all(r['tests'] == selected[0]['tests'] for r in selected), 'paired test selections differ')
            require(artifacts[c, s, 'baseline'] == artifacts[c, s, 'candidate'], 'paired bytecode differs')
    for s in states:
        require(len({r['source_sha256'] for r in rows if r['state'] == s}) == 1, 'repeated source state differs')
    if cycles == 3:
        for s in range(1, edits + 1):
            orders = [o['modes'] for o in report['mode_orders'] if o['state'] == s]
            for m in modes:
                require(sorted(o.index(m) for o in orders) == [0, 1, 2], 'unbalanced mode positions')
    require(len(report['comparison']['pairs']) == cycles * edits, 'missing edited pairs')
    require(len(report['cycle_anchor_seconds']) == cycles - 1, 'incorrect anchor count')
    require(report['cold_success_seconds'] == {r['mode']: r['seconds'] for r in rows if r['phase'] == 'cold'}, 'cold results contain warm anchors')
    cross_cycle = [{"state": s, "sha256_by_cycle": [artifacts[c, s, 'candidate'] for c in range(cycles)]} for s in states]
    history = None
    if reference:
        old = read(ROOT / reference['raw'] / 'records.json')
        require(report['case_sha256'] == reference['case_sha256'], 'reference case differs')
        comparisons = []
        for row in rows:
            matching = [r for r in old if r['state'] == row['state'] and r['mode'] == row['mode']]
            require(len(matching) == 1, 'reference must contain one cycle')
            prior = matching[0]
            require(prior['source_sha256'] == row['source_sha256'] and prior['tests'] == row['tests'], 'reference source/tests differ')
            if row['mode'] != 'native':
                comparisons.append(artifacts[row['cycle'], row['state'], row['mode']] == prior['artifacts'][0]['sha256'])
        history = dict(identical=sum(comparisons), different=len(comparisons) - sum(comparisons))
    return dict(schema_version=1, measurement_controls_verified=True,
        commands=len(rows), cycles=cycles, edited_pairs=cycles * edits,
        exact_artifact_hashes_verified=len(paths), paired_bytecode_identical=True,
        cross_cycle_bytecode_identical=all(len(set(x['sha256_by_cycle'])) == 1 for x in cross_cycle),
        cross_cycle_artifacts=cross_cycle, reference_bytecode=history,
        cross_cycle_semantic_equivalence_proven=False,
        note='Control verification does not imply identical compilation across cache histories or a performance claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--reference', type=Path)
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = verify(read(args.report), read(args.reference) if args.reference else None)
        with args.report.with_name('verification.json').open('x') as output:
            json.dump(result, output, indent=2)
            output.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
