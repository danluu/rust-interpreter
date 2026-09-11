#!/usr/bin/env python3
"""Check origin queries against the preserved, execution-qualified allocation traces."""
import argparse
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import inspect_allocation_origins as inspector
from verify_repeated_workflow import require
from workflow_io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid qualification ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw, out = ROOT / '.work/runs' / args.run_id, ROOT / 'results' / args.run_id
        require(not raw.exists() and not out.exists(), 'qualification identity exists')
        raw.mkdir()
        base = ROOT / '.work/runs/allocation-trace-fixtures-01'
        static_trace = base / 'static/enabled/program.rbc.allocations.jsonl'
        static_artifact = base / 'static/enabled/program.rbc'
        tls_trace = base / 'tls/enabled/program.rbc.allocations.jsonl'
        tls_artifact = base / 'tls/enabled/program.rbc'
        paths = [Path(__file__), Path(inspector.__file__), Path(__file__).with_name('check_allocation_trace.py'),
                 static_trace, static_artifact, tls_trace, tls_artifact]
        frozen = {str(p.relative_to(ROOT)): inspector.sha(p) for p in paths}
        needle = (113).to_bytes(8, 'little')
        static = inspector.inspect(static_trace, static_artifact, needle)
        require(len(static['matches']) == 1, 'original IMMUTABLE allocation count differs')
        match = static['matches'][0]
        origins = match['origins']
        require(match['materialization']['mutable'] is False and len(origins) == 3 and
                [origin['request']['cache_hit'] for origin in origins] == [False, True, True],
                'one materialization and repeated cached references were not preserved')
        require(origins[0]['allocation_kind'][0]['definition'] == 'IMMUTABLE' and
                any(event['kind'] == 'relocation' for event in origins[0]['ancestry']) and
                all(origin['function']['definition'] == 'rust_interp_entry' and
                    origin['function']['instance_kind'] for origin in origins),
                'static definition, recursive relocation or function context is missing')
        tls = inspector.inspect(tls_trace, tls_artifact, (5).to_bytes(8, 'little'))
        require(len(tls['matches']) == 6, 'equal-content allocations were collapsed')
        mutable_tls = [m for m in tls['matches'] if m['materialization']['tls_definition'] is not None]
        require(len(mutable_tls) == 2 and
                {m['materialization']['tls_definition'].split('::')[0] for m in mutable_tls} == {'LEFT', 'RIGHT'} and
                len({m['materialization']['pointer'] for m in mutable_tls}) == 2 and
                all(m['materialization']['mutable'] for m in mutable_tls), 'equal TLS values lost distinct identity')
        partial = inspector.inspect(static_trace, static_artifact, b'\x07' + b'\0' * 63)
        require(partial['matches'] == [], 'uninitialized padding became a fully initialized match')
        missing = inspector.inspect(static_trace, static_artifact, b'not an allocation in this original fixture')
        require(missing['matches'] == [], 'absent query reported a match')
        rejected = []

        def rejects(label, operation):
            try:
                operation()
            except RuntimeError as error:
                rejected.append(dict(label=label, error=str(error)))
            else:
                raise RuntimeError('invalid origin query succeeded: ' + label)

        rejects('wrong artifact binding', lambda: inspector.inspect(static_trace, tls_artifact, needle))
        for label, value in [('empty query', b''), ('oversized query', b'x' * 4097), ('nonbyte query', 'text')]:
            rejects(label, lambda: inspector.inspect(static_trace, static_artifact, value))
        for name, value in [('MAX_MATCHES', 0), ('MAX_REQUESTS', 2), ('MAX_ANCESTRY_EVENTS', 0), ('MAX_REPORT_BYTES', 1)]:
            with patch.object(inspector, name, value):
                rejects(name, lambda: inspector.inspect(static_trace, static_artifact, needle))
        size = len((json.dumps(static, indent=2) + '\n').encode())
        with patch.object(inspector, 'MAX_REPORT_BYTES', size):
            require(inspector.check_report_size(static) == size, 'exact report byte boundary differs')
        with patch.object(inspector, 'MAX_REPORT_BYTES', size - 1):
            rejects('report indentation and newline count', lambda: inspector.check_report_size(static))
        events = [json.loads(line) for line in static_trace.read_text().splitlines()]
        duplicate = deepcopy(next(event for event in events if event['kind'] == 'function'))
        events.insert(-1, duplicate)
        for index, event in enumerate(events):
            event['event'] = index
        events[-1]['prior_events'] = len(events) - 1
        altered = raw / 'repeated-function.jsonl'
        altered.write_text(''.join(json.dumps(event) + '\n' for event in events))
        rejects('repeated function identity', lambda: inspector.inspect(altered, static_artifact, needle))
        require(all(inspector.sha(ROOT / p) == h for p, h in frozen.items()), 'original inputs or inspector source changed')
        out.mkdir()
        write_json(out / 'summary.json', dict(status='passed', static_query=static, tls_query=tls,
            partial_initialization_excluded=True, missing_query_empty=True, exact_report_byte_boundary_verified=True, rejected=rejected,
            frozen_sha256=frozen, raw=str(raw.relative_to(ROOT)),
            note='Queries use original execution-qualified traces. No source fixture, compiler cache, bytecode or guest execution behavior changed.'))
        print(json.dumps(dict(status='passed', static_origins=len(origins), equal_content_allocations=len(tls['matches']),
            distinct_mutable_tls=len(mutable_tls), rejections=len(rejected))))


if __name__ == '__main__':
    main()
