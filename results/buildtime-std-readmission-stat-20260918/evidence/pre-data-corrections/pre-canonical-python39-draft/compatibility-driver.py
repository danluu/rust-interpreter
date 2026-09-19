#!/usr/bin/env python3
"""Run one source-bound suite with the requested std_mir_readmission already loaded."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

PACKET = Path("/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe")
MANIFEST = PACKET / "unit-source-manifest.json"
MANIFEST_SHA = "8d09306a6b13459ca442059a0aa226ff4c125f7c4eea8b41f54f578121a88378"


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def content(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def load(name, path):
    require(name not in sys.modules, "module already imported: " + name)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "cannot load exact module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    require(Path(module.__file__).resolve() == path, "loaded wrong module: " + name)
    return module


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test.id()


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.successful_ids = []

    def addSuccess(self, test):
        self.successful_ids.append(test.id())
        super().addSuccess(test)


def main():
    require(len(sys.argv) == 3, "expected suite label and exclusive report path")
    label, report_name = sys.argv[1:]
    data = MANIFEST.read_bytes()
    require(hashlib.sha256(data).hexdigest() == MANIFEST_SHA, "unit manifest changed")
    manifest = json.loads(data)
    rows = [row for row in manifest["tests"] if row["label"] == label]
    require(len(rows) == 1, "unknown unit suite")
    row = rows[0]
    root = Path(manifest["arms"][row["arm"]]["root"])
    require(sys.implementation.name == "cpython" and tuple(sys.version_info[:3]) == (3, 9, 6),
            "compatibility child must be actual pinned CPython3.9.6")
    require(str(Path(sys.executable).resolve()) in (
        "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9",
        "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python"),
        "compatibility child loaded another executable")
    report = Path(report_name)
    require(report.parent == PACKET / "compatibility-screen-01" and
            report.name == label + "-tests.json" and not report.exists() and not report.is_symlink(),
            "wrong or occupied report destination")
    module_path = root / "scripts/std_mir_readmission.py"
    test_path = Path(row["path"])
    expected_module = manifest["arms"][row["arm"]]["sources"]["scripts/std_mir_readmission.py"]
    test_arm = "candidate"
    expected_test = manifest["arms"][test_arm]["sources"]["tests/" + row["filename"]]
    require(content(module_path) == expected_module and content(test_path) == expected_test,
            "test or std readmission source changed before import")
    sys.path.insert(0, str(root / "scripts"))
    recovery = load("std_mir_readmission", module_path)
    # Both arms use the candidate test; its import must reuse this canonical production module.
    test_module = load(Path(row["filename"]).stem, test_path)
    require(test_module.recovery is recovery and sys.modules["std_mir_readmission"] is recovery,
            "test imported a different std readmission module")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_module)
    ids = sorted(flatten(suite))
    require(not loader.errors and ids == row["expected_ids"] and len(ids) == row["expected_tests"],
            "discovered test names differ")
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    passed = (result.wasSuccessful() and not result.skipped and not result.expectedFailures and
              not result.unexpectedSuccesses and result.testsRun == row["expected_tests"] and
              sorted(result.successful_ids) == ids)
    require(sys.modules["std_mir_readmission"] is recovery and
            Path(recovery.__file__).resolve() == module_path and
            content(module_path) == expected_module and content(test_path) == expected_test,
            "module source/identity changed during tests")
    record = dict(status="passed" if passed else "failed", arm=row["arm"], label=label,
                  filename=row["filename"], discovered_ids=ids,
                  successful_ids=sorted(result.successful_ids), tests_run=result.testsRun,
                  failures=[test.id() for test, _ in result.failures],
                  errors=[test.id() for test, _ in result.errors],
                  skipped=[dict(id=test.id(), reason=why) for test, why in result.skipped],
                  expected_failures=[test.id() for test, _ in result.expectedFailures],
                  unexpected_successes=[test.id() for test in result.unexpectedSuccesses],
                  module_path=str(module_path), module_content=content(module_path),
                  test_path=str(test_path), test_content=content(test_path),
                  canonical_module_object_preserved=True, manifest_sha256=MANIFEST_SHA,
                  python=dict(executable=sys.executable, version=sys.version,
                              version_info=list(sys.version_info), implementation=sys.implementation.name),
                  single_stat_guard=getattr(recovery, "_SINGLE_STAT_FILES", None))
    with report.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(dict(status=record["status"], label=label, tests_run=result.testsRun,
                          report=str(report))), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
