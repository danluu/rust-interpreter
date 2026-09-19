# Paired allocation decoder unit qualification

Prepared source only; no controller or project module was imported, no tests ran, and no fixtures were created. C6 is the root-applied v3 candidate. The earlier v2-bound draft is preserved byte-for-byte in `unit-draft-v2-unexecuted/`; it was never executed. Production source, old proposal versions and existing C4/C5 packets are unchanged by this preparation.

Frozen decision: `af6f52d6c088a5924714d26a42626b33aa64cc836c042e5f96f7e514a84319a9`. Selected v3 patch: `998dd3bc1ca338efe7ca5aeaed02c9447b82c88e2730d0675064d152da63f569`. Both roots have base `835382dbe182ebf5f10d322e79ac290cdd3ef2f2`. Baseline C3 has186 top-level scripts/tests Python sources; candidate C6 has187. Their only differences are allocation_trace.py and the new test_allocation_trace.py. The controller binds all373 sources, exact inventories, proposal metadata/patch/source copies/docs, itself, driver, manifest, frozen decision, reviewed C5 controller, pinned Python executable/framework and the three JSON stdlib sources before and after (389 proof records).

## Four suites,52 exact names

1. Baseline allocation_trace:7 new parser tests.
2. Baseline interpreter_build_metrics:19 existing launcher tests.
3. Candidate allocation_trace:7 new parser tests.
4. Candidate interpreter_build_metrics:19 existing launcher tests.

Four memory admissions plus four test children give eight children total. Static AST inventory records every exact test ID and rejects changed counts, inheritance, decorators or custom loaders. The child driver records both discovered and successful IDs; controller requires all52 names, zero skips/failures/errors/expected-failures, matching unittest text totals/OK, and exact source/module receipts. Counts are source evidence only until execution.

For the new tests, the driver loads the requested arm's actual canonical allocation_trace path into `sys.modules["allocation_trace"]` before importing the unchanged C6 test file. It verifies that the test module references that same object and that file path/content persist after the suite. The C6 test's own sys.path insertion therefore cannot redirect baseline imports. Both new suites exercise actual parser/file APIs. The two metrics suites load their matching tree's existing test file and verify interpreter.py came from that same root. No baseline source/test file is edited or copied. Children share the owned packet as their recorded cwd, and every suite has an exclusive private TMPDIR.

## Fixture and process boundary audit

The new parser tests import only standard-library helpers and allocation_trace. They use bounded byte strings,32/4096-level correctness records, standard-library scanner patches, and a private TemporaryDirectory sidecar; no subprocess, compiler, VM, network or existing runtime installation is accessed. Their synthetic nesting cases are correctness checks, not performance data.

The existing metrics suite creates private tool manifests, bytecode/sidecars and fake clocks. setUp patches interpreter.ROOT, installed_tools, exporter capability checks, fcntl.flock, resource/time functions, selected_trace and interpreter.subprocess.run. Its run_process returns CompletedProcess objects and captures exact Cargo/VM arguments instead of launching them. Every test executes after that setup; cleanup restores patches. The existing stock-launch import test forbids custom_compiler/custom_cargo imports while reaching those stubbed boundaries. Selected_trace verification in this metrics suite is intentionally stubbed; real parser behavior is checked by the new suite and later frozen qualification. No full-build or performance conclusion follows from these unit tests.

## Preserved execution controls

The reviewed ancestor is C5 `4cdc55de282224d4f99ecd6ea929ac9f9b4c7677fbd55c3ed4c7f70b7ff32d42`. Functions require/free_bytes/identity/proof/write/run_child/admission are AST-identical. New code only supplies paired source bindings, exact test inventory/driver loading, and report validation. The helper keeps the canonical shared benchmark lock and inode check, fresh16GiB disk/30% memory,20-second memory admission age, pinned Python -I -S -B, unchanged HOME/minimal environment, planned/start/terminal receipts, exclusive logs, wait4 CPU/wall/RSS, five-second read-only disk observations, and finally-settlement before parsing or lock release. No signals, cleanup, retries, peer mutation, runtime probe or Rust build. Ordinary log files have1MiB bounded proof readers, not hard disk quotas. Rust admission remains32GiB.

Result schema retains status/error/post_binding_error, expected_tests/passed_tests, tests, test_inventory, bindings/bindings_after and children. Success requires status="passed", null errors, expected_tests=passed_tests=52, four successful suite rows with embedded exact-name/module reports, and eight settled zero-exit children. Before/after bindings must be identical. These timings are correctness receipts only.

Final controller SHA256: `62b815d3987b9b6a2b709a8541a58049b544caab3b456112efac8041ecabebb5`.
Final preload driver SHA256: `5ece3cd071e48c2cbef6da2686c5d1ec6a7fa0a1149c832a025ab7cf76ffeada`.
Final manifest SHA256: `ff4e2acdaf21d4ef0a039c883cfb9de5052378e6b10e8f69de5c9cb11610c846`.

Future reviewed command (not executed):
`/usr/bin/python3 /Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-probe/run-unit-tests.py --execute-synthetic-unit-tests`

## Finalization diff from preserved v2 draft

The driver changes only its manifest binding. The manifest changes only candidate allocation_trace.py bytes/SHA. Paths and hashes alone normalize away below; the two additional report/decision consistency assertions stay visible. No helper behavior changes.

```diff
--- unexecuted-v2-draft.normalized
+++ final-v3-unit-controller.normalized
@@ -89,6 +89,7 @@
     decision = json.loads((PACKET / "decision-plan.json").read_bytes())
     q = decision["qualification"]["unit_tests"]
     require(decision["base_commit"] == descriptor["base_commit"] and
+            decision["proposal_patch_sha256"] == FIXED[PROPOSAL / "candidate.patch"] and
             q["total"] == EXPECTED_TESTS and q["work_processes"] == q["memory_processes"] == 4 and
             q["per_arm"] == {"test_allocation_trace.py": 7, "test_interpreter_build_metrics.py": 19},
             "unit qualification differs from frozen decision")
@@ -310,6 +311,7 @@
                         report["module_path"] == str(Path(source["root"]) / "scripts/allocation_trace.py") and
                         report["module_content"] == source["sources"]["scripts/allocation_trace.py"] and
                         report["test_path"] == declared["path"] and
+                        report["test_content"] == {k: before[declared["path"]][k] for k in ("bytes", "sha256")} and
                         report["canonical_module_object_preserved"] is True and report["manifest_sha256"] == SOURCE_SHA,
                         "driver names/module/result mismatch: " + label)
                 tests.append(dict(label=label, arm=arm, pattern=filename, passed=expected,
```
