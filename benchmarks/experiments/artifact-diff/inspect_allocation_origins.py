#!/usr/bin/env python3
"""Find exact initialized allocation contents and their request origins in one export."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_repeated_workflow import require
from workflow_io import write_json
from check_allocation_trace import verify_trace, sha

MAX_MATCHES = 256
MAX_REQUESTS = 1000
MAX_ANCESTRY_EVENTS = 10000
MAX_REPORT_BYTES = 64 * 1024 * 1024


def check_report_size(result):
    # Match write_json's indentation, escaping and trailing newline, stopping
    # before constructing a potentially huge fully expanded report string.
    size = 1
    for chunk in json.JSONEncoder(indent=2).iterencode(result):
        size += len(chunk.encode())
        require(size <= MAX_REPORT_BYTES, 'allocation query report byte limit reached')
    return size


def inspect(trace, artifact, needle):
    require(isinstance(needle, bytes) and 1 <= len(needle) <= 4096, 'query must contain 1..4096 bytes')
    before = {str(path): sha(path) for path in [trace, artifact]}
    validation = verify_trace(trace, artifact)
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    functions = {event['index']: event for event in events if event['kind'] == 'function'}
    require(len(functions) == sum(event['kind'] == 'function' for event in events), 'repeated function identity in trace')
    children, allocations, thread_locals = {}, {}, {}
    for event in events:
        children.setdefault(event.get('parent'), []).append(event)
        if event['kind'] == 'allocation-request':
            allocations.setdefault(event['allocation_id'], []).append(event)
        elif event['kind'] == 'tls-request':
            thread_locals.setdefault(event['definition_id'], []).append(event)

    def brief(event):
        return {key: value for key, value in event.items() if key not in ['bytes_hex', 'initialized_bits_hex']}

    ancestry_events = 0

    def lineage(event):
        nonlocal ancestry_events
        result = []
        parent = event.get('parent')
        while parent is not None:
            ancestry_events += 1
            require(ancestry_events <= MAX_ANCESTRY_EVENTS, 'allocation query ancestry limit reached')
            result.append(brief(events[parent]))
            parent = events[parent].get('parent')
        return list(reversed(result))

    matches, request_count = [], 0
    for event in events:
        if event['kind'] != 'materialization' or event['bytes_hex'] != needle.hex():
            continue
        if sum(bin(byte).count('1') for byte in bytes.fromhex(event['initialized_bits_hex'])) != event['size']:
            continue
        allocation_id = event['allocation_id']
        if allocation_id is not None:
            requests = allocations[allocation_id]
        else:
            definition_id = events[event['parent']]['definition_id']
            requests = thread_locals[definition_id]
        request_count += len(requests)
        require(len(matches) < MAX_MATCHES and request_count <= MAX_REQUESTS, 'allocation query match/request limit reached')
        origins = []
        for request in requests:
            details = [brief(e) for e in children.get(request['event'], []) if e['kind'] == 'allocation-kind']
            origins.append(dict(request=brief(request), allocation_kind=details,
                function=functions.get(request.get('function_index')), ancestry=lineage(request)))
        matches.append(dict(materialization=brief(event), fully_initialized=True, origins=origins))
    require(all(sha(Path(path)) == digest for path, digest in before.items()), 'trace or artifact changed during inspection')
    result = dict(status='verified inspection', query_hex=needle.hex(), exact_whole_allocation_match=True,
        matches=matches, validation=validation, input_sha256=before,
        limits=dict(matches=MAX_MATCHES, requests=MAX_REQUESTS, ancestry_events=MAX_ANCESTRY_EVENTS, report_bytes=MAX_REPORT_BYTES),
        note='Origins and compiler IDs belong to this one export. Function indices precede optimization. Equal initialized contents do not establish interchangeable allocation identity; no deduplication or equivalence is inferred.')
    check_report_size(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--artifact', type=Path, required=True)
    query = parser.add_mutually_exclusive_group(required=True)
    query.add_argument('--literal', help='UTF-8 bytes of the exact allocation')
    query.add_argument('--hex', help='exact bytes in hexadecimal')
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid inspection ID')
    trace, artifact = args.trace.resolve(strict=True), args.artifact.resolve(strict=True)
    require(trace.is_relative_to(ROOT) and artifact.is_relative_to(ROOT), 'expected workspace trace and artifact')
    needle = args.literal.encode() if args.literal is not None else bytes.fromhex(args.hex)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out = ROOT / 'results' / args.run_id
        require(not out.exists(), 'inspection identity exists')
        result = inspect(trace, artifact, needle)
        result['sources'] = {str(p.relative_to(ROOT)): sha(p) for p in
            [Path(__file__), Path(__file__).with_name('check_allocation_trace.py')]}
        check_report_size(result)
        out.mkdir()
        write_json(out / 'summary.json', result)
        print(json.dumps(dict(status=result['status'], matching_allocations=len(result['matches']),
            request_origins=sum(len(m['origins']) for m in result['matches']))))


if __name__ == '__main__':
    main()
