#!/usr/bin/env python3
"""Inspect preserved typed comparisons and raw literal occurrences; execute no guest code."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
REPORT = 'results/interface-nushell-artifact-diff-01/summary.json'
RAW = '.work/runs/interface-nushell-artifact-diff-01'
LITERAL = b'Expected OneOf'
PIN = '9d3157963241cf89447119d34d6e887859f5e7e8'
SOURCE = 'crates/nu-protocol/src/ty.rs'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def positions(payload, needle):
    result = []
    start = payload.find(needle)
    while start >= 0:
        result.append(start)
        start = payload.find(needle, start + 1)
    return result


def inspect():
    report_bytes = (ROOT / REPORT).read_bytes()
    report = json.loads(report_bytes)
    require([c['state'] for c in report['comparisons']] == [0, -1, 1], 'comparison matrix differs')
    source = subprocess.check_output(['git', 'show', PIN + ':' + SOURCE],
                                    cwd=ROOT / '.work/sources/nushell')
    source_lines = [index for index, line in enumerate(source.splitlines(), 1) if LITERAL in line]
    comparisons = []
    for comparison in report['comparisons']:
        state = comparison['state']
        path = f'{RAW}/command-{state}.json'
        receipt_bytes = (ROOT / path).read_bytes()
        receipt = json.loads(receipt_bytes)
        require(receipt['returncode'] == 0 and receipt['stderr'] == '', 'typed comparison failed')
        typed = json.loads(receipt['stdout'])
        require(typed['data']['lengths'] == comparison['data_lengths'] and
                len(typed['changed_functions']) == comparison['changed_functions'] and
                sum(f['changed_common_ops'] for f in typed['changed_functions']) == comparison['changed_ops'] and
                sum(f['non_immediate_changes'] for f in typed['changed_functions']) == 0,
                'typed comparison no longer matches preserved summary')
        artifacts = []
        for artifact in comparison['artifacts']:
            payload = (ROOT / artifact['path']).read_bytes()
            require(digest(payload) == artifact['sha256'], 'artifact changed')
            artifacts.append(dict(**artifact, literal_file_offsets=positions(payload, LITERAL)))
        counts = Counter()
        reported = 0
        distinguished = []
        for function in typed['changed_functions']:
            require(function['headers_identical'], 'function header differs')
            for operation in function['first_op_changes']:
                values = []
                destinations = []
                for side in ['a', 'b']:
                    match = re.fullmatch(r'Imm \{ dst: (\d+), value: (\d+) \}', operation[side])
                    require(match is not None, 'reported opcode is not the expected immediate')
                    destinations.append(int(match[1]))
                    values.append(int(match[2]))
                require(destinations[0] == destinations[1] and all(v < 1 << 128 for v in values),
                        'immediate register or width differs')
                low = [value & ((1 << 64) - 1) for value in values]
                high = [value >> 64 for value in values]
                counts[low[1] - low[0]] += 1
                reported += 1
                if function['a']['name'] == 'ty::tests::oneof_flattening::test_oneof_deduplicates[]':
                    distinguished.append(dict(function_index=function['index'], name=function['a']['name'],
                        pc=operation['pc'], values=values, low64=low, high64=high))
        comparisons.append(dict(state=state, typed_receipt=path, typed_receipt_sha256=digest(receipt_bytes),
            artifacts=artifacts, data_lengths=typed['data']['lengths'],
            first_data_changes=typed['data']['first_changes'],
            changed_ops=comparison['changed_ops'], reported_prefix_ops=reported,
            reported_prefix_low64_deltas=[dict(delta=k, count=v) for k, v in sorted(counts.items())],
            deduplicates_test_immediates=distinguished))
    return dict(schema_version=1, status='completed read-only inspection', equivalence_proof=False,
        input_report=REPORT, input_report_sha256=digest(report_bytes),
        driver_sha256=digest(Path(__file__).read_bytes()),
        source=dict(revision=PIN, path=SOURCE, sha256=digest(source), literal_lines=source_lines),
        literal=LITERAL.decode(), literal_bytes=len(LITERAL), comparisons=comparisons,
        note='Literal counts search the entire serialized file; file offsets are not guest addresses. '
             'Immediate deltas cover only the bounded prefixes in the earlier typed report, not all changes. '
             'Packed halves are numeric observations, not a pointer classification. No artifact is normalized, '
             'replaced or executed; no compiler cache is read or changed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid run ID')
    output = ROOT / 'results' / args.run_id
    require(not output.exists(), 'result already exists')
    result = inspect()
    output.mkdir()
    (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], report=str(output.relative_to(ROOT) / 'summary.json'))))


if __name__ == '__main__':
    main()
