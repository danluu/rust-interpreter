#!/usr/bin/env python3
"""Candidate-only 21 synthetic selection tests; no actual child process is permitted."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

PACKET = Path("/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-mir-lazy-selection-probe")
MANIFEST = PACKET / "unit-source-manifest.json"
MANIFEST_SHA = "db14ba649b5f51f9533e950e731a0fe3e5ecb4bf33a6403fde6b10e5b0702755"
PYTHON = Path("/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14")


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


def loaded_modules(manifest):
    source = manifest["arms"]["candidate"]
    root = Path(source["root"])
    baseline = Path(manifest["baseline_root"])
    runtime = manifest["runtime"]["files"]
    project, dependencies = {}, {}
    for name, module in sorted(sys.modules.items()):
        if module is None:
            continue
        value = vars(module).get("__file__")
        if not isinstance(value, str):
            continue
        path = Path(value).resolve()
        if path == Path(__file__).resolve():
            continue
        require(not path.is_relative_to(baseline), "baseline module imported into candidate suite: " + name)
        observed = content(path)
        if path.is_relative_to(root):
            expected = source["sources"].get(str(path.relative_to(root)))
            require(expected is not None and observed == expected, "unbound candidate import: " + name)
            project[name] = dict(path=str(path), content=observed)
        else:
            expected = runtime.get(str(path))
            require(expected is not None and observed == {k: expected[k] for k in ("bytes", "sha256")},
                    "unbound runtime import: " + name)
            dependencies[name] = dict(path=str(path), content=observed)
    return project, dependencies


def main():
    require(MANIFEST_SHA != "UNBOUND", "C13 unit source manifest is not frozen")
    require(len(sys.argv) == 3 and sys.argv[1] == "candidate-selection", "expected suite label and exclusive report")
    require(sys.version_info[:3] == (3, 14, 7) and sys.implementation.name == "cpython"
            and Path(sys.executable).resolve() == PYTHON.resolve()
            and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
            "pinned isolated no-bytecode Python required")
    label, report_name = sys.argv[1:]
    raw = MANIFEST.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == MANIFEST_SHA, "unit manifest changed")
    manifest = json.loads(raw)
    require(manifest["status"] == "frozen" and manifest["expected_tests"] == 21
            and len(manifest["tests"]) == 3 and set(manifest["arms"]) == {"candidate"}, "wrong unit manifest")
    root = Path(manifest["arms"]["candidate"]["root"])
    report = Path(report_name)
    require(root.resolve() == root and report.parent == PACKET / "unit-screen-01"
            and report.name == label + "-tests.json" and not report.exists() and not report.is_symlink(),
            "wrong source or occupied report destination")
    cache = report.parent / "pycache"
    require(sys.pycache_prefix == str(cache) and cache.resolve() == cache
            and cache.is_dir() and not list(cache.iterdir()), "private bytecode cache must remain empty")
    temporary = report.parent / (label + "-tmp")
    require(os.environ.get("TMPDIR") == str(temporary) and temporary.resolve() == temporary
            and temporary.is_dir() and Path(tempfile.gettempdir()) == temporary,
            "wrong private temporary directory")
    attempts = []
    def reject_process(event, args):
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec",
                     "os.fork", "os.forkpty", "os.spawn"}:
            attempts.append(event)
            raise RuntimeError("synthetic test attempted an actual process: " + event)
    sys.addaudithook(reject_process)
    sources = manifest["arms"]["candidate"]["sources"]
    module_path = root / "scripts/std_mir.py"
    require(content(module_path) == sources["scripts/std_mir.py"], "std_mir source changed before import")
    # Existing selected-tool suites import test_custom_compiler's fixture helpers.
    sys.path.insert(0, str(root / "tests"))
    sys.path.insert(0, str(root / "scripts"))
    std_mir = load("std_mir", module_path)
    modules, test_proofs = [], {}
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for row in manifest["tests"]:
        test_path = Path(row["path"])
        require(row["arm"] == "candidate" and test_path == root / "tests" / row["filename"]
                and content(test_path) == sources["tests/" + row["filename"]], "wrong candidate test source")
        module = load(Path(row["filename"]).stem, test_path)
        require(getattr(module, row["std_alias"]) is std_mir and sys.modules["std_mir"] is std_mir,
                "test imported a different std_mir module")
        sub_suite = loader.loadTestsFromModule(module)
        require(sorted(flatten(sub_suite)) == row["expected_ids"]
                and sub_suite.countTestCases() == row["expected_tests"], "discovered module test IDs differ")
        suite.addTests(sub_suite)
        modules.append((module, row))
        test_proofs[row["filename"]] = dict(path=str(test_path), content=content(test_path))
    ids = sorted(flatten(suite))
    expected_ids = sorted(i for row in manifest["tests"] for i in row["expected_ids"])
    require(not loader.errors and ids == expected_ids and len(ids) == 21, "discovered test names differ")
    before_project, before_dependencies = loaded_modules(manifest)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    require(not list(cache.iterdir()), "synthetic unit test wrote private bytecode")
    project, dependencies = loaded_modules(manifest)
    require(all(project.get(name) == value for name, value in before_project.items())
            and all(dependencies.get(name) == value for name, value in before_dependencies.items()),
            "loaded module changed during tests")
    require(sys.modules["std_mir"] is std_mir and Path(std_mir.__file__).resolve() == module_path
            and content(module_path) == sources["scripts/std_mir.py"], "canonical std_mir changed")
    for module, row in modules:
        require(getattr(module, row["std_alias"]) is std_mir
                and content(Path(row["path"])) == test_proofs[row["filename"]]["content"],
                "canonical test alias or source changed")
    require(all(name in project for name in ("std_mir", "interpreter", "custom_compiler", "custom_cargo",
                                            "build_custom_tools", "test_custom_compiler")),
            "selected-tool suites did not load their actual bound modules")
    passed = (result.wasSuccessful() and not result.skipped and not result.expectedFailures
              and not result.unexpectedSuccesses and not attempts
              and result.testsRun == 21 and sorted(result.successful_ids) == ids)
    record = dict(status="passed" if passed else "failed", arm="candidate", label=label,
        discovered_ids=ids, successful_ids=sorted(result.successful_ids), tests_run=result.testsRun,
        failures=[test.id() for test, _ in result.failures], errors=[test.id() for test, _ in result.errors],
        failure_details=[dict(id=test.id(), traceback=details) for test, details in result.failures],
        error_details=[dict(id=test.id(), traceback=details) for test, details in result.errors],
        skipped=[dict(id=test.id(), reason=why) for test, why in result.skipped],
        expected_failures=[test.id() for test, _ in result.expectedFailures],
        unexpected_successes=[test.id() for test in result.unexpectedSuccesses],
        module_path=str(module_path), module_content=content(module_path), test_sources=test_proofs,
        project_modules=project, runtime_modules=dependencies,
        canonical_module_object_preserved=True, actual_process_attempts=attempts,
        private_tmpdir=str(temporary), pycache_prefix=str(cache), cache_empty=True,
        manifest_sha256=MANIFEST_SHA,
        python=dict(executable=sys.executable, version=sys.version, version_info=list(sys.version_info),
                    implementation=sys.implementation.name))
    with report.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(dict(status=record["status"], label=label, tests_run=result.testsRun,
                          report=str(report))), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
