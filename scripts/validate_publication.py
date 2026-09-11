#!/usr/bin/env python3
"""Exercise executable reuse, configuration changes, repair, and failed builds."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def validate():
    work = ROOT / ".work" / ("publication-validation-" + str(time.time_ns()))
    (work / "src").mkdir(parents=True)
    (work / "Cargo.toml").write_text('[package]\nname="publication-fixture"\nversion="0.1.0"\nedition="2024"\n[features]\nalternative=[]\n[workspace]\n')
    source = work / "src/main.rs"
    original = '''#[cfg(feature="alternative")] const VALUE: &str = "two";
#[cfg(not(feature="alternative"))] const VALUE: &str = "one";
fn main() {
    std::panic::set_hook(Box::new(|_| {}));
    assert!(std::panic::catch_unwind(|| panic!("normal unwinding")).is_err());
    println!("{VALUE}");
}
'''
    source.write_text(original)
    binary = work / "target/debug/publication-fixture"
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("RUST_INTERP_", "CARGO_PROFILE_")) or key in ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC", "CARGO_TARGET_DIR"):
            env.pop(key)
    env.update(RUST_INTERP_PRESERVE_EXECUTABLES="1", RUSTC_WRAPPER="", RUSTC_WORKSPACE_WRAPPER="")
    base = ["rustup", "run", "nightly-2026-09-08", str(ROOT / ".work/cargo-build/release/cargo"),
            "run", "--offline", "--quiet", "--target-dir", str(work / "target")]
    results = []

    def run(name, expected, arguments=(), same_inode=None):
        before = binary.stat().st_ino if binary.exists() else None
        p = subprocess.run(base + list(arguments), env=env, cwd=work, capture_output=True)
        (work / (name + ".stderr")).write_bytes(p.stderr)
        if expected is None:
            assert p.returncode != 0 and p.stdout == b"", (name, p.returncode, p.stdout)
        else:
            assert p.returncode == 0 and p.stdout == expected, (name, p.returncode, p.stdout, p.stderr[-1000:])
            if same_inode is not None:
                assert (before == binary.stat().st_ino) == same_inode, name
        results.append({"case": name, "passed": True})
        print(name, "passed", flush=True)

    with (ROOT / ".work/benchmark.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run("initial", b"one\n")
        run("no-op", b"one\n", same_inode=True)
        run("feature-change", b"two\n", ["--features", "alternative"], same_inode=False)
        run("feature-revert", b"one\n", same_inode=False)
        source.write_text(original.replace('"one"', '"new"'))
        run("body-change", b"new\n", same_inode=False)
        run("changed-no-op", b"new\n", same_inode=True)
        subprocess.run(["/usr/bin/xattr", "-w", "com.rust-interp.test", "fixture", str(binary)], check=True)
        run("extended-attribute-fallback", b"new\n", same_inode=False)
        assert subprocess.check_output(["/usr/bin/xattr", str(binary)]) == b""
        # On macOS Cargo publishes a distinct copy. Corrupt only that public
        # copy; the next command must repair it before trying to execute it.
        with binary.open("r+b") as file:
            file.seek(-1, 2)
            byte = file.read(1)
            file.seek(-1, 2)
            file.write(bytes([byte[0] ^ 1]))
        run("damaged-copy-repair", b"new\n", same_inode=False)
        source.write_text(original + '\nfn invalid_uncalled() -> u64 { "wrong" }\n')
        run("failed-build-does-not-run-old-binary", None)
    (work / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(work, flush=True)


if __name__ == "__main__":
    validate()
