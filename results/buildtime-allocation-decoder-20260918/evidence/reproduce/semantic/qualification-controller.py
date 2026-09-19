#!/usr/bin/env python3
"""Fixed semantic qualification only; no performance timings or project imports."""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time

PACKET = Path("/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-probe")
OUT = PACKET / "qualification-01"
LOCK = Path("/Users/danluu/dev/rust-interp/.work/benchmark.lock")
BINDINGS = PACKET / "qualification-bindings.json"
BINDINGS_SHA = "5d95b0186647e0d6d1ed01610270b525f6f7397b143fa0567d07e6b8e40521a7"
PLAN = PACKET / "decision-plan.json"
PLAN_SHA = "4843e329a9f134fb0f4d7a0473509176f23d54bb7f7b2fa6a1bd875a42d12917"
QUALIFICATION = PACKET / "unit-screen-02/result.json"
QUALIFICATION_SHA = "e7db839bee8e417288538ad92b06389001a8442ffe62dce182da67cd5e7e51d0"
PYTHON = Path("/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14")
CACHE = OUT / "pycache"
GIB, MIB, FLOOR = 1024**3, 1024**2, 16*1024**3
CHILDREN = []



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


def verify_inputs(descriptor):
    recorded = {p: verify_expected(Path(p), e) for p,e in descriptor["fixed_files"].items()}
    recorded.update({p: verify_expected(Path(p),e) for p,e in descriptor["real_sources"].items()})
    for arm,root in descriptor["roots"].items():
        root = Path(root)
        require(root.resolve() == root, "source root indirect")
        expected = descriptor["sources"][arm]
        names = {str(p.relative_to(root)) for directory in ("scripts","tests") for p in (root/directory).glob("*.py")}
        require(names == set(expected), "project inventory changed")
        recorded.update({str(root/p):verify_expected(root/p,e) for p,e in expected.items()})
    require(proof(BINDINGS)["sha256"] == BINDINGS_SHA and proof(PLAN)["sha256"] == PLAN_SHA
            and proof(QUALIFICATION)["sha256"] == QUALIFICATION_SHA, "descriptor/plan/qualification changed")
    return recorded


def real_snapshot(fixtures):
    result = {}
    for name, expected in fixtures.items():
        directory = OUT / "real-fixtures" / name
        require(directory.resolve() == directory and not directory.lstat().st_mode & 0o222, "real fixture directory changed")
        result[str(directory)] = dict(stamp=stamp(directory.lstat()))
        require({p.name for p in directory.iterdir()} == {"program.rbc","program.rbc.allocations.jsonl"}, "real directory inventory changed")
        for key in ("artifact_path","path"):
            path = Path(expected[key])
            require(path.parent == directory and not path.lstat().st_mode & 0o222, "wrong/writable real file")
            result[str(path)] = proof(path)
    parent = OUT / "real-fixtures"
    require({p.name for p in parent.iterdir()} == set(fixtures)
            and parent.resolve() == parent and not parent.lstat().st_mode & 0o222, "real root changed")
    result[str(parent)] = dict(stamp=stamp(parent.lstat()))
    result[str(OUT/"fixtures.json")] = proof(OUT/"fixtures.json")
    return result


def loaded_sources(reports, descriptor):
    paths = {Path(x["file"]) for r in reports for x in r["modules"].values()}
    require(len(paths) <= 384, "loaded file count bound")
    project = {str(Path(root)/p) for arm,root in descriptor["roots"].items() for p in descriptor["sources"][arm]}
    result,total = {},0
    for path in sorted(paths):
        require(str(path) in project or str(path) in descriptor["fixed_files"]
                or path.resolve().is_relative_to(Path(descriptor["stdlib_root"]).resolve()), "unexpected loaded dependency")
        item = proof(path)
        total += item["bytes"]
        require(total <= 64*MIB, "loaded source size bound")
        result[str(path)] = item
    return result


def recursion_rows(path, scanner, limit):
    before = proof(path)
    require(before["bytes"] <= 16*MIB, "recursion log bound")
    expected = []
    for shape in ("arrays","objects","alternating-array-object"):
        expected += [("depth",shape,d,0) for d in range(limit+9)]
    for shape in ("first-record-BOM","whitespace-BOM"):
        expected += [("caller_bom",shape,d,d) for d in range(limit+9)]
    for shape in ("arrays","objects","alternating-array-object"):
        for d in (0,16,64):
            expected += [("hooks",shape+":"+x,d,0) for x in ("duplicate","NaN","Infinity","-Infinity")]
            expected.append(("overflow",shape,d,0))
    bad = count = 0
    with path.open() as stream:
        for index,line in enumerate(stream):
            require(index < len(expected), "extra recursion row")
            r = json.loads(line)
            require((r["category"],r["shape"],r["depth"],r["caller_depth"]) == expected[index]
                    and r["scanner"] == scanner and r["recursion_limit"] == limit
                    and r["order"] == (["baseline","candidate"] if r["depth"]%2==0 else ["candidate","baseline"]),
                    "recursion row schedule differs")
            bad += not (r["outcomes_equal"] and r["expectation_passed"] and r["shallow_after_passed"])
            count += 1
    require(count == len(expected) and proof(path) == before, "recursion log incomplete/changed")
    return dict(rows=count,mismatches=bad,proof=before)


