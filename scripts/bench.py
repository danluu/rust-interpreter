#!/usr/bin/env python3
"""Reproducible, serial Cargo edit/build/run experiments on owned snapshots.

This first experiment uses executable body-edit probes, not replayed developer
history. Each edit must be observed in the resulting binary before a timing is
accepted. Cold means empty project target/cache; downloaded sources and stdlib
are already present. See README for the exact profile and remaining limitations.
"""
import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "benchmarks/corpus.json").read_text())
WORK = ROOT / ".work"
TOOLCHAIN = CONFIG["toolchain"]
BACKEND = WORK / ("backend-build/release/librustc_codegen_cranelift." + ("dylib" if sys.platform == "darwin" else "so"))
HARNESS_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
VARIANTS = ["llvm", "clif", "clif-cache"]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_output(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def environment(variant, target, cache, stats, incremental="1", debug="0", linker="system"):
    env = os.environ.copy()
    # Eliminate accidental compiler wrappers, inherited flags or shared targets.
    for key in list(env):
        if key.startswith(("RUST_INTERP_", "CARGO_PROFILE_")) or key in (
            "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC", "RUSTC_WRAPPER",
            "RUSTC_WORKSPACE_WRAPPER", "CARGO_BUILD_TARGET", "CARGO_TARGET_DIR",
            "CARGO_BUILD_RUSTFLAGS", "RUSTC_BOOTSTRAP", "CARGO_BUILD_INCREMENTAL",
        ) or (key.startswith("CARGO_TARGET_") and key.endswith("_RUSTFLAGS")):
            env.pop(key)
    env.update(CARGO_TARGET_DIR=str(target), CARGO_TERM_COLOR="never")
    env["RUSTC_WRAPPER"] = ""
    env["RUSTC_WORKSPACE_WRAPPER"] = ""
    if incremental != "repository":
        env["CARGO_INCREMENTAL"] = incremental
    else:
        env.pop("CARGO_INCREMENTAL", None)
    if debug != "repository":
        env["CARGO_PROFILE_DEV_DEBUG"] = debug
    flags = [] if variant == "llvm-unwind" else ["-Cpanic=abort"]
    if linker != "system":
        flags += ["-Clinker=clang", "-Clink-arg=-fuse-ld=" + linker]
    if variant.startswith("clif"):
        flags += ["-Zcodegen-backend=" + str(BACKEND)]
    env["CARGO_ENCODED_RUSTFLAGS"] = "\x1f".join(flags)
    if variant == "clif-cache":
        env["RUST_INTERP_FUNCTION_CACHE"] = str(cache)
        env["RUST_INTERP_CACHE_STATS_PATH"] = str(stats)
    return env


@contextlib.contextmanager
def source_probe(name, project):
    source = WORK / "sources" / name
    marker = json.loads((source / ".rust-interp-owned.json").read_text())
    if marker["owner"] != str(ROOT) or marker["revision"] != project["revision"]:
        raise RuntimeError("Snapshot ownership/revision mismatch: " + name)
    if checked_output(["git", "rev-parse", "HEAD"], source) != project["revision"]:
        raise RuntimeError("Snapshot HEAD mismatch: " + name)
    if checked_output(["git", "diff", "--name-only", "HEAD"], source):
        raise RuntimeError("Snapshot has existing tracked modifications: " + name)
    path = source / project["edit_file"]
    original = path.read_bytes()
    text = original.decode()
    if text.count(project["anchor"]) != 1:
        raise RuntimeError("Probe anchor is not unique")
    extra = None
    if project["probe_kind"] == "library" and not project.get("driver"):
        extra = source / "crates/fre/examples/rust_interp_probe.rs"
        if extra.exists():
            raise RuntimeError("Refusing to replace an existing example")
        extra.parent.mkdir(exist_ok=True)
        extra.write_text('fn main() { println!("{}", fre::escape("[a+b]")); }\n')
    last = original

    def set_state(state):
        nonlocal last
        if path.read_bytes() != last:
            raise RuntimeError("Source changed outside benchmark; refusing overwrite")
        factor = 11 if state == "A" else 13 + 2 * int(state[1:])
        expression = 'std::hint::black_box(7u64).wrapping_mul(' + str(factor) + 'u64)'
        result = 'return format!("rust-interp-probe-{}", ' + expression + ');' if project["probe_kind"] == "library" else (
            'println!("rust-interp-probe-{}", ' + expression + '); std::process::exit(0);')
        body = '\n    if std::env::var_os("RUST_INTERP_BENCH_PROBE").is_some() { ' + result + ' }\n'
        data = text.replace(project["anchor"], project["anchor"] + body).encode()
        if data != last:
            path.write_bytes(data)
        last = data
        return digest(data)
    try:
        yield source, set_state
    finally:
        if path.read_bytes() == last:
            path.write_bytes(original)
        else:
            raise RuntimeError("Source changed outside benchmark; original retained in git")
        if extra is not None:
            extra.unlink()


def cargo_messages(path):
    artifacts, rebuilt, fresh = [], 0, 0
    for line in path.read_text(errors="replace").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if item.get("reason") == "compiler-artifact":
            if item.get("fresh"):
                fresh += 1
            else:
                rebuilt += 1
            if item.get("executable"):
                artifacts.append(item["executable"])
    return artifacts, rebuilt, fresh


def execute_check(binary, name, state, fixture):
    env = os.environ.copy()
    env["RUST_INTERP_BENCH_PROBE"] = "1"
    start = time.perf_counter()
    p = subprocess.run([binary], env=env, capture_output=True)
    elapsed = time.perf_counter() - start
    factor = 11 if state == "A" else 13 + 2 * int(state[1:])
    expected = ("rust-interp-probe-" + str(7 * factor) + "\n").encode()
    if p.returncode != 0 or p.stdout != expected:
        raise RuntimeError("Edited binary did not produce expected probe: " + repr((p.returncode, p.stdout, p.stderr[-500:])))
    env.pop("RUST_INTERP_BENCH_PROBE")
    if name == "fre":
        args, expected, status = [], b"\\[a\\+b\\] 4193920\n", 0
    elif name == "nushell":
        args, expected, status = ["--no-config-file", "--no-history", "-c", "[1 2 3] | math sum"], b"6\n", 0
    elif name == "ruff":
        fixture.mkdir(exist_ok=True)
        (fixture / "input.py").write_text("import os\n")
        args, expected, status = ["check", "--no-cache", "--isolated", "--output-format", "concise", str(fixture / "input.py")], None, 1
    elif name == "rg-aot":
        fixture.mkdir(exist_ok=True)
        corpus = fixture / "corpus"
        corpus.mkdir(exist_ok=True)
        (corpus / "input.rs").write_text("needle\nother\n")
        manifest = fixture / "queries.json"
        manifest.write_text(json.dumps({"schema_version": 1, "name": "rust-interp-fixture", "queries": [{"id": "needle", "pattern": "needle"}]}))
        args, expected, status = ["scan", "--manifest", str(manifest), "--root", str(corpus), "--output", "matches"], None, 0
    else:
        # The initial pgrust pass checks linking and startup only. Database
        # correctness requires an unwind-capable backend and a separate suite.
        args, expected, status = ["--version"], None, 0
    start = time.perf_counter()
    p = subprocess.run([binary] + args, env=env, capture_output=True)
    runtime = time.perf_counter() - start
    if p.returncode != status or (expected is not None and p.stdout != expected):
        raise RuntimeError("Runtime check failed: " + repr((p.returncode, p.stdout[-500:], p.stderr[-500:])))
    if name == "ruff" and b"F401" not in p.stdout:
        raise RuntimeError("Ruff missed the seeded unused import")
    if name == "rg-aot" and b"needle" not in p.stdout:
        raise RuntimeError("rg-aot missed seeded search result")
    if name == "pgrust" and b"postgres" not in p.stdout.lower():
        raise RuntimeError("Unexpected postgres version output")
    return elapsed, runtime, digest(p.stdout), args


def build(run_dir, name, project, variant, case, ordinal, state, source, sha, jobs, target_triple, incremental, debug, linker):
    prefix = run_dir / ("%03d-%s-%s" % (ordinal, variant, case))
    target = WORK / "targets" / run_dir.parent.name / name / variant
    cache = WORK / "function-caches" / run_dir.parent.name / name / digest(BACKEND.read_bytes())[:24] if variant == "clif-cache" else WORK / "unused-cache"
    stats = prefix.with_suffix(".cache")
    env = environment(variant, target, cache, stats, incremental, debug, linker)
    if variant == "clif-cache":
        env["RUST_INTERP_CACHE_WORKSPACE"] = str(source)
    command = ["cargo", "+" + TOOLCHAIN, "build", "--locked", "--offline", "--target", target_triple,
               "--jobs", str(jobs), "--message-format=json-render-diagnostics"] + project["cargo_args"]
    if project.get("driver"):
        command += ["--manifest-path", str(WORK / project["driver"] / "Cargo.toml")]
    start = time.perf_counter()
    cpu = resource.getrusage(resource.RUSAGE_CHILDREN)
    row = {"project": name, "variant": variant, "case": case, "ordinal": ordinal, "state": state,
           "source_sha256": sha, "command": command, "target_dir": str(target), "cache_dir": str(cache),
           "load_before": os.getloadavg(), "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "free_disk_bytes": shutil.disk_usage(WORK).free, "status": "running"}
    if row["free_disk_bytes"] < 15 * 1024 ** 3:
        raise RuntimeError("Less than 15 GiB free; preserve existing artifacts and stop")
    with prefix.with_suffix(".stdout").open("w") as out, prefix.with_suffix(".stderr").open("w") as err:
        process = subprocess.Popen(command, cwd=source, env=env, stdout=out, stderr=err)
        row["pid"] = process.pid
        prefix.with_suffix(".process.json").write_text(json.dumps(row, indent=2))
        status = process.wait()
    row["build_seconds"] = time.perf_counter() - start
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    row["cpu_seconds"] = after.ru_utime + after.ru_stime - cpu.ru_utime - cpu.ru_stime
    row["load_after"] = os.getloadavg()
    row["exit_code"] = status
    artifacts, row["rebuilt_artifacts"], row["fresh_artifacts"] = cargo_messages(prefix.with_suffix(".stdout"))
    row.update(cache_hits=0, cache_misses=0, cache_write_errors=0)
    if stats.exists():
        for line in stats.read_text().splitlines():
            _, hits, misses, errors = map(int, line.split())
            row["cache_hits"] += hits
            row["cache_misses"] += misses
            row["cache_write_errors"] += errors
    row["status"] = "build-failed" if status else "ok"
    if not status:
        try:
            if variant == "clif-cache" and row["rebuilt_artifacts"] and not row["cache_hits"] + row["cache_misses"]:
                raise RuntimeError("Rebuild had no function-cache telemetry")
            if case == "no-op" and row["rebuilt_artifacts"]:
                raise RuntimeError("No-op unexpectedly rebuilt artifacts")
            if len(artifacts) != 1:
                raise RuntimeError("Expected exactly one executable, got " + repr(artifacts))
            row["binary"] = artifacts[0]
            row["probe_seconds"], row["runtime_seconds"], row["runtime_stdout_sha256"], row["runtime_args"] = execute_check(artifacts[0], name, state, run_dir / "fixture")
            row["feedback_seconds"] = row["build_seconds"] + row["probe_seconds"] + row["runtime_seconds"]
        except Exception as exc:
            row["status"] = "validation-failed"
            row["error"] = str(exc)
    if status:
        row["error_tail"] = prefix.with_suffix(".stderr").read_text(errors="replace")[-4000:]
    prefix.with_suffix(".json").write_text(json.dumps(row, indent=2) + "\n")
    with (run_dir / "results.jsonl").open("a") as file:
        file.write(json.dumps(row) + "\n")
    print("%s %s %s %.3fs %s rebuilt=%d hits=%d misses=%d" % (
        name, variant, case, row["build_seconds"], row["status"], row["rebuilt_artifacts"], row["cache_hits"], row["cache_misses"]), flush=True)
    if row["status"] != "ok":
        print(row.get("error", row.get("error_tail", ""))[-1800:], flush=True)
    return row


def benchmark(args):
    WORK.mkdir(exist_ok=True)
    failed = False
    # One lock for all timing runs and source edits in this workspace. Never
    # probe/kill processes in other sessions to create an artificially idle host.
    with (WORK / "benchmark.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        rustc = checked_output(["rustup", "run", TOOLCHAIN, "rustc", "-vV"])
        triple = next(line.split(": ", 1)[1] for line in rustc.splitlines() if line.startswith("host:"))
        linker = "system"
        if args.linker == "lld":
            sysroot = Path(checked_output(["rustup", "run", TOOLCHAIN, "rustc", "--print", "sysroot"]))
            linker = str(sysroot / "lib/rustlib" / triple / "bin/gcc-ld" / ("ld64.lld" if sys.platform == "darwin" else "ld.lld"))
            if not Path(linker).is_file():
                raise RuntimeError("Pinned toolchain has no LLD at " + linker)
        for name in args.projects:
            project = CONFIG["projects"][name]
            run_dir = WORK / "runs" / args.run_id / name
            run_dir.mkdir(parents=True, exist_ok=True)
            if (run_dir / "results.jsonl").exists():
                raise RuntimeError("Run already contains results; choose a new run-id")
            run_dir.joinpath("provenance.json").write_text(json.dumps({
                "project": project, "compiler": rustc, "platform": platform.platform(), "jobs": args.jobs,
                "variants": args.variants, "incremental": args.incremental, "dev_debug": args.debug,
                "linker": linker,
                "edit_note": "Synthetic arithmetic body edit; each B state is new, with a black_box operand and a different immediate multiplier; A is the revert",
                "cache_scope": "workspace source directories; registry functions excluded",
                "profile_note": "Repository optimization settings retained; explicit debug/incremental settings as recorded; matching panic=abort except llvm-unwind",
                "backend_sha256": digest(BACKEND.read_bytes()) if BACKEND.exists() else None,
                "harness_sha256": HARNESS_SHA256,
                "cargo_lock_sha256": digest(((WORK / project["driver"] if project.get("driver") else WORK / "sources" / name) / "Cargo.lock").read_bytes()),
                "driver_sources": {p: digest((WORK / project["driver"] / p).read_bytes()) for p in ["Cargo.toml", "main.rs"]} if project.get("driver") else None,
            }, indent=2) + "\n")
            with source_probe(name, project) as (source, set_state):
                ordinal = 0
                alive = list(args.variants)
                cases = [("cold", "A"), ("no-op", "A")]
                for iteration in range(args.repeats):
                    cases += [("body-edit", "B%04d" % iteration), ("revert", "A"), ("no-op", "A")]
                for index, (case, state) in enumerate(cases):
                    sha = set_state(state)
                    # Reverse order in alternating rounds to reduce fixed order bias.
                    order = list(alive) if index % 2 == 0 else list(reversed(alive))
                    for variant in order:
                        if case == "cold":
                            target = WORK / "targets" / args.run_id / name / variant
                            if target.exists():
                                raise RuntimeError("Cold target already exists: " + str(target))
                        row = build(run_dir, name, project, variant, case, ordinal, state, source, sha, args.jobs, triple, args.incremental, args.debug, linker)
                        ordinal += 1
                        if row["status"] != "ok":
                            failed = True
                            alive.remove(variant)
                    if not alive:
                        break
    return not failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projects", nargs="+", choices=list(CONFIG["projects"]))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--variants", nargs="+", choices=VARIANTS + ["llvm-unwind"], default=VARIANTS)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--incremental", choices=["0", "1", "repository"], default="1")
    parser.add_argument("--debug", choices=["0", "1", "2", "repository"], default="repository")
    parser.add_argument("--linker", choices=["system", "lld"], default="system")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id) or args.repeats < 0 or args.jobs < 1:
        parser.error("Invalid run-id, repetitions, or job count")
    sys.exit(0 if benchmark(args) else 1)
