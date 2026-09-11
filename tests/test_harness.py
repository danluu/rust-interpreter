import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bench", ROOT / "scripts/bench.py")
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class HarnessTests(unittest.TestCase):
    def test_environment_isolates_flags_and_cache_scope(self):
        dirty = {"RUSTFLAGS": "-Copt-level=3", "CARGO_TARGET_DIR": "/unrelated", "RUSTC_WRAPPER": "/unrelated-wrapper",
                 "CARGO_PROFILE_DEV_DEBUG": "2", "RUST_INTERP_FUNCTION_CACHE": "/unrelated-cache"}
        with patch.dict(os.environ, dirty):
            env = bench.environment("llvm", Path("target"), Path("cache"), Path("stats"))
        self.assertEqual(env["CARGO_TARGET_DIR"], "target")
        self.assertEqual(env["CARGO_PROFILE_DEV_DEBUG"], "0")
        self.assertEqual(env["CARGO_ENCODED_RUSTFLAGS"], "-Cpanic=abort")
        self.assertFalse(env.get("RUSTC_WRAPPER"))
        self.assertNotIn("RUST_INTERP_FUNCTION_CACHE", env)
        normal = bench.environment("llvm-unwind", Path("target"), Path("cache"), Path("stats"), "repository", "repository")
        self.assertNotIn("CARGO_INCREMENTAL", normal)
        self.assertNotIn("CARGO_PROFILE_DEV_DEBUG", normal)
        self.assertEqual(normal["CARGO_ENCODED_RUSTFLAGS"], "")

    def test_probe_restores_bytes_on_failure_and_noop_does_not_touch(self):
        with tempfile.TemporaryDirectory(prefix="rust-interp-harness-test-") as directory:
            root = Path(directory)
            source = root / ".work/sources/example"
            source.mkdir(parents=True)
            original = b"fn main() { println!(\"original\"); }\n"
            path = source / "main.rs"
            path.write_bytes(original)
            subprocess.run(["git", "init", "--quiet"], cwd=source, check=True)
            subprocess.run(["git", "add", "main.rs"], cwd=source, check=True)
            subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "fixture"], cwd=source, check=True)
            revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
            (source / ".rust-interp-owned.json").write_text(json.dumps({"owner": str(root), "revision": revision}))
            project = {"revision": revision, "edit_file": "main.rs", "anchor": "fn main() {", "probe_kind": "main"}
            with patch.multiple(bench, ROOT=root, WORK=root / ".work"):
                with self.assertRaisesRegex(RuntimeError, "deliberate"):
                    with bench.source_probe("example", project) as (_, set_state):
                        first = set_state("A")
                        stamp = path.stat().st_mtime_ns
                        self.assertEqual(first, set_state("A"))
                        self.assertEqual(stamp, path.stat().st_mtime_ns)
                        self.assertNotEqual(first, set_state("B0000"))
                        self.assertIn(b"wrapping_mul(13u64)", path.read_bytes())
                        raise RuntimeError("deliberate")
                self.assertEqual(path.read_bytes(), original)
                path.write_text("user modification")
                with self.assertRaisesRegex(RuntimeError, "existing tracked modifications"):
                    with bench.source_probe("example", project):
                        self.fail("Accepted an edited snapshot")
                self.assertEqual(path.read_text(), "user modification")


if __name__ == "__main__":
    unittest.main()
