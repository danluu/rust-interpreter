#!/usr/bin/env python3
"""Frozen 28-process launcher screen. Never imports the measured implementation."""
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import statistics
import subprocess
import sys
import threading
import time

PACKET = Path("/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/compiler-association-probe")
OUT = PACKET / "screen-01"
LOCK = Path("/Users/danluu/dev/rust-interp/.work/benchmark.lock")
BINDINGS = PACKET / "screen-bindings.json"
BINDINGS_SHA = "7a80b841df5be300412056e574e2e0cea5dd124c472d97eb73f86e152cd5666d"
PLAN = PACKET / "decision-plan.json"
PLAN_SHA = "f4fc89ff9c419a748db281d0c946770c8d909249bfdc2f80cf8f187d86d97c3b"
QUALIFICATION = PACKET / "unit-screen-01/result.json"
QUALIFICATION_SHA = "2da23207fbb7896cbe471b584f8308c09617055dcda1ae29e5639b07bd1a0c28"
PYTHON = Path("/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14")
OWNER = Path("/Users/danluu/dev/rust-interp-perf-20260912")
KEY = "eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d"
TOOLS = OWNER / ".work/interpreter-tools" / KEY
CACHE = OUT / "pycache"
GIB, MIB, FLOOR = 1024 ** 3, 1024 ** 2, 16 * 1024 ** 3
ROWS, CHILDREN = [], []


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def free_bytes():
    info = os.statvfs(PACKET)
    return info.f_bavail * info.f_frsize


def stamp(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def proof(path, cap=16 * MIB):
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "unsafe/oversized input: " + str(path))
    data = path.read_bytes()
    require(stamp(before) == stamp(path.lstat()) and len(data) == before.st_size,
            "input changed while reading: " + str(path))
    return dict(path=str(path), resolved=str(path.resolve()), bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(), stamp=stamp(before))


def write(name, data):
    with (OUT / name).open("x", encoding="utf-8") as output:
        json.dump(data, output, sort_keys=True, indent=2)
        output.write("\n")


def verify_expected(path, expected):
    actual = proof(path)
    require({k: actual[k] for k in ("bytes", "sha256")} == expected, "binding changed: " + str(path))
    return actual


def verify_inputs(descriptor):
    recorded = {path: verify_expected(Path(path), expected)
                for path, expected in descriptor["fixed_files"].items()}
    for arm, root_name in descriptor["roots"].items():
        root = Path(root_name)
        require(root.resolve() == root, "noncanonical source root")
        expected = descriptor["sources"][arm]
        actual = {str(p.relative_to(root)) for folder in ("scripts", "tests")
                  for p in (root / folder).glob("*.py")}
        require(actual == set(expected), "project Python source inventory changed")
        for relative, expected_proof in expected.items():
            require(not Path(relative).is_absolute() and ".." not in Path(relative).parts, "bad source path")
            recorded[str(root / relative)] = verify_expected(root / relative, expected_proof)
    require(all(not (TOOLS / name).exists() and not (TOOLS / name).is_symlink()
                for name in ("compiler.json", "runtime.json")), "stock association changed")
    require(proof(BINDINGS)["sha256"] == BINDINGS_SHA and proof(PLAN)["sha256"] == PLAN_SHA,
            "screen descriptor/decision changed")
    require(proof(QUALIFICATION)["sha256"] == QUALIFICATION_SHA, "qualification receipt changed")
    return recorded


