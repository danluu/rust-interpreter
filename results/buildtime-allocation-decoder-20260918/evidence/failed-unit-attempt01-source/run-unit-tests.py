#!/usr/bin/env python3
"""Paired allocation-trace correctness: four suites, 52 exact named tests."""
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-probe')  # Common owned cwd; each arm is imported by exact source path.
PACKET = ROOT
PROPOSAL = PACKET.parent / "allocation-decoder-proposal/v3"
OUT = PACKET / "unit-screen-01"
LOCK = Path("/Users/danluu/dev/rust-interp/.work/benchmark.lock")
SOURCE = PACKET / "unit-source-manifest.json"
SOURCE_SHA = 'ff4e2acdaf21d4ef0a039c883cfb9de5052378e6b10e8f69de5c9cb11610c846'
DRIVER = PACKET / "unit-driver.py"
PYTHON = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
FIXED = {
    Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14'): '87d4df53fd91304be5bac391fb204643c36b7df2023c04a0953bcbc7d4fdf634',
    Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/Python'): 'b112695af23f5e46d84a7c4ef6057603b70b94aacc32e9d548808c2875759d47',
    Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-probe/unit-source-manifest.json'): 'ff4e2acdaf21d4ef0a039c883cfb9de5052378e6b10e8f69de5c9cb11610c846',
    Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-probe/unit-driver.py'): '5ece3cd071e48c2cbef6da2686c5d1ec6a7fa0a1149c832a025ab7cf76ffeada',
    Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-probe/decision-plan.json'): 'af6f52d6c088a5924714d26a42626b33aa64cc836c042e5f96f7e514a84319a9',
    Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/runtime-relative-paths-probe/run-unit-tests.py'): '4cdc55de282224d4f99ecd6ea929ac9f9b4c7677fbd55c3ed4c7f70b7ff32d42',
    Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-proposal/v3/source-bindings.json'): 'e2f1a307e977a3d87289cb0e8aa7f3d2378f61fd87a92f878ce69d51f0d99208',
    Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-proposal/v3/candidate.patch'): '998dd3bc1ca338efe7ca5aeaed02c9447b82c88e2730d0675064d152da63f569',
    Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-proposal/v3/README.md'): '864a30bbecef0ee0c51f0e1bd506b283e9b667a8cfaa4a7a515736afe29c6611',
    Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-proposal/v3/PLAN.md'): 'f8340a405406b0bc004cf48fc46ca4d3dafd671e1e1349ba9592c31430a8010f',
    Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/json/__init__.py'): '2dd10f1bf4c9ea5478e589216805e7f279d0e4bce134a19efa297404fb87407d',
    Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/json/decoder.py'): 'dc98d3e677612ea7311303f06a144cec6b91ebadc7ec037d1777501647578a07',
    Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/lib/python3.14/json/scanner.py'): '572958017eae8842eeddd0e3d18d3c56cc0a197348224915e1d87ce937841764',
}

GIB = 1024 ** 3
MIB = 1024 ** 2
FLOOR = 16 * GIB  # Only these tiny synthetic Python tests; Rust builds remain 32 GiB.
TESTS = (('baseline-allocation-trace', 'baseline', 'test_allocation_trace.py', 7), ('baseline-interpreter-build-metrics', 'baseline', 'test_interpreter_build_metrics.py', 19), ('candidate-allocation-trace', 'candidate', 'test_allocation_trace.py', 7), ('candidate-interpreter-build-metrics', 'candidate', 'test_interpreter_build_metrics.py', 19))
EXPECTED_TESTS = sum(count for _, _, _, count in TESTS)
CHILDREN = []


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def free_bytes():
    s = os.statvfs(PACKET)
    return s.f_bavail * s.f_frsize


def identity(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def proof(path, cap=8 * MIB):
    before = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(before.st_mode) and before.st_size <= cap,
            "noncanonical/nonregular/oversized input: " + str(path))
    data = path.read_bytes()
    require(len(data) == before.st_size and identity(path.lstat()) == identity(before),
            "input changed while reading: " + str(path))
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                identity=identity(before))


