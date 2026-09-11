#!/usr/bin/env python3
"""Separate diagnostic runs: rustc phase times on a fresh body edit.

These instrumented runs are not added to the primary timing samples. Phase
timings may nest; do not sum them as independent work.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
import bench


def profile(run_id, projects, linker, strip):
    rustc = bench.checked_output(["rustup", "run", bench.TOOLCHAIN, "rustc", "-vV"])
    triple = next(line.split(": ", 1)[1] for line in rustc.splitlines() if line.startswith("host:"))
    with (bench.WORK / "benchmark.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for name in projects:
            directory = bench.WORK / "runs" / run_id / name
            metadata = json.loads((directory / "provenance.json").read_text())
            project = bench.CONFIG["projects"][name]
            with bench.source_probe(name, project) as (source, set_state):
                source_sha = set_state("B9999")
                for variant in metadata["variants"]:
                    prefix = directory / ("profile-" + linker + ("-nostrip" if strip == "none" else "") + "-" + variant)
                    target = bench.WORK / "targets" / run_id / name / variant
                    cache = bench.WORK / "function-caches" / run_id / name / bench.digest(bench.BACKEND.read_bytes())[:24]
                    env = bench.environment(variant, target, cache, prefix.with_suffix(".cache"), metadata["incremental"], metadata["dev_debug"], metadata.get("linker", "system"))
                    env["RUST_INTERP_CACHE_WORKSPACE"] = str(source)
                    cargo_args = ["-p", "fre", "--lib"] if name == "fre" else project["cargo_args"]
                    extra = ["-Ztime-passes", "-Ztime-passes-format=json"]
                    if strip == "none":
                        extra.append("-Cstrip=none")
                    if linker == "lld":
                        sysroot = Path(bench.checked_output(["rustup", "run", bench.TOOLCHAIN, "rustc", "--print", "sysroot"]))
                        lld = sysroot / "lib/rustlib" / triple / "bin/gcc-ld" / ("ld64.lld" if os.uname().sysname == "Darwin" else "ld.lld")
                        extra += ["-Clinker=clang", "-Clink-arg=-fuse-ld=" + str(lld)]
                    command = ["cargo", "+" + bench.TOOLCHAIN, "rustc", "--locked", "--offline", "--target", triple, "--jobs", str(metadata["jobs"])] + cargo_args + ["--"] + extra
                    start = time.perf_counter()
                    result = subprocess.run(command, cwd=source, env=env, capture_output=True)
                    duration = time.perf_counter() - start
                    prefix.with_suffix(".stdout").write_bytes(result.stdout)
                    prefix.with_suffix(".stderr").write_bytes(result.stderr)
                    phases = []
                    for line in result.stderr.decode(errors="replace").splitlines():
                        # rustc JSON phase output is one object per line.
                        try:
                            item = json.loads(line[line.index("{"):])
                            if isinstance(item, dict):
                                phases.append(item)
                        except (ValueError, IndexError):
                            pass
                    prefix.with_suffix(".json").write_text(json.dumps({"command": command, "source_sha256": source_sha,
                        "seconds": duration, "exit_code": result.returncode, "phases": phases}, indent=2) + "\n")
                    print(name, variant, result.returncode, "%.3fs" % duration, len(phases), "phase records", flush=True)
                    if result.returncode == 0 and name != "fre":
                        rows = [json.loads(line) for line in (directory / "results.jsonl").read_text().splitlines()]
                        binary = next(row["binary"] for row in reversed(rows) if row["variant"] == variant and row["status"] == "ok")
                        bench.execute_check(binary, name, "B9999", directory / "fixture")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("projects", nargs="+", choices=list(bench.CONFIG["projects"]))
    parser.add_argument("--linker", choices=["system", "lld"], default="system")
    parser.add_argument("--strip", choices=["repository", "none"], default="repository")
    args = parser.parse_args()
    profile(args.run_id, args.projects, args.linker, args.strip)
