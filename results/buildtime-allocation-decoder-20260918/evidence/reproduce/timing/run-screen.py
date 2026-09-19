#!/usr/bin/env python3
"""Fixed actual allocation-trace API screen; semantic bindings required before execution."""
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

PACKET = Path("/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-probe")
OUT = PACKET / "screen-01"
LOCK = Path("/Users/danluu/dev/rust-interp/.work/benchmark.lock")
BINDINGS = PACKET / "screen-bindings.json"
BINDINGS_SHA = "e178c72930eb81c30c91bfa9e3fe03c401b71b416ffacc88ad21398555d2086a"
PLAN = PACKET / "decision-plan.json"
PLAN_SHA = "4843e329a9f134fb0f4d7a0473509176f23d54bb7f7b2fa6a1bd875a42d12917"
SEMANTIC = PACKET / "qualification-01"
QUALIFICATION = SEMANTIC / "result.json"
QUALIFICATION_SHA = "b74c344d5385e95de2ed5553ba0179d9b06ce90ee15d1b0fe86e85f5ee280def"
UNIT = PACKET / "unit-screen-02/result.json"
UNIT_SHA = "e7db839bee8e417288538ad92b06389001a8442ffe62dce182da67cd5e7e51d0"
PYTHON = Path("/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14")
CACHE = OUT / "pycache"
GIB, MIB, FLOOR = 1024 ** 3, 1024 ** 2, 16 * 1024 ** 3
FIXTURES = ("caller", "scalar_constant", "static", "tls")
CASES = tuple(name + "_" + api for name in FIXTURES for api in ("validate", "selected"))
ROWS, CHILDREN = [], []



def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def free_bytes():
    info = os.statvfs(PACKET)
    return info.f_bavail * info.f_frsize


def stamp(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink]


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


def child(label, command, environment, gate=None):
    """Blocking wait4 avoids polling quantization; a thread only observes disk."""
    require(free_bytes() > FLOOR, "16 GiB disk floor")
    if gate is not None:
        require(time.monotonic() - gate["monotonic"] < 20, "memory gate expired")
    record = dict(label=label, command=list(map(str, command)), cwd=str(PACKET),
        environment=environment, parent_pid=os.getpid(), admission=gate, started_epoch=None, pid=None, free_bytes_before=free_bytes())
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
    record["logs"] = {name: proof(OUT / (label + "." + name), 16 * MIB) for name in ("stdout", "stderr")}
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


def dependency_proofs(reports, descriptor):
    paths = {Path(module["file"]) for report in reports for module in report["modules"].values()}
    require(len(paths) <= 384, "dependency file count bound")
    standard = Path(descriptor["stdlib_root"]).resolve()
    project = {str(Path(descriptor["roots"][arm]) / p) for arm in descriptor["roots"]
               for p in descriptor["sources"][arm]}
    result, total = {}, 0
    for path in sorted(paths):
        require(path.is_absolute() and (str(path) in project or path == PACKET / "timing-driver.py"
                or path.resolve().is_relative_to(standard)), "unexpected dependency: " + str(path))
        item = proof(path)
        total += item["bytes"]
        require(total <= 64 * MIB, "dependency byte bound")
        result[str(path)] = item
    return result


def verify_inputs(descriptor):
    recorded = {path: verify_expected(Path(path), expected)
                for group in ("fixed_files", "semantic_fixed_files")
                for path, expected in descriptor[group].items()}
    for arm, root_name in descriptor["roots"].items():
        root = Path(root_name)
        require(root.resolve() == root, "noncanonical source root")
        expected = descriptor["sources"][arm]
        actual = {str(p.relative_to(root)) for folder in ("scripts", "tests")
                  for p in (root / folder).glob("*.py")}
        require(actual == set(expected) and len(actual) == {"baseline": 186, "candidate": 187}[arm],
                "project source inventory changed")
        for relative, expected_proof in expected.items():
            require(not Path(relative).is_absolute() and ".." not in Path(relative).parts, "bad source path")
            recorded[str(root / relative)] = verify_expected(root / relative, expected_proof)
    require(proof(BINDINGS)["sha256"] == BINDINGS_SHA and proof(PLAN)["sha256"] == PLAN_SHA
            and proof(QUALIFICATION)["sha256"] == QUALIFICATION_SHA and proof(UNIT)["sha256"] == UNIT_SHA,
            "screen descriptor/decision/qualification changed")
    return recorded


