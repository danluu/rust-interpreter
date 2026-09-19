#!/usr/bin/env python3
"""One actual std_mir_readmission.validate call; immutable owned fixture parity."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import time

PACKET = Path(__file__).resolve().parent
PLAN_SHA = "a10f461883b1b3d68416b23c863d304a3c7f3b65edba2fc35fe8f5beb630c76b"
FIXTURE_OUT = PACKET / "fixture-qualification-01"
FIXTURES = FIXTURE_OUT / "fixtures"
MIB = 1024**2
MAX_ENTRIES, MAX_TOTAL, MAX_FILE = 256, MIB, 64*1024
REPORT = dict(schema_version=1, status="FAIL", stage="driver", api_calls=0)


def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def stamp(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]

def file_proof(path, cap=MAX_FILE):
    before = path.lstat()
    require(path.resolve(strict=True) == path and stat.S_ISREG(before.st_mode)
            and before.st_size <= cap, 'unsafe input: '+str(path))
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        require(stamp(os.fstat(fd)) == stamp(before), 'opening input changed')
        data = b''
        while len(data) <= before.st_size:
            part = os.read(fd, min(64*1024, before.st_size+1-len(data)))
            if not part:
                break
            data += part
            require(len(data) <= before.st_size, 'input grew')
        require(len(data) == before.st_size and stamp(os.fstat(fd)) == stamp(before)
                and stamp(path.lstat()) == stamp(before), 'input changed')
    finally:
        os.close(fd)
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),stamp=stamp(before)), data

def inventory(root):
    require(root.resolve(strict=True) == root and stat.S_ISDIR(root.lstat().st_mode),
            'unsafe fixture root')
    rows = {}
    pending = [root]
    total = 0
    while pending:
        path = pending.pop()
        s = path.lstat()
        require(path.resolve(strict=True) == path, 'fixture symlink/indirection')
        relative = str(path.relative_to(root))
        if stat.S_ISDIR(s.st_mode):
            rows[relative] = dict(kind='directory',stamp=stamp(s))
            children = []
            for child in path.iterdir():
                children.append(child)
                require(len(children)+len(pending)+len(rows) <= MAX_ENTRIES,
                        'fixture entries exceed bound')
            pending.extend(sorted(children,reverse=True))
        else:
            require(stat.S_ISREG(s.st_mode), 'nonregular fixture entry')
            row, _ = file_proof(path)
            rows[relative] = dict(kind='file',**row)
            total += row['bytes']
            require(total <= MAX_TOTAL, 'fixture byte budget exceeded')
        require(len(rows) <= MAX_ENTRIES, 'fixture entries exceed bound')
    return dict(entries=rows,total_file_bytes=total,entry_count=len(rows))


def canonical(value, parent=None):
    path = Path(value)
    require(path.is_absolute() and path.resolve(strict=True) == path, "noncanonical driver path")
    if parent is not None:
        require(path != parent and path.is_relative_to(parent), "path escaped owned root")
    return path


def digest_text(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def snapshot_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def exception_record(error):
    record = dict(type=type(error).__name__, module=type(error).__module__, message=str(error))
    if isinstance(error, json.JSONDecodeError):
        record["json"] = {name: getattr(error, name) for name in ("msg", "doc", "pos", "lineno", "colno")}
    if isinstance(error, OSError):
        record.update(errno=error.errno, filename=error.filename, filename2=error.filename2)
    return record


def modules():
    result = {}
    for name, module in sorted(sys.modules.items()):
        if module is None:
            continue
        namespace = vars(module)
        filename, cached = namespace.get("__file__"), namespace.get("__cached__")
        if isinstance(filename, str):
            result[name] = dict(file=filename, cached=cached if isinstance(cached, str) else None)
    return result


def main():
    require(len(sys.argv) == 2, "one sample config required")
    config_path = canonical(sys.argv[1], PACKET)
    config_proof, config_raw = file_proof(config_path, 2*MIB)
    config = json.loads(config_raw)
    require(config["schema_version"] == 1 and config["arm"] in ("baseline", "candidate"), "invalid arm/schema")
    phase, case = config["phase"], config["case"]
    require(phase in ("parity", "warmup", "measured") and case in
            ("matching_saved_stamps", "matching_device_readmission_receipt"), "unknown phase/case")
    REPORT.update(arm=config["arm"], phase=phase, warmup=phase == "warmup", case=case,
                  config_proof=config_proof, api="validate")
    output = canonical(config["output_root"], PACKET)
    cache = canonical(config["pycache_prefix"], output)
    require(output.is_dir() and config_path.is_relative_to(output) and cache.is_dir()
            and sys.pycache_prefix == str(cache) and sys.dont_write_bytecode == (phase != "warmup")
            and sys.flags.isolated and sys.flags.no_site and sys.version_info[:2] == (3, 14)
            and sys.implementation.name == "cpython" and os.name == "posix",
            "wrong Python or private cache regime")

    def reject_process(event, args):
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec",
                     "os.fork", "os.forkpty", "os.spawn"}:
            raise RuntimeError("validation driver attempted a child: " + event)
    sys.addaudithook(reject_process)
    plan_proof, plan_raw = file_proof(PACKET/"decision-plan.json", 2*MIB)
    require(plan_proof["sha256"] == PLAN_SHA == config["decision_sha256"], "frozen decision differs")
    plan = json.loads(plan_raw)
    runtime_proof, runtime_raw = file_proof(PACKET/"screen-bindings.json", 2*MIB)
    require(digest_text(config["runtime_manifest_sha256"])
            and runtime_proof["sha256"] == config["runtime_manifest_sha256"], "runtime descriptor differs")
    runtime = json.loads(runtime_raw)
    fixed = runtime["fixed_files"]
    receipt_paths = {
        "unit_receipt_sha256": PACKET/"unit-screen-01/result.json",
        "compatibility_receipt_sha256": PACKET/"compatibility-screen-01/result.json",
        "fixture_qualification_sha256": FIXTURE_OUT/"result.json",
        "fixture_descriptor_sha256": FIXTURE_OUT/"fixtures.json",
    }
    for key, path in receipt_paths.items():
        require(digest_text(config[key]) and config[key] == fixed[str(path)]["sha256"],
                "stage receipt binding differs: " + key)
    own_proof, _ = file_proof(Path(__file__).resolve(), 2*MIB)
    require({key: own_proof[key] for key in ("bytes", "sha256")} == fixed[str(Path(__file__).resolve())],
            "driver source differs")
    root = canonical(config["source_root"])
    require(str(root) == runtime["roots"][config["arm"]] == plan[config["arm"]+"_root"], "wrong source arm")
    module_path = root/"scripts/std_mir_readmission.py"
    source_proof, _ = file_proof(module_path, 2*MIB)
    source_expected = runtime["sources"][config["arm"]]["scripts/std_mir_readmission.py"]
    require({key: source_proof[key] for key in ("bytes", "sha256")} == source_expected
            and source_proof["sha256"] == plan["applied_sources"]["scripts/std_mir_readmission.py"][config["arm"]]["sha256"],
            "selected module source differs")
    require("std_mir_readmission" not in sys.modules, "target module already loaded")
    sys.path.insert(0, str(root/"scripts"))
    import std_mir_readmission
    require(Path(std_mir_readmission.__file__).resolve() == module_path, "wrong actual module import")

    fixtures_proof, fixtures_raw = file_proof(FIXTURE_OUT/"fixtures.json", 2*MIB)
    require(fixtures_proof["sha256"] == config["fixture_descriptor_sha256"], "fixture descriptor differs")
    fixtures = json.loads(fixtures_raw)
    require(fixtures["schema_version"] == 1 and fixtures["status"] == "passed"
            and fixtures["decision_sha256"] == PLAN_SHA
            and fixtures["fixture_shape_sha256"] == plan["fixture_shape_sha256"]
            and canonical(fixtures["root"]) == FIXTURES and fixtures["expected_baseline_calls"] == 3
            and len(fixtures["actual_baseline_calls"]) == 3
            and [row["name"] for row in fixtures["cases"]] == [row["name"] for row in plan["cases"]],
            "unqualified fixture descriptor")
    fixture = next(row for row in fixtures["cases"] if row["name"] == case)
    work = canonical(fixture["work"], FIXTURES)
    ready = canonical(fixture["ready"], work)
    require(work.is_dir() and fixture["artifact_count"] == 26, "wrong fixture work/count")
    ready_proof, ready_bytes = file_proof(ready)
    manifest = json.loads(ready_bytes)
    require(ready_proof == fixture["ready_proof"] and ready_bytes.decode("utf-8") == fixture["ready_text"]
            and manifest == fixture["result"] and len(manifest["artifacts"]) == 26,
            "actual ready manifest differs from qualification")
    for name in manifest["artifacts"]:
        relative = Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts
                and canonical(work/relative, work).is_relative_to(FIXTURES), "unsafe artifact name")
    receipt = fixture["receipt"]
    receipt_proof = None
    if case == "matching_saved_stamps":
        require(receipt is None, "unexpected receipt for direct reuse")
    else:
        require(isinstance(receipt, dict), "qualified readmission receipt missing")
        receipt_path = canonical(receipt["path"], work)
        receipt_proof, receipt_raw = file_proof(receipt_path)
        require(receipt_proof == receipt["proof"] and receipt_raw.decode("utf-8") == receipt["text"]
                and json.loads(receipt_raw) == receipt["parsed"], "actual readmission receipt differs")
    before = inventory(FIXTURES)
    require(before == fixtures["root_inventory"], "fixture state changed before component")
    stdout, stderr = io.StringIO(), io.StringIO()
    REPORT.update(preclock_modules=modules(), fixture_before_sha256=snapshot_sha(before),
        fixture_expected_sha256=snapshot_sha(fixtures["root_inventory"]),
        fixture_root=str(FIXTURES), fixture_work=str(work), ready_path=str(ready),
        ready_proof=ready_proof, receipt_proof=receipt_proof, artifact_count=26,
        fixture_entry_count=before["entry_count"], fixture_total_file_bytes=before["total_file_bytes"],
        source_module=source_proof, single_stat_guard=getattr(std_mir_readmission, "_SINGLE_STAT_FILES", None))
    result = caught = None
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        REPORT["api_calls"] = 1
        wall_start, cpu_start = time.perf_counter_ns(), time.process_time_ns()
        try:
            result = std_mir_readmission.validate(work, ready, manifest)
        except BaseException as error:
            caught = error
        finally:
            cpu_ns = time.process_time_ns()-cpu_start
            wall_ns = time.perf_counter_ns()-wall_start
    REPORT.update(component_cpu_ns=cpu_ns, component_wall_ns=wall_ns,
        result=None if result is None else repr(result), result_is_none=result is None,
        api_stdout=stdout.getvalue(), api_stderr=stderr.getvalue(),
        error=None if caught is None else exception_record(caught),
        argument_unchanged=manifest == fixture["result"])
    after = inventory(FIXTURES)
    after_source, _ = file_proof(module_path, 2*MIB)
    after_descriptor, _ = file_proof(FIXTURE_OUT/"fixtures.json", 2*MIB)
    fixture_parity = after == before == fixtures["root_inventory"]
    parity = (caught is None and result is None and not stdout.getvalue() and not stderr.getvalue()
              and fixture_parity and manifest == fixture["result"]
              and after_source == source_proof and after_descriptor == fixtures_proof)
    REPORT.update(status="PASS" if parity else "FAIL", stage="api", parity=parity,
        fixture_parity=fixture_parity, fixture_after_sha256=snapshot_sha(after), modules=modules(),
        decision_sha256=PLAN_SHA, runtime_manifest_sha256=config["runtime_manifest_sha256"],
        **{key:config[key] for key in receipt_paths},
        python=dict(executable=sys.executable, version=sys.version, cache_tag=sys.implementation.cache_tag,
            magic=importlib.util.MAGIC_NUMBER.hex(), prefix=sys.prefix, base_prefix=sys.base_prefix),
        pycache_prefix=sys.pycache_prefix, dont_write_bytecode=sys.dont_write_bytecode)
    return REPORT


if __name__ == "__main__":
    try:
        output = main()
    except BaseException as caught:
        REPORT.update(status="FAIL", driver_error=exception_record(caught))
        output = REPORT
    print(json.dumps(output, sort_keys=True))
    raise SystemExit(0 if output["status"] == "PASS" else 1)
