#!/usr/bin/env python3
"""Qualify allocation trace transport with real exports and damaged sidecars."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from allocation_trace import selected_trace, validate_trace
from verify_repeated_workflow import require
from workflow_io import write_json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw, out = [ROOT / parent / args.run_id for parent in ['.work/runs', 'results']]
        require(not raw.exists() and not out.exists(), 'qualification already exists')
        raw.mkdir()
        report_path = ROOT / 'results/allocation-trace-fixtures-01/summary.json'
        report = json.loads(report_path.read_text())
        require(report['status'] == 'passed' and report['commands'] == 383, 'fixture qualification differs')
        inputs = [Path(__file__), ROOT / 'scripts/allocation_trace.py', report_path]
        real = []
        for fixture in report['fixtures']:
            artifact = ROOT / report['raw'] / fixture['fixture'] / 'enabled/program.rbc'
            trace = Path(str(artifact) + '.allocations.jsonl')
            require(sha(artifact) == fixture['artifact_sha256'] and sha(trace) == fixture['trace_sha256'],
                    'original fixture bytes changed')
            receipt = selected_trace(artifact)
            require(receipt['events'] == fixture['events'] and receipt['bytes'] == fixture['bytes'] and
                    receipt['sha256'] == fixture['trace_sha256'], 'real trace receipt differs')
            inputs += [artifact, trace]
            real.append(dict(fixture=fixture['fixture'], **receipt))
        frozen = {str(path.relative_to(ROOT)): sha(path) for path in inputs}
        artifact = raw / 'program.rbc'
        artifact.write_bytes(b'owned synthetic artifact binding fixture')
        digest = sha(artifact)
        header = dict(kind='allocation-trace', schema_version=1, strict_frontend=True, event=0)
        body = dict(kind='function', event=1)
        footer = dict(kind='complete', prior_events=2, artifact_sha256=digest, event=2)

        def encode(events):
            return b''.join(json.dumps(e, separators=(',', ':')).encode() + b'\n' for e in events)

        good = encode([header, body, footer])
        require(validate_trace(good, digest, max_bytes=len(good), max_events=3) == 3,
                'exact transport bounds rejected')
        rejected = []

        def reject(label, call):
            try:
                call()
            except (ValueError, RuntimeError, TypeError, RecursionError):
                rejected.append(label)
            else:
                raise RuntimeError('invalid diagnostic accepted: ' + label)

        cases = {
            'empty': b'',
            'missing-newline': good[:-1],
            'blank-record': good + b'\n',
            'missing-footer': encode([header, body]),
            'only-footer': encode([dict(footer, event=0, prior_events=0)]),
            'wrong-artifact': encode([header, body, dict(footer, artifact_sha256='0' * 64)]),
            'wrong-count': encode([header, body, dict(footer, prior_events=1)]),
            'trailing-event': good + encode([dict(body, event=3)]),
            'repeated-header': encode([header, dict(header, event=1), footer]),
            'non-strict': encode([dict(header, strict_frontend=False), body, footer]),
            'unknown-schema': encode([dict(header, schema_version=2), body, footer]),
            'boolean-schema': encode([dict(header, schema_version=True), body, footer]),
            'boolean-event': encode([header, dict(body, event=True), footer]),
            'boolean-footer-count': encode([header, body, dict(footer, prior_events=True)]),
            'skipped-event': encode([header, dict(body, event=2), footer]),
            'self-parent': encode([header, dict(body, parent=1), footer]),
            'future-parent': encode([header, dict(body, parent=2), footer]),
            'negative-parent': encode([header, dict(body, parent=-1), footer]),
            'boolean-parent': encode([header, dict(body, parent=False), footer]),
            'unknown-kind': encode([header, dict(body, kind='unknown'), footer]),
            'non-object': encode([header, [1], footer]),
            'nonfinite-number': encode([header, dict(body, value=float('nan')), footer]),
            'duplicate-field': good.replace(b'"event":1', b'"event":1,"event":1'),
            'invalid-utf8': good.replace(b'function', b'\xffunction'),
        }
        for label, data in cases.items():
            (raw / (label + '.jsonl')).write_bytes(data)
            reject(label, lambda data=data: validate_trace(data, digest))
        reject('one-byte-over-bound', lambda: validate_trace(good, digest, max_bytes=len(good) - 1))
        reject('one-event-over-bound', lambda: validate_trace(good, digest, max_events=2))
        reject('invalid-artifact-digest', lambda: validate_trace(good, 'not-a-digest'))
        sidecar = Path(str(artifact) + '.allocations.jsonl')
        reject('missing-sidecar', lambda: selected_trace(artifact))
        sidecar.write_bytes(good)
        require(selected_trace(artifact)['artifact_sha256'] == digest, 'selected sidecar binding differs')
        other = raw / 'other.jsonl'
        other.write_bytes(good)
        sidecar.unlink()
        sidecar.symlink_to(other)
        reject('symlink-sidecar', lambda: selected_trace(artifact))
        sidecar.unlink()
        os.mkfifo(sidecar)
        reject('fifo-sidecar', lambda: selected_trace(artifact))
        sidecar.unlink()
        sidecar.mkdir()
        reject('directory-sidecar', lambda: selected_trace(artifact))
        sidecar.rmdir()
        sidecar.write_bytes(good)
        with sidecar.open('r+b') as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
        reject('oversize-sidecar', lambda: selected_trace(artifact))
        sidecar.write_bytes(good)
        artifact.write_bytes(b'changed artifact')
        reject('changed-selected-artifact', lambda: selected_trace(artifact))
        require(all(sha(ROOT / path) == digest for path, digest in frozen.items()), 'frozen trace inputs changed')
        out.mkdir()
        write_json(out / 'summary.json', dict(status='passed', real_traces=real, rejections=rejected,
            exact_byte_and_event_bounds_passed=True, sources_sha256=frozen, raw=str(raw.relative_to(ROOT)),
            note='Transport and artifact binding only. Synthetic malformed records do not establish allocation semantics; real traces retain their independent original fixture qualification. No guest compilation or execution occurs here.'))
        print(json.dumps(dict(real_traces=len(real), rejections=len(rejected), exact_bounds=True)))


if __name__ == '__main__':
    main()