def child(label, command, environment, gate=None):
    """Blocking wait4 avoids polling quantization; a thread only observes disk."""
    require(free_bytes() > FLOOR, "16 GiB disk floor")
    if gate is not None:
        require(time.monotonic() - gate["monotonic"] < 20, "memory gate expired")
    record = dict(label=label, command=list(map(str, command)), cwd=str(PACKET),
        environment=environment, parent_pid=os.getpid(), admission=gate, started_epoch=None, pid=None)
    write(label + "-planned.json", record)
    done, observations, observer_errors = threading.Event(), [], []
    def observe():
        try:
            with (OUT / (label + "-disk.jsonl")).open("x") as output:
                while not done.wait(5):
                    value = dict(epoch=time.time(), free_bytes=free_bytes(), action="read_only_no_signals")
                    observations.append(value)
                    output.write(json.dumps(value, sort_keys=True) + "\n")
                    output.flush()
        except BaseException as error:
            observer_errors.append(repr(error))
    watcher = threading.Thread(target=observe, name="owned-disk-observer", daemon=True)
    process = usage = wait_status = None
    error, started, ended = None, None, None
    with (OUT / (label + ".stdout")).open("xb") as stdout, \
         (OUT / (label + ".stderr")).open("xb") as stderr:
        watcher.start()
        try:
            require(free_bytes() > FLOOR, "disk fell before launch")
            record["started_epoch"], started = time.time(), time.perf_counter()
            process = subprocess.Popen(record["command"], cwd=PACKET, env=environment,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, close_fds=True)
            record.update(pid=process.pid, popen_completed_epoch=time.time())
            write(label + "-start.json", record)
            while wait_status is None:
                try:
                    pid, wait_status, usage = os.wait4(process.pid, 0)
                    ended = time.perf_counter()
                    require(pid == process.pid, "unexpected waited child")
                except InterruptedError:
                    continue
        except BaseException as caught:
            error = repr(caught)
        finally:
            if process is not None:
                while wait_status is None:
                    try:
                        pid, wait_status, usage = os.wait4(process.pid, 0)
                        ended = time.perf_counter()
                        require(pid == process.pid, "unexpected waited child")
                    except InterruptedError:
                        continue
                    except ChildProcessError as caught:
                        error = error or repr(caught)
                        process.wait()
                        break
                if wait_status is not None:
                    process.returncode = os.waitstatus_to_exitcode(wait_status)
                record.update(returncode=process.returncode, finished_epoch=time.time(),
                    wall_seconds=(ended or time.perf_counter()) - started)
            done.set()
            watcher.join()
    record.update(error=error, observer_errors=observer_errors, disk_observations=observations,
                  free_bytes_after=free_bytes())
    if usage is not None:
        record.update(cpu_seconds=usage.ru_utime + usage.ru_stime, user_seconds=usage.ru_utime,
                      system_seconds=usage.ru_stime, peak_rss_bytes=usage.ru_maxrss)
    CHILDREN.append(record)
    write(label + "-terminal.json", record)
    record["logs"] = {name: proof(OUT / (label + "." + name), MIB) for name in ("stdout", "stderr")}
    require(process is not None and usage is not None and error is None and not observer_errors
            and process.returncode == 0, "failed child/incomplete settlement: " + label)
    require(record["free_bytes_after"] > FLOOR and all(o["free_bytes"] > FLOOR for o in observations),
            "disk floor crossed; stop before another sample")
    return record


def admission(label, environment):
    receipt = child(label + "-memory", ["/usr/bin/memory_pressure", "-Q"], environment)
    output, error = ((OUT / (label + "-memory." + name)).read_bytes() for name in ("stdout", "stderr"))
    values = re.findall(rb"System-wide memory free percentage:\s*(\d+)%", output)
    require(len(values) == 1 and not error and int(values[0]) >= 30, "30% memory floor")
    return dict(epoch=time.time(), monotonic=time.monotonic(), free_bytes=free_bytes(),
                memory_free_percent=int(values[0]), memory_receipt=receipt["label"])


def dependency_proofs(reports, descriptor):
    paths = {Path(module["file"]) for report in reports for module in report["modules"].values()}
    require(len(paths) <= 384, "dependency file count bound")
    standard = Path(descriptor["stdlib_root"]).resolve()
    project = {str(Path(descriptor["roots"][arm]) / p) for arm in descriptor["roots"]
               for p in descriptor["sources"][arm]}
    result, total = {}, 0
    for path in sorted(paths):
        require(path.is_absolute() and (str(path) in project or path == PACKET / "driver.py"
                or path.resolve().is_relative_to(standard)), "unexpected dependency: " + str(path))
        item = proof(path)
        total += item["bytes"]
        require(total <= 64 * MIB, "dependency byte bound")
        result[str(path)] = item
    return result


