#!/usr/bin/env python3
"""One real allocation-trace API call per fresh measurement child."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time

QUALIFICATION_SHA = "b74c344d5385e95de2ed5553ba0179d9b06ce90ee15d1b0fe86e85f5ee280def"
PACKET = Path(__file__).resolve().parent
LIMIT = 64 * 1024 ** 2


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def canonical(value, parent=None):
    path = Path(value)
    require(path.is_absolute() and path.resolve(strict=True) == path,
            "noncanonical driver input path")
    if parent is not None:
        require(path != parent and path.is_relative_to(parent), "driver input escaped owned root")
    return path


def sha256_text(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def preload(path, size, digest):
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size == size, "trace preload type/size differs")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(path, flags), "rb") as stream:
        require(stamp(os.fstat(stream.fileno())) == stamp(before), "trace changed before preload")
        data = stream.read(size + 1)
        require(stamp(os.fstat(stream.fileno())) == stamp(before)
                and stamp(path.lstat()) == stamp(before), "trace changed during preload")
    require(len(data) == size and hashlib.sha256(data).hexdigest() == digest, "trace preload digest differs")
    return data


def exception_record(error):
    record = dict(type=type(error).__name__, module=type(error).__module__, message=str(error),
                  cause=None if error.__cause__ is None else exception_record(error.__cause__))
    if isinstance(error, json.JSONDecodeError):
        record["json"] = {name: getattr(error, name) for name in ("msg", "doc", "pos", "lineno", "colno")}
    if isinstance(error, UnicodeDecodeError):
        record["unicode"] = dict(encoding=error.encoding, object_hex=error.object.hex(),
                                 start=error.start, end=error.end, reason=error.reason)
    return record


def main():
    require(len(sys.argv) == 2, "one sample config required")
    config_path = canonical(sys.argv[1], PACKET)
    config = json.loads(config_path.read_bytes())
    require(config["schema_version"] == 1 and config["arm"] in ("baseline", "candidate"), "invalid schema/arm")
    require(sha256_text(QUALIFICATION_SHA) and config["qualification_sha256"] == QUALIFICATION_SHA,
            "successful frozen semantic qualification is UNBOUND or differs")
    phase = config["phase"]
    require(phase in ("parity", "warmup", "measured"), "invalid phase")
    output = canonical(config["output_root"], PACKET)
    fixture_root = canonical(config["fixture_root"], PACKET)
    cache = canonical(config["pycache_prefix"], output)
    require(config_path.is_relative_to(output) and output.is_dir() and fixture_root.is_dir() and cache.is_dir(),
            "wrong owned config/fixture/cache directories")
    require(sys.pycache_prefix == str(cache) and sys.dont_write_bytecode == (phase != "warmup"),
            "wrong private bytecode-cache regime")

    def reject_process(event, args):
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec",
                     "os.fork", "os.forkpty", "os.spawn"}:
            raise RuntimeError("allocation trace API attempted a child: " + event)
    sys.addaudithook(reject_process)
    root = canonical(config["source_root"])
    require("allocation_trace" not in sys.modules, "allocation trace module already loaded")
    sys.path.insert(0, str(root / "scripts"))
    import allocation_trace
    require(Path(allocation_trace.__file__).resolve() == root / "scripts/allocation_trace.py", "wrong source")

    fixture = config["fixture"]
    require(fixture["name"] in ("caller", "scalar_constant", "static", "tls"), "unknown fixture")
    api = config["api"]
    require(api in ("validate", "selected") and config["case"] == fixture["name"] + "_" + api,
            "case/API/fixture differs")
    artifact = canonical(fixture["artifact_path"], fixture_root)
    trace = canonical(fixture["path"], fixture_root)
    require(str(trace) == str(artifact) + ".allocations.jsonl", "trace is not selected artifact sidecar")
    require(all(type(fixture[k]) is int and 0 < fixture[k] <= LIMIT for k in ("bytes", "artifact_bytes"))
            and all(sha256_text(fixture[k]) for k in ("sha256", "artifact_sha256")), "invalid fixture bounds/digests")
    require(type(fixture["events"]) is int and 0 < fixture["events"] <= 1_000_000
            and type(fixture["qualified_events"]) is int and fixture["qualified_events"] == fixture["events"],
            "historical and qualified event counts differ")
    expected = dict(kind="allocation-trace", schema_version=1, strict_frontend=True,
        path=str(trace), bytes=fixture["bytes"], sha256=fixture["sha256"], events=fixture["events"],
        artifact_path=str(artifact), artifact_bytes=fixture["artifact_bytes"],
        artifact_sha256=fixture["artifact_sha256"])
    data = preload(trace, fixture["bytes"], fixture["sha256"]) if api == "validate" else None

    # Imports, fixture metadata and validate-only preload precede both clocks.
    # selected_trace performs its actual file reads/stamps/hashes within them.
    result = caught_error = None
    wall_started, cpu_started = time.perf_counter_ns(), time.process_time_ns()
    try:
        result = (allocation_trace.validate_trace(data, fixture["artifact_sha256"])
                  if api == "validate" else allocation_trace.selected_trace(artifact))
    except BaseException as caught:
        caught_error = caught
    finally:
        cpu_ns = time.process_time_ns() - cpu_started
        wall_ns = time.perf_counter_ns() - wall_started
    error = None if caught_error is None else exception_record(caught_error)
    parity = error is None and ((type(result) is int and result == fixture["qualified_events"])
                               if api == "validate" else result == expected)
    modules = {}
    for name, module in sorted(sys.modules.items()):
        if module is None:
            continue
        namespace = vars(module)
        filename, cached = namespace.get("__file__"), namespace.get("__cached__")
        if isinstance(filename, str):
            modules[name] = dict(file=filename, cached=cached if isinstance(cached, str) else None)
    return dict(schema_version=1, status="PASS" if parity else "FAIL", stage="api", api_calls=1,
        arm=config["arm"], case=config["case"], api=api, phase=phase, warmup=(phase == "warmup"),
        component_cpu_ns=cpu_ns, component_wall_ns=wall_ns, result=result, error=error, parity=parity,
        expected_events=fixture["qualified_events"], expected_selected_receipt=expected,
        qualification_sha256=QUALIFICATION_SHA, modules=modules,
        python=dict(executable=sys.executable, version=sys.version, cache_tag=sys.implementation.cache_tag,
            magic=importlib.util.MAGIC_NUMBER.hex(), prefix=sys.prefix, base_prefix=sys.base_prefix),
        pycache_prefix=sys.pycache_prefix, dont_write_bytecode=sys.dont_write_bytecode)


if __name__ == "__main__":
    try:
        output = main()
    except BaseException as caught:
        output = dict(schema_version=1, status="FAIL", stage="driver", error=exception_record(caught))
    print(json.dumps(output, sort_keys=True))
    raise SystemExit(0 if output["status"] == "PASS" else 1)
