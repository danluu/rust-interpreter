#!/usr/bin/env python3
"""Finite differential scanner/caller recursion qualification; no performance clock."""
import hashlib
import json
import json.scanner
from pathlib import Path
import sys
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from qualification_outcomes import setup, owned, guard, require, load, capture_depth, compact, modules

def main():
    c = setup()
    output = Path(c["output_root"])
    row_path = owned(c["rows_path"], output)
    implementations = {arm: load(c["roots"][arm], arm) for arm in ("baseline", "candidate")}
    scanner, limit = c["scanner"], c["limit"]
    require(scanner in ("installed-C", "stdlib-py_make_scanner") and limit in (200, 1000), "unplanned scanner/limit")
    old_scanner, old_limit = json.scanner.make_scanner, sys.getrecursionlimit()
    require(old_scanner is json.scanner.c_make_scanner, "installed scanner differs")
    digest = hashlib.sha256(b"owned recursion correctness artifact").hexdigest()
    header = b'{"kind":"allocation-trace","schema_version":1,"strict_frontend":true,"event":0}\n'
    footer = ('{"kind":"complete","prior_events":2,"artifact_sha256":"' + digest + '","event":2}\n').encode()
    def trace(value):
        return header + b'{"kind":"function","event":1,"unknown":' + value + b'}\n' + footer
    shallow = trace(b"0")
    def nested(shape, depth, atom):
        opens, closes = [], []
        for i in range(depth):
            obj = shape == "objects" or shape == "alternating-array-object" and i % 2 == 1
            opens.append(b'{"accepted_unique_key":' if obj else b"[")
            closes.append(b"}" if obj else b"]")
        return b"".join(opens) + atom + b"".join(reversed(closes))
    counts = dict(depth=0, caller_bom=0, hooks=0, overflow=0, shallow_after=0)
    mismatches = 0
    def pair(stream, category, shape, depth, data, caller_depth=0, expected=None):
        nonlocal mismatches
        order = ("baseline", "candidate") if depth % 2 == 0 else ("candidate", "baseline")
        outcomes = {arm: capture_depth(implementations[arm], data, digest, caller_depth) for arm in order}
        equal = outcomes["baseline"] == outcomes["candidate"]
        expected_ok = (expected is None or all(o["ok"] == expected for o in outcomes.values()))
        expected_ok = expected_ok and all(not o["ok"] or o["value"] == 3 for o in outcomes.values())
        after = {arm: capture_depth(implementations[arm], shallow, digest, 0) for arm in ("baseline", "candidate")}
        shallow_ok = after["baseline"] == after["candidate"] == dict(ok=True, value=3, api_entered=True)
        good = equal and expected_ok and shallow_ok
        mismatches += not good
        counts[category] += 1
        counts["shallow_after"] += 1
        row = dict(category=category, scanner=scanner, recursion_limit=limit, shape=shape, depth=depth,
                   caller_depth=caller_depth, order=order, input_bytes=len(data),
                   input_sha256=hashlib.sha256(data).hexdigest(), outcomes_equal=equal,
                   expectation_passed=expected_ok, shallow_after_passed=shallow_ok,
                   baseline=compact(outcomes["baseline"]), candidate=compact(outcomes["candidate"]),
                   shallow_after=compact(after))
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    try:
        if scanner == "stdlib-py_make_scanner":
            json.scanner.make_scanner = json.scanner.py_make_scanner
        sys.setrecursionlimit(limit)
        guard(output)
        with row_path.open("x") as stream:
            for shape in ("arrays", "objects", "alternating-array-object"):
                for depth in range(limit + 9):
                    pair(stream, "depth", shape, depth, trace(nested(shape, depth, b"0")))
            for shape, prefix in (("first-record-BOM", b"\xef\xbb\xbf"), ("whitespace-BOM", b" \t\xef\xbb\xbf")):
                for depth in range(limit + 9):
                    pair(stream, "caller_bom", shape, depth, prefix + shallow, caller_depth=depth, expected=False)
            for shape in ("arrays", "objects", "alternating-array-object"):
                for depth in (0, 16, 64):
                    for label, atom in (("duplicate", b'{"dup":1,"dup":2}'), ("NaN", b"NaN"), ("Infinity", b"Infinity"), ("-Infinity", b"-Infinity")):
                        pair(stream, "hooks", shape + ":" + label, depth, trace(nested(shape, depth, atom)), expected=False)
                    pair(stream, "overflow", shape, depth, trace(nested(shape, depth, b"1e999")), expected=True if depth == 0 else None)
    finally:
        sys.setrecursionlimit(old_limit)
        json.scanner.make_scanner = old_scanner
    require(counts == dict(depth=3*(limit+9), caller_bom=2*(limit+9), hooks=36, overflow=9,
                           shallow_after=5*(limit+9)+45), "recursion schedule incomplete")
    print(json.dumps(dict(status="PASS" if not mismatches else "FAIL", mismatches=mismatches,
                         counts=counts, scanner=scanner, limit=limit, rows_path=str(row_path),
                         scanner_restored=json.scanner.make_scanner is old_scanner,
                         recursion_limit_restored=sys.getrecursionlimit()==old_limit, modules=modules()), sort_keys=True))

if __name__ == "__main__":
    main()
