# Qualify the retained store before a recognized panic call

This is source-only preparation. It is a correctness check of future compiler
key `14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75`
against published baseline `eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d`.
It makes no performance, frequency or adoption claim. Nothing was executed
while preparing these files. The unchanged 408-test/profile and 23,727-command
core qualification must pass first. Cache/replay qualification is separate.

The exact f06 `tests/panic_store_fixture.rs` (SHA-256
`71ee4a3d817990ea243968be710f9d233450ea25cd0f5ab921055f2bd1651cc3`)
must first be installed by root at the same absolute root-worktree pathname for
all native and exporter compilations. No source copy, mutation or assertion
replacement is performed by this controller. Root's inspector reads a bounded
artifact with the pinned bincode options, runs the public bytecode validator,
then prints the complete Program as JSON. Its Cargo.lock is the retained exact
28-package closure; a locked offline build must validate that graph.

From the root worktree, run `local_export_panic_qualification.py freeze` with
`--rustc` and `--cargo` set to the exact canonical installed nightly-2026-09-08
aarch64-apple-darwin binaries, not rustup shims. This hash-only step binds the
actual core receipt and all its proofs, all 146 current compiler inputs, common
sources, both installed bundles, native tools, actual Python binary, fixture, inspector source/lock,
this plan/controller/static inputs, and every concrete command vector. It writes
`local-export-panic-frozen.json` exclusively. No Cargo/rustc discovery is run by
freeze. The selected VM and wrapper must match the baseline bytes.

Invoke `local_export_panic_qualification.py run --attempt 1` **directly, without
run_locked.py**. It acquires the original
`/Users/danluu/dev/rust-interp/.work/benchmark.lock` exactly once, with a bounded
300-second wait, and holds it across this sequence. Only a recorded unstarted
lock timeout with the entire run directory absent permits the next numbered
attempt. No started workload is retried, altered, cleaned up or reclassified.
No process is signaled. All new files, build outputs and MIR dumps belong to the
fresh `.work/runs/local-export-panic-20260912-01` directory. Preserve every partial
attempt and command log. Admission and every launch require 4 GiB free space;
this is a conservative reserve, not a measured three-cache estimate.

The fixed 90 subprocesses are:

1. One release, locked, offline, two-job inspector build into the fresh owned
   target and one pinned native fixture compilation. Each produced executable
   is hashed before any use. No std-MIR cache, Cargo fixture workspace or
   incremental compilation cache is needed.
2. Twelve native runs: `observe`, normal mode `0`, and uncaught mode `1`, for
   each decimal value `0`, `1`, `9223372036854775808`, `18446744073709551615`.
   The unchanged observer catches unwind and asserts the actual destination
   contains the requested value. Normal/observe stdout is exactly that decimal
   plus newline. The native uncaught case must exit 101, print no stdout, and
   retain its panic-hook diagnostic. No `-C panic=abort` is added.
3. Eight strict exports: each compiler, bytecode leaf inlining off/on, primary
   and secondary MIR-diagnostic export. Primary flags are exactly the frozen
   `--crate-name panic_store_fixture --edition=2024 --emit=metadata -o ...`;
   **the common extra MIR optimization flag list is empty**, matching the
   ordinary native-fixture validator. The pinned compiler determines its normal
   MIR policy. Secondary exports add only
   `-Zdump-mir=store_then_panic -Zdump-mir-dir=OWNED_ARM_DIRECTORY`. Inherited
   exporter/cache/selection/observer flags are cleared. Demand/cache modes are
   explicitly off; inline-off means the enabling environment variable is
   absent. Bytecode must be byte-for-byte identical between both compilers and
   between primary/diagnostic exports for each leaf setting. Different leaf
   settings are not required to have the same bytecode.
4. Four inspector invocations, one per primary artifact. Retain their complete
   validated Program JSON. Diagnostic/primary byte identity binds this JSON to
   the secondary compile too. Each dump set must contain 1–1,000 `.mir` files
   totaling at most 64 MiB; each bytecode artifact is at most 64 MiB.
5. Sixty-four primary artifact runs: both compilers × both leaf settings ×
   interpreter/JIT × four values × normal/uncaught modes. Every VM invocation
   has a 1,000,000 logical instruction limit. Normal output must equal the native
   value; failure must be a panic diagnostic, exit 1 and empty stdout. Require
   exact exit/stdout/stderr parity between baseline/candidate and between the
   two engines for each case. Native and VM panic wording is not conflated.

Every argv, PID, interval, return code, selected executable hash, raw stdout,
stderr and artifact hash is retained. The full frozen inputs are verified after
lock acquisition and after the sequence. The 90-command pass reaches only
`awaiting structural inspection`; it is not yet qualification success.

Root must then write a new explicit structural inspection JSON, following
`local-export-panic-inspection.example.json`, using the **actual** retained
MIR and Program dumps. Each of the four compiler/leaf combinations needs its own
case. A file/name match or an arbitrary Store is insufficient. The report must:

- Bind this execution, frozen receipt, exact fixture, primary artifact, Program
  JSON and selected MIR file by hash. Quote the real helper signature, entire
  reachable basic block, dereference assignment and original panic-call FnDef.
- Explain why the selected MIR dump/stage is the `instance_mir` body consumed
  by lowering under these flags, why the Store and recognized call are in the
  same reachable block, and why the first-argument dereference assignment is
  outside `panic_preparation`. Check the actual definition against the frozen
  compiler classifier, including crate/signature/name conditions; a textual
  function-name substring is not a DefId classification proof.
- Identify the actual size-8 Store and later Trap by function and PC. Retain an
  operation-by-operation argument/control-flow derivation showing that its
  address is the helper's destination argument and its value is the helper's
  value argument. Include caller argument routing if inlining or promotion
  changes representation. Explicitly exclude the caller's initial `!value`
  Store, unrelated frame stores, or a path that bypasses the identified Store.

The controller validates all witness hashes, quoted text, actual instruction
payloads and required reviewed assertions; the semantic derivation remains an
explicit source/artifact review, not an automated symbolic proof. Root runs
`finalize --inspection ABSOLUTE_REPORT_PATH` only after that review. If the
actual body, recognized FnDef, same-block property or argument-directed Store
cannot be established, record failed coverage and stop. Do not change the
fixture, MIR optimizer flags, inline policy, or inspection criteria to claim
this planned coverage. Any revised fixture or compiler policy requires its own
prospective plan and preserved original failure. Final success binds all raw
evidence and the inspection report in `local-export-panic-passed.json`.