def cache_snapshot(descriptor, cache_tag, magic):
    require(CACHE.resolve() == CACHE and CACHE.is_dir(), "private cache root changed")
    items, directories, total = {}, 0, 0
    for directory, subdirs, names in os.walk(CACHE, followlinks=False):
        directories += 1
        require(directories <= 256, "cache directory bound")
        require(all(not (Path(directory) / n).is_symlink() for n in subdirs), "cache directory symlink")
        for name in sorted(names):
            path = Path(directory) / name
            item = proof(path, 4 * MIB)
            total += item["bytes"]
            require(len(items) < 512 and total <= 64 * MIB, "cache inventory bound")
            suffix = "." + cache_tag + ".pyc"
            require(name.endswith(suffix), "unexpected private cache file")
            relative = path.relative_to(CACHE)
            source = Path("/") / relative.parent / (name.removesuffix(suffix) + ".py")
            resolved = source.resolve()
            require(resolved.is_relative_to(Path(descriptor["stdlib_root"]).resolve())
                    or any(resolved.is_relative_to(Path(r) / "scripts") for r in descriptor["roots"].values()),
                    "cache source outside frozen roots")
            source_item = proof(source)
            data, source_data = path.read_bytes(), source.read_bytes()
            require(len(data) >= 16 and data[:4].hex() == magic, "pyc magic/header mismatch")
            flags = int.from_bytes(data[4:8], "little")
            require(flags in (0, 1, 3), "unknown pyc flags")
            if flags == 0:
                require(int.from_bytes(data[8:12], "little") == (int(source.stat().st_mtime) & 0xffffffff)
                        and int.from_bytes(data[12:16], "little") == (len(source_data) & 0xffffffff),
                        "stale timestamp pyc")
            else:
                require(data[8:16] == importlib.util.source_hash(source_data), "stale hash pyc")
            require(hashlib.sha256(source_data).hexdigest() == source_item["sha256"]
                    and hashlib.sha256(data).hexdigest() == item["sha256"], "cache/source changed")
            items[str(relative)] = dict(cache=item, source=source_item, header=data[:16].hex(), flags=flags)
    require(items, "empty warmed bytecode cache")
    return dict(files=items, directories=directories, bytes=total)


def require_cached_sources(report, cache):
    paths = {entry["cache"]["path"] for entry in cache["files"].values()}
    for module in report["modules"].values():
        if module["cached"] is not None:
            require(module["cached"] in paths, "module lacks frozen warm bytecode")


def metrics():
    result = {}
    measured = [r for r in ROWS if not r["warmup"]]
    require(len(ROWS) == 28 and len(measured) == 24, "incomplete schedule")
    geo = lambda values: math.exp(sum(math.log(v) for v in values) / len(values))
    for field in ("component_cpu_ns", "component_wall_ns", "cpu_seconds", "wall_seconds", "peak_rss_bytes"):
        ratios, baseline, candidate = [], [], []
        for pair in range(12):
            pair_rows = {r["arm"]: r for r in measured if r["pair"] == pair}
            require(set(pair_rows) == {"baseline", "candidate"}, "missing pair")
            a, b = pair_rows["baseline"][field], pair_rows["candidate"][field]
            require(a > 0 and b > 0, "nonpositive metric")
            baseline.append(a)
            candidate.append(b)
            ratios.append(b / a)
        result[field] = dict(paired_ratios=ratios, geometric_mean_ratio=geo(ratios),
            strict_wins=sum(r < 1 for r in ratios), median_baseline=statistics.median(baseline),
            median_candidate=statistics.median(candidate), AB_geometric_mean_ratio=geo(ratios[::2]),
            BA_geometric_mean_ratio=geo(ratios[1::2]))
    return result


