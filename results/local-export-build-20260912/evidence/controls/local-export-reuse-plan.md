# Qualify reuse, dependency observation and cache faults for local exporter reuse

This is source-only preparation for compiler key
`14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75`.
No checker has been imported or executed during preparation. No historical
build or qualification result is substituted for this candidate's results.

After the future core qualification records 408 passing tests, zero failures
and one ignored test in each profile, run `local_export_reuse_qualification.py
freeze`. It verifies that core receipt and every bound proof, the exact candidate
bundle, the published `eb91912d` baseline bundle, and the frozen source-input map.
It writes `local-export-reuse-build-schema.json` exclusively. That receipt is an
explicit compatibility adapter: its `test-debug: 408` and `test-release: 408`
values come from actual whole-workspace results. It does not claim that the
historical exporter-only build script ran or that its former 47/50-test suite
produced these counts. The full original test results and source receipts remain
bound alongside the flattened values.

Run the following adapter modes in separate fresh Python processes, in order:

1. `reuse --attempt 1`: unchanged `reuse_check.py`, run ID
   `export-reuse-fixtures-71`, with `--typed-relocations --binding-replay
   --function-reuse --expected-tests 408`. Require its actual 337-command summary.
2. `dependency --attempt 1`: unchanged `dependency_check.py`, run ID
   `export-dependency-fixture-71`, with `--persistent-cache --function-reuse` and
   the actual preceding reuse summary as `--binding-replay-qualification`.
   Require 293 commands and the original supported-dependency-boundary predicates.
3. `cache --attempt 1`: unchanged `cache_check.py`, run ID
   `export-cache-fixture-71`, with `--function-reuse` and the actual preceding
   dependency summary as `--qualification`. Its existing sequence totals 98
   commands, including cache corruption, namespace/missing controls, both policy
   changes, recovery, and failed publication after staging.

The adapter sets only the selected module's `CONTROL` constant to the actual
published baseline key `eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d`
before calling its original `main`. CLI arguments are exactly those frozen above.
It does not replace helpers, validators, capture functions, environments, source
edits, cache-fault bounds, compiler flags or assertions. Importing `reuse_build`
only obtains definitions; its `main` is never called. The baseline VM and wrapper
must remain byte-identical in the candidate bundle.

**Invoke this adapter directly; never use `run_locked.py`.** Every original
checker acquires `.work/benchmark.lock` itself for up to 45 seconds. The adapter
verifies that this path resolves to the established original shared lock at
`/Users/danluu/dev/rust-interp/.work/benchmark.lock` but never acquires it. Each
checker retains its existing 8 GiB free-space checks. All fixture copies, edits,
incremental sessions, deliberate faults and result files stay in its exact new
task-owned run directory. Existing directories or result summaries stop launch.

Each attempt gets exclusive `local-export-MODE-attempt-NN.json/.log` records.
Only the exact original lock TimeoutError, with neither run nor result directory
created, is marked `unstarted-lock-timeout`. Root may retry that condition with
the next attempt number while retaining the same frozen plan. An attempted run,
preflight failure, interrupted checker or assertion failure is retained and is
not automatically retried, cleaned up, signaled or reclassified.

On success, `local-export-MODE-passed.json` binds the actual summary, plan, raw
records, every referenced stdout/stderr, top-level artifacts/census/cache snapshots,
and copied source files. The next mode verifies those proofs before proceeding.
The dependency checker legitimately calls its summary `completed diagnostic`;
the adapter preserves that status and separately requires its actual correctness
predicates. Observation modes still fully lower functions; actual-reuse modes
skip qualified green functions. No claim that every mode fully lowers is added.

The static inputs manifest fixes checker/import sources, seven existing reuse
fixtures, both dependency fixture sources, checker documentation, the common
launcher scripts, toolchain and the 146-input compiler manifest. The future
compatibility receipt additionally freezes actual core proofs and both installed
tool bundles. No original-checkout cache contents or other-window source paths
are consumed. The original lock pathname is used only to verify lock identity.

All outcomes are correctness evidence. They make no build-latency, runtime,
holdout, workload-frequency or adoption claim. Audit/leaf-inline and actual
Store-before-Trap qualification remain separate prerequisites for any later
prospectively fixed performance screen.

Independent source review by `binary_codegen` found no blocker in the schema
derivation, command counts, proof chain, original locks or timeout-only retry.
The review did not import checkers, execute commands or inspect run caches.