def fixture_snapshot(fixtures):
    result = {}
    require(set(fixtures) == set(FIXTURES), "real fixture panel changed")
    for name, expected in fixtures.items():
        directory = SEMANTIC / "real-fixtures" / name
        require(directory.resolve() == directory and not directory.lstat().st_mode & 0o222,
                "real fixture directory changed")
        result[str(directory)] = dict(stamp=stamp(directory.lstat()))
        require({p.name for p in directory.iterdir()} == {"program.rbc", "program.rbc.allocations.jsonl"},
                "real directory inventory changed")
        for key, filename, size, digest in (("artifact_path", "program.rbc", "artifact_bytes", "artifact_sha256"),
                                          ("path", "program.rbc.allocations.jsonl", "bytes", "sha256")):
            path = Path(expected[key])
            require(path == directory / filename and path.resolve() == path and
                    not path.lstat().st_mode & 0o222 and path.lstat().st_nlink == 1,
                    "wrong/writable/linked real file")
            item = proof(path)
            require(item["bytes"] == expected[size] and item["sha256"] == expected[digest],
                    "real file bytes changed")
            result[str(path)] = item
    parent = SEMANTIC / "real-fixtures"
    require({p.name for p in parent.iterdir()} == set(fixtures) and parent.resolve() == parent
            and not parent.lstat().st_mode & 0o222, "real root changed")
    result[str(parent)] = dict(stamp=stamp(parent.lstat()))
    result[str(SEMANTIC / "fixtures.json")] = proof(SEMANTIC / "fixtures.json")
    return result


def verify_unit(descriptor):
    unit = json.loads(UNIT.read_bytes())
    require(proof(UNIT)["sha256"] == UNIT_SHA and unit["status"] == "passed"
            and unit["error"] is None and unit["post_binding_error"] is None
            and unit["expected_tests"] == unit["passed_tests"] == 52
            and len(unit["tests"]) == 4 and len(unit["children"]) == 8
            and unit["bindings"] == unit["bindings_after"]
            and all(r["returncode"] == 0 and r["error"] is None for r in unit["children"]),
            "complete successful 52-test qualification required")
    manifest = json.loads((PACKET / "unit-source-manifest.json").read_bytes())
    expected_tests = {(r["arm"], r["filename"]): r for r in manifest["tests"]}
    require(len(expected_tests) == 4, "unit suite inventory differs")
    for row in unit["tests"]:
        expected = expected_tests.pop((row["arm"], row["pattern"]))
        report = row["report"]
        require(row["passed"] == expected["expected_tests"] and row["failures"] == row["ignored"] == 0
                and report["status"] == "passed" and report["discovered_ids"] == expected["expected_ids"]
                and report["successful_ids"] == expected["expected_ids"]
                and not any(report[k] for k in ("failures", "errors", "skipped", "expected_failures", "unexpected_successes")),
                "unit exact names or outcome differ")
    require(not expected_tests, "missing unit suite")
    for arm, root in descriptor["roots"].items():
        require(manifest["arms"][arm]["root"] == root and manifest["arms"][arm]["sources"] == descriptor["sources"][arm],
                "unit manifest/source inventory differs")
        for relative, expected in descriptor["sources"][arm].items():
            item = unit["bindings"][str(Path(root) / relative)]
            require({k: item[k] for k in ("bytes", "sha256")} == expected, "unit/source binding differs")
    return unit


def semantic_evidence(qualification):
    """Recheck bounded retained receipts, never reread the eight peer originals."""
    recorded = {}
    for child_record in qualification["children"]:
        for item in child_record["logs"].values():
            path = Path(item["path"])
            require(path.is_relative_to(SEMANTIC), "semantic log escaped output")
            require(proof(path) == item, "semantic child log changed")
            recorded[str(path)] = item
    for row in qualification["recursion"]:
        item = row["audit"]["proof"]
        path = Path(item["path"])
        require(path.is_relative_to(SEMANTIC) and proof(path) == item, "semantic recursion log changed")
        recorded[str(path)] = item
    return recorded


