#!/usr/bin/env python3
"""Python-only association correctness: eight frozen modules, 81 source-counted tests."""
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

ROOT = Path("/Users/danluu/dev/rust-interp-launcher-association-20260918")
PACKET = Path("/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/compiler-association-probe")
PROPOSAL = PACKET.parent / "compiler-association-proposal-v2"
OUT = PACKET / "unit-screen-01"
LOCK = Path("/Users/danluu/dev/rust-interp/.work/benchmark.lock")
SOURCE = PACKET / "unit-source-manifest.json"
SOURCE_SHA = "4a714912a69721dbc827e8a5f71bcd77e09e0dbe4f77fdb039919fb00578b9f2"
PYTHON = Path("/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14")
FRAMEWORK = PYTHON.parent.parent / "Python"
FIXED = {
    PYTHON: "87d4df53fd91304be5bac391fb204643c36b7df2023c04a0953bcbc7d4fdf634",
    FRAMEWORK: "b112695af23f5e46d84a7c4ef6057603b70b94aacc32e9d548808c2875759d47",
    SOURCE: SOURCE_SHA,
    PROPOSAL / "source-bindings.json": "5770f3a82f740dfe3fe2f0b4ce1ffac01171b3a1d52692e2f28f86ba9fc339fb",
    PROPOSAL / "candidate.patch": "932e88bde51e4233825d8c0bc8a20076edcb7da94ace1ec2889d289f729dc508",
    PROPOSAL / "README.md": "6732a0690532b0bab40d4ddf9e7bbc0eceac2c2934a3e21615975ea472e907d1",
}
GIB = 1024 ** 3
MIB = 1024 ** 2
FLOOR = 16 * GIB  # Only these tiny synthetic Python tests; Rust builds remain 32 GiB.
TESTS = (("association", "test_compiler_association.py", 3),
         ("custom-compiler", "test_custom_compiler.py", 13),
         ("custom-launcher", "test_custom_compiler_launcher.py", 6),
         ("runtime-tools", "test_runtime_tools.py", 10),
         ("custom-cargo", "test_custom_cargo.py", 7),
         ("std-source-paths", "test_std_mir_source_paths.py", 18),
         ("tools", "test_interpreter_tools.py", 5),
         ("build-metrics", "test_interpreter_build_metrics.py", 19))
EXPECTED_TESTS = sum(count for _, _, count in TESTS)
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
    require(descriptor["root"] == str(ROOT) and
            descriptor["base_commit"] == "2ba2696675cfd275ea9a9ef4c937bc8579f618f2",
            "wrong source descriptor")
    expected = descriptor["sources"]
    actual_paths = {str(p.relative_to(ROOT)) for folder in ("scripts", "tests")
                    for p in (ROOT / folder).glob("*.py")}
    require(len(expected) == 186 and actual_paths == set(expected), "Python source inventory changed")
    for relative, expected_proof in expected.items():
        path = Path(relative)
        require(not path.is_absolute() and ".." not in path.parts, "invalid source path")
        p = proof(ROOT / path)
        require({k: p[k] for k in ("bytes", "sha256")} == expected_proof,
                "project source changed: " + relative)
        files[str(ROOT / path)] = p
    proposal = json.loads((PROPOSAL / "source-bindings.json").read_bytes())
    require(proposal["base_commit"] == descriptor["base_commit"] and len(proposal["files"]) == 6,
            "wrong association proposal")
    for relative, expected_proof in proposal["files"].items():
        require(expected[relative] == expected_proof["candidate"], "source does not match proposal")
        path = PROPOSAL / "source" / relative
        p = proof(path)
        require({k:p[k] for k in ("bytes", "sha256")} == expected_proof["candidate"],
                "candidate proposal copy changed")
        files[str(path)] = p
    return files


def test_inventory():
    """Verify frozen method counts without importing any test or production module."""
    inventory=[]
    for label,filename,expected_count in TESTS:
        tree=ast.parse((ROOT / "tests" / filename).read_text())
        require(not any(isinstance(n,ast.FunctionDef) and n.name=="load_tests" for n in tree.body),
                "unexpected custom unittest loader")
        classes=[]
        for node in tree.body:
            if not isinstance(node,ast.ClassDef): continue
            methods=[n.name for n in node.body if isinstance(n,ast.FunctionDef) and n.name.startswith("test")]
            if not methods: continue
            require(len(node.bases)==1 and isinstance(node.bases[0],ast.Attribute) and
                    isinstance(node.bases[0].value,ast.Name) and node.bases[0].value.id=="unittest" and
                    node.bases[0].attr=="TestCase", "unexpected test inheritance")
            require(len(methods)==len(set(methods)), "duplicate test method")
            classes.append(dict(name=node.name,methods=methods,inherited_test_methods=0))
        require(sum(len(c["methods"]) for c in classes)==expected_count,"frozen test count changed")
        inventory.append(dict(label=label,filename=filename,expected_tests=expected_count,classes=classes))
    # No direct frozen-script inventory assertion exists in the workflow test modules.
    # Record the exact new member statically; do not run the benchmark workflow.
    tree=ast.parse((ROOT / "scripts/bench_e2e_workflow.py").read_text())
    workflow=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="run_workflow"]
    require(len(workflow)==1,"ambiguous workflow function")
    additions=[n for n in workflow[0].body if isinstance(n,ast.AugAssign) and
               isinstance(n.op,ast.Add) and isinstance(n.target,ast.Name) and n.target.id=="script_paths"]
    require(len(additions)==1 and isinstance(additions[0].value,ast.List),"unexpected unconditional workflow input extension")
    wanted=ast.dump(ast.parse("ROOT/'scripts/compiler_association.py'",mode="eval").body,include_attributes=False)
    require(sum(ast.dump(n,include_attributes=False)==wanted for n in additions[0].value.elts)==1,
            "new association module omitted from unconditional frozen workflow inputs")
    return dict(method="static AST only; no test/production module imports",modules=inventory,
                expected_tests=EXPECTED_TESTS,workflow_association_input_present=True,
                bench_tests_added=False,bench_reason="no direct frozen-script inventory assertions in existing workflow tests")


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
            for label, filename, expected in TESTS:
                temporary = OUT / (label + "-tmp")
                temporary.mkdir(mode=0o700)
                env = dict(environment, TMPDIR=str(temporary))
                gate = admission(label, env)
                command = [PYTHON, "-I", "-S", "-B", "-m", "unittest", "discover",
                           "-s", str(ROOT / "tests"), "-p", filename, "-v"]
                receipt = run_child(label, command, env, gate)
                stderr = (OUT / (label + ".stderr")).read_text()
                found = re.findall(r"(?m)^Ran (\d+) tests? in [^\n]+$", stderr)
                successful = re.findall(r"(?m)^test_.* \.\.\. ok$", stderr)
                require(found == [str(expected)] and len(successful) == expected and
                        re.search(r"(?m)^OK\s*\Z", stderr) is not None,
                        "unexpected unittest count/result or skipped/non-success test: " + label)
                tests.append(dict(label=label, pattern=filename, passed=expected,
                                  failures=0, ignored=0, child_pid=receipt["pid"]))
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
                      scope="81 source-counted Python correctness tests across eight modules, exact new association and stock-import guards; no Rust/compiler/Cargo/VM workload or performance claim")
        write("result.json", result)
        print(json.dumps(dict(status=result["status"], passed_tests=result["passed_tests"],
                              error=error, result=str(OUT / "result.json"))), flush=True)
        return 0 if error is None else 1
    finally:
        os.close(fd)


if __name__ == "__main__":
    raise SystemExit(main())
