#!/usr/bin/env python3
"""Original 33 transport cases plus both public APIs on four owned real traces."""
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from qualification_outcomes import setup, owned, guard, proof, require, load, capture, lossless, exception, modules


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(raw):
    require(raw.resolve() == raw and raw.is_dir(), "synthetic tree is indirect")
    names = sorted(raw.iterdir())
    require(len(names) <= 32, "synthetic file inventory bound")
    return {p.name: proof(p) for p in names}


def main():
    c = setup()
    module = load(c["source_root"], c["arm"])
    selected_trace, validate_trace = module.selected_trace, module.validate_trace
    output = Path(c["output_root"])
    raw = owned(c["synthetic_root"], output)
    if c["arm"] == "baseline":
        require(not raw.exists() and not raw.is_symlink(), "fresh synthetic tree required")
        guard(output)
        raw.mkdir(mode=0o700)
        synthetic_before = {}
    else:
        baseline = json.loads(Path(c["baseline_report"]).read_bytes())
        require(baseline["arm"] == "baseline" and baseline["status"] == "PASS",
                "complete baseline replay receipt required")
        synthetic_before = tree(raw)
        require(synthetic_before == baseline["synthetic_after"], "synthetic baseline state changed")
        # Only reset the exact known ordinary sidecar after verifying every owned file.
        # Original case setup then overwrites the same named artifact/case files.
        sidecar = raw / "program.rbc.allocations.jsonl"
        require(proof(sidecar) == synthetic_before[sidecar.name], "sidecar reset identity changed")
        guard(output)
        sidecar.unlink()
    fixtures = json.loads(Path(c["fixture_descriptor"]).read_bytes())["fixtures"]
    real = []
    for name in ("caller", "scalar_constant", "static", "tls"):
        expected = fixtures[name]
        artifact, trace = Path(expected["artifact_path"]), Path(expected["path"])
        before = {str(p): proof(p) for p in (artifact, trace)}
        validated = capture(lambda: validate_trace(trace.read_bytes(), expected["artifact_sha256"]))
        selected = capture(lambda: selected_trace(artifact))
        require(validated == dict(ok=True, value=expected["events"])
                and selected == dict(ok=True, value={k:v for k,v in expected.items() if k != "fixture"}),
                "real public API differs from bound receipt")
        require(before == {str(p): proof(p) for p in (artifact, trace)}, "real fixture changed")
        real.append(dict(fixture=name, validate=lossless(validated), selected=lossless(selected)))
    guard(output)
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
    rejection_outcomes = []

    def reject(label, call):
        try:
            call()
        except (ValueError, RuntimeError, TypeError, RecursionError) as error:
            rejected.append(label)
            rejection_outcomes.append(dict(label=label, outcome=lossless(dict(ok=False, error=exception(error)))))
        else:
            raise RuntimeError("invalid diagnostic accepted: " + label)

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
    require(len(rejected) == 33 and len(set(rejected)) == 33, "original rejection inventory changed")
    synthetic_after = tree(raw)
    report = dict(status="PASS", arm=c["arm"], real_traces=real, rejections=rejection_outcomes,
                  exact_byte_and_event_bounds_passed=True, synthetic_before=synthetic_before,
                  synthetic_after=synthetic_after, original_transport_sha256=c["original_transport_sha256"],
                  modules=modules())
    report_path = owned(c["report_path"], output)
    with report_path.open("x") as out:
        json.dump(report, out, sort_keys=True, indent=2)
        out.write("\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