def verify_semantics(descriptor, plan):
    qualification = json.loads(QUALIFICATION.read_bytes())
    require(proof(QUALIFICATION)["sha256"] == QUALIFICATION_SHA
            and descriptor["semantic_result_sha256"] == QUALIFICATION_SHA
            and qualification["status"] == "PASS" and qualification["completed"] is True
            and qualification["error"] is None and qualification["post_binding_error"] is None
            and qualification["decision_sha256"] == PLAN_SHA and qualification["unit_qualification_sha256"] == UNIT_SHA
            and len(qualification["reports"]) == 7 and len(qualification["children"]) == 14
            and len({r["label"] for r in qualification["children"]}) == 14
            and all(r["returncode"] == 0 and r["error"] is None and not r["observer_errors"] for r in qualification["children"]),
            "complete successful semantic qualification required")
    wanted_checks = {"eight_real_copies", "transport-baseline", "transport-candidate", "exact_transport_errors", "exact_real_api_receipts"}
    wanted_checks.update("recursion-" + scanner + "-" + str(limit)
                         for scanner in ("installed-C", "stdlib-py_make_scanner") for limit in (200, 1000))
    require(set(qualification["checks"]) == wanted_checks and all(qualification["checks"].values()),
            "semantic parity checks missing or failed")
    before = json.loads((SEMANTIC / "inputs-before.json").read_bytes())
    after = json.loads((SEMANTIC / "inputs-after.json").read_bytes())
    require(before == after, "semantic source bindings changed")
    qdescriptor = json.loads((SEMANTIC / "qualification-bindings.json").read_bytes())
    require(qdescriptor["roots"] == descriptor["roots"] and qdescriptor["sources"] == descriptor["sources"]
            and qdescriptor["base_commit"] == descriptor["base_commit"]
            and qualification["bindings_sha256"] == proof(SEMANTIC / "qualification-bindings.json")["sha256"],
            "semantic descriptor differs")
    for arm, root in descriptor["roots"].items():
        for relative, expected in descriptor["sources"][arm].items():
            item = before[str(Path(root) / relative)]
            require({k: item[k] for k in ("bytes", "sha256")} == expected, "semantic/source content differs")
    require(len(qualification["recursion"]) == 4
            and sum(r["report"]["counts"]["depth"] for r in qualification["recursion"]) == 7308
            and sum(r["report"]["counts"]["caller_bom"] for r in qualification["recursion"]) == 4872
            and all(r["audit"]["mismatches"] == 0 and r["report"]["mismatches"] == 0
                    and r["report"]["scanner_restored"] and r["report"]["recursion_limit_restored"]
                    for r in qualification["recursion"]), "dense semantic panel differs")
    prepared = json.loads((SEMANTIC / "fixtures.json").read_bytes())
    prep = qualification["reports"][0]
    require(prep["status"] == "PASS" and prepared == dict(fixtures=prep["fixtures"], copies=prep["copies"])
            and len(prepared["copies"]) == 8, "semantic fixture preparation differs")
    fixtures = prepared["fixtures"]
    require(set(fixtures) == set(FIXTURES) == set(descriptor["historical_fixtures"]), "fixture panel differs")
    for name in FIXTURES:
        old = descriptor["historical_fixtures"][name]
        expected = dict(old, artifact_path=str(SEMANTIC / "real-fixtures" / name / "program.rbc"),
                        path=str(SEMANTIC / "real-fixtures" / name / "program.rbc.allocations.jsonl"))
        require(fixtures[name] == expected, "qualified fixture metadata differs from historical bytes")
    snapshot = fixture_snapshot(fixtures)
    require(snapshot == json.loads((SEMANTIC / "real-fixtures-before.json").read_bytes())
            == json.loads((SEMANTIC / "real-fixtures-after.json").read_bytes()), "qualified real fixtures changed")
    for copy in prepared["copies"]:
        require(copy["source_before"] == copy["source_after"], "original changed during copying")
        dest = copy["destination"]
        require(dest["path"] in snapshot and {k: snapshot[dest["path"]][k] for k in dest} == dest,
                "qualified copy identity changed")
    baseline, candidate = qualification["reports"][1:3]
    require(baseline["arm"] == "baseline" and candidate["arm"] == "candidate"
            and baseline["real_traces"] == candidate["real_traces"]
            and baseline["rejections"] == candidate["rejections"]
            and len(baseline["rejections"]) == 33
            and baseline["exact_byte_and_event_bounds_passed"] and candidate["exact_byte_and_event_bounds_passed"],
            "transport parity differs")
    for report, arm in ((baseline, "baseline"), (candidate, "candidate")):
        require(report == json.loads((SEMANTIC / ("transport-" + arm + "-report.json")).read_bytes()),
                "retained transport report differs")
        require([r["fixture"] for r in report["real_traces"]] == list(FIXTURES), "real API order differs")
        for row in report["real_traces"]:
            fixture = fixtures[row["fixture"]]
            expected_receipt = {k: v for k, v in fixture.items() if k != "fixture"}
            require(row["validate"] == dict(ok=True, value=fixture["events"])
                    and row["selected"] == dict(ok=True, value=expected_receipt), "full real receipt/count differs")
    evidence = semantic_evidence(qualification)
    return qualification, fixtures, snapshot, evidence


