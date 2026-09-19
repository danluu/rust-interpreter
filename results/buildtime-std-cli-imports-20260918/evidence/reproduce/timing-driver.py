#!/usr/bin/env python3
"""One real stock std CLI reuse call on synthetic metadata; discovery alone is stubbed.

Source-only draft. A separately reviewed controller must bind the fixture and runtime.
"""
import io
import json
import os
from pathlib import Path
import sys
import time

FORBIDDEN = ("std_mir", "std_mir_readmission", "toolchain_lookup", "custom_compiler",
             "custom_cargo", "compiler_association", "custom_cargo_libraries",
             "tempfile", "dataclasses", "unittest")
PROCESS_EVENTS = frozenset(("subprocess.Popen", "os.system", "os.posix_spawn", "os.exec",
                            "os.fork", "os.forkpty", "os.spawn"))


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    require(len(sys.argv) == 2, "one bound sample descriptor required")
    sample = Path(sys.argv[1])
    require(not sample.is_symlink() and sample.stat().st_size <= 1024 ** 2,
            "sample must be a bounded regular input")
    config = json.loads(sample.read_bytes())
    require(config["schema_version"] == 1 and config["arm"] in ("baseline", "candidate"),
            "wrong sample schema or arm")
    require(sys.implementation.name == "cpython" and sys.version_info[:3] == (3, 14, 7)
            and sys.flags.isolated and sys.flags.no_site and sys.flags.no_user_site,
            "pinned isolated Python required")
    require(sys.pycache_prefix == config["pycache_prefix"]
            and sys.dont_write_bytecode == (not config["warmup"]), "wrong bytecode regime")
    root, owner = Path(config["source_root"]), Path(config["fixture_owner"])
    compiler_sysroot = Path(config["compiler_sysroot"])
    output_root = Path(config["fixture_output_root"])
    require(all(path.resolve() == path and path.is_dir()
                for path in (root, owner, compiler_sysroot, output_root)), "noncanonical roots")
    require(owner.is_relative_to(output_root) and compiler_sysroot.is_relative_to(output_root),
            "fixture paths must stay within the owned qualification output")
    require(config["toolchain"] == "nightly-2026-09-08" and config["artifact_count"] == 26,
            "unexpected fixture shape")
    require(not any(name == blocked or name.startswith(blocked + ".")
                    for name in sys.modules for blocked in FORBIDDEN), "implementation preloaded")
    require(not any(name.startswith("RUST_INTERP_") for name in os.environ),
            "ambient interpreter configuration")
    preloaded = sorted(sys.modules)
    discovery_calls, setup_calls, process_attempts = [], [], []
    saved_checked = None

    def discovery(toolchain, cache_directory=None):
        require(toolchain == config["toolchain"] and cache_directory is None
                and not discovery_calls, "unexpected identity discovery boundary")
        discovery_calls.append(dict(toolchain=toolchain, cache_directory=None, outcome="fresh"))
        return config["compiler_text"], compiler_sysroot, "fresh"

    def checked(*args, **kwargs):
        # Keep ordinary lookup imports in the clock for both arms. Baseline may
        # already have imported them through the unused custom Cargo installer.
        import toolchain_lookup
        require(args == (config["toolchain"],) and kwargs == {"fetch": False}
                and not setup_calls, "unexpected std setup selection")
        require(Path(toolchain_lookup.__file__).resolve() == root / "scripts/toolchain_lookup.py",
                "wrong lookup module")
        setup_calls.append(dict(toolchain=args[0], fetch=False))
        original_discovery = toolchain_lookup.compiler_identity
        toolchain_lookup.compiler_identity = discovery
        try:
            return saved_checked(*args, **kwargs)
        finally:
            toolchain_lookup.compiler_identity = original_discovery

    def reject_process(event, args):
        if event in PROCESS_EVENTS:
            process_attempts.append(event)
            raise RuntimeError("unexpected process launch: " + event)

    sys.path.insert(0, str(root / "scripts"))
    sys.argv = [str(root / "scripts/std_mir.py")]
    captured = io.StringIO()
    original_stdout = sys.stdout
    sys.addaudithook(reject_process)
    sys.stdout = captured
    try:
        wall_started, cpu_started = time.perf_counter_ns(), time.process_time_ns()
        import std_mir
        std_mir.ROOT = owner
        saved_checked = std_mir.checked_std_mir
        std_mir.checked_std_mir = checked
        try:
            result = std_mir.main()
        finally:
            std_mir.checked_std_mir = saved_checked
        cpu_ns = time.process_time_ns() - cpu_started
        wall_ns = time.perf_counter_ns() - wall_started
    finally:
        sys.stdout = original_stdout
    raw_report = captured.getvalue()
    require(result is None and len(discovery_calls) == len(setup_calls) == 1
            and not process_attempts, "wrong stock main outcome")
    require(Path(std_mir.__file__).resolve() == root / "scripts/std_mir.py", "wrong CLI module")
    require(json.loads(raw_report) == config["expected_report"], "std CLI receipt differs")
    expected_order = ("sysroot", "target", "key", "setup_seconds", "build_seconds", "metadata_bytes")
    ordered_report = {key: config["expected_report"][key] for key in expected_order}
    require(raw_report == json.dumps(ordered_report, indent=2) + "\n",
            "std CLI receipt formatting differs")
    require(all(name in sys.modules for name in ("toolchain_lookup", "tempfile", "std_mir_readmission")),
            "ordinary lookup/readmission imports missing")
    for name in ("custom_compiler", "custom_cargo", "custom_cargo_libraries", "compiler_association"):
        require((name in sys.modules) == (config["arm"] == "baseline"),
                "unexpected optional module: " + name)
    require("unittest" not in sys.modules, "test machinery entered measured driver")
    import importlib.util
    modules = {}
    for name, module in sorted(sys.modules.items()):
        namespace = vars(module)
        filename, cached = namespace.get("__file__"), namespace.get("__cached__")
        if isinstance(filename, str):
            modules[name] = dict(file=filename, cached=cached if isinstance(cached, str) else None)
    print(json.dumps(dict(schema_version=1, status="PASS", arm=config["arm"], warmup=config["warmup"],
        component_cpu_ns=cpu_ns, component_wall_ns=wall_ns, main_returnvalue=result,
        setup_calls=setup_calls, discovery_calls=discovery_calls, process_attempts=process_attempts,
        cli_stdout=raw_report, preloaded=preloaded, modules=modules,
        python=dict(executable=sys.executable, version=sys.version, cache_tag=sys.implementation.cache_tag,
                    magic=importlib.util.MAGIC_NUMBER.hex(), prefix=sys.prefix, base_prefix=sys.base_prefix),
        pycache_prefix=sys.pycache_prefix, dont_write_bytecode=sys.dont_write_bytecode,
        scope="actual stock std CLI synthetic prepared reuse; only identity discovery stubbed; no std build"),
        sort_keys=True))


if __name__ == "__main__":
    main()
