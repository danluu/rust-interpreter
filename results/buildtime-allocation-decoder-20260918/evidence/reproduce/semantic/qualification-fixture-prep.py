#!/usr/bin/env python3
"""Copy exactly eight named real files into a new immutable owned fixture tree."""
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from qualification_outcomes import setup, owned, guard, proof, require, modules

def main():
    c = setup()
    output = Path(c["output_root"])
    root = owned(c["fixtures_root"], output)
    require(not root.exists() and not root.is_symlink(), "fresh real fixture tree required")
    provenance = json.loads(Path(c["provenance"]).read_bytes())
    records = provenance["historical_records"]
    require(len(records) == 4 and {r["fixture"] for r in records} == {"caller", "scalar_constant", "static", "tls"}, "real panel differs")
    guard(output)
    root.mkdir(mode=0o700)
    fixtures, copies = {}, []
    for record in records:
        directory = root / record["fixture"]
        directory.mkdir(mode=0o700)
        receipt = dict(record)
        for key, size_key, digest_key, name in (
            ("artifact_path", "artifact_bytes", "artifact_sha256", "program.rbc"),
            ("path", "bytes", "sha256", "program.rbc.allocations.jsonl")):
            source = Path(record[key])
            require(source.is_absolute() and source.resolve(strict=True) == source, "indirect real input")
            before = proof(source)
            require(before["bytes"] == record[size_key] and before["sha256"] == record[digest_key], "real source binding changed")
            target = directory / name
            guard(output)
            stamp = lambda s: [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]
            with os.fdopen(os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb", buffering=0) as inp:
                require(stamp(os.fstat(inp.fileno())) == before["stamp"], "real input changed while opening")
                remaining = before["bytes"]
                guard(output)
                with target.open("xb") as out:
                    while True:
                        chunk = inp.read(min(1024 ** 2, remaining + 1))
                        require(len(chunk) <= remaining, "real input grew beyond recorded size")
                        if not chunk:
                            require(remaining == 0, "real input truncated during copy")
                            break
                        guard(output)
                        out.write(chunk)
                        guard(output)
                        remaining -= len(chunk)
                require(stamp(os.fstat(inp.fileno())) == before["stamp"]
                        and stamp(source.lstat()) == before["stamp"], "real input changed during copy")
            guard(output)
            target.chmod(0o444)
            guard(output)
            after, destination = proof(source), proof(target)
            require(after == before and destination["bytes"] == before["bytes"]
                    and destination["sha256"] == before["sha256"], "real copy differs")
            copies.append(dict(source_before=before, source_after=after, destination=destination))
            receipt[key] = str(target)
        directory.chmod(0o555)
        fixtures[record["fixture"]] = receipt
    root.chmod(0o555)
    destination = owned(c["fixture_descriptor"], output)
    with destination.open("x") as out:
        json.dump(dict(fixtures=fixtures, copies=copies), out, sort_keys=True, indent=2)
        out.write("\n")
    destination.chmod(0o444)
    require(len(copies) == 8, "copy count differs")
    print(json.dumps(dict(status="PASS", copies=copies, fixtures=fixtures, modules=modules()), sort_keys=True))

if __name__ == "__main__":
    main()
