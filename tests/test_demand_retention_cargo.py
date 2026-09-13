"""Opt-in ordinary Cargo host/target histories; caller holds the shared lock."""
import json
import os
from pathlib import Path
import unittest

import test_borrowck_cache_cargo as cargo_helpers
import test_demand_retention as compiler_helpers


@unittest.skipUnless(os.environ.get("RUST_INTERP_TEST_EXPORTER"),
                     "set RUST_INTERP_TEST_EXPORTER to run Cargo correctness tests")
class DemandRetentionCargoTests(unittest.TestCase):
    setUp = cargo_helpers.BorrowckCacheCargoTests.setUp
    invoke = cargo_helpers.BorrowckCacheCargoTests.invoke
    assert_success = cargo_helpers.BorrowckCacheCargoTests.assert_success
    fixture = cargo_helpers.BorrowckCacheCargoTests.fixture
    write_source = cargo_helpers.BorrowckCacheCargoTests.write_source
    messages = staticmethod(cargo_helpers.BorrowckCacheCargoTests.messages)
    cargo_command = cargo_helpers.BorrowckCacheCargoTests.cargo_command
    native = cargo_helpers.BorrowckCacheCargoTests.native
    assert_export_artifact = cargo_helpers.BorrowckCacheCargoTests.assert_export_artifact
    assert_borrow_error = cargo_helpers.BorrowckCacheCargoTests.assert_borrow_error

    @classmethod
    def setUpClass(cls):
        cargo_helpers.BorrowckCacheCargoTests.setUpClass.__func__(cls)

    def export(self, mode, test_body=False):
        target = self.work / ("target-" + mode)
        bytecode = self.work / (mode + ("-test" if test_body else "-lib") + ".rbc")
        env = dict(self.cargo_env, RUSTC_WRAPPER=str(self.wrapper), RUSTC_WORKSPACE_WRAPPER="",
                   RUST_INTERP_QUERY_CACHE_RETENTION=mode,
                   RUST_INTERP_BORROWCK_CACHE="reuse" if test_body else "off",
                   RUST_INTERP_EXPORT_PACKAGE=cargo_helpers.PACKAGE,
                   RUST_INTERP_EXPORT_CRATE=cargo_helpers.CRATE,
                   RUST_INTERP_EXPORT_MANIFEST=str(self.package),
                   RUST_INTERP_EXPORT_TEST="1" if test_body else "0",
                   RUST_INTERP_ENTRY="selected" if test_body else "entry",
                   RUST_INTERP_OUTPUT=str(bytecode))
        env.pop("RUSTC", None)
        env.pop("RUSTDOC", None)
        env["RUSTUP_AUTO_INSTALL"] = "0"
        command = self.cargo_command("check", target, rustup=True)
        if test_body:
            command += ["--profile", "test"]
        with (self.work / "cargo-routing.jsonl").open("a") as output:
            output.write(json.dumps({"retention_mode": mode, "test_body": test_body,
                                     "borrowck_mode": env["RUST_INTERP_BORROWCK_CACHE"],
                                     "command": [str(arg) for arg in command]}) + "\n")
        return self.invoke(command, env), bytecode, target

    def reports(self, result, test_body=False):
        prefix = compiler_helpers.PREFIX
        reports = [json.loads(line[len(prefix):]) for line in result.stderr.splitlines()
                   if line.startswith(prefix)]
        # Cargo may replay fresh dependencies' stderr. The selected unit must
        # have a report too; cold build also verifies real native host callbacks.
        selected = [report for report in reports
                    if report["crate_name"] == cargo_helpers.CRATE
                    and report["test"] == test_body]
        self.assertEqual(len(selected), 1, reports)
        for report in reports:
            self.assertTrue(report["strict_checking"], report)
            if report["provider_installed"]:
                self.assertFalse(report["disabled_reason"], report)
                self.assertEqual(report["promotion_passes_omitted"], 1, report)
                self.assertEqual(Path(report["effective_incremental_directory"]),
                                 Path(report["original_incremental_directory"])
                                 / compiler_helpers.NAMESPACE, report)
        self.assertTrue(selected[0]["provider_installed"], selected)
        return reports

    def test_cargo_host_dependency_edits_export_parity_and_error_restoration(self):
        self.fixture()
        states = [("cold", 3, 2, 4, False), ("body", 7, 2, 4, False),
                  ("host-and-target", 11, 6, 8, False), ("wrong", 11, 6, 8, True),
                  ("restored", 19, 6, 8, False)]
        for label, value, helper, host, invalid in states:
            with self.subTest(state=label):
                self.write_source(value, helper, host, invalid)
                expected = value + helper + host
                result, bytecode, target = self.export("demand")
                control, plain, _ = self.export("off")
                native = self.native(expected)
                if invalid:
                    for failed in [result, control, native]:
                        self.assert_borrow_error(failed)
                    self.assertFalse(bytecode.exists())
                    self.assertFalse(plain.exists())
                    continue
                for completed in [result, control, native]:
                    self.assert_success(completed)
                self.assertIn("2 passed", native.stdout)
                reports = self.reports(result)
                if label == "cold":
                    self.assertTrue(any(report["crate_name"] == "build_script_build"
                                        and report["provider_installed"] for report in reports), reports)
                self.assert_export_artifact(result, bytecode)
                self.assert_export_artifact(control, plain)
                self.assertEqual(bytecode.read_bytes(), plain.read_bytes())
                outputs = [Path(message["out_dir"]) for message in self.messages(result)
                           if message.get("reason") == "build-script-executed"]
                self.assertEqual(len(outputs), 1)
                self.assertTrue(outputs[0].is_relative_to(target))
                self.assertEqual((outputs[0] / "host-marker.txt").read_text(), str(host))
                if self.vm:
                    executed = self.invoke([self.vm, "--engine", "interpreter", bytecode])
                    self.assert_success(executed)
                    self.assertEqual(executed.stdout, str(expected) + "\n")
                selected, selected_bytecode, _ = self.export("demand", test_body=True)
                stock, stock_bytecode, _ = self.export("off", test_body=True)
                self.assert_success(selected)
                self.assert_success(stock)
                self.reports(selected, test_body=True)
                self.assert_export_artifact(selected, selected_bytecode, test_body=True)
                self.assertEqual(selected_bytecode.read_bytes(), stock_bytecode.read_bytes())
                if self.vm:
                    executed = self.invoke([self.vm, "--engine", "interpreter", selected_bytecode])
                    self.assert_success(executed)
                    self.assertEqual(executed.stdout, "0\n")


if __name__ == "__main__":
    unittest.main()
