#!/usr/bin/env python3
"""Differential compiler checks, including cache verification and diagnostics."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / ".work/backend-build/release/librustc_codegen_cranelift.dylib"
TOOLCHAIN = "nightly-2026-09-08"


def validate():
    work = ROOT / ".work" / ("validation-" + str(time.time_ns()))
    work.mkdir()
    original = (ROOT / "tests/codegen_fixture.rs").read_text()
    states = {
        "initial": original,
        "callee-rebinding": original.replace("{ choose_a(x) }", "{ choose_b(x) }"),
        "layout-constant": original.replace("const OFFSET: i64 = 3;", "const OFFSET: i64 = 11;").replace("a: u64, b: u32", "a: u64, b: u128"),
        "source-locations": "\n" * 11 + original,
        "revert": original,
    }
    results = []
    for mode in ["normal", "verify"]:
        cache = work / ("cache-" + mode)
        for state, source in states.items():
            source_path = work / "fixture.rs"
            source_path.write_text(source)
            outputs = []
            for backend in ["llvm", "cache"]:
                env = os.environ.copy()
                for key in list(env):
                    if key.startswith("RUST_INTERP_"):
                        env.pop(key)
                name = mode + "-" + state + "-" + backend
                binary = work / name
                command = ["rustup", "run", TOOLCHAIN, "rustc", str(source_path), "--edition=2024",
                           "-Cpanic=abort", "-Cdebuginfo=2", "-Ccodegen-units=1", "-o", str(binary)]
                if backend == "cache":
                    command += ["-Zcodegen-backend=" + str(BACKEND)]
                    env["RUST_INTERP_FUNCTION_CACHE"] = str(cache)
                    env["RUST_INTERP_CACHE_STATS_PATH"] = str(work / (name + ".stats"))
                    if mode == "verify":
                        env["RUST_INTERP_CACHE_VERIFY"] = "1"
                result = subprocess.run(command, env=env, capture_output=True)
                (work / (name + ".stderr")).write_bytes(result.stderr)
                if result.returncode:
                    raise RuntimeError(name + " compile failed: " + result.stderr.decode(errors="replace")[-4000:])
                outputs.append(subprocess.check_output([str(binary)]))
            assert outputs[0] == outputs[1], (mode, state, outputs)
            totals = [0, 0, 0]
            for line in (work / (mode + "-" + state + "-cache.stats")).read_text().splitlines():
                for i, value in enumerate(map(int, line.split()[1:])):
                    totals[i] += value
            if state == "revert":
                assert totals[0] > 0 and totals[1] == 0, totals
            results.append({"mode": mode, "state": state, "hits": totals[0], "misses": totals[1], "write_errors": totals[2], "output": outputs[0].decode()})
            print(mode, state, totals, flush=True)
    # An uncalled invalid body must still fail, despite any populated cache.
    for name, source in {
        "type-error": 'fn unused() -> u64 { "wrong" } fn main() {}',
        "borrow-error": 'fn unused() { let mut s=String::new(); let r=&s; s.push_str("x"); println!("{}", r); } fn main() {}',
        "const-error": 'const BAD: usize = 1 / 0; fn main() { println!("{}", BAD); }',
    }.items():
        path = work / (name + ".rs")
        path.write_text(source)
        env = os.environ.copy()
        env["RUST_INTERP_FUNCTION_CACHE"] = str(work / "cache-normal")
        p = subprocess.run(["rustup", "run", TOOLCHAIN, "rustc", str(path), "-Cpanic=abort", "-Zcodegen-backend=" + str(BACKEND), "-o", str(work / name)], env=env, capture_output=True)
        assert p.returncode != 0 and b"error" in p.stderr, name
        (work / (name + ".stderr")).write_bytes(p.stderr)
        results.append({"diagnostic": name, "rejected": True})
    # Context.want_disasm is not part of Cranelift's stencil key. Dump requests
    # bypass our cache so cached code cannot suppress requested disassembly.
    dump = work / "dump"
    dump.mkdir()
    source_path = dump / "fixture.rs"
    source_path.write_text(original)
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("RUST_INTERP_"):
            env.pop(key)
    env["RUST_INTERP_FUNCTION_CACHE"] = str(work / "cache-normal")
    p = subprocess.run(["rustup", "run", TOOLCHAIN, "rustc", str(source_path), "--edition=2024", "-Cpanic=abort",
        "-Cdebuginfo=2", "--emit=link,llvm-ir", "-Zcodegen-backend=" + str(BACKEND), "-o", str(dump / "fixture")], env=env, capture_output=True)
    (dump / "compiler.stderr").write_bytes(p.stderr)
    assert list(dump.rglob("*.vcode")), "Requested disassembly was not emitted"
    baseline_env = env.copy()
    baseline_env.pop("RUST_INTERP_FUNCTION_CACHE")
    baseline = subprocess.run(["rustup", "run", TOOLCHAIN, "rustc", str(source_path), "--edition=2024", "-Cpanic=abort",
        "-Cdebuginfo=2", "--emit=link,llvm-ir", "-Zcodegen-backend=" + str(BACKEND), "-o", str(dump / "baseline")], env=baseline_env, capture_output=True)
    (dump / "baseline.stderr").write_bytes(baseline.stderr)
    assert p.returncode == baseline.returncode, "Cache changed diagnostic-dump outcome"
    if p.returncode:
        # This pinned upstream backend emits .clif/.vcode but rustc's LLVM-IR
        # copying step expects a .ll file. Record the existing limitation.
        assert b"could not copy" in p.stderr and b"could not copy" in baseline.stderr
        results.append({"diagnostic": "disassembly-after-cache", "vcode_emitted": True,
                        "upstream_llvm_ir_limitation": True, "matched_uncached_exit_code": p.returncode})
    else:
        subprocess.run([str(dump / "fixture")], check=True, capture_output=True)
        results.append({"diagnostic": "disassembly-after-cache", "emitted": True})
    (work / "results.json").write_text(json.dumps({"backend_sha256": hashlib.sha256(BACKEND.read_bytes()).hexdigest(), "results": results}, indent=2) + "\n")
    print("Validation passed:", work, flush=True)


if __name__ == "__main__":
    validate()
