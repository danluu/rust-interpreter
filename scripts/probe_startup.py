#!/usr/bin/env python3
"""Separate post-Cargo execution latency from repeated execution and probe mode."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import resource
import subprocess
import time

import bench


def stamp(binary):
    s = Path(binary).stat()
    return {"inode": s.st_ino, "mtime_ns": s.st_mtime_ns, "ctime_ns": s.st_ctime_ns,
            "bytes": s.st_size, "links": s.st_nlink}


def probe(run_id, name):
    run = bench.WORK / "runs" / run_id / name
    rows = [json.loads(line) for line in (run / "results.jsonl").read_text().splitlines()]
    project = bench.CONFIG["projects"][name]
    assert name == "pgrust", "This diagnostic currently uses postgres --version"
    work = bench.WORK / ("startup-probe-" + str(time.time_ns()))
    work.mkdir()
    results = []
    provenance = json.loads((run / "provenance.json").read_text())
    with (bench.WORK / "benchmark.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with bench.source_probe(name, project) as (source, set_state):
            set_state("A")
            for variant in ["llvm", "clif"]:
                row = next(r for r in reversed(rows) if r["variant"] == variant and r["status"] == "ok")
                env = bench.environment(variant, row["target_dir"], work / "unused", work / "unused.stats",
                                        provenance["incremental"], provenance["dev_debug"], provenance["linker"])
                binary = row["binary"]

                def cargo(label, fresh=False):
                    before = stamp(binary)
                    p = subprocess.run(row["command"], cwd=source, env=env, capture_output=True)
                    prefix = work / (variant + "-" + label)
                    prefix.with_suffix(".stdout").write_bytes(p.stdout)
                    prefix.with_suffix(".stderr").write_bytes(p.stderr)
                    assert p.returncode == 0, p.stderr[-2000:]
                    _, rebuilt, _ = bench.cargo_messages(prefix.with_suffix(".stdout"))
                    if fresh:
                        assert rebuilt == 0, rebuilt
                    results.append({"variant": variant, "case": label, "rebuilt": rebuilt,
                                    "before": before, "after": stamp(binary)})

                def execute(label, use_probe):
                    child_env = env.copy()
                    child_env.pop("RUST_INTERP_BENCH_PROBE", None)
                    if use_probe:
                        child_env["RUST_INTERP_BENCH_PROBE"] = "1"
                    before = resource.getrusage(resource.RUSAGE_CHILDREN)
                    start = time.perf_counter()
                    p = subprocess.run([binary] + ([] if use_probe else ["--version"]), env=child_env, capture_output=True)
                    elapsed = time.perf_counter() - start
                    after = resource.getrusage(resource.RUSAGE_CHILDREN)
                    assert p.returncode == 0, p.stderr[-2000:]
                    assert p.stdout == b"rust-interp-probe-77\n" if use_probe else b"postgres" in p.stdout.lower()
                    result = {"variant": variant, "case": label, "probe": use_probe, "seconds": elapsed,
                              "child_cpu_seconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime}
                    results.append(result)
                    print(result, flush=True)

                cargo("prepare")
                for i in range(3):
                    execute("repeated-probe-" + str(i), True)
                cargo("no-op-normal-first", fresh=True)
                execute("normal-first", False)
                execute("normal-repeat", False)
                execute("probe-after-normal", True)
                cargo("no-op-probe-first", fresh=True)
                execute("probe-first", True)
                execute("normal-after-probe", False)
                # Cargo run may execute a different artifact path than the
                # public binary reported by cargo build. Measure it explicitly.
                command = list(row["command"])
                command[2] = "run"
                command += ["--", "--version"]
                for i in range(2):
                    start = time.perf_counter()
                    p = subprocess.run(command, cwd=source, env=env, capture_output=True)
                    elapsed = time.perf_counter() - start
                    assert p.returncode == 0 and p.stdout.splitlines()[-1].lower().startswith(b"postgres "), p.stderr[-2000:]
                    (work / (variant + "-cargo-run-%d.stderr" % i)).write_bytes(p.stderr)
                    results.append({"variant": variant, "case": "cargo-run-%d" % i, "seconds": elapsed})
                    print(results[-1], flush=True)
    (work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(work)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    args = parser.parse_args()
    probe(args.run_id, "pgrust")