def main():
    require(sys.argv[1:] == ["--execute-frozen-startup-screen"], "explicit execution flag required")
    require(QUALIFICATION_SHA != "UNBOUND", "completed unit qualification remains UNBOUND")
    require(sys.platform == "darwin" and sys.version_info[:2] == (3, 14)
            and Path(sys.executable).resolve() == PYTHON.resolve(), "pinned macOS Python required")
    require(proof(BINDINGS)["sha256"] == BINDINGS_SHA and proof(PLAN)["sha256"] == PLAN_SHA,
            "unbound/changed descriptor or decision")
    descriptor, plan = json.loads(BINDINGS.read_bytes()), json.loads(PLAN.read_bytes())
    require(descriptor["base_commit"] == plan["base_commit"] and descriptor["roots"] ==
            {"baseline": plan["baseline_root"], "candidate": plan["candidate_root"]}, "decision/root mismatch")
    qualification = json.loads(QUALIFICATION.read_bytes())
    require(proof(QUALIFICATION)["sha256"] == QUALIFICATION_SHA and qualification.get("status") == "passed"
            and qualification.get("error") is None and qualification.get("post_binding_error") is None
            and qualification.get("expected_tests") == qualification.get("passed_tests") == 81
            and len(qualification.get("tests", [])) == 8 and len(qualification.get("children", [])) == 16
            and qualification.get("bindings") == qualification.get("bindings_after"),
            "successful frozen 81-test qualification required")
    before = verify_inputs(descriptor)
    require(PACKET.resolve() == PACKET and free_bytes() > FLOOR and not OUT.exists()
            and not OUT.is_symlink(), "fresh output/16 GiB required")
    fd = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW)
    try:
        lock_info = os.fstat(fd)
        require(stat.S_ISREG(lock_info.st_mode), "shared lock is not regular")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require((lock_info.st_dev, lock_info.st_ino) == (LOCK.lstat().st_dev, LOCK.lstat().st_ino),
                "shared lock inode changed")
        require(free_bytes() > FLOOR and not OUT.exists(), "output/admission changed")
        OUT.mkdir(mode=0o700)
        reports, sample_inputs = [], []
        warmed = dependencies = module_sets = fixture = fixtures = None
        error = post_error = summary = checks = None
        controller_before = proof(Path(__file__).resolve())
        try:
            before = verify_inputs(descriptor)
            write("inputs-before.json", before)
            write("decision-plan.json", plan)
            write("screen-bindings.json", descriptor)
            write("qualification.json", qualification)
            write("controller.json", controller_before)
            CACHE.mkdir(mode=0o700)
            (OUT / "tmp").mkdir(mode=0o700)
            fixture = OUT / "fixture"
            fixture.mkdir()
            (fixture / "Cargo.toml").write_text('[package]\nname="fixture"\nversion="0.0.0"\nedition="2021"\n[lib]\npath="lib.rs"\n')
            (fixture / "lib.rs").write_text("pub fn selected() -> u32 { 7 }\n")
            (fixture / "libfixture.rmeta.rbc").write_bytes(b"STUB-BOUNDARY-NO-GUEST-EXECUTION\n")
            fixtures = {str(p): proof(p) for p in sorted(fixture.iterdir())}
            write("fixture-inputs.json", fixtures)
            environment = dict(HOME="/Users/danluu", PATH="/usr/bin:/bin", LANG="C", LC_ALL="C",
                PYTHONNOUSERSITE="1", PYTHONPYCACHEPREFIX=str(CACHE), TMPDIR=str(OUT / "tmp"))
            schedule = [(True, pair, arm) for pair, order in enumerate(
                (("baseline", "candidate"), ("candidate", "baseline"))) for arm in order]
            schedule += [(False, pair, arm) for pair in range(12) for arm in
                (("baseline", "candidate") if pair % 2 == 0 else ("candidate", "baseline"))]
            write("schedule.json", schedule)
            for index, (warmup, pair, arm) in enumerate(schedule):
                label = f"{index:02d}-{'warm' if warmup else 'measured'}-{pair:02d}-{arm}"
                require(verify_inputs(descriptor) == before, "source/tool metadata changed")
                require({str(p): proof(p) for p in sorted(fixture.iterdir())} == fixtures, "fixture changed")
                if not warmup:
                    require(dependency_proofs(reports[:4], descriptor) == dependencies, "dependencies changed")
                    require(cache_snapshot(descriptor, reports[0]["python"]["cache_tag"],
                            reports[0]["python"]["magic"]) == warmed, "cache changed before sample")
                workspace = OUT / (label + "-workspace")
                workspace.mkdir(mode=0o700)
                namespace = "rust-interp-" + hashlib.sha256(str(OWNER).encode()).hexdigest()[:24]
                identity = hashlib.sha256(("shared-entries-v1\0" + str(fixture / "Cargo.toml")
                                           + "\0fixture\0False").encode()).hexdigest()[:24]
                work = workspace / namespace / "workspaces" / KEY / identity
                config = dict(schema_version=1, arm=arm, warmup=warmup, source_root=descriptor["roots"][arm],
                    tool_owner=str(OWNER), tool_directory=str(TOOLS), tool_key=KEY,
                    manifest=str(fixture / "Cargo.toml"), artifact=str(fixture / "libfixture.rmeta.rbc"),
                    expected_work=str(work), workspace_cache_root=str(workspace),
                    output_root=str(OUT), pycache_prefix=str(CACHE))
                write(label + "-input.json", config)
                sample_inputs.append(proof(OUT / (label + "-input.json")))
                gate = admission(label, environment)
                command = [str(PYTHON), "-I", "-S", "-X", "pycache_prefix=" + str(CACHE)]
                if not warmup:
                    command.append("-B")
                command += [str(PACKET / "driver.py"), str(OUT / (label + "-input.json"))]
                receipt = child(label, command, environment, gate)
                require((OUT / (label + ".stderr")).read_bytes() == b"", "unexpected launcher stderr")
                report = json.loads((OUT / (label + ".stdout")).read_bytes())
                require(report["status"] == "PASS" and report["arm"] == arm and report["warmup"] == warmup
                        and report["main_returncode"] == 0, "driver result mismatch")
                if reports:
                    require(report["python"] == reports[0]["python"]
                        and report["preloaded"] == reports[0]["preloaded"]
                        and report["boundaries"] == reports[0]["boundaries"], "runtime/boundary parity failure")
                reports.append(report)
                row = dict(receipt, arm=arm, warmup=warmup, pair=pair,
                    component_cpu_ns=report["component_cpu_ns"], component_wall_ns=report["component_wall_ns"])
                ROWS.append(row)
                with (OUT / "samples.jsonl").open("a") as output:
                    output.write(json.dumps(row, sort_keys=True) + "\n")
                if index == 3:
                    require(reports[0]["modules"] == reports[3]["modules"]
                            and reports[1]["modules"] == reports[2]["modules"], "warmup module instability")
                    module_sets = dict(baseline=reports[0]["modules"], candidate=reports[1]["modules"])
                    dependencies = dependency_proofs(reports, descriptor)
                    warmed = cache_snapshot(descriptor, reports[0]["python"]["cache_tag"],
                                            reports[0]["python"]["magic"])
                    for value in reports:
                        require_cached_sources(value, warmed)
                    write("dependencies-frozen.json", dependencies)
                    write("bytecode-cache-frozen.json", warmed)
                if not warmup:
                    require(report["modules"] == module_sets[arm], "measured module inventory changed")
                    require_cached_sources(report, warmed)
                    require(cache_snapshot(descriptor, report["python"]["cache_tag"],
                            report["python"]["magic"]) == warmed, "measured child changed cache")
            summary, g = metrics(), plan["adoption_gates"]
            cpu = summary["component_cpu_ns"]
            checks = dict(
                component_cpu=cpu["geometric_mean_ratio"] <= g["component_cpu_geometric_mean_ratio_max"],
                component_wins=cpu["strict_wins"] >= g["component_cpu_strict_wins_min"],
                component_AB=cpu["AB_geometric_mean_ratio"] < g["both_order_component_cpu_geometric_mean_ratio_max_exclusive"],
                component_BA=cpu["BA_geometric_mean_ratio"] < g["both_order_component_cpu_geometric_mean_ratio_max_exclusive"],
                component_wall=summary["component_wall_ns"]["geometric_mean_ratio"] <= g["component_wall_geometric_mean_ratio_max"],
                process_cpu=summary["cpu_seconds"]["geometric_mean_ratio"] <= g["process_cpu_geometric_mean_ratio_max"],
                process_wall=summary["wall_seconds"]["geometric_mean_ratio"] <= g["process_wall_geometric_mean_ratio_max"],
                process_rss=summary["peak_rss_bytes"]["geometric_mean_ratio"] <= g["process_rss_geometric_mean_ratio_max"])
        except BaseException as caught:
            error = repr(caught)
        finally:
            try:
                require(verify_inputs(descriptor) == before, "final source/tool identity changed")
                require(proof(Path(__file__).resolve()) == controller_before, "controller changed")
                if fixtures is not None:
                    require({str(p): proof(p) for p in sorted(fixture.iterdir())} == fixtures, "final fixture changed")
                if warmed is not None:
                    require(cache_snapshot(descriptor, reports[0]["python"]["cache_tag"],
                            reports[0]["python"]["magic"]) == warmed, "final cache changed")
                    require(dependency_proofs(reports[:4], descriptor) == dependencies, "final dependencies changed")
                require(all(proof(Path(p["path"])) == p for p in sample_inputs), "sample descriptor changed")
                write("inputs-after.json", verify_inputs(descriptor))
            except BaseException as caught:
                post_error = repr(caught)
        status = "PASS" if error is None and post_error is None and len(ROWS) == 28 else "FAIL"
        result = dict(status=status, error=error, post_binding_error=post_error, rows=ROWS, children=CHILDREN,
            summary=summary, gates=checks, fixed_decision_satisfied=status == "PASS" and all(checks.values()),
            scope=plan["scope"], decision_sha256=PLAN_SHA, bindings_sha256=BINDINGS_SHA,
            qualification_sha256=QUALIFICATION_SHA)
        write("result.json", result)
        print(json.dumps({k: result[k] for k in ("status", "error", "post_binding_error",
            "summary", "gates", "fixed_decision_satisfied")}), flush=True)
        return 0 if status == "PASS" else 1
    finally:
        os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main())
