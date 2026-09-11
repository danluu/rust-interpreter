#!/usr/bin/env python3
"""Check actual Cargo config propagation and host/target compiler separation."""
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    work = ROOT / ".work" / ("launcher-validation-" + str(time.time_ns()))
    (work / "src").mkdir(parents=True)
    (work / ".cargo").mkdir()
    (work / "Cargo.toml").write_text('[package]\nname="launcher-fixture"\nversion="0.1.0"\nedition="2024"\n[workspace]\n')
    (work / ".cargo/config.toml").write_text('[build]\nrustflags=["--cfg", "project_probe"]\n')
    (work / "src/main.rs").write_text('#[cfg(not(project_probe))]\ncompile_error!("Cargo project flags were lost");\nfn main() { assert_eq!(std::env::args().skip(1).collect::<Vec<_>>(), ["--backend", "application", "--release"]); println!("flags-preserved"); }\n')
    (work / "build.rs").write_text('fn main() {\n assert!(std::panic::catch_unwind(|| panic!("expected host unwind")).is_err());\n println!("cargo:rustc-check-cfg=cfg(project_probe)");\n}\n')
    rows = []
    for backend in ["llvm", "clif", "clif-cache"]:
        for preserve in [False, True]:
            command = ["python3", str(ROOT / "scripts/dev.py"), "--backend", backend]
            if backend != "llvm":
                command.append("--panic-abort")
            if preserve:
                command.append("--preserve-executables")
            command += ["run", "--offline", "--quiet", "--", "--backend", "application", "--release"]
            result = subprocess.run(command, cwd=work, capture_output=True)
            (work / (backend + ("-preserve" if preserve else "") + ".stderr")).write_bytes(result.stderr)
            assert result.returncode == 0, (backend, preserve, result.stderr.decode(errors="replace")[-3000:])
            assert result.stdout == b"flags-preserved\n", result.stdout
            rows.append({"backend": backend, "preserve_executables": preserve, "config_preserved": True, "host_unwind_preserved": True, "application_arguments_preserved": True})
            print(backend, "preserve=" + str(preserve), "config and host/target separation passed", flush=True)
    (work / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(work)
