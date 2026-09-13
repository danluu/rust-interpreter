"""Opt-in Cargo routing smoke; the caller owns the shared correctness-test lock.

Only local fixture packages are built. Command receipts use the artifact directory
and helpers from the direct compiler suite, without inheriting that suite's tests.
"""
import json
import os
from pathlib import Path
import unittest

import test_borrowck_cache as compiler_tests


PACKAGE = "borrowck-cargo-smoke"
CRATE = "borrowck_cargo_smoke"
TOOLCHAIN = "nightly-2026-09-08"


@unittest.skipUnless(os.environ.get("RUST_INTERP_TEST_EXPORTER"),
                     "set RUST_INTERP_TEST_EXPORTER to run Cargo correctness tests")
class BorrowckCacheCargoTests(unittest.TestCase):
    setUp = compiler_tests.BorrowckCacheTests.setUp
    invoke = compiler_tests.BorrowckCacheTests.invoke
    assert_success = compiler_tests.BorrowckCacheTests.assert_success

    @classmethod
    def setUpClass(cls):
        compiler_tests.BorrowckCacheTests.setUpClass.__func__(cls)
        cls.cargo = cls.rustc.with_name("cargo").resolve(strict=True)
        cls.wrapper = cls.exporter.with_name("rust-interp-rustc-wrapper").resolve(strict=True)

    def fixture(self):
        self.package = self.work / "package"
        (self.package / "src").mkdir(parents=True)
        (self.package / "helper/src").mkdir(parents=True)
        (self.package / "Cargo.toml").write_text(
            '[package]\nname = "' + PACKAGE + '"\nversion = "0.0.0"\nedition = "2024"\n'
            '[workspace]\nmembers = ["helper"]\n'
            '[dependencies]\nborrowck-cargo-helper = { path = "helper" }\n'
            '[build-dependencies]\nborrowck-cargo-helper = { path = "helper" }\n')
        (self.package / "helper/Cargo.toml").write_text(
            '[package]\nname = "borrowck-cargo-helper"\nversion = "0.0.0"\nedition = "2024"\n')
        (self.package / "build.rs").write_text(
            'fn main() {\n'
            '    let output = std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap());\n'
            '    let value = borrowck_cargo_helper::host_value();\n'
            '    std::fs::write(output.join("generated.rs"),\n'
            '        format!("pub const BUILD_VALUE: u32 = {value};\\n")).unwrap();\n'
            '    std::fs::write(output.join("host-marker.txt"), value.to_string()).unwrap();\n'
            '    println!("cargo:rerun-if-changed=build.rs");\n'
            '}\n')
        version = self.invoke([self.rustc, "-vV"])
        self.assert_success(version)
        self.host = next(line.removeprefix("host: ") for line in version.stdout.splitlines()
                         if line.startswith("host: "))
        # Exclude user Cargo configuration and target/profile environment inputs.
        self.cargo_env = {key: value for key, value in self.base_env.items()
                          if not key.startswith(("CARGO_", "RUSTDEV_"))}
        self.cargo_env.update(CARGO_HOME=str(self.work / "cargo-home"),
                              CARGO_INCREMENTAL="1", CARGO_TERM_COLOR="never",
                              CARGO_ENCODED_RUSTFLAGS="", RUSTC=str(self.rustc),
                              RUSTDOC=str(self.rustc.with_name("rustdoc")))

    def write_source(self, value, helper, host, invalid=False):
        helper_path = self.package / "helper/src/lib.rs"
        helper_source = (
            'pub fn value() -> u32 { ' + str(helper) + ' }\n'
            'pub fn host_value() -> u32 { ' + str(host) + ' }\n')
        if not helper_path.exists() or helper_path.read_text() != helper_source:
            helper_path.write_text(helper_source)
        source = (
            '#![allow(dead_code)]\n'
            'include!(concat!(env!("OUT_DIR"), "/generated.rs"));\n'
            'pub fn changing_value() -> u32 { ' + str(value) + ' }\n'
            'pub fn entry() -> u32 { changing_value() + BUILD_VALUE + borrowck_cargo_helper::value() }\n'
            '#[test]\nfn selected() {\n'
            '    assert!(entry() - changing_value() == BUILD_VALUE + borrowck_cargo_helper::value());\n'
            '}\n'
            '#[test]\nfn native_current_output() {\n'
            '    let expected: u32 = std::env::var("BORROWCK_SMOKE_EXPECTED").unwrap().parse().unwrap();\n'
            '    assert_eq!(entry(), expected);\n'
            '}\n')
        if invalid:
            source += "fn uncalled_invalid() -> &'static u32 { let local = 1; &local }\n"
        (self.package / "src/lib.rs").write_text(source)
        with (self.work / "source-states.jsonl").open("a") as output:
            output.write(json.dumps({"source": source, "helper_source": helper_source,
                                     "expected": value + helper + host,
                                     "invalid_uncalled_borrow": invalid}) + "\n")

    @staticmethod
    def messages(result):
        return [json.loads(line) for line in result.stdout.splitlines()
                if line.startswith("{")]

    def cargo_command(self, operation, target, rustup=False):
        executable = ["cargo", "+" + TOOLCHAIN] if rustup else [self.cargo]
        return [*executable, operation, "--manifest-path", self.package / "Cargo.toml",
                "--package", PACKAGE, "--lib", "--offline", "--jobs", "2",
                "--target", self.host, "--target-dir", target,
                "--message-format=json-render-diagnostics"]

    def export(self, mode, test_body=False):
        target = self.work / ("target-" + mode)
        bytecode = self.work / (mode + ("-test" if test_body else "-lib") + ".rbc")
        env = dict(self.cargo_env, RUSTC_WRAPPER=str(self.wrapper), RUSTC_WORKSPACE_WRAPPER="",
                   RUST_INTERP_BORROWCK_CACHE=mode, RUST_INTERP_EXPORT_PACKAGE=PACKAGE,
                   RUST_INTERP_EXPORT_CRATE=CRATE, RUST_INTERP_EXPORT_MANIFEST=str(self.package),
                   RUST_INTERP_EXPORT_TEST="1" if test_body else "0",
                   RUST_INTERP_ENTRY="selected" if test_body else "entry",
                   RUST_INTERP_OUTPUT=str(bytecode))
        # Exercise the launcher's ordinary rustup convention in reuse mode.
        # An explicit RUSTC would hide a failure to accept the compiler argument
        # Cargo supplies when the caller leaves compiler selection to rustup.
        rustup = mode == "reuse"
        if rustup:
            env.pop("RUSTC", None)
            env.pop("RUSTDOC", None)
            env["RUSTUP_AUTO_INSTALL"] = "0"
        command = self.cargo_command("check", target, rustup=rustup)
        if rustup:
            # Retain Cargo's actual wrapper/compiler argv in the command receipt.
            command += ["--verbose"]
        if test_body:
            command += ["--profile", "test"]
        with (self.work / "cargo-routing.jsonl").open("a") as output:
            output.write(json.dumps({"mode": mode, "test_body": test_body,
                                     "rustup": rustup, "rustc_env": env.get("RUSTC"),
                                     "command": [str(arg) for arg in command]}) + "\n")
        result = self.invoke(command, env)
        return result, bytecode, target

    def reports(self, result, mode):
        reports = [json.loads(line[len(compiler_tests.PREFIX):])
                   for line in result.stderr.splitlines() if line.startswith(compiler_tests.PREFIX)]
        self.assertTrue(reports, result.stderr)
        for report in reports:
            self.assertEqual(report["mode"], mode, report)
            for field in compiler_tests.COUNTERS:
                self.assertIs(type(report[field]), int, (field, report))
                self.assertGreaterEqual(report[field], 0, report)
        # Some native units may have caching disabled. At least the selected
        # incremental exporter must actually have installed its provider.
        self.assertTrue(any(report["provider_wrapped"] and not report["disabled_reason"]
                            for report in reports), reports)
        return reports

    def native(self, expected):
        env = dict(self.cargo_env, BORROWCK_SMOKE_EXPECTED=str(expected))
        return self.invoke(self.cargo_command("test", self.work / "target-native")
                           + ["--", "--test-threads=1"], env)

    def assert_export_artifact(self, result, bytecode, test_body=False):
        selected = [message for message in self.messages(result)
                    if message.get("reason") == "compiler-artifact"
                    and message["target"]["name"] == CRATE
                    and bool(message["profile"]["test"]) == test_body]
        self.assertEqual(len(selected), 1, result.stdout)
        sidecars = [Path(filename + ".rbc") for filename in selected[0]["filenames"]
                    if Path(filename + ".rbc").is_file()]
        self.assertEqual(len(sidecars), 1, selected)
        self.assertEqual(sidecars[0].read_bytes(), bytecode.read_bytes())

    def assert_borrow_error(self, result):
        self.assertNotEqual(result.returncode, 0, result.stderr)
        codes = [message.get("message", {}).get("code") for message in self.messages(result)
                 if message.get("reason") == "compiler-message"]
        self.assertIn("E0515", [code["code"] for code in codes if code], result.stdout)

    def test_cargo_exports_native_build_scripts_and_failed_edit_restoration(self):
        self.fixture()
        for mode in ("verify", "reuse"):
            previous_bytecode = None
            states = [("cold", 3, 2, 4, False), ("edit", 7, 6, 8, False),
                      ("wrong", 7, 6, 8, True), ("restored", 19, 6, 8, False)]
            for label, value, helper, host, invalid in states:
                with self.subTest(mode=mode, state=label):
                    self.write_source(value, helper, host, invalid)
                    expected = value + helper + host
                    result, bytecode, target = self.export(mode)
                    if invalid:
                        self.assert_borrow_error(result)
                        self.assertFalse(bytecode.exists(), "failed export retained the previous standalone output")
                        self.assert_borrow_error(self.native(expected))
                        continue
                    self.assert_success(result)
                    self.reports(result, mode)
                    current_bytecode = bytecode.read_bytes()
                    self.assertTrue(current_bytecode)
                    self.assert_export_artifact(result, bytecode)
                    if previous_bytecode is not None:
                        self.assertNotEqual(current_bytecode, previous_bytecode,
                                            "changed integer result retained stale bytecode")
                    previous_bytecode = current_bytecode
                    messages = self.messages(result)
                    if label == "cold":
                        self.assertTrue(any(message.get("reason") == "build-script-executed"
                                            for message in messages), result.stdout)
                        self.assertTrue(any(message.get("reason") == "compiler-artifact"
                                            and message["target"]["name"] == "borrowck_cargo_helper"
                                            for message in messages), result.stdout)
                    build_outputs = [Path(message["out_dir"]) for message in messages
                                     if message.get("reason") == "build-script-executed"]
                    self.assertEqual(len(build_outputs), 1, result.stdout)
                    self.assertTrue(build_outputs[0].is_relative_to(target))
                    self.assertEqual((build_outputs[0] / "host-marker.txt").read_text(), str(host))
                    if self.vm:
                        executed = self.invoke([self.vm, "--engine", "interpreter", bytecode])
                        self.assert_success(executed)
                        self.assertEqual(executed.stdout, str(expected) + "\n")
                    test_result, test_bytecode, _ = self.export(mode, test_body=True)
                    self.assert_success(test_result)
                    self.reports(test_result, mode)
                    self.assertGreater(test_bytecode.stat().st_size, 0)
                    self.assert_export_artifact(test_result, test_bytecode, test_body=True)
                    if self.vm:
                        executed = self.invoke([self.vm, "--engine", "interpreter", test_bytecode])
                        self.assert_success(executed)
                        self.assertEqual(executed.stdout, "0\n")
                    native = self.native(expected)
                    self.assert_success(native)
                    self.assertIn("2 passed", native.stdout)


if __name__ == "__main__":
    unittest.main()