def write(name, data):
    with (OUT / name).open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def bindings():
    files = {}
    for path, digest in [*FIXED.items(), (Path(__file__).resolve(), None)]:
        p = proof(path)
        require(digest is None or p["sha256"] == digest, "fixed input changed: " + str(path))
        files[str(path)] = p
    descriptor = json.loads(SOURCE.read_bytes())
    require(descriptor["base_commit"] == "835382dbe182ebf5f10d322e79ac290cdd3ef2f2" and
            descriptor["expected_tests"] == EXPECTED_TESTS and set(descriptor["arms"]) == {"baseline", "candidate"},
            "wrong source descriptor")
    decision = json.loads((PACKET / "decision-plan.json").read_bytes())
    q = decision["qualification"]["unit_tests"]
    require(decision["base_commit"] == descriptor["base_commit"] and
            decision["proposal_patch_sha256"] == FIXED[PROPOSAL / "candidate.patch"] and
            q["total"] == EXPECTED_TESTS and q["work_processes"] == q["memory_processes"] == 4 and
            q["per_arm"] == {"test_allocation_trace.py": 7, "test_interpreter_build_metrics.py": 19},
            "unit qualification differs from frozen decision")
    for arm, count in [("baseline", 186), ("candidate", 187)]:
        source = descriptor["arms"][arm]
        root = Path(source["root"])
        require(str(root) == decision[arm + "_root"] and root.resolve() == root and
                source["base_commit"] == descriptor["base_commit"], "wrong arm source root")
        expected = source["sources"]
        actual_paths = {str(p.relative_to(root)) for folder in ("scripts", "tests")
                        for p in (root / folder).glob("*.py")}
        require(len(expected) == count and actual_paths == set(expected), "Python source inventory changed")
        for relative, expected_proof in expected.items():
            path = Path(relative)
            require(not path.is_absolute() and ".." not in path.parts, "invalid source path")
            p = proof(root / path)
            require({k: p[k] for k in ("bytes", "sha256")} == expected_proof,
                    "project source changed: " + arm + "/" + relative)
            files[str(root / path)] = p
    proposal = json.loads((PROPOSAL / "source-bindings.json").read_bytes())
    changed = proposal["changed_paths"]
    require(proposal["base_commit"] == descriptor["base_commit"] and
            set(changed) == {"scripts/allocation_trace.py", "tests/test_allocation_trace.py"},
            "wrong allocation decoder proposal")
    baseline = descriptor["arms"]["baseline"]["sources"]
    candidate = descriptor["arms"]["candidate"]["sources"]
    differences = {name for name in set(baseline) | set(candidate)
                   if baseline.get(name) != candidate.get(name)}
    require(differences == set(changed), "unexpected source arm differences")
    for relative, expected_proof in changed.items():
        require(baseline.get(relative) == expected_proof["baseline"] and
                candidate[relative] == expected_proof["candidate"], "arm source does not match proposal")
        path = PROPOSAL / "source" / relative
        p = proof(path)
        require({k: p[k] for k in ("bytes", "sha256")} == expected_proof["candidate"],
                "candidate proposal copy changed")
        files[str(path)] = p
    return files


def test_inventory():
    """Verify exact source-counted method names without importing project modules."""
    descriptor = json.loads(SOURCE.read_bytes())
    inventory = []
    for label, arm, filename, expected_count in TESTS:
        rows = [row for row in descriptor["tests"] if row["label"] == label]
        require(len(rows) == 1, "wrong suite descriptor")
        row = rows[0]
        test_arm = "candidate" if filename == "test_allocation_trace.py" else arm
        path = Path(descriptor["arms"][test_arm]["root"]) / "tests" / filename
        require(row["arm"] == arm and row["filename"] == filename and row["path"] == str(path),
                "wrong test module binding")
        tree = ast.parse(path.read_text())
        require(not any(isinstance(n, ast.FunctionDef) and n.name == "load_tests" for n in tree.body),
                "unexpected custom unittest loader")
        classes = []
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test")]
            if not methods:
                continue
            require(len(node.bases) == 1 and isinstance(node.bases[0], ast.Attribute) and
                    isinstance(node.bases[0].value, ast.Name) and node.bases[0].value.id == "unittest" and
                    node.bases[0].attr == "TestCase" and not node.decorator_list,
                    "unexpected test inheritance or decoration")
            require(len(methods) == len(set(methods)) and all(not n.decorator_list for n in node.body
                    if isinstance(n, ast.FunctionDef) and n.name in methods), "duplicate/decorated test method")
            classes.append(dict(name=node.name, methods=methods, inherited_test_methods=0))
        ids = sorted(Path(filename).stem + "." + c["name"] + "." + name
                     for c in classes for name in c["methods"])
        require(len(ids) == expected_count == row["expected_tests"] and
                ids == row["expected_ids"] and classes == row["classes"], "frozen test names changed")
        inventory.append(row)
    require(len(descriptor["tests"]) == len(TESTS), "extra suite in descriptor")
    return dict(method="static AST only; no test/production module imports", modules=inventory,
                expected_tests=EXPECTED_TESTS,
                fixture_scope="synthetic allocation sidecars and actual launcher paths with Cargo/VM stubbed")


