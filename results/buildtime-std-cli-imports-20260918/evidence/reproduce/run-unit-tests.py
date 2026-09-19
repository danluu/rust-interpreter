#!/usr/bin/env python3
"""Candidate-only21 selection tests; pinned synthetic Python controls, no real tool build."""
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
ROOT = Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-mir-lazy-selection-probe')
PACKET = ROOT
PROPOSAL = PACKET.parent / "std-mir-lazy-selection-proposal"
OUT = PACKET / "unit-screen-01"
LOCK = Path("/Users/danluu/dev/rust-interp/.work/benchmark.lock")
SOURCE = PACKET / "unit-source-manifest.json"
SOURCE_SHA = "db14ba649b5f51f9533e950e731a0fe3e5ecb4bf33a6403fde6b10e5b0702755"
DRIVER = PACKET / "unit-driver.py"
UNIT_PLAN = PACKET / "decision-plan.json"
UNIT_PLAN_SHA = "c432cb2dc3cb182e038a936c898e7d6a76c1270d6425629a4239ef1136838826"
APPLIED_SHA = "801f46e3be8c9a224d2478b0d69584d254859f1faa6f5fbe336ab322c2c7cc72"
PYTHON = Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
FIXED = {
    PYTHON: '87d4df53fd91304be5bac391fb204643c36b7df2023c04a0953bcbc7d4fdf634',
    PYTHON.parent.parent / 'Python': 'b112695af23f5e46d84a7c4ef6057603b70b94aacc32e9d548808c2875759d47',
    SOURCE: SOURCE_SHA,
    DRIVER: "d1546542fdaa7287320468bd31e63022cfa279d9ac6588a65c5fc16f7d7a5ebf",
    UNIT_PLAN: UNIT_PLAN_SHA,
    PACKET / 'applied-source-manifest.json': APPLIED_SHA,
    PROPOSAL / 'source-bindings.json': 'ae6871a985c1be5c228be993d1176a630d1c591c3628d014b8669896a18a1a22',
    PROPOSAL / 'candidate.patch': 'e5df711ee51cc0e53d255af38d19d2a88e5b6112727ecd2fe702dc3f083dbb23',
    PROPOSAL / 'packet-manifest.json': 'b801a3e0de6440b0c24bea7a162a377a2cee3b9138fcdaf9890e6d14ce409d8e',
    PACKET.parent / 'bytecode-core-split-probe/run-unit-tests.py': '0dca06642975710a89d49222b58df73a2dd5016d2eaaf9593faf13cff34c695a',
    PACKET.parent / 'bytecode-core-split-probe/unit-driver.py': '7dd826a91d00a6fd2788ea2a17567299b6f7d080ed81c8cb68a4cd009d78fbdb',
    Path('/Users/danluu/.codex/AGENTS.md'): 'e1605bf47fa1c85e645485621ae89be1915409934df327797ee1b8ca10165949',
}
GIB = 1024 ** 3
MIB = 1024 ** 2
FLOOR = 16 * GIB
TESTS = (('selection-routing', 'candidate', 'test_std_mir_selection.py', 8),
         ('custom-compiler-launcher', 'candidate', 'test_custom_compiler_launcher.py', 6),
         ('custom-cargo', 'candidate', 'test_custom_cargo.py', 7))
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
    require(descriptor["status"] == "frozen" and descriptor["base_commit"] == "050a7d2a1e9677bc467a49fdba7a2ab485566e97"
            and descriptor["expected_tests"] == 21 and set(descriptor["arms"]) == {"candidate"}
            and descriptor["work_processes"] == descriptor["memory_processes"] == 1,
            "wrong candidate-only source descriptor")
    require(descriptor["decision_sha256"] == UNIT_PLAN_SHA
            and descriptor["applied_source_manifest_sha256"] == APPLIED_SHA
            and descriptor["proposal_bindings_sha256"] == FIXED[PROPOSAL / "source-bindings.json"],
            "descriptor stage bindings differ")
    runtime = descriptor["runtime"]
    require(runtime["executable"] == str(PYTHON) and runtime["required_version"] == [3, 14, 7]
            and runtime["private_empty_pycache"] == str(OUT / "pycache")
            and runtime["flags"] == ["-I", "-S", "-B"] and len(runtime["files"]) == 1955,
            "runtime binding differs")
    for path, expected in runtime["files"].items():
        p = proof(Path(path))
        require({k: p[k] for k in ("bytes", "sha256", "identity")} == expected,
                "installed runtime changed: " + path)
        files[path] = p
    for row in runtime["links"]:
        path = Path(row["path"])
        observed = dict(path=str(path), identity=identity(path.lstat()), text=os.readlink(path), resolved=str(path.resolve()))
        require(stat.S_ISLNK(path.lstat().st_mode) and observed == row, "runtime link changed")
        files[str(path)] = observed
    for path, expected in descriptor["fixed_files"].items():
        p = proof(Path(path))
        require({k: p[k] for k in ("bytes", "sha256")} == expected, "support input changed: " + path)
        files[path] = p
    decision = json.loads(UNIT_PLAN.read_bytes())
    q = decision["qualification"]
    require(decision["state"].startswith("numerical decision frozen")
            and decision["base_commit"] == descriptor["base_commit"]
            and decision["candidate_root"] == descriptor["arms"]["candidate"]["root"]
            and decision["baseline_root"] == descriptor["baseline_root"]
            and decision["proposal_patch_sha256"] == FIXED[PROPOSAL / "candidate.patch"]
            and decision["applied_source_manifest_sha256"] == APPLIED_SHA
            and q["candidate_tests"] == 21 and q["new_selection_tests"] == 8
            and q["unchanged_downstream_tests"] == 13
            and decision["resource"]["free_gib_min"] == 16
            and decision["resource"]["memory_free_percent_min"] == 30,
            "unit stage differs from frozen decision")
    source = descriptor["arms"]["candidate"]
    root = Path(source["root"])
    require(root.resolve() == root and source["base_commit"] == descriptor["base_commit"], "wrong candidate source root")
    expected = source["sources"]
    actual_paths = {str(p.relative_to(root)) for folder in ("scripts", "tests")
                    for p in (root / folder).glob("*.py")}
    require(len(expected) == 190 and actual_paths == set(expected), "Python source inventory changed")
    for relative, expected_proof in expected.items():
        path = Path(relative)
        require(not path.is_absolute() and ".." not in path.parts, "invalid source path")
        p = proof(root / path)
        require({k: p[k] for k in ("bytes", "sha256")} == expected_proof,
                "project source changed: " + relative)
        files[str(root / path)] = p
    proposal = json.loads((PROPOSAL / "source-bindings.json").read_bytes())
    applied = json.loads((PACKET / "applied-source-manifest.json").read_bytes())
    require(proposal["base_commit"] == applied["base_commit"] == descriptor["base_commit"]
            and applied["root"] == str(root)
            and proposal["patch_sha256"] == applied["patch_sha256"] == FIXED[PROPOSAL / "candidate.patch"]
            and applied["source_bindings_sha256"] == FIXED[PROPOSAL / "source-bindings.json"],
            "wrong source proposal/application")
    require(set(proposal["files"]) == set(applied["files"]) == {"scripts/std_mir.py", "tests/test_std_mir_selection.py"},
            "unexpected source proposal scope")
    for relative, change in proposal["files"].items():
        require(expected[relative] == change["candidate"] == applied["files"][relative], "candidate proposal mismatch")
        path = PROPOSAL / "candidate" / relative
        p = proof(path)
        require({k: p[k] for k in ("bytes", "sha256")} == expected[relative], "candidate proposal copy changed")
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
        test_arm = arm
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
                fixture_scope="private synthetic tool inventories, compilation mocked; no actual Cargo/compiler/VM processes")


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
    require(all(digest != "UNBOUND" for digest in FIXED.values()), "C13 unit source/plan/apply bindings remain UNBOUND")
    require(sys.version_info[:3] == (3, 14, 7) and sys.implementation.name == "cpython"
            and Path(sys.executable).resolve() == PYTHON.resolve()
            and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
            "pinned isolated no-bytecode Python3.14.7 required")
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
            descriptor = json.loads(SOURCE.read_bytes())
            write("test-inventory.json", inventory)
            write("inputs.json", dict(bindings=before, tests=TESTS, expected_tests=EXPECTED_TESTS,
                work_processes=1, memory_processes=1,
                controller_pid=os.getpid(), controller_parent_pid=os.getppid(),
                lock_identity=[identity_before.st_dev, identity_before.st_ino],
                resource_scope="candidate-only synthetic Python tests; 16 GiB/30%; no Rust/std/tool build",
                log_limit="1 MiB bounded reader per stream, ordinary file logs; not hard disk cap"))
            cache = OUT / "pycache"
            cache.mkdir(mode=0o700)
            label = "candidate-selection"
            temporary = OUT / (label + "-tmp")
            temporary.mkdir(mode=0o700)
            env = dict(environment, TMPDIR=str(temporary))
            gate = admission(label, env)
            report_path = OUT / (label + "-tests.json")
            require(not list(cache.iterdir()), "private unit cache changed")
            command = [PYTHON, "-I", "-S", "-B", "-X", "pycache_prefix=" + str(cache), DRIVER, label, report_path]
            receipt = run_child(label, command, env, gate)
            stderr = (OUT / (label + ".stderr")).read_text()
            found = re.findall(r"(?m)^Ran (\d+) tests? in [^\n]+$", stderr)
            successful = re.findall(r"(?m)^test_.* \.\.\. ok$", stderr)
            require(found == ["21"] and len(successful) == 21 and re.search(r"(?m)^OK\s*\Z", stderr) is not None,
                    "unexpected unittest count/result or skipped/non-success test")
            report_proof = proof(report_path, MIB)
            report = json.loads(report_path.read_bytes())
            ids = sorted(i for row in inventory["modules"] for i in row["expected_ids"])
            source = descriptor["arms"]["candidate"]
            root = Path(source["root"])
            require(report["status"] == "passed" and report["arm"] == "candidate" and report["label"] == label
                    and report["tests_run"] == 21 and report["discovered_ids"] == report["successful_ids"] == ids
                    and not any(report[key] for key in ("failures", "errors", "failure_details", "error_details",
                        "skipped", "expected_failures", "unexpected_successes", "actual_process_attempts"))
                    and report["module_path"] == str(root / "scripts/std_mir.py")
                    and report["module_content"] == source["sources"]["scripts/std_mir.py"]
                    and report["canonical_module_object_preserved"] is True
                    and report["manifest_sha256"] == SOURCE_SHA
                    and report["private_tmpdir"] == str(temporary) and report["pycache_prefix"] == str(cache)
                    and report["cache_empty"] is True and not list(cache.iterdir())
                    and report["python"]["version_info"][:3] == [3, 14, 7]
                    and report["python"]["implementation"] == "cpython"
                    and Path(report["python"]["executable"]).resolve() == PYTHON.resolve(), "unit report mismatch")
            expected_test_sources = {row["filename"]: dict(path=row["path"],
                content=source["sources"]["tests/" + row["filename"]]) for row in inventory["modules"]}
            require(report["test_sources"] == expected_test_sources, "reported test source differs")
            for name, observed in report["project_modules"].items():
                path = Path(observed["path"])
                require(path.is_relative_to(root) and observed["content"] == source["sources"].get(str(path.relative_to(root))),
                        "driver imported a different project source: " + name)
            for name in ("std_mir", "interpreter", "custom_compiler", "custom_cargo", "build_custom_tools", "test_custom_compiler"):
                folder = "tests" if name.startswith("test_") else "scripts"
                require(report["project_modules"][name]["path"] == str(root / folder / (name + ".py")),
                        "required canonical import missing: " + name)
            for name, observed in report["runtime_modules"].items():
                expected = descriptor["runtime"]["files"].get(observed["path"])
                require(expected is not None and observed["content"] == {k: expected[k] for k in ("bytes", "sha256")},
                        "unbound driver runtime dependency: " + name)
            tests.append(dict(label=label, arm="candidate", patterns=[row["filename"] for row in inventory["modules"]],
                              passed=21, failures=0, ignored=0, child_pid=receipt["pid"], report=report, report_proof=report_proof))
            require(len(CHILDREN) == 2 and [c["label"] for c in CHILDREN] == [label + "-memory", label]
                    and all(c["returncode"] == 0 and c["error"] is None for c in CHILDREN), "incomplete correctness panel")
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
                      scope="21 exact candidate-only Python correctness tests:8 selection routing,6 custom compiler launcher,7 custom Cargo. Private synthetic fixtures and mocked tool work; no real subprocess inside units or performance claim")
        write("result.json", result)
        print(json.dumps(dict(status=result["status"], passed_tests=result["passed_tests"], error=error,
                              result=str(OUT / "result.json"))), flush=True)
        return 0 if error is None else 1
    finally:
        os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main())

