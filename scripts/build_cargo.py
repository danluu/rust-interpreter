#!/usr/bin/env python3
"""Build a pinned, opt-in Cargo publication experiment without replacing Cargo."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from prepare import ROOT, PINS

SOURCE = ROOT / ".work/sources/cargo"


def build():
    with (ROOT / ".work/benchmark.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = json.loads((SOURCE / ".rust-interp-owned.json").read_text())
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SOURCE, text=True).strip()
        assert marker["owner"] == str(ROOT) and marker["revision"] == head == PINS["cargo"]
        relative = "crates/cargo-util/src/paths.rs"
        original = subprocess.check_output(["git", "show", "HEAD:" + relative], cwd=SOURCE).decode()
        anchor = "    // NB: we can't use dst.exists(), as if dst is a broken symlink,"
        insertion = '''    #[cfg(target_os = "macos")]
    if std::env::var_os("RUST_INTERP_PRESERVE_EXECUTABLES").is_some_and(|v| v == "1")
        && preserve_executable::identical_executables(src, dst).unwrap_or(false)
    {
        return Ok(());
    }

'''
        assert original.count(anchor) == 1
        patched = original.replace(anchor, insertion + anchor)
        patched += '\n#[cfg(target_os = "macos")]\n#[path = "preserve_executable.rs"]\nmod preserve_executable;\n'
        path = SOURCE / relative
        assert path.read_text() in (original, patched), "Unrecognized Cargo source edits"
        if path.read_text() != patched:
            path.write_text(patched)
        helper = ROOT / "compiler/preserve_executable.rs"
        destination = path.parent / helper.name
        if not destination.exists() or destination.read_bytes() != helper.read_bytes():
            shutil.copyfile(helper, destination)
        target = ROOT / ".work/cargo-build"
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(("RUST_INTERP_", "CARGO_PROFILE_")) or key in ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC", "CARGO_TARGET_DIR"):
                env.pop(key)
        env.update(CFG_RELEASE_CHANNEL="nightly", RUSTC_WRAPPER="", RUSTC_WORKSPACE_WRAPPER="")
        command = ["cargo", "+nightly-2026-09-08", "build", "--manifest-path", str(SOURCE / "Cargo.toml"),
                   "--release", "--locked", "--jobs", "4", "--target-dir", str(target), "--bin", "cargo"]
        subprocess.run(command, env=env, cwd=ROOT, check=True)
        binary = target / "release/cargo"
        record = {"revision": head, "cargo": str(binary), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                  "helper_sha256": hashlib.sha256(helper.read_bytes()).hexdigest(), "command": command}
        (target / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
        print(binary, flush=True)


if __name__ == "__main__":
    build()