def run_child(label, command, environment, gate=None):
    require(free_bytes() >= FLOOR, "synthetic Python disk floor requires 16 GiB")
    if gate is not None:
        require(time.monotonic() - gate["monotonic"] < 20, "memory admission expired")
    record = dict(label=label, command=list(map(str, command)), cwd=str(ROOT),
                  environment=environment, parent_pid=os.getpid(), terminal=None,
                  admission=gate, free_bytes_before=free_bytes())
    write(label + "-planned.json", record)
    child = usage = status = None
    error = None
    with (OUT / (label + ".stdout")).open("xb") as stdout, \
         (OUT / (label + ".stderr")).open("xb") as stderr:
        started = time.perf_counter()
        record["started_epoch"] = time.time()
        try:
            require(free_bytes() >= FLOOR, "disk fell before child launch")
            child = subprocess.Popen(record["command"], cwd=ROOT, env=environment,
                                     stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     close_fds=True)
            record.update(pid=child.pid, popen_completed_epoch=time.time())
            write(label + "-start.json", record)
            next_observation = 0.0
            with (OUT / (label + "-observations.jsonl")).open("x") as observations:
                while status is None:
                    pid, got_status, got_usage = os.wait4(child.pid, os.WNOHANG)
                    if pid:
                        require(pid == child.pid, "unexpected wait4 child")
                        status, usage = got_status, got_usage
                        break
                    if time.monotonic() >= next_observation:
                        free = free_bytes()
                        observations.write(json.dumps(dict(epoch=time.time(), pid=child.pid,
                            free_bytes=free, below_launch_floor=free < FLOOR,
                            action="read_only_no_signals")) + "\n")
                        observations.flush()
                        next_observation = time.monotonic() + 5
                    time.sleep(0.05)
        except BaseException as caught:
            error = repr(caught)
        finally:
            if child is not None:
                while status is None:
                    try:
                        pid, status, usage = os.wait4(child.pid, 0)
                        require(pid == child.pid, "unexpected wait4 child")
                    except InterruptedError:
                        continue
                    except BaseException as caught:
                        if error is None:
                            error = repr(caught)
                        if isinstance(caught, ChildProcessError):
                            child.wait()  # Already reaped elsewhere: invalid evidence.
                            break
                if status is not None:
                    child.returncode = os.waitstatus_to_exitcode(status)
                record.update(returncode=child.returncode, finished_epoch=time.time(),
                              wall_seconds=time.perf_counter() - started)
    record["error"] = error
    if usage is not None:
        record.update(user_seconds=usage.ru_utime, system_seconds=usage.ru_stime,
                      cpu_seconds=usage.ru_utime + usage.ru_stime, peak_rss_bytes=usage.ru_maxrss)
    CHILDREN.append(record)
    # Every child has settled before any terminal/log parsing can fail.
    record["logs"] = {name: proof(OUT / (label + "." + name), MIB)
                      for name in ("stdout", "stderr")}
    write(label + "-terminal.json", record)
    require(child is not None and usage is not None and error is None and child.returncode == 0,
            "child failed or incomplete evidence: " + label)
    return record


def admission(label, environment):
    receipt = run_child(label + "-memory", ["/usr/bin/memory_pressure", "-Q"], environment)
    stdout = (OUT / (label + "-memory.stdout")).read_bytes()
    stderr = (OUT / (label + "-memory.stderr")).read_bytes()
    values = re.findall(rb"System-wide memory free percentage:\s*(\d+)%", stdout)
    require(len(values) == 1 and not stderr and int(values[0]) >= 30,
            "synthetic Python task requires 30% free memory")
    require(free_bytes() >= FLOOR, "synthetic Python task requires 16 GiB disk")
    return dict(monotonic=time.monotonic(), epoch=time.time(), free_bytes=free_bytes(),
                memory_free_percent=int(values[0]), memory_receipt=receipt["label"])


