#!/usr/bin/env python3
"""One actual stock launcher call; Cargo and VM process boundaries alone are stubbed."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

FORBIDDEN = ("interpreter", "compiler_association", "custom_compiler", "custom_cargo",
    "runtime_compiler", "runtime_tools", "std_mir", "std_mir_source", "frontend_workers",
    "host_library_opt", "host_proc_macro_opt", "stable_mono_cgu", "allocation_trace",
    "dataclasses", "unittest")
FEATURES = tuple(n for n in FORBIDDEN if n not in
    ("interpreter", "compiler_association", "custom_compiler", "dataclasses", "unittest"))


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    require(len(sys.argv) == 2, "one sample descriptor required")
    config = json.loads(Path(sys.argv[1]).read_bytes())
    require(config["schema_version"] == 1, "sample schema")
    root, owner = Path(config["source_root"]), Path(config["tool_owner"])
    tools, manifest = Path(config["tool_directory"]), Path(config["manifest"])
    artifact, work = Path(config["artifact"]), Path(config["expected_work"])
    cache_parent = Path(config["workspace_cache_root"])
    require(root.resolve() == root and owner.resolve() == owner, "noncanonical roots")
    require(cache_parent.resolve() == cache_parent and cache_parent.is_dir()
            and cache_parent.is_relative_to(Path(config["output_root"])), "owned cache parent required")
    require(sys.pycache_prefix == config["pycache_prefix"]
            and sys.dont_write_bytecode == (not config["warmup"]), "wrong bytecode regime")
    require(not any(n == blocked or n.startswith(blocked + ".")
                    for n in sys.modules for blocked in FORBIDDEN), "implementation preloaded")
    preloaded = sorted(sys.modules)
    sys.path.insert(0, str(root / "scripts"))
    base_env = dict(os.environ)
    require(not any(n.startswith("RUST_INTERP_") for n in base_env), "ambient interpreter options")
    require(base_env["PYTHONPYCACHEPREFIX"] == config["pycache_prefix"], "cache environment mismatch")
    expected_env = dict(base_env)
    expected_env.update(RUSTC_WRAPPER=str(tools / "rust-interp-rustc-wrapper"),
        RUSTC_WORKSPACE_WRAPPER="", RUST_INTERP_EXPORT_PACKAGE="fixture",
        RUST_INTERP_OUTPUT=str(work / "program.rbc"), RUST_INTERP_EXPORT_TEST="0",
        CARGO_TARGET_DIR=str(work / "target"), RUST_INTERP_INLINE_LEAVES="1", RUST_INTERP_ENTRY="selected")
    cargo = ["cargo", "+nightly-2026-09-08", "check", "--manifest-path", str(manifest),
        "--package", "fixture", "--lib", "--locked", "--offline", "--jobs", "1",
        "--message-format=json-render-diagnostics"]
    vm = [str(tools / "rust-interp-vm"), "--engine", "interpreter", str(artifact)]
    event = json.dumps(dict(reason="compiler-artifact", profile=dict(test=False),
                           filenames=[str(artifact).removesuffix(".rbc")])) + "\n"
    calls = []

    def stub(command, **kwargs):
        command = list(map(str, command))
        if not calls:
            require(command == cargo and set(kwargs) == {"cwd", "env", "stdout", "text"}
                and kwargs["cwd"] == manifest.parent and kwargs["env"] == expected_env
                and kwargs["stdout"] == subprocess.PIPE and kwargs["text"] is True,
                "unexpected Cargo boundary")
            calls.append(dict(kind="cargo", command=command, cwd=str(kwargs["cwd"]), env=kwargs["env"]))
            return subprocess.CompletedProcess(command, 0, stdout=event)
        require(len(calls) == 1 and command == vm and set(kwargs) == {"env"}
                and kwargs["env"] == expected_env, "unexpected VM/additional boundary")
        calls.append(dict(kind="vm", command=command, env=kwargs["env"]))
        return subprocess.CompletedProcess(command, 0)

    def reject_process(event, args):
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec",
                     "os.fork", "os.forkpty", "os.spawn"}:
            raise RuntimeError("unexpected process launch: " + event)

    subprocess.run = stub
    sys.addaudithook(reject_process)
    sys.argv = [str(root / "scripts/interpreter.py"), "--manifest-path", str(manifest),
        "--package", "fixture", "--entry", "selected", "--tool-key", config["tool_key"],
        "--workspace-cache-root", str(cache_parent), "--inline-leaves", "--jobs", "1"]
    wall_started, cpu_started = time.perf_counter_ns(), time.process_time_ns()
    import interpreter
    interpreter.ROOT = owner
    result = interpreter.main()
    cpu_ns = time.process_time_ns() - cpu_started
    wall_ns = time.perf_counter_ns() - wall_started
    require(result == 0 and len(calls) == 2, "main/boundary failure")
    require(Path(interpreter.__file__).resolve() == root / "scripts/interpreter.py", "wrong source")
    require(("custom_compiler" in sys.modules) == (config["arm"] == "baseline"),
            "custom compiler import boundary changed")
    require(("compiler_association" in sys.modules) == (config["arm"] == "candidate"),
            "light association import boundary changed")
    require(not any(n in sys.modules for n in FEATURES) and "unittest" not in sys.modules,
            "stock route imported optional feature/test machinery")
    # Provenance formatting is outside component clocks, inside parent process metrics.
    import importlib.util
    modules = {}
    for name, module in sorted(sys.modules.items()):
        namespace = vars(module)
        filename, cached = namespace.get("__file__"), namespace.get("__cached__")
        if isinstance(filename, str):
            modules[name] = dict(file=filename, cached=cached if isinstance(cached, str) else None)
    for call in calls:
        call["env"] = {k: v.replace(str(work), "<WORK>") for k, v in call["env"].items()}
    print(json.dumps(dict(schema_version=1, status="PASS", arm=config["arm"], warmup=config["warmup"],
        component_cpu_ns=cpu_ns, component_wall_ns=wall_ns, main_returncode=result,
        boundaries=calls, preloaded=preloaded, modules=modules,
        python=dict(executable=sys.executable, version=sys.version, cache_tag=sys.implementation.cache_tag,
                    magic=importlib.util.MAGIC_NUMBER.hex(), prefix=sys.prefix, base_prefix=sys.base_prefix),
        pycache_prefix=sys.pycache_prefix, dont_write_bytecode=sys.dont_write_bytecode), sort_keys=True))


if __name__ == "__main__":
    main()
