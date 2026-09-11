#!/usr/bin/env python3
"""Bounded compatibility experiment; it does not enable unwinding in the launcher."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = "nightly-2026-09-08"

if __name__ == "__main__":
    with (ROOT / ".work/benchmark.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        work = ROOT / ".work" / ("unwind-probe-" + str(time.time_ns()))
        work.mkdir()
        command = ["cargo", "+" + TOOLCHAIN, "build", "--manifest-path", str(ROOT / ".work/sources/cg-clif/Cargo.toml"),
            "--release", "--features", "unstable-features,unwinding", "--jobs", "4", "--target-dir", str(ROOT / ".work/backend-unwind-build"), "--locked"]
        with (work / "build.log").open("w") as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        backend = ROOT / ".work/backend-unwind-build/release/librustc_codegen_cranelift.dylib"
        results = []
        for variant in ["llvm", "clif", "clif-cache", "clif-cache-restart"]:
            env = os.environ.copy()
            for key in list(env):
                if key.startswith("RUST_INTERP_"):
                    env.pop(key)
            binary = work / variant
            command = ["rustup", "run", TOOLCHAIN, "rustc", str(ROOT / "tests/unwind_fixture.rs"), "--edition=2024", "-Cpanic=unwind", "-o", str(binary)]
            if variant != "llvm":
                command.append("-Zcodegen-backend=" + str(backend))
            if variant.startswith("clif-cache"):
                env["RUST_INTERP_FUNCTION_CACHE"] = str(work / "cache")
            compile_result = subprocess.run(command, env=env, capture_output=True)
            (work / (variant + ".compile.stderr")).write_bytes(compile_result.stderr)
            row = {"variant": variant, "compile_exit_code": compile_result.returncode}
            if compile_result.returncode == 0:
                run_result = subprocess.run([str(binary)], env=env, capture_output=True)
                (work / (variant + ".run.stderr")).write_bytes(run_result.stderr)
                row.update(run_exit_code=run_result.returncode, stdout=run_result.stdout.decode(errors="replace"))
                row["passed"] = run_result.returncode == 0 and run_result.stdout == b"unwind-ok\n"
            else:
                row["passed"] = False
            results.append(row)
            print(row, flush=True)
        (work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        print("Compatibility probe:", work)