def main():
    require(sys.argv[1:] == ["--execute-synthetic-unit-tests"], "explicit execution flag required")
    require(sys.platform == "darwin" and ROOT.resolve() == ROOT and PACKET.resolve() == PACKET,
            "wrong platform or owned paths")
    require(os.environ.get("HOME") == "/Users/danluu", "HOME must remain unchanged")
    require(free_bytes() >= FLOOR and not OUT.exists() and not OUT.is_symlink(),
            "16 GiB and a fresh output directory required")
    fd = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW)
    try:
        identity_before = os.fstat(fd)
        require(stat.S_ISREG(identity_before.st_mode), "benchmark lock must be regular")
        print(json.dumps(dict(status="waiting for shared benchmark lock", controller_pid=os.getpid())), flush=True)
        fcntl.flock(fd, fcntl.LOCK_EX)
        require((identity_before.st_dev, identity_before.st_ino) ==
                (LOCK.lstat().st_dev, LOCK.lstat().st_ino), "benchmark lock replaced while waiting")
        require(free_bytes() >= FLOOR and not OUT.exists() and not OUT.is_symlink(),
                "admission/output changed while waiting")
        OUT.mkdir(mode=0o700)
        before = after = inventory = None
        tests = []
        error = post_binding_error = None
        environment = dict(HOME="/Users/danluu", PATH="/usr/bin:/bin", LANG="C", LC_ALL="C",
                           PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
        try:
            before = bindings()
            inventory = test_inventory()
            write("test-inventory.json", inventory)
            write("inputs.json", dict(bindings=before, tests=TESTS, expected_tests=EXPECTED_TESTS,
                controller_pid=os.getpid(), controller_parent_pid=os.getppid(),
                lock_identity=[identity_before.st_dev, identity_before.st_ino],
                resource_scope="synthetic Python tests only; 16 GiB/30%; no Rust/std/tool build",
                log_limit="1 MiB bounded reader per stream, ordinary file logs; not hard disk cap"))
            for label, arm, filename, expected in TESTS:
                temporary = OUT / (label + "-tmp")
                temporary.mkdir(mode=0o700)
                env = dict(environment, TMPDIR=str(temporary))
                gate = admission(label, env)
                report_path = OUT / (label + "-tests.json")
                command = [PYTHON, "-I", "-S", "-B", DRIVER, label, report_path]
                receipt = run_child(label, command, env, gate)
                stderr = (OUT / (label + ".stderr")).read_text()
                found = re.findall(r"(?m)^Ran (\d+) tests? in [^\n]+$", stderr)
                successful = re.findall(r"(?m)^test_.* \.\.\. ok$", stderr)
                require(found == [str(expected)] and len(successful) == expected and
                        re.search(r"(?m)^OK\s*\Z", stderr) is not None,
                        "unexpected unittest count/result or skipped/non-success test: " + label)
                report_proof = proof(report_path, MIB)
                report = json.loads(report_path.read_bytes())
                declared = next(row for row in inventory["modules"] if row["label"] == label)
                source = json.loads(SOURCE.read_bytes())["arms"][arm]
                require(report["status"] == "passed" and report["arm"] == arm and
                        report["label"] == label and report["filename"] == filename and
                        report["tests_run"] == expected and report["discovered_ids"] == declared["expected_ids"] and
                        report["successful_ids"] == declared["expected_ids"] and
                        not any(report[key] for key in ("failures", "errors", "skipped", "expected_failures", "unexpected_successes")) and
                        report["module_path"] == str(Path(source["root"]) / "scripts/allocation_trace.py") and
                        report["module_content"] == source["sources"]["scripts/allocation_trace.py"] and
                        report["test_path"] == declared["path"] and
                        report["test_content"] == {k: before[declared["path"]][k] for k in ("bytes", "sha256")} and
                        report["canonical_module_object_preserved"] is True and report["manifest_sha256"] == SOURCE_SHA,
                        "driver names/module/result mismatch: " + label)
                tests.append(dict(label=label, arm=arm, pattern=filename, passed=expected,
                                  failures=0, ignored=0, child_pid=receipt["pid"],
                                  report=report, report_proof=report_proof))
            require(sum(row["passed"] for row in tests) == EXPECTED_TESTS, "incomplete correctness panel")
        except BaseException as caught:
            error = repr(caught)
        finally:
            if before is not None:
                try:
                    after = bindings()
                    require(after == before, "bound inputs changed during tests")
                except BaseException as caught:
                    post_binding_error = repr(caught)
                    if error is None:
                        error = post_binding_error
        result = dict(status="passed" if error is None else "failed", error=error,
                      expected_tests=EXPECTED_TESTS, passed_tests=sum(r["passed"] for r in tests),
                      tests=tests, test_inventory=inventory, bindings=before,
                      bindings_after=after, post_binding_error=post_binding_error, children=CHILDREN,
                      scope="52 exact named Python correctness tests across four arm/module suites; actual allocation parsing and stubbed launcher metrics; no Rust/compiler/Cargo/VM workload or performance claim")
        write("result.json", result)
        print(json.dumps(dict(status=result["status"], passed_tests=result["passed_tests"],
                              error=error, result=str(OUT / "result.json"))), flush=True)
        return 0 if error is None else 1
    finally:
        os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main())
