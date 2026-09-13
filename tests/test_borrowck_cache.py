"""Opt-in real-rustc correctness tests; the caller owns the shared test lock."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "borrowck-cache"
PREFIX = "rust-interp-borrowck-cache: "
COUNTERS = ("provider_calls", "green_candidates", "fingerprint_matches", "reused",
            "verified", "fingerprint_misses")
PINNED_RUSTC = (Path.home() / ".rustup/toolchains/"
                "nightly-2026-09-08-aarch64-apple-darwin/bin/rustc")


@unittest.skipUnless(os.environ.get("RUST_INTERP_TEST_EXPORTER"),
                     "set RUST_INTERP_TEST_EXPORTER to run compiler correctness tests")
class BorrowckCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exporter = Path(os.environ["RUST_INTERP_TEST_EXPORTER"]).resolve(strict=True)
        cls.rustc = Path(os.environ.get("RUST_INTERP_TEST_RUSTC", PINNED_RUSTC)).resolve(strict=True)
        supplied_vm = os.environ.get("RUST_INTERP_TEST_VM")
        cls.vm = Path(supplied_vm).resolve(strict=True) if supplied_vm else None
        cls.base_env = {key: value for key, value in os.environ.items()
                        if not key.startswith(("RUST_INTERP_", "CARGO_PROFILE_"))
                        and key not in ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC",
                                        "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER",
                                        "CARGO_INCREMENTAL", "CARGO_TARGET_DIR")}

    def setUp(self):
        retained = os.environ.get("RUST_INTERP_TEST_ARTIFACT_DIR")
        if retained:
            base = Path(retained).resolve()
            base.mkdir(parents=True, exist_ok=True)
            self.work = Path(tempfile.mkdtemp(prefix=self._testMethodName + "-", dir=base))
            print("borrowck correctness artifacts:", self.work, flush=True)
        else:
            temporary = tempfile.TemporaryDirectory(prefix="rust-interp-borrowck-correctness-")
            self.addCleanup(temporary.cleanup)
            self.work = Path(temporary.name)

    def invoke(self, command, env=None):
        result = subprocess.run([str(arg) for arg in command], cwd=self.work,
                                env=env or self.base_env, capture_output=True, text=True)
        with (self.work / "commands.jsonl").open("a") as output:
            output.write(json.dumps({"command": [str(arg) for arg in command],
                                     "mode": (env or {}).get("RUST_INTERP_BORROWCK_CACHE"),
                                     "returncode": result.returncode,
                                     "stdout": result.stdout, "stderr": result.stderr}) + "\n")
        return result

    def compile(self, source, mode="reuse", native=False, incremental=True, extra=(),
                name="fixture", source_path=None, output_path=None, crate_type="bin",
                history=None, env_overrides=None):
        source_path = source_path or self.work / (name + ".rs")
        source_path.write_text(source)
        flavor = history or ("native" if native else "custom")
        output_path = output_path or self.work / (name + "-" + flavor)
        arguments = ["--crate-name", name, "--edition=2024", "--crate-type", crate_type,
                     "-Copt-level=0", "-Cdebuginfo=0", "--error-format=json",
                     "-o", output_path]
        if incremental:
            arguments += ["-C", "incremental=" + str(self.work / (name + "-" + flavor + "-incr"))]
        arguments += [*extra, source_path]
        env = dict(self.base_env)
        if native:
            command = [self.rustc, *arguments]
        else:
            env["RUST_INTERP_BORROWCK_CACHE"] = mode
            command = [self.exporter, self.rustc, *arguments]
        if env_overrides:
            env.update(env_overrides)
        return self.invoke(command, env), output_path

    def report(self, result, mode):
        reports = [json.loads(line[len(PREFIX):]) for line in result.stderr.splitlines()
                   if line.startswith(PREFIX)]
        self.assertEqual(len(reports), 1, result.stderr)
        report = reports[0]
        self.assertEqual(report["mode"], mode)
        for field in COUNTERS:
            self.assertIs(type(report[field]), int, (field, report))
            self.assertGreaterEqual(report[field], 0, report)
        self.assertIn("disabled_reason", report)
        return report

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_output(self, executable, expected):
        result = self.invoke([executable])
        self.assert_success(result)
        self.assertEqual(result.stdout, expected + "\n", result.stderr)

    @staticmethod
    def diagnostics(result):
        def without_rendering(value):
            if isinstance(value, dict):
                return {key: without_rendering(item) for key, item in value.items()
                        if key != "rendered"}
            if isinstance(value, list):
                return [without_rendering(item) for item in value]
            return value

        diagnostics = []
        for line in result.stderr.splitlines():
            if not line.startswith("{"):
                continue
            value = json.loads(line)
            if value.get("$message_type") == "diagnostic":
                code = value.get("code")
                diagnostics.append((value["level"], code.get("code") if code else None,
                                    value["message"], without_rendering(value.get("spans", [])),
                                    without_rendering(value.get("children", []))))
        return diagnostics

    def native_matches(self, source, custom, expected=None, **kwargs):
        native, executable = self.compile(source, native=True, **kwargs)
        self.assertEqual(custom.returncode, native.returncode,
                         "custom:\n" + custom.stderr + "\nnative:\n" + native.stderr)
        self.assertEqual(self.diagnostics(custom), self.diagnostics(native))
        if expected is not None:
            self.assert_success(native)
            self.assert_output(executable, expected)

    def test_cached_unchanged_bodies_need_no_borrowcheck_value(self):
        original = (FIXTURES / "basic.rs").read_text()
        for mode in ("verify", "reuse"):
            for value in (3, 7):
                with self.subTest(mode=mode, value=value):
                    source = original.replace("3 // changed body", str(value) + " // changed body")
                    result, executable = self.compile(source, mode=mode, name="body_" + mode)
                    self.assert_success(result)
                    report = self.report(result, mode)
                    self.assertFalse(report["disabled_reason"], report)
                    if value == 3:
                        self.assertGreater(report["provider_calls"], 0, report)
                        self.assertEqual(report["reused"], 0, report)
                    else:
                        # Rustc reloads unchanged optimized MIR from its own
                        # cache. Only the edited body needs its provider.
                        self.assertEqual(report["provider_calls"], 1, report)
                        self.assertEqual(report["green_candidates"], 0, report)
                        self.assertEqual(report["verified"], 0, report)
                        self.assertEqual(report["reused"], 0, report)
                    expected = str(value) + ":5:17"
                    self.assert_output(executable, expected)
                    self.native_matches(source, result, expected, name="body_" + mode)

    def test_opaque_results_and_disabled_intervening_compilation(self):
        original = (FIXTURES / "basic.rs").read_text()
        opaque = original.replace("fn opaque_value() -> u32", "fn opaque_value() -> impl std::fmt::Display")
        states = [(original, "reuse", 3), (opaque, "off", 7),
                  (opaque, "reuse", 9), (opaque, "verify", 11)]
        for source, mode, value in states:
            with self.subTest(mode=mode, value=value):
                source = source.replace("3 // changed body", str(value) + " // changed body")
                result, executable = self.compile(source, mode=mode)
                self.assert_success(result)
                if mode != "off":
                    report = self.report(result, mode)
                    if value in (9, 11):
                        self.assertEqual(report["provider_calls"], 1, report)
                        self.assertEqual(report["green_candidates"], 0, report)
                        self.assertEqual(report["reused"], 0, report)
                        self.assertEqual(report["verified"], 0, report)
                expected = str(value) + ":5:17"
                self.assert_output(executable, expected)
                self.native_matches(source, result, expected)

    def test_uncalled_errors_are_rejected_and_restoration_is_current(self):
        original = (FIXTURES / "basic.rs").read_text()
        initial, _ = self.compile(original)
        self.assert_success(initial)
        errors = [("E0308", '\nfn uncalled_type_error() -> u32 { "wrong" }\n'),
                  ("E0515", "\nfn uncalled_borrow_error() -> &'static u32 { let value = 3; &value }\n")]
        for code, addition in errors:
            with self.subTest(code=code):
                source = original + addition
                result, _ = self.compile(source)
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertIn(code, [row[1] for row in self.diagnostics(result)], result.stderr)
                self.native_matches(source, result)
        restored = original.replace("3 // changed body", "19 // changed body")
        result, executable = self.compile(restored)
        self.assert_success(result)
        self.assert_output(executable, "19:5:17")

    def test_warnings_and_lint_expectations_are_preserved(self):
        original = (FIXTURES / "basic.rs").read_text()
        extra = ("\n#[warn(unused_variables)]\nfn warning() { let warning_token = 7; }\n"
                 "#[deny(unfulfilled_lint_expectations)]\n#[expect(unused_variables)]\n"
                 "fn expectation() -> u32 { let expected_unused = 7; 0 }\n"
                 "#[warn(unused_mut)]\nfn mut_warning() -> u32 { let mut mut_warning_token = 7; mut_warning_token }\n"
                 "#[deny(unfulfilled_lint_expectations)]\n#[expect(unused_mut)]\n"
                 "fn mut_expectation() -> u32 { let mut mut_expected_unused = 7; mut_expected_unused }\n")
        for value in (3, 7):
            source = original.replace("3 // changed body", str(value) + " // changed body") + extra
            result, _ = self.compile(source)
            self.assert_success(result)
            self.assertIn("unused_variables", [row[1] for row in self.diagnostics(result)])
            self.assertIn("unused_mut", [row[1] for row in self.diagnostics(result)])
            self.native_matches(source, result)
        for before, after in [("let expected_unused = 7; 0", "let expected_unused = 7; expected_unused"),
                              ("let mut mut_expected_unused = 7; mut_expected_unused",
                               "let mut mut_expected_unused = 7; mut_expected_unused += 1; mut_expected_unused")]:
            source = original + extra.replace(before, after)
            result, _ = self.compile(source)
            self.assertNotEqual(result.returncode, 0, result.stderr)
            self.assertIn("unfulfilled_lint_expectations", [row[1] for row in self.diagnostics(result)])
            self.native_matches(source, result)

    def test_metadata_only_library_uses_same_compiler_checks(self):
        original = (FIXTURES / "basic.rs").read_text()
        flags = ("--emit=metadata", "-Zalways-encode-mir=yes")
        for mode in ("verify", "reuse"):
            for value in (3, 7):
                with self.subTest(mode=mode, value=value):
                    source = original.replace("3 // changed body", str(value) + " // changed body")
                    name = "metadata_" + mode
                    result, metadata = self.compile(source, mode=mode, crate_type="rlib", extra=flags,
                                                    name=name, output_path=self.work / ("lib" + name + ".rmeta"))
                    self.assert_success(result)
                    self.assertGreater(metadata.stat().st_size, 0)
                    report = self.report(result, mode)
                    self.assertFalse(report["disabled_reason"], report)
                    if value == 7:
                        self.assertEqual(report["provider_calls"], 1, report)
                        self.assertEqual(report["green_candidates"], 0, report)
                        self.assertEqual(report["reused"], 0, report)
                        self.assertEqual(report["verified"], 0, report)
                    self.native_matches(source, result, crate_type="rlib", extra=flags, name=name)
                    # Consume the newly emitted metadata, rather than merely checking
                    # that a path was left behind by a previous successful command.
                    consumer = ("pub fn checked() -> u32 { " + name + "::changing_value() + "
                                + name + "::unchanged(2) }\n")
                    checked, _ = self.compile(consumer, native=True, crate_type="rlib",
                                              name="read_" + name,
                                              extra=("--emit=metadata", "--extern", name + "=" + str(metadata)))
                    self.assert_success(checked)

    def test_newly_reachable_bodies_reconstruct_only_empty_results(self):
        original = (FIXTURES / "newly_reachable.rs").read_text()
        # Keep compiler-side incremental hash verification enabled throughout
        # each history, including the off-mode and native controls.
        flags = ("-Zincremental-verify-ich=yes",)
        opaque = original.replace("fn old_opaque() -> u32",
                                  "fn old_opaque() -> impl PartialEq<u32>")
        reachable = opaque.replace("3 // changed body", "7 // changed body").replace(
            "let sum = changing_value(); // selected calls",
            "assert!(old_opaque() == 17u32);\n"
            "    let sum = changing_value() + old_ordinary(2) + old_warning() + old_expectation();")
        for mode in ("verify", "reuse"):
            name = "reachable_" + mode
            for source, step_mode, expected in [(original, mode, "3"), (opaque, "off", "3"),
                                                (reachable, mode, "30")]:
                with self.subTest(mode=mode, expected=expected, step_mode=step_mode):
                    result, executable = self.compile(source, mode=step_mode, name=name, extra=flags)
                    self.assert_success(result)
                    self.assert_output(executable, expected)
                    self.native_matches(source, result, expected, name=name, extra=flags)
                    self.assertIn("unused_mut", [row[1] for row in self.diagnostics(result)])
                    if step_mode != "off":
                        report = self.report(result, step_mode)
                        if expected == "30":
                            # These bodies were checked while unreachable, but
                            # had no optimized MIR to reload. Their first value
                            # demands now reach green borrow-check queries.
                            self.assertGreater(report["fingerprint_misses"], 0, report)
                            self.assertGreater(report["reused" if mode == "reuse" else "verified"], 0, report)
                            self.assertGreaterEqual(report["green_candidates"], 4, report)

    def test_selected_export_cached_and_inlined_value_demands(self):
        original = (FIXTURES / "test_export.rs").read_text()
        opaque = original.replace("fn opaque_value() -> u32",
                                  "fn opaque_value() -> impl PartialEq<u32>")
        states = [(original, "reuse", 3), (opaque, "off", 7),
                  (opaque, "reuse", 9), (opaque, "verify", 11)]
        for profile, optimization in [("cached", ()), ("mir3", ("-Zmir-opt-level=3",))]:
            name = "selected_export_" + profile
            flags = ("--test", "--emit=metadata", "-Zalways-encode-mir=yes", *optimization)
            bytecode = self.work / (profile + ".rbc")
            control_bytecode = self.work / (profile + "-control.rbc")
            for source, mode, value in states:
                with self.subTest(profile=profile, mode=mode, value=value):
                    source = source.replace("3 // changed body", str(value) + " // changed body")
                    env = {"RUST_INTERP_EXPORT_CRATE": name, "RUST_INTERP_EXPORT_TEST": "1",
                           "RUST_INTERP_ENTRY": "selected", "RUST_INTERP_OUTPUT": str(bytecode)}
                    result, _ = self.compile(source, mode=mode, name=name, crate_type="lib", extra=flags,
                                              output_path=self.work / (profile + ".rmeta"), env_overrides=env)
                    self.assert_success(result)
                    self.assertGreater(bytecode.stat().st_size, 0)
                    if mode != "off":
                        report = self.report(result, mode)
                        if value in (9, 11):
                            if profile == "mir3":
                                # Changed callee MIR invalidates inlined callers
                                # without changing their borrow-check inputs.
                                self.assertGreater(report["fingerprint_misses"], 0, report)
                                self.assertGreater(report["reused" if mode == "reuse" else "verified"], 0, report)
                            else:
                                self.assertEqual(report["provider_calls"], 1, report)
                                self.assertEqual(report["green_candidates"], 0, report)
                                self.assertEqual(report["reused"], 0, report)
                                self.assertEqual(report["verified"], 0, report)
                    control, _ = self.compile(source, mode="off", name=name, history="full-control",
                                               crate_type="lib", extra=flags,
                                               output_path=self.work / (profile + "-control.rmeta"),
                                               env_overrides=dict(env, RUST_INTERP_OUTPUT=str(control_bytecode)))
                    self.assert_success(control)
                    self.assertEqual(self.diagnostics(result), self.diagnostics(control))
                    self.assertEqual(bytecode.read_bytes(), control_bytecode.read_bytes())
                    native, executable = self.compile(source, native=True, name=name, crate_type="lib",
                                                       extra=("--test", *optimization))
                    self.assert_success(native)
                    self.assertEqual(self.diagnostics(result), self.diagnostics(native))
                    executed = self.invoke([executable, "--exact", "selected", "--test-threads=1"])
                    self.assert_success(executed)
                    self.assertIn("1 passed", executed.stdout)
                    if self.vm:
                        executed = self.invoke([self.vm, "--engine", "interpreter", bytecode])
                        self.assert_success(executed)
                        self.assertEqual(executed.stdout, "0\n")

    def test_no_incremental_and_explicit_mir_dump_use_original_provider(self):
        source = (FIXTURES / "basic.rs").read_text()
        result, executable = self.compile(source, incremental=False, name="without_incremental")
        self.assert_success(result)
        report = self.report(result, "reuse")
        self.assertTrue(report["disabled_reason"], report)
        self.assertEqual(report["reused"], 0, report)
        self.assert_output(executable, "3:5:17")
        dump_dir = self.work / "mir-dump"
        result, executable = self.compile(source, name="with_dump",
                                          extra=("-Zdump-mir=all", "-Zdump-mir-dir=" + str(dump_dir)))
        self.assert_success(result)
        report = self.report(result, "reuse")
        self.assertTrue(report["disabled_reason"], report)
        self.assertEqual(report["reused"], 0, report)
        self.assertTrue(list(dump_dir.glob("*.mir")), "requested MIR dump was not produced")
        self.assert_output(executable, "3:5:17")
        facts_dir = self.work / "nll-facts"
        for name, flags in [("with_polonius", ("-Zpolonius=next",)),
                            ("with_nll_facts", ("-Znll-facts", "-Znll-facts-dir=" + str(facts_dir)))]:
            with self.subTest(flag=name):
                result, executable = self.compile(source, name=name, extra=flags)
                self.assert_success(result)
                report = self.report(result, "reuse")
                self.assertTrue(report["disabled_reason"], report)
                self.assertEqual(report["green_candidates"], 0, report)
                self.assertEqual(report["reused"], 0, report)
                self.assert_output(executable, "3:5:17")
        facts = list(facts_dir.rglob("*.facts"))
        self.assertTrue(facts, "requested NLL facts were not produced")
        self.assertTrue(any(path.stat().st_size for path in facts), "all NLL fact files were empty")
        attrs_source = "#![feature(rustc_attrs)]\n" + source
        result, executable = self.compile(attrs_source, name="with_internal_attributes")
        self.assert_success(result)
        report = self.report(result, "reuse")
        self.assertEqual(report["disabled_reason"], "internal compiler attributes enabled", report)
        self.assertGreater(report["provider_calls"], 0, report)
        self.assertEqual(report["reused"], 0, report)
        self.assert_output(executable, "3:5:17")
        result, executable = self.compile(source, name="with_time_passes", extra=("-Ztime-passes",))
        self.assert_success(result)
        self.report(result, "reuse")
        # Check the requested diagnostic survived the adapter. Do not parse
        # or assess its timing values as performance evidence.
        self.assertTrue(any(line.startswith("time: ") and line.endswith("\ttotal")
                            for line in result.stderr.splitlines()), result.stderr)
        self.assert_output(executable, "3:5:17")

    def test_dependency_edits_preserve_output_and_invalidate_changed_semantics(self):
        original_dep = (FIXTURES / "dependency.rs").read_text()
        consumer = (FIXTURES / "consumer.rs").read_text()
        dep_path = self.work / "dependency.rs"
        dep_output = self.work / "libborrowck_dependency.rlib"
        changed_body = original_dep.replace("5 // changed dependency body", "9 // changed dependency body")
        changed_metadata = changed_body.replace("WIDTH: usize = 2", "WIDTH: usize = 3").replace("13u32", "23u32")
        missing_impl = original_dep.replace("impl Convert for u32", "impl Convert for u64")
        states = [(original_dep, "5:41:2:13:5", None),
                  (changed_body, "9:41:2:13:5", None),
                  (changed_metadata, "9:41:3:23:5", None),
                  (original_dep.replace("pub type Word = u32", "pub type Word = u64"), None, "E0308"),
                  (missing_impl, None, "E0599"),
                  (original_dep, "5:41:2:13:5", None)]
        for index, (dependency, expected, error_code) in enumerate(states):
            with self.subTest(state=index):
                built, _ = self.compile(dependency, native=True, crate_type="rlib",
                                        name="borrowck_dependency", source_path=dep_path,
                                        output_path=dep_output)
                self.assert_success(built)
                extra = ("--extern", "borrowck_dependency=" + str(dep_output))
                result, executable = self.compile(consumer, extra=extra, name="consumer")
                if expected is not None:
                    self.assert_success(result)
                    self.assert_output(executable, expected)
                    report = self.report(result, "reuse")
                    if index == 1:
                        self.assertEqual(report["provider_calls"], 0, report)
                        self.assertEqual(report["green_candidates"], 0, report)
                        self.assertEqual(report["reused"], 0, report)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stderr)
                    self.assertIn(error_code, [row[1] for row in self.diagnostics(result)], result.stderr)
                self.native_matches(consumer, result, expected, extra=extra, name="consumer")


if __name__ == "__main__":
    unittest.main()
