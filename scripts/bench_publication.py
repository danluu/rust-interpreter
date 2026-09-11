#!/usr/bin/env python3
"""Matched no-op build/run comparison of the Cargo executable-publication change."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

import bench


def run(run_id, projects, repeats):
    cargo = bench.WORK / "cargo-build/release/cargo"
    manifest = json.loads((cargo.parent.parent / "manifest.json").read_text())
    assert hashlib.sha256(cargo.read_bytes()).hexdigest() == manifest["sha256"]
    work = bench.WORK / ("publication-" + str(time.time_ns()))
    work.mkdir()
    results = []
    with (bench.WORK / "benchmark.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for name in projects:
            original_run = bench.WORK / "runs" / run_id / name
            original = [json.loads(x) for x in (original_run / "results.jsonl").read_text().splitlines()]
            provenance = json.loads((original_run / "provenance.json").read_text())
            project = bench.CONFIG["projects"][name]
            with bench.source_probe(name, project) as (source, set_state):
                set_state("A")
                for variant in ["llvm", "clif"]:
                    row = next(r for r in reversed(original) if r["variant"] == variant and r["status"] == "ok")
                    directory = work / name / variant
                    directory.mkdir(parents=True)
                    env = bench.environment(variant, row["target_dir"], work / "unused", work / "unused.stats",
                                            provenance["incremental"], provenance["dev_debug"], provenance["linker"])
                    command = ["rustup", "run", bench.TOOLCHAIN, str(cargo)] + row["command"][2:]
                    binary = Path(row["binary"])
                    for iteration in range(-1, repeats):
                        order = [False] if iteration < 0 else ([False, True] if iteration % 2 == 0 else [True, False])
                        for enabled in order:
                            env["RUST_INTERP_PRESERVE_EXECUTABLES"] = "1" if enabled else "0"
                            prefix = directory / ("%02d-%s" % (iteration, "preserve" if enabled else "control"))
                            inode = binary.stat().st_ino
                            load = os.getloadavg()
                            start = time.perf_counter()
                            p = subprocess.run(command, env=env, cwd=source, capture_output=True)
                            build_seconds = time.perf_counter() - start
                            prefix.with_suffix(".stdout").write_bytes(p.stdout)
                            prefix.with_suffix(".stderr").write_bytes(p.stderr)
                            assert p.returncode == 0, p.stderr[-2000:]
                            _, rebuilt, _ = bench.cargo_messages(prefix.with_suffix(".stdout"))
                            if iteration >= 0:
                                assert rebuilt == 0, rebuilt
                                if enabled:
                                    assert inode == binary.stat().st_ino, "Executable was not preserved"
                            probe, runtime, _, _ = bench.execute_check(str(binary), name, "A", directory / "fixture")
                            if iteration >= 0:
                                result = {"project": name, "variant": variant, "preserve": enabled,
                                          "iteration": iteration, "build_seconds": build_seconds,
                                          "probe_seconds": probe, "runtime_seconds": runtime,
                                          "feedback_seconds": build_seconds + probe + runtime,
                                          "inode_before": inode, "inode_after": binary.stat().st_ino,
                                          "load_before": load, "load_after": os.getloadavg()}
                                results.append(result)
                                (work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
                                print(name, variant, "preserve" if enabled else "control",
                                      "build %.3fs feedback %.3fs" % (build_seconds, result["feedback_seconds"]), flush=True)
    summary = []
    for name, variant, enabled in sorted({(r["project"], r["variant"], r["preserve"]) for r in results}):
        rows = [r for r in results if (r["project"], r["variant"], r["preserve"]) == (name, variant, enabled)]
        summary.append({"project": name, "variant": variant, "preserve": enabled, "n": len(rows),
                        **{key: statistics.median(r[key] for r in rows) for key in ("build_seconds", "probe_seconds", "runtime_seconds", "feedback_seconds")},
                        "feedback_min_seconds": min(r["feedback_seconds"] for r in rows),
                        "feedback_max_seconds": max(r["feedback_seconds"] for r in rows)})
    record = {"cargo": manifest, "source_run": run_id, "note": "Same Cargo binary with flag off/on; unchanged source, zero rebuilt artifacts, alternating order. This measures no-op workflows, not body edits.", "summary": summary}
    (work / "summary.json").write_text(json.dumps(record, indent=2) + "\n")
    destination = bench.ROOT / "results" / run_id / "publication-summary.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2) + "\n")
    print(work, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("projects", nargs="+", choices=list(bench.CONFIG["projects"]))
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    run(args.run_id, args.projects, args.repeats)
