#!/usr/bin/env python3
"""Measure launcher overhead against its exact resolved Cargo invocation."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

import dev


def run(fixture):
    fixture = Path(fixture).resolve()
    assert fixture.parent == dev.ROOT / ".work" and fixture.name.startswith("launcher-validation-")
    work = dev.ROOT / ".work" / ("launcher-benchmark-" + str(time.time_ns()))
    work.mkdir()
    results = []
    with (dev.ROOT / ".work/benchmark.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.chdir(fixture)
        for backend in ["llvm", "clif", "clif-cache"]:
            arguments = ["--backend", backend, "--preserve-executables"]
            if backend != "llvm":
                arguments.append("--panic-abort")
            arguments += ["run", "--offline", "--quiet", "--message-format=json-render-diagnostics",
                          "--", "--backend", "application", "--release"]
            resolved = []
            # Execute the actual launcher's setup, capturing only its final exec
            # in memory. No environment variables are written to reports.
            with patch.object(sys, "argv", ["dev.py"] + arguments), patch("os.execvpe", lambda exe, args, env: resolved.append((args, env))):
                dev.main()
            command, env = resolved[0]
            for iteration in range(-1, 5):
                order = [False, True] if iteration % 2 == 0 else [True, False]
                for launcher in order:
                    start = time.perf_counter()
                    p = subprocess.run([sys.executable, str(dev.ROOT / "scripts/dev.py")] + arguments if launcher else command,
                                       cwd=fixture, env=None if launcher else env, capture_output=True)
                    elapsed = time.perf_counter() - start
                    assert p.returncode == 0 and p.stdout.splitlines()[-1] == b"flags-preserved", p.stderr[-2000:]
                    for line in p.stdout.splitlines()[:-1]:
                        item = json.loads(line)
                        if iteration >= 0 and item.get("reason") == "compiler-artifact":
                            assert item["fresh"], "Unexpected compilation during overhead measurement"
                    if iteration >= 0:
                        results.append({"backend": backend, "launcher": launcher, "iteration": iteration, "seconds": elapsed})
            for launcher in [False, True]:
                values = [r["seconds"] for r in results if r["backend"] == backend and r["launcher"] == launcher]
                print(backend, "launcher" if launcher else "direct", round(statistics.median(values), 4), flush=True)
    (work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    summary = []
    for backend in ["llvm", "clif", "clif-cache"]:
        medians = {flag: statistics.median(r["seconds"] for r in results if r["backend"] == backend and r["launcher"] == flag) for flag in [False, True]}
        summary.append({"backend": backend, "n_per_condition": 5, "direct_seconds": medians[False],
                        "launcher_seconds": medians[True], "median_difference_seconds": medians[True] - medians[False]})
    (dev.ROOT / "results/launcher-overhead.json").write_text(json.dumps({"note": "Tiny owned integration fixture, preserve-executables enabled, exact resolved Cargo invocation as control, alternating order, all compiler artifacts fresh. This does not measure overhead on the full corpus.", "summary": summary}, indent=2) + "\n")
    print(work)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture")
    run(parser.parse_args().fixture)