def schedule():
    result = []
    for case in CASES:
        result.extend(dict(phase="parity", warmup=False, pair=0, case=case, arm=arm)
                      for arm in ("baseline", "candidate"))
    for case in CASES:
        for pair, order in enumerate((("baseline", "candidate"), ("candidate", "baseline"))):
            result.extend(dict(phase="warmup", warmup=True, pair=pair, case=case, arm=arm) for arm in order)
    for pair in range(20):
        cases = CASES if pair % 2 == 0 else tuple(reversed(CASES))
        order = ("baseline", "candidate") if pair % 2 == 0 else ("candidate", "baseline")
        for case in cases:
            result.extend(dict(phase="measured", warmup=False, pair=pair, case=case, arm=arm) for arm in order)
    require(len(result) == 368 and {p: sum(r["phase"] == p for r in result)
            for p in ("parity", "warmup", "measured")} == {"parity": 16, "warmup": 32, "measured": 320},
            "schedule construction differs")
    return result


def metrics():
    require([{k: r[k] for k in ("phase", "warmup", "pair", "case", "arm")} for r in ROWS] == schedule(),
            "incomplete or changed schedule")
    result = {}
    geo = lambda values: math.exp(sum(math.log(v) for v in values) / len(values))
    for case in CASES:
        measured = [r for r in ROWS if r["phase"] == "measured" and r["case"] == case]
        require(len(measured) == 40, "case incomplete")
        result[case] = {}
        for field in ("component_cpu_ns", "component_wall_ns", "cpu_seconds", "wall_seconds", "peak_rss_bytes"):
            ratios, baseline, candidate = [], [], []
            for pair in range(20):
                pair_rows = {r["arm"]: r for r in measured if r["pair"] == pair}
                require(set(pair_rows) == {"baseline", "candidate"}, "missing pair")
                a, b = pair_rows["baseline"][field], pair_rows["candidate"][field]
                require(a > 0 and b > 0 and math.isfinite(a) and math.isfinite(b), "nonpositive/nonfinite metric")
                baseline.append(a); candidate.append(b); ratios.append(b / a)
            result[case][field] = dict(paired_ratios=ratios, geometric_mean_ratio=geo(ratios),
                strict_wins=sum(r < 1 for r in ratios), median_baseline=statistics.median(baseline),
                median_candidate=statistics.median(candidate),
                median_paired_delta=statistics.median(b - a for a, b in zip(baseline, candidate)),
                median_arm_delta=statistics.median(candidate) - statistics.median(baseline),
                AB_geometric_mean_ratio=geo(ratios[::2]), BA_geometric_mean_ratio=geo(ratios[1::2]))
    return result


