#!/usr/bin/env python3
"""Compare real, bounded workloads using the binaries produced by bench.py."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def workload(name, directory):
    directory.mkdir(parents=True, exist_ok=True)
    if name == "fre":
        return ["2048"], 0
    if name == "nushell":
        return ["--no-config-file", "--no-history", "-c", "1..100000 | each {|x| $x * 3 } | math sum"], 0
    if name == "ruff":
        source = "import os\n" + "".join("def function_%d(value):\n    unused = 1\n    return value + 1\n\n" % i for i in range(2000))
        path = directory / "lint.py"
        path.write_text(source)
        return ["check", "--no-cache", "--isolated", "--select", "F401,F841", "--output-format", "json", str(path)], 1
    if name == "rg-aot":
        corpus = directory / "corpus"
        corpus.mkdir(exist_ok=True)
        block = b"alpha beta needle gamma delta\n" * 16384
        for i in range(16):
            (corpus / ("input-%02d.rs" % i)).write_bytes(block)
        manifest = directory / "queries.json"
        manifest.write_text(json.dumps({"schema_version": 1, "name": "runtime-fixture", "queries": [
            {"id": "literal", "pattern": "needle"}, {"id": "regex", "pattern": "a[a-z]+a"}, {"id": "absent", "pattern": "absent[0-9]+"}]}))
        return ["scan", "--manifest", str(manifest), "--root", str(corpus), "--output", "digest"], 0
    raise ValueError(name)


def normalize(name, output):
    if name == "rg-aot":
        data = json.loads(output)["queries"]
        assert [item["count"] for item in data] == [262144, 262144, 0], data
        return json.dumps(data, sort_keys=True).encode()
    if name == "ruff":
        data = json.loads(output)
        assert len(data) == 2001, len(data)
        return json.dumps(data, sort_keys=True).encode()
    if name == "fre":
        assert output == b"\\[a\\+b\\] 134205440\n", output
    if name == "nushell":
        assert output == b"15000150000\n", output
    return output


def run(run_id, repeats):
    work = ROOT / ".work/runs" / run_id
    records = []
    env = os.environ.copy()
    env.pop("RUST_INTERP_BENCH_PROBE", None)
    with (ROOT / ".work/benchmark.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for name in ["rg-aot", "fre", "ruff", "nushell"]:
            data = work / name / "results.jsonl"
            if not data.exists():
                continue
            binaries = {}
            for line in data.read_text().splitlines():
                row = json.loads(line)
                if row["status"] == "ok":
                    binaries[row["variant"]] = row["binary"]
            if not binaries:
                continue
            identities = {variant: {"binary_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
                                    "binary_bytes": Path(binary).stat().st_size}
                          for variant, binary in binaries.items()}
            command, status = workload(name, work / "runtime-fixtures" / name)
            oracle = None
            # Include an unmeasured first invocation for each binary/fixture.
            for iteration in range(-1, repeats):
                order = list(binaries) if iteration % 2 == 0 else list(reversed(binaries))
                for variant in order:
                    before = os.getloadavg()
                    start = time.perf_counter()
                    p = subprocess.run([binaries[variant]] + command, env=env, capture_output=True)
                    elapsed = time.perf_counter() - start
                    row = {"project": name, "variant": variant, "iteration": iteration,
                           "seconds": elapsed, "load_before": before, "load_after": os.getloadavg(),
                           "args": command, "exit_code": p.returncode, **identities[variant]}
                    try:
                        if p.returncode != status:
                            raise RuntimeError((name, variant, p.returncode, p.stderr[-1000:]))
                        result = normalize(name, p.stdout)
                        if oracle is None:
                            oracle = result
                        assert result == oracle, (name, variant, "output mismatch")
                    except Exception as error:
                        row.update(status="failed", error=str(error))
                        records.append(row)
                        (work / "runtime-results.json").write_text(json.dumps(records, indent=2) + "\n")
                        (work / "runtime-failure.stdout").write_bytes(p.stdout)
                        (work / "runtime-failure.stderr").write_bytes(p.stderr)
                        raise
                    if iteration >= 0:
                        row.update(status="ok", output_sha256=hashlib.sha256(result).hexdigest())
                        records.append(row)
                        (work / "runtime-results.json").write_text(json.dumps(records, indent=2) + "\n")
                        print(name, variant, "%.3fs" % elapsed, flush=True)
    (work / "runtime-results.json").write_text(json.dumps(records, indent=2) + "\n")
    summary = []
    for name, variant in sorted({(r["project"], r["variant"]) for r in records}):
        times = [r["seconds"] for r in records if r["project"] == name and r["variant"] == variant]
        summary.append({"project": name, "variant": variant, "n": len(times), "median_seconds": statistics.median(times), "min_seconds": min(times), "max_seconds": max(times)})
    destination = ROOT / "results" / run_id
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "runtime-summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    run(args.run_id, args.repeats)