def main():
    require(sys.argv[1:] == ["--execute-frozen-semantic-qualification"], "explicit execution flag required")
    require(QUALIFICATION_SHA != "UNBOUND", "successful 52-test qualification remains UNBOUND")
    require(sys.platform == "darwin" and sys.version_info[:2] == (3,14)
            and Path(sys.executable).resolve() == PYTHON.resolve(), "pinned Python required")
    require(proof(BINDINGS)["sha256"] == BINDINGS_SHA and proof(PLAN)["sha256"] == PLAN_SHA, "changed descriptor/decision")
    descriptor,plan = json.loads(BINDINGS.read_bytes()),json.loads(PLAN.read_bytes())
    require(descriptor["roots"] == {"baseline":plan["baseline_root"],"candidate":plan["candidate_root"]}
            and descriptor["base_commit"] == plan["base_commit"], "plan/source mismatch")
    unit = json.loads(QUALIFICATION.read_bytes())
    require(proof(QUALIFICATION)["sha256"] == QUALIFICATION_SHA and unit["status"] == "passed"
            and unit["error"] is None and unit["post_binding_error"] is None
            and unit["expected_tests"] == unit["passed_tests"] == 52 and len(unit["tests"]) == 4
            and len(unit["children"]) == 8 and unit["bindings"] == unit["bindings_after"]
            and all(r["returncode"] == 0 and r["error"] is None for r in unit["children"])
            and sorted(r["passed"] for r in unit["tests"]) == [7,7,19,19]
            and all(r["failures"] == r["ignored"] == 0 for r in unit["tests"]), "complete bound 52-test result required")
    for arm,root in descriptor["roots"].items():
        for relative,expected in descriptor["sources"][arm].items():
            item = unit["bindings"][str(Path(root)/relative)]
            require({k:item[k] for k in ("bytes","sha256")} == expected, "unit/source binding mismatch")
    before = verify_inputs(descriptor)
    require(PACKET.resolve() == PACKET and not OUT.exists() and not OUT.is_symlink() and free_bytes()>FLOOR, "fresh owned output required")
    fd = os.open(LOCK,os.O_RDWR|os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode), "invalid lock")
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require((info.st_dev,info.st_ino)==(LOCK.lstat().st_dev,LOCK.lstat().st_ino), "lock inode changed")
        require(free_bytes()>FLOOR and not OUT.exists(), "admission/output changed")
        OUT.mkdir(mode=0o700)
        reports,inputs,recursion,artifacts = [],[],[],[]
        frozen_real = fixtures = None
        error = post_error = None
        checks = {}
        controller = proof(Path(__file__).resolve())
        try:
            before = verify_inputs(descriptor)
            for name,value in (("inputs-before.json",before),("decision-plan.json",plan),
                               ("qualification-bindings.json",descriptor),("unit-qualification.json",unit),("controller.json",controller)):
                write(name,value)
            CACHE.mkdir(mode=0o700)
            (OUT/"tmp").mkdir(mode=0o700)
            env=dict(HOME="/Users/danluu",PATH="/usr/bin:/bin",LANG="C",LC_ALL="C",
                     PYTHONNOUSERSITE="1",TMPDIR=str(OUT/"tmp"),PYTHONPYCACHEPREFIX=str(CACHE))
            tasks=[("prepare","qualification-fixture-prep.py",dict(fixtures_root=str(OUT/"real-fixtures"),
                fixture_descriptor=str(OUT/"fixtures.json"),provenance=descriptor["provenance"]))]
            for arm in ("baseline","candidate"):
                tasks.append(("transport-"+arm,"qualification-transport.py",dict(arm=arm,source_root=descriptor["roots"][arm],
                    synthetic_root=str(OUT/"synthetic"),baseline_report=str(OUT/"transport-baseline-report.json"),
                    fixture_descriptor=str(OUT/"fixtures.json"),report_path=str(OUT/("transport-"+arm+"-report.json")),
                    original_transport_sha256=descriptor["fixed_files"][descriptor["original_transport"]]["sha256"])))
            for scanner in ("installed-C","stdlib-py_make_scanner"):
                for limit in (200,1000):
                    label="recursion-"+scanner+"-"+str(limit)
                    tasks.append((label,"qualification-recursion.py",dict(roots=descriptor["roots"],scanner=scanner,limit=limit,
                                                                         rows_path=str(OUT/(label+".jsonl")))))
            write("schedule.json",[dict(label=l,driver=d,parameters=c) for l,d,c in tasks])
            for label,driver,parameters in tasks:
                require(verify_inputs(descriptor)==before, "source/provenance changed")
                require(all(proof(Path(p["path"]))==p for p in artifacts), "retained evidence changed")
                if frozen_real is not None:
                    require(real_snapshot(fixtures)==frozen_real, "real fixture changed before child")
                config=dict(parameters,output_root=str(OUT),pycache_prefix=str(CACHE))
                write(label+"-input.json",config)
                inputs.append(proof(OUT/(label+"-input.json")))
                gate=admission(label,env)
                receipt=child(label,[str(PYTHON),"-I","-S","-B","-X","pycache_prefix="+str(CACHE),
                                     str(PACKET/driver),str(OUT/(label+"-input.json"))],env,gate)
                require(not (OUT/(label+".stderr")).read_bytes(), "qualification stderr")
                report=json.loads((OUT/(label+".stdout")).read_bytes())
                require(report["status"] in ("PASS","FAIL"), "missing terminal driver status")
                reports.append(report)
                require(not list(CACHE.iterdir()), "qualification changed private bytecode cache")
                if label=="prepare":
                    require(report["status"]=="PASS" and len(report["copies"])==8, "fixture copying failed")
                    prepared=json.loads((OUT/"fixtures.json").read_bytes())
                    require(prepared==dict(fixtures=report["fixtures"],copies=report["copies"]), "fixture descriptor differs")
                    fixtures=report["fixtures"]
                    frozen_real=real_snapshot(fixtures)
                    write("real-fixtures-before.json",frozen_real)
                    checks["eight_real_copies"]=True
                elif label.startswith("transport"):
                    require(report["status"]=="PASS" and len(report["real_traces"])==4
                            and len(report["rejections"])==33 and report["exact_byte_and_event_bounds_passed"], "transport incomplete")
                    require(json.loads(Path(parameters["report_path"]).read_bytes())==report, "transport report/stdout differs")
                    artifacts.append(proof(Path(parameters["report_path"])))
                    checks[label]=True
                    if label=="transport-candidate":
                        baseline=reports[-2]
                        checks["exact_transport_errors"]=report["rejections"]==baseline["rejections"]
                        checks["exact_real_api_receipts"]=report["real_traces"]==baseline["real_traces"]
                else:
                    audit=recursion_rows(Path(report["rows_path"]),parameters["scanner"],parameters["limit"])
                    require(audit["mismatches"]==report["mismatches"] and report["scanner_restored"]
                            and report["recursion_limit_restored"], "recursion report/log or restoration differs")
                    recursion.append(dict(label=label,report=report,audit=audit))
                    artifacts.append(audit["proof"])
                    checks[label]=report["status"]=="PASS" and not audit["mismatches"]
                if frozen_real is not None:
                    require(real_snapshot(fixtures)==frozen_real, "real fixture changed after child")
            require(len(reports)==7 and len(CHILDREN)==14 and len(recursion)==4, "qualification schedule incomplete")
            require(sum(r["report"]["counts"]["depth"] for r in recursion)==7308
                    and sum(r["report"]["counts"]["caller_bom"] for r in recursion)==4872, "dense pair counts differ")
            write("loaded-sources.json",loaded_sources(reports,descriptor))
        except BaseException as caught:
            error=repr(caught)
        finally:
            try:
                require(verify_inputs(descriptor)==before and proof(Path(__file__).resolve())==controller, "final inputs/controller changed")
                require(all(proof(Path(p["path"]))==p for p in inputs), "child descriptor changed")
                require(all(proof(Path(p["path"]))==p for p in artifacts), "retained evidence changed")
                if frozen_real is not None:
                    require(real_snapshot(fixtures)==frozen_real, "final real fixture changed")
                    write("real-fixtures-after.json",real_snapshot(fixtures))
                write("inputs-after.json",verify_inputs(descriptor))
            except BaseException as caught:
                post_error=repr(caught)
        completed=error is None and post_error is None and len(reports)==7 and len(CHILDREN)==14
        result=dict(status="PASS" if completed and all(checks.values()) else "FAIL",error=error,post_binding_error=post_error,
            completed=completed,checks=checks,children=CHILDREN,reports=reports,recursion=recursion,
            decision_sha256=PLAN_SHA,bindings_sha256=BINDINGS_SHA,unit_qualification_sha256=QUALIFICATION_SHA,
            scope="finite semantic parity only; no timing or adoption evidence")
        write("result.json",result)
        print(json.dumps({k:result[k] for k in ("status","completed","error","post_binding_error","checks")}),flush=True)
        return 0 if result["status"]=="PASS" else 1
    finally:
        os.close(fd)


if __name__=="__main__":
    raise SystemExit(main())
