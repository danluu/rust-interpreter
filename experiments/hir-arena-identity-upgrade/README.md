# Current worker arena identity repair

The completed native diagnostic built compiler source `0bc623ee` and compiled
the unchanged fixture successfully, but all 24 records rejected the cold audit.
Capture stored the `WorkerLocal` wrapper address while lowering supplied its
dereferenced worker arena. The new checkpoint `84166943` stores the latter via
an explicit `&hir::Arena` coercion. All admission, tree, journal and replay
comparisons remain intact. Reuse remains off by default.

The full 25-file patch has SHA-256
`485194f2f9e995b6ad1ee2c39d66d05deb776df7b6e26b22085925c28edd6671`.
Only body_cache/mod.rs and generated source_identity.rs differ from checkpoint
`3b34821e`. All 26 prior unit tests remain, with one additional test distinguishing
the worker arena from its wrapper and a different arena. These 27 tests have not
yet run against the repair.

This continuation uses the unchanged UpgradeContext engine and the existing
task-owned compiler checkout. Its immediate positive predecessor is the
322-member selected-check/unit archive. The 250-member native diagnostic is
a separately verified reference, alongside the four older archives. Its 25
children and both supervisors are bound to actual raw output and source. The
diagnostic does not qualify native cache hits or execution of its output binary.
No successful compiler check or diagnostic is substituted for native reuse tests.

Four Python controls cover the two-file/27-test transition, refusal to promote
or alter the diagnostic result, verification of every historical archive, and
the reviewed plan's complete test and capacity constraints. Run them under the
existing canonical supervisor before planning. Planning, applying, checking and
unit testing are separate stages; each retains the 600-second canonical lock
admission, 16 GiB entry, 9 GiB stop and 8 GiB floor. No process is stopped and no
cleanup is performed by this controller.

After source review and those controls, freeze the concrete plan:

```sh
python3 scripts/supervise_experiment.py --run-id hir-arena-identity-upgrade-plan-supervisor-01 -- \
  python3 experiments/hir-arena-identity-upgrade/upgrade.py \
  --write-plan /Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hir-arena-identity-upgrade/planned-upgrade-01.json \
  --attempt plan-01 \
  --terminal /Users/danluu/dev/rust-interp-hir-diagnostic-native-20260913/.work/hir-diagnostic-native-01/stages/run-01/receipt.json \
  --archive /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-fixture-phase-check-01/evidence.tar.gz \
  --archive-manifest /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-fixture-phase-check-01/manifest.json \
  --archive-summary /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-fixture-phase-check-01/summary.json
```

Review that plan and its digest before separate `--stage apply`, `--stage check`
and `--stage unit` invocations with the same `--plan` and `--plan-sha256`.
Native qualification subsequently requires the actual new compiler, corrected
hit parser and fixture override controls. No compiler installation, interpreter
benchmark or sub-0.5-second result follows from this continuation alone.
