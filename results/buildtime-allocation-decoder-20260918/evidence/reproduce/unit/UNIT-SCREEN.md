# Paired allocation decoder unit qualification

Attempt02 is prepared source only; no new controller/project import, test or fixture execution occurred during this revision. C6 has the root-applied v4 test correction; its production allocation_trace.py is unchanged from v3. The earlier v2-bound draft is preserved byte-for-byte in `unit-draft-v2-unexecuted/`; it was never executed. The executed v3 attempt01 controller/driver/manifest/plan/notes and C6 source copies are separately preserved under `unit-attempt01-source/`, with all seven preservation hashes verified before this edit. Its failed raw `unit-screen-01` remains unchanged and is not relabeled. Production source, old proposal versions and existing C4/C5 packets are unchanged by this preparation.

Frozen decision: `4843e329a9f134fb0f4d7a0473509176f23d54bb7f7b2fa6a1bd875a42d12917`. Selected v4 patch: `f9a32243517c0fcf3de19a47f4a686d090f69ca6dec0052f8890a2c3935a6bc4`. Both roots have base `835382dbe182ebf5f10d322e79ac290cdd3ef2f2`. Baseline C3 has186 top-level scripts/tests Python sources; candidate C6 has187. Their only differences are allocation_trace.py and the new test_allocation_trace.py. The controller binds all373 sources, exact inventories, proposal metadata/patch/source copies/docs, itself, driver, manifest, frozen decision, reviewed C5 controller, pinned Python executable/framework and the three JSON stdlib sources before and after (389 proof records).

## Four suites,52 exact names

1. Baseline allocation_trace:7 new parser tests.
2. Baseline interpreter_build_metrics:19 existing launcher tests.
3. Candidate allocation_trace:7 new parser tests.
4. Candidate interpreter_build_metrics:19 existing launcher tests.

Four memory admissions plus four test children give eight children total. Static AST inventory records every exact test ID and rejects changed counts, inheritance, decorators or custom loaders. The child driver records both discovered and successful IDs; controller requires all52 names, zero skips/failures/errors/expected-failures, matching unittest text totals/OK, and exact source/module receipts. Attempt02 remains unexecuted. Attempt01 reached only the baseline parser suite and failed an invalid C-scanner recursion expectation; its count/results are retained separately.

For the new tests, the driver loads the requested arm's actual canonical allocation_trace path into `sys.modules["allocation_trace"]` before importing the unchanged C6 test file. It verifies that the test module references that same object and that file path/content persist after the suite. The C6 test's own sys.path insertion therefore cannot redirect baseline imports. Both new suites exercise actual parser/file APIs. The two metrics suites load their matching tree's existing test file and verify interpreter.py came from that same root. No baseline source/test file is edited or copied. Children share the owned packet as their recorded cwd, and every suite has an exclusive private TMPDIR.

## Fixture and process boundary audit

The new parser tests import only standard-library helpers and allocation_trace. They use bounded byte strings,32-level valid/malformed records for both scanners, a4096-level recursion rejection only for py_make_scanner, standard-library scanner patches, and a private TemporaryDirectory sidecar; no subprocess, compiler, VM, network or existing runtime installation is accessed. Their synthetic nesting cases are correctness checks, not performance data.

The existing metrics suite creates private tool manifests, bytecode/sidecars and fake clocks. setUp patches interpreter.ROOT, installed_tools, exporter capability checks, fcntl.flock, resource/time functions, selected_trace and interpreter.subprocess.run. Its run_process returns CompletedProcess objects and captures exact Cargo/VM arguments instead of launching them. Every test executes after that setup; cleanup restores patches. The existing stock-launch import test forbids custom_compiler/custom_cargo imports while reaching those stubbed boundaries. Selected_trace verification in this metrics suite is intentionally stubbed; real parser behavior is checked by the new suite and later frozen qualification. No full-build or performance conclusion follows from these unit tests.

## Preserved execution controls

The reviewed ancestor is C5 `4cdc55de282224d4f99ecd6ea929ac9f9b4c7677fbd55c3ed4c7f70b7ff32d42`. Functions require/free_bytes/identity/proof/write/run_child/admission are AST-identical. New code only supplies paired source bindings, exact test inventory/driver loading, and report validation. The helper keeps the canonical shared benchmark lock and inode check, fresh16GiB disk/30% memory,20-second memory admission age, pinned Python -I -S -B, unchanged HOME/minimal environment, planned/start/terminal receipts, exclusive logs, wait4 CPU/wall/RSS, five-second read-only disk observations, and finally-settlement before parsing or lock release. No signals, cleanup, retries, peer mutation, runtime probe or Rust build. Ordinary log files have1MiB bounded proof readers, not hard disk quotas. Rust admission remains32GiB.

Result schema retains status/error/post_binding_error, expected_tests/passed_tests, tests, test_inventory, bindings/bindings_after and children. Success requires status="passed", null errors, expected_tests=passed_tests=52, four successful suite rows with embedded exact-name/module reports, and eight settled zero-exit children. Before/after bindings must be identical. These timings are correctness receipts only.

Final controller SHA256: `d24ecce51e04651ed7141cec9bce8cdc1016a302b866014796cd3946d0416447`.
Final preload driver SHA256: `28cfcb430d6435a7157ef373c94986ff8ec344ba6a3bc21148f3ba7c6e289cb2`.
Final manifest SHA256: `86679602b2820d9d19a80edb6234b1c32e19e6317c0a13016423fde366856769`.

Future reviewed command (not executed):
`/usr/bin/python3 /Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/allocation-decoder-probe/run-unit-tests.py --execute-synthetic-unit-tests`

## Preserved baseline failure and attempt02 scope

Attempt01 result SHA256: `ba47f8284e996ef84ee685f02487e9c5dc00817c7d3208de9e3e24b204d45b1e`. It contains two settled children, stable before/after source bindings, and failure in the first baseline seven-test suite. The unchanged baseline C scanner accepted depth4096; the erroneous universal RecursionError expectation failed, while the pure-Python subcase and six other methods passed. No candidate implementation suite or timing ran.

V4 corrects only that one new method/name. Both scanners must accept shallow nesting, reject a malformed nested record and recover; only the Python fallback asserts depth4096 recursion rejection. Production bytes, all other test methods and every frozen count/panel/gate remain unchanged. The new manifest updates only the candidate test bytes/hash and this method name in the two parser suite inventories.

Fresh output is `unit-screen-02` in both controller and driver. Controller differences from the preserved attempt01 source are only proposal/plan/manifest/driver binding values and that output path. Reversing those exact literal substitutions recovers the complete previous controller byte for byte; driver changes only its manifest hash and destination. All process/settlement logic is unchanged. The previous failed result is retained as failure, not reused as qualification. No execution occurred during rebinding.