def decision_checks(summary, plan):
    checks, gates = {}, plan["adoption_gates"]
    for case in CASES:
        data = summary[case]; cpu = data["component_cpu_ns"]
        checks[case + ".component_cpu"] = cpu["geometric_mean_ratio"] <= gates["all_8_cases_component_cpu_geometric_mean_ratio_max"]
        checks[case + ".wins"] = cpu["strict_wins"] >= gates["all_8_cases_component_cpu_strict_wins_min"]
        for order in ("AB", "BA"):
            checks[case + "." + order] = cpu[order + "_geometric_mean_ratio"] < gates["each_case_both_order_component_cpu_ratio_max_exclusive"]
        checks[case + ".component_wall"] = data["component_wall_ns"]["geometric_mean_ratio"] <= gates["each_case_component_wall_geometric_mean_ratio_max"]
        for field, key in (("cpu_seconds", "cpu"), ("wall_seconds", "wall"), ("peak_rss_bytes", "peak_rss")):
            checks[case + ".process_" + key] = data[field]["geometric_mean_ratio"] <= gates["each_case_process_" + key + "_geometric_mean_ratio_max"]
    require(len(checks) == 64, "performance gate count differs")
    return checks



def main():
    require(sys.argv[1:] == ["--execute-frozen-allocation-screen"], "explicit execution flag required")
    require(QUALIFICATION_SHA != "UNBOUND", "completed semantic qualification remains UNBOUND")
    require(sys.platform == "darwin" and sys.version_info[:2] == (3, 14)
            and Path(sys.executable).resolve() == PYTHON.resolve(), "pinned macOS Python required")
    require(os.environ.get("HOME") == "/Users/danluu", "HOME must remain unchanged")
    require(proof(BINDINGS)["sha256"] == BINDINGS_SHA and proof(PLAN)["sha256"] == PLAN_SHA,
            "unbound/changed descriptor or decision")
    descriptor, plan = json.loads(BINDINGS.read_bytes()), json.loads(PLAN.read_bytes())
    require(descriptor["base_commit"] == plan["base_commit"] and descriptor["roots"] ==
            {"baseline": plan["baseline_root"], "candidate": plan["candidate_root"]}
            and list(CASES) == plan["cases"], "decision/root/case mismatch")
    require(descriptor["changed_files"] == ["scripts/allocation_trace.py", "tests/test_allocation_trace.py"],
            "unexpected candidate scope")
    a, b = descriptor["sources"]["baseline"], descriptor["sources"]["candidate"]
    require({name for name in set(a) | set(b) if a.get(name) != b.get(name)} == set(descriptor["changed_files"]),
            "unexpected actual arm difference")
    require(descriptor["fixed_files"][str(PACKET.parent / "allocation-decoder-proposal/v4/candidate.patch")]["sha256"]
            == plan["proposal_patch_sha256"] and plan["schedule"]["total_api_processes"] == 368
            and plan["schedule"]["memory_processes"] == 368 and plan["schedule"]["measured_pairs_per_case"] == 20,
            "frozen patch/schedule differs")
    before = verify_inputs(descriptor)
    unit = verify_unit(descriptor)
    qualification, fixtures, frozen_fixtures, semantic_proofs = verify_semantics(descriptor, plan)
    require(PACKET.resolve() == PACKET and free_bytes() > FLOOR and not OUT.exists()
            and not OUT.is_symlink(), "fresh output/16 GiB required")
    fd = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW)
    try:
        lock_info = os.fstat(fd)
        require(stat.S_ISREG(lock_info.st_mode), "shared lock is not regular")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require((lock_info.st_dev, lock_info.st_ino) == (LOCK.lstat().st_dev, LOCK.lstat().st_ino), "shared lock inode changed")
        require(free_bytes() > FLOOR and not OUT.exists() and not OUT.is_symlink(), "output/admission changed")
        OUT.mkdir(mode=0o700)
        reports, sample_inputs, report_proofs, warm_reports = [], [], [], []
        warmed = dependencies = None
        module_sets = {}
        error = post_error = summary = checks = None
        controller_before = proof(Path(__file__).resolve())
        try:
            require(verify_inputs(descriptor) == before and fixture_snapshot(fixtures) == frozen_fixtures,
                    "inputs changed during admission")
            require(semantic_evidence(qualification) == semantic_proofs, "semantic evidence changed during admission")
            for name, value in (("inputs-before.json", before), ("decision-plan.json", plan),
                                ("screen-bindings.json", descriptor), ("qualification.json", qualification),
                                ("unit-qualification.json", unit), ("controller.json", controller_before),
                                ("fixtures-before.json", frozen_fixtures), ("schedule.json", schedule())):
                write(name, value)
            CACHE.mkdir(mode=0o700)
            (OUT / "tmp").mkdir(mode=0o700)
            environment = dict(HOME="/Users/danluu", PATH="/usr/bin:/bin", LANG="C", LC_ALL="C",
                PYTHONNOUSERSITE="1", PYTHONPYCACHEPREFIX=str(CACHE), TMPDIR=str(OUT / "tmp"))
            for index, entry in enumerate(schedule()):
                phase, warmup, pair, case, arm = (entry[k] for k in ("phase", "warmup", "pair", "case", "arm"))
                name, api = case.rsplit("_", 1)
                label = f"{index:03d}-{phase}-{case}-{pair:02d}-{arm}"
                require(verify_inputs(descriptor) == before, "source/tool/semantic metadata changed")
                require(fixture_snapshot(fixtures) == frozen_fixtures, "fixture changed before sample")
                if phase == "parity":
                    require(not list(CACHE.iterdir()), "parity cache must remain empty")
                if phase == "measured":
                    require(warmed is not None and len(warm_reports) == 32, "warm cache not frozen")
                    require(dependency_proofs(warm_reports, descriptor) == dependencies, "dependencies changed")
                    require(cache_snapshot(descriptor, reports[0]["python"]["cache_tag"], reports[0]["python"]["magic"]) == warmed,
                            "cache changed before sample")
                fixture = dict(fixtures[name], name=name, qualified_events=fixtures[name]["events"])
                config = dict(schema_version=1, arm=arm, phase=phase, case=case, api=api,
                    source_root=descriptor["roots"][arm], fixture=fixture,
                    fixture_root=str(SEMANTIC / "real-fixtures"), output_root=str(OUT), pycache_prefix=str(CACHE),
                    qualification_sha256=QUALIFICATION_SHA)
                write(label + "-input.json", config)
                sample_inputs.append(proof(OUT / (label + "-input.json")))
                gate = admission(label, environment)
                command = [str(PYTHON), "-I", "-S", "-X", "pycache_prefix=" + str(CACHE)]
                if not warmup:
                    command.append("-B")
                command += [str(PACKET / "timing-driver.py"), str(OUT / (label + "-input.json"))]
                receipt = report = None
                child_error = parse_error = None
                try:
                    receipt = child(label, command, environment, gate)
                except BaseException as caught:
                    child_error = repr(caught)
                    if CHILDREN and CHILDREN[-1]["label"] == label:
                        receipt = CHILDREN[-1]
                # Preserve raw stdout and a row before any exit/parity/report-field assertion.
                stdout_proof = proof(OUT / (label + ".stdout"), 16 * MIB)
                try:
                    report = json.loads((OUT / (label + ".stdout")).read_bytes())
                except BaseException as caught:
                    parse_error = repr(caught)
                write(label + "-report.json", dict(report=report, parse_error=parse_error, stdout=stdout_proof))
                report_proofs.append(proof(OUT / (label + "-report.json")))
                row = dict(receipt or {}, **entry, child_error=child_error, report_parse_error=parse_error,
                    component_cpu_ns=report.get("component_cpu_ns") if isinstance(report, dict) else None,
                    component_wall_ns=report.get("component_wall_ns") if isinstance(report, dict) else None,
                    driver_status=report.get("status") if isinstance(report, dict) else None,
                    driver_report=report, raw_stdout=stdout_proof)
                ROWS.append(row)
                with (OUT / "samples.jsonl").open("a") as output:
                    output.write(json.dumps(row, sort_keys=True) + "\n")
                require(child_error is None and parse_error is None and receipt is not None
                        and not (OUT / (label + ".stderr")).read_bytes(), "child/driver transport failed")
                expected = {k: v for k, v in fixtures[name].items() if k != "fixture"}
                require(report["schema_version"] == 1 and report["status"] == "PASS" and report["stage"] == "api"
                        and report["api_calls"] == 1 and report["parity"] is True and report["error"] is None
                        and report["arm"] == arm and report["case"] == case and report["api"] == api
                        and report["phase"] == phase and report["warmup"] == warmup
                        and report["expected_events"] == fixtures[name]["events"]
                        and report["expected_selected_receipt"] == expected
                        and ((type(report["result"]) is int and report["result"] == fixtures[name]["events"])
                             if api == "validate" else report["result"] == expected)
                        and report["qualification_sha256"] == QUALIFICATION_SHA
                        and report["pycache_prefix"] == str(CACHE) and report["dont_write_bytecode"] == (not warmup),
                        "actual API parity/regime failure")
                require(all(type(report[k]) is int and report[k] > 0 for k in ("component_cpu_ns", "component_wall_ns")),
                        "invalid component clocks")
                if reports:
                    require(report["python"] == reports[0]["python"], "Python identity differs")
                require(Path(report["python"]["executable"]).resolve() == PYTHON.resolve(), "driver interpreter differs")
                previous_modules = module_sets.setdefault((arm, api), report["modules"])
                require(previous_modules == report["modules"], "per-API module inventory changed")
                reports.append(report)
                require(fixture_snapshot(fixtures) == frozen_fixtures, "API changed fixture")
                if phase == "parity":
                    require(not list(CACHE.iterdir()), "-B parity wrote bytecode")
                if warmup:
                    warm_reports.append(report)
                if index == 47:
                    require(len(warm_reports) == 32, "warmup schedule incomplete")
                    dependencies = dependency_proofs(warm_reports, descriptor)
                    warmed = cache_snapshot(descriptor, report["python"]["cache_tag"], report["python"]["magic"])
                    for value in reports:
                        require_cached_sources(value, warmed)
                    write("dependencies-frozen.json", dependencies)
                    write("bytecode-cache-frozen.json", warmed)
                if phase == "measured":
                    require_cached_sources(report, warmed)
                    require(cache_snapshot(descriptor, report["python"]["cache_tag"], report["python"]["magic"]) == warmed,
                            "measured child changed cache")
            require(len(ROWS) == 368 and len(CHILDREN) == 736 and len({r["label"] for r in CHILDREN}) == 736
                    and all(r["returncode"] == 0 and r["error"] is None for r in CHILDREN), "incomplete child settlement")
            summary = metrics()
            checks = decision_checks(summary, plan)
        except BaseException as caught:
            error = repr(caught)
        finally:
            try:
                after = verify_inputs(descriptor)
                require(after == before, "final source/tool/semantic identity changed")
                require(proof(Path(__file__).resolve()) == controller_before, "controller changed")
                require(fixture_snapshot(fixtures) == frozen_fixtures, "final real fixture changed")
                require(semantic_evidence(qualification) == semantic_proofs, "final semantic evidence changed")
                write("fixtures-after.json", fixture_snapshot(fixtures))
                if warmed is not None:
                    final_cache = cache_snapshot(descriptor, reports[0]["python"]["cache_tag"], reports[0]["python"]["magic"])
                    require(final_cache == warmed, "final cache changed")
                    require(dependency_proofs(warm_reports, descriptor) == dependencies, "final dependencies changed")
                    write("bytecode-cache-after.json", final_cache)
                require(all(proof(Path(p["path"])) == p for p in sample_inputs + report_proofs), "retained sample input/report changed")
                write("inputs-after.json", after)
            except BaseException as caught:
                post_error = repr(caught)
        status = "PASS" if error is None and post_error is None and len(ROWS) == 368 and len(CHILDREN) == 736 else "FAIL"
        result = dict(status=status, error=error, post_binding_error=post_error, rows=ROWS, children=CHILDREN,
            preparation=[], summary=summary, gates=checks,
            fixed_decision_satisfied=status == "PASS" and checks is not None and len(checks) == 64 and all(checks.values()),
            scope=plan["scope"], decision_sha256=PLAN_SHA, bindings_sha256=BINDINGS_SHA,
            qualification_sha256=QUALIFICATION_SHA, unit_qualification_sha256=UNIT_SHA)
        write("result.json", result)
        print(json.dumps({k: result[k] for k in ("status", "error", "post_binding_error", "summary", "gates", "fixed_decision_satisfied")}), flush=True)
        return 0 if status == "PASS" else 1
    finally:
        os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main())

