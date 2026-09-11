#!/usr/bin/env python3
"""Build FRE as a dependency, avoiding unrelated workspace dev-dependencies."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def prepare():
    driver = ROOT / ".work/drivers/fre"
    marker = driver / ".rust-interp-owned.json"
    if driver.exists():
        if not marker.exists() or json.loads(marker.read_text())["owner"] != str(ROOT):
            raise RuntimeError("Unowned driver directory")
    else:
        driver.mkdir(parents=True)
        marker.write_text(json.dumps({"owner": str(ROOT)}))
    path = str(ROOT / ".work/sources/fre/crates/fre")
    (driver / "Cargo.toml").write_text('[package]\nname = "rust-interp-fre-driver"\nversion = "0.1.0"\nedition = "2024"\n\n[workspace]\n\n[[bin]]\nname = "rust-interp-fre-driver"\npath = "main.rs"\n\n[dependencies]\nfre = { path = ' + json.dumps(path) + ' }\n')
    (driver / "main.rs").write_bytes((ROOT / "benchmarks/fre-driver/main.rs").read_bytes())
    subprocess.run(["cargo", "+nightly-2026-09-08", "generate-lockfile", "--offline"], cwd=driver, check=True)
    print(driver)


if __name__ == "__main__":
    prepare()
