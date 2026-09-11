#!/usr/bin/env python3
"""Count archived validator commands without conflating commands and test cases."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(command, work):
    executable = Path(command[0])
    if executable.name == 'rust-interp-vm':
        if '--engine' not in command:
            return 'vm-default-rejection'
        engine = command[command.index('--engine') + 1]
        if engine not in ['interpreter', 'jit']:
            raise RuntimeError('unknown VM engine')
        return 'vm-' + engine
    if executable.name == 'rust-interp-mir-export':
        return 'exporter'
    if executable.name in ['rustc', 'cargo']:
        return 'native-build'
    if executable.is_absolute() and executable.is_relative_to(work):
        return 'native-execution'
    raise RuntimeError('unclassified validation command')


def count_commands(path, work):
    counts, outcomes = Counter(), Counter()
    with path.open() as records:
        for line in records:
            row = json.loads(line)
            kind = classify(row['command'], work)
            counts[kind] += 1
            outcomes[(kind, row['returncode'])] += 1
    return dict(commands=sum(counts.values()), counts=dict(counts),
                outcomes=[dict(kind=k, returncode=c, commands=n) for (k, c), n in sorted(outcomes.items())])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('invalid run ID')
    source = args.summary.resolve()
    if not source.is_relative_to(ROOT):
        parser.error('expected a workspace receipt')
    summary = json.loads(source.read_text())
    evidence = {str(source.relative_to(ROOT)): sha(source)}
    modes, total = {}, Counter()
    for mode, run in summary['runs'].items():
        detail = run['detail']
        work = (ROOT / detail['raw']).resolve()
        if not work.is_relative_to(ROOT / '.work'):
            raise RuntimeError('unexpected archived validator directory')
        records = work / 'commands.jsonl'
        digest = sha(records)
        result = count_commands(records, work)
        if result['commands'] != detail['completed_commands'] or sha(records) != digest:
            raise RuntimeError('incomplete or changed command archive')
        modes[mode] = result
        total.update(result['counts'])
        evidence[str(records.relative_to(ROOT))] = digest
    if sum(total.values()) != summary['commands'] or sha(source) != evidence[str(source.relative_to(ROOT))]:
        raise RuntimeError('aggregate command count or receipt changed')
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    (out / 'summary.json').write_text(json.dumps(dict(status='verified', modes=modes,
        counts=dict(total), commands=sum(total.values()), evidence=evidence,
        script_sha256=sha(Path(__file__)), performance_measurement=False,
        limitation='Command counts are not unique cases or native comparison counts. Some native invocations emit many oracle values. Failed exits include intentional rejection checks; no new execution occurred.'), indent=2) + '\n')
    print(json.dumps(dict(commands=sum(total.values()), counts=dict(total))))


if __name__ == '__main__':
    main()
