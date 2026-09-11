#!/usr/bin/env python3
"""Cargo launcher with isolated native artifacts and an optional function cache."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLCHAIN = "nightly-2026-09-08"


def cargo_config(key, arguments):
    command = ["cargo", "+" + TOOLCHAIN, "-Zunstable-options", "config", "get", key, "--format", "json"]
    for i, argument in enumerate(arguments):
        if argument == "--config" and i + 1 < len(arguments):
            command += [argument, arguments[i + 1]]
        elif argument.startswith("--config="):
            command.append(argument)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        if "config value `" + key + "` is not set" in result.stderr:
            return None
        raise RuntimeError(result.stderr)
    value = json.loads(result.stdout)
    for part in key.split("."):
        value = value[part]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__, usage="%(prog)s [--backend llvm|clif|clif-cache] [--panic-abort] CARGO_COMMAND ...")
    parser.add_argument("--backend", choices=["llvm", "clif", "clif-cache"], default="llvm")
    parser.add_argument("--panic-abort", action="store_true")
    parser.add_argument("--linker", choices=["system", "lld"], default="system")
    parser.add_argument("--preserve-executables", action="store_true",
                        help="Use the experimental macOS Cargo publication fix")
    parser.add_argument("cargo_args", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    cargo_args = options.cargo_args
    if cargo_args and cargo_args[0] == "--":
        cargo_args.pop(0)
    if not cargo_args or cargo_args[0] not in ["build", "check", "run", "test", "rustc"]:
        parser.error("Supply build, check, run, test, or rustc")
    fast = options.backend != "llvm"
    cargo_options = cargo_args[:cargo_args.index("--")] if "--" in cargo_args else list(cargo_args)
    if any(x == "--target-dir" or x.startswith("--target-dir=") for x in cargo_options):
        parser.error("This launcher manages target directories to isolate backend versions; use Cargo directly for a custom --target-dir")
    if fast and not options.panic_abort:
        parser.error("This backend build requires --panic-abort. Use --backend llvm for ordinary unwinding semantics.")
    release_profile = "--release" in cargo_options or "--profile=release" in cargo_options or any(
        value == "--profile" and index + 1 < len(cargo_options) and cargo_options[index + 1] == "release"
        for index, value in enumerate(cargo_options)
    )
    if fast and (cargo_args[0] == "test" or release_profile):
        parser.error("Use LLVM for tests and release builds in this prototype")
    locate = ["cargo", "+" + TOOLCHAIN, "locate-project", "--workspace", "--message-format", "plain"]
    for i, arg in enumerate(cargo_options):
        if arg == "--manifest-path" and i + 1 < len(cargo_options):
            locate += [arg, cargo_options[i + 1]]
        elif arg.startswith("--manifest-path="):
            locate.append(arg)
    workspace = Path(subprocess.check_output(locate, text=True).strip()).parent.resolve()
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("RUST_INTERP_"):
            env.pop(key)
    cargo_command = ["cargo", "+" + TOOLCHAIN]
    if options.preserve_executables:
        if sys.platform != "darwin":
            parser.error("Executable preservation is currently a macOS experiment")
        manifest = ROOT / ".work/cargo-build/manifest.json"
        if not manifest.exists():
            parser.error("Build the Cargo experiment first with scripts/build_cargo.py")
        build = json.loads(manifest.read_text())
        cargo = Path(build["cargo"])
        helper = ROOT / "compiler/preserve_executable.rs"
        if (build["revision"] != "3c0b534756e166d12eb9fd2e1abfe5b42ac6101e"
                or hashlib.sha256(cargo.read_bytes()).hexdigest() != build["sha256"]
                or hashlib.sha256(helper.read_bytes()).hexdigest() != build["helper_sha256"]):
            parser.error("Cargo experiment identity changed; rerun scripts/build_cargo.py")
        env["RUST_INTERP_PRESERVE_EXECUTABLES"] = "1"
        cargo_command = ["rustup", "run", TOOLCHAIN, str(cargo)]
    flags = []
    if options.panic_abort:
        flags.append("-Cpanic=abort")
    if options.linker == "lld":
        info = subprocess.check_output(["rustup", "run", TOOLCHAIN, "rustc", "-vV"], text=True)
        host = next(line.split(": ", 1)[1] for line in info.splitlines() if line.startswith("host:"))
        sysroot = Path(subprocess.check_output(["rustup", "run", TOOLCHAIN, "rustc", "--print", "sysroot"], text=True).strip())
        linker = sysroot / "lib/rustlib" / host / "bin/gcc-ld" / ("ld64.lld" if sys.platform == "darwin" else "ld.lld")
        if not linker.is_file():
            parser.error("No bundled LLD for this host")
        flags += ["-Clinker=clang", "-Clink-arg=-fuse-ld=" + str(linker)]
    identity = {"workspace": str(workspace), "toolchain": TOOLCHAIN, "backend": options.backend, "flags": list(flags)}
    if fast:
        manifest = ROOT / ".work/backend-build/manifest.json"
        if not manifest.exists():
            parser.error("Build the backend first with scripts/build_backend.py")
        build = json.loads(manifest.read_text())
        backend = Path(build["backend"])
        sha = hashlib.sha256(backend.read_bytes()).hexdigest()
        if sha != build["backend_sha256"] or any(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != value for p, value in build["inputs"].items()):
            parser.error("Backend/source identity changed; rerun scripts/build_backend.py")
        identity["backend_sha256"] = sha
        flags.append("-Zcodegen-backend=" + str(backend))
        if options.backend == "clif-cache":
            env["RUST_INTERP_FUNCTION_CACHE"] = str(ROOT / ".work/dev-cache" / sha)
            env["RUST_INTERP_CACHE_WORKSPACE"] = str(workspace)
    if flags:
        dispatcher = ROOT / ".work/dispatch-build/release/rustc-dispatch"
        if not dispatcher.is_file():
            parser.error("Build the dispatcher first with scripts/build_backend.py")
        identity["dispatcher_sha256"] = hashlib.sha256(dispatcher.read_bytes()).hexdigest()
        identity["flags"] = list(flags)
        real_rustc = subprocess.check_output(["rustup", "which", "--toolchain", TOOLCHAIN, "rustc"], text=True).strip()
        custom = env.get("RUSTC") or cargo_config("build.rustc", cargo_options)
        if custom and Path(custom).resolve() != Path(real_rustc).resolve():
            parser.error("This launcher requires its pinned rustc; use Cargo directly for a custom compiler")
        env["RUST_INTERP_REAL_RUSTC"] = real_rustc
        env["RUST_INTERP_DISPATCH_FLAGS"] = "\x1f".join(flags)
        env["RUST_INTERP_DISPATCH_TARGET_ONLY"] = "1"
        # An explicit target keeps host build scripts/proc macros on LLVM. Honor
        # target selection from the command, environment, and Cargo config.
        explicit = any(x == "--target" or x.startswith("--target=") for x in cargo_options)
        configured = env.get("CARGO_BUILD_TARGET") or cargo_config("build.target", cargo_options)
        if not explicit and not configured:
            info = subprocess.check_output(["rustup", "run", TOOLCHAIN, "rustc", "-vV"], text=True)
            host = next(line.split(": ", 1)[1] for line in info.splitlines() if line.startswith("host:"))
            # Place Cargo flags before a possible `--` introducing application args.
            index = cargo_args.index("--") if "--" in cargo_args else len(cargo_args)
            cargo_args[index:index] = ["--target", host]
    namespace = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
    if flags:
        facade = ROOT / ".work/dispatchers" / namespace / "rustc"
        facade.parent.mkdir(parents=True, exist_ok=True)
        if facade.exists():
            if hashlib.sha256(facade.read_bytes()).hexdigest() != identity["dispatcher_sha256"]:
                parser.error("Dispatcher identity mismatch")
        else:
            shutil.copy2(dispatcher, facade)
        env["RUSTC"] = str(facade)
    # Backend file contents are part of this namespace: Cargo does not itself
    # guarantee invalidation when an external backend dylib changes in place.
    env["CARGO_TARGET_DIR"] = str(ROOT / ".work/dev-targets" / namespace)
    env.setdefault("CARGO_BUILD_JOBS", "4")
    # Publication changes only whether byte-identical files are replaced. It
    # deliberately shares the existing compiler-artifact namespace.
    command = cargo_command + cargo_args
    os.execvpe(command[0], command, env)


if __name__ == "__main__":
    main()
