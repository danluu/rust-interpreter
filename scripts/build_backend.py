#!/usr/bin/env python3
"""Build the pinned backend; all products stay inside this project."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import shutil
import fcntl
from patch_backend import patch, ROOT

TOOLCHAIN = "nightly-2026-09-08"

if __name__ == "__main__":
    lock = (ROOT / ".work/benchmark.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    patch()
    command = ["cargo", "+" + TOOLCHAIN, "build", "--manifest-path", str(ROOT / ".work/sources/cg-clif/Cargo.toml"),
               "--release", "--features", "unstable-features", "--jobs", "4", "--target-dir", str(ROOT / ".work/backend-build"), "--locked"]
    subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run(["cargo", "+" + TOOLCHAIN, "build", "-p", "rustc-dispatch", "--release", "--jobs", "4", "--target-dir", str(ROOT / ".work/dispatch-build"), "--locked"], cwd=ROOT, check=True)
    backend = ROOT / (".work/backend-build/release/librustc_codegen_cranelift." + ("dylib" if sys.platform == "darwin" else "so"))
    sha = hashlib.sha256(backend.read_bytes()).hexdigest()
    versioned = ROOT / ".work/backends" / sha / backend.name
    versioned.parent.mkdir(parents=True, exist_ok=True)
    if versioned.exists():
        if hashlib.sha256(versioned.read_bytes()).hexdigest() != sha:
            raise RuntimeError("Existing versioned backend has unexpected contents")
    else:
        shutil.copy2(backend, versioned)
    data = {"toolchain": TOOLCHAIN, "command": command, "backend": str(backend),
            "backend_sha256": hashlib.sha256(backend.read_bytes()).hexdigest(),
            "inputs": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in [
                "compiler/cache_adapter.rs", "compiler/Cargo.lock", "scripts/patch_backend.py", "crates/function-cache/src/lib.rs", "crates/function-cache/Cargo.toml"]}}
    dispatcher = ROOT / ".work/dispatch-build/release/rustc-dispatch"
    data["dispatcher"] = str(dispatcher)
    data["dispatcher_sha256"] = hashlib.sha256(dispatcher.read_bytes()).hexdigest()
    data["backend"] = str(versioned)
    (ROOT / ".work/backend-build/manifest.json").write_text(json.dumps(data, indent=2) + "\n")
    print(backend)
