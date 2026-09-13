# Native qualification after the worker-arena fix

This continuation requires the actual source `7efc0d94` from checkpoint
`84166943`, successful selected compiler checking, all 27 unit tests, and a
verified archive of that completed history. The actual 334-member archive is
pinned as `ce5931c23ba0af5247f85848df64ef0735b14ae5ba0c1fd4ce1a080477b023ce`.
The predecessor's successful diagnostic rejected all 24 cold audits and does
not qualify capture, reuse, or native program execution.

The existing native engine receives a small explicit context. Its original
default remains unchanged. The same three commands run serially under one
canonical lock, with a 16 GiB entry requirement, continuous 9 GiB stop and 8 GiB
floor. Existing analogous net-space observations are estimates, not peak bounds
or reusable-space credit. The full stage2/package requirement remains 36 GiB.

1. `./x build --stage 1 compiler/rustc library --jobs 2 -vv`
2. `./x test --stage 1 compiler/rustc_interface --test-args test_unstable_options_tracking_hash --jobs 2 -vv`
3. `./x test --stage 1 tests/run-make/hir-body-cache-capture --jobs 2 -vv --no-capture`

Three real identity/capability probes follow the build. Full source, original
bootstrap/environment/configuration, copied offline seeds, runtime/native std
inventories and all archived prerequisites remain guarded. Successful native
qualification requires the one actual option-test pass and one actual run-make
pass, with visible verified reuse messages and valid `S`/exclusive `E` ranges.
The corrected parser from `eca617cd` is unchanged. The sequence has 26 retained
children: four five-command source guards, three bootstrap commands, and three
probes. Planning has five source-guard children.

The frozen run-make source preserves ordinary, capture and reuse comparisons,
source/edit/restore and raw error histories. It removes bootstrap's
`RUSTC_FORCE_RUSTC_VERSION` only for the intended compiler controls, then tests
explicit empty and nonempty overrides separately across all three modes. These
negative controls must execute native programs, preserve exact ordinary output
and raw errors, and produce neither capture logs nor cache sidecars. No runtime
checks, fixture branches, or compiler flags are replaced by a diagnostic-only
probe. Every hit retains tree, journal and post-state verification.

The immediate archive contains the new check/unit history and 25 current source
files. Six historical archives remain separate verified references: phase322,
diagnostic250, ReadyHit324, failed-native203, cold314 and failed318. Historical
tar inputs are omitted only from the current archive's required payload map;
their full digests, manifests, required members and source origins are verified
separately. No compiler or native executable is relabeled or published.

Five new Python controls cover default compatibility, complete native plan
constraints, six references, missing or rehashed old unit history, source
identity and raw-output tampering. Run them together with the seven existing
native-engine controls under the canonical supervisor before planning.

Use this isolated worktree for controls, plan and native execution. The current
upgrade history freezes the old native-engine bytes in PRIMARY. Merging the
engine adaptation into PRIMARY before this sequence completes would invalidate
that evidence and is not part of the launch procedure. No SOURCE edits occur
in the native driver. After root reviews the source and the 12 Python controls
pass, prepare the plan from this worktree:

```sh
python3 scripts/supervise_experiment.py --run-id hir-arena-native-plan-supervisor-01 -- \
  python3 experiments/hir-arena-native/check.py plan --attempt plan-01 \
  --write-plan /Users/danluu/dev/rust-interp-hir-arena-native-20260913/experiments/hir-arena-native/planned-native-01.json \
  --ready-plan-sha256 01edd2672a7a0cbe850b9f6b38984b01ba4172d009417e9aaf40ae205cba9299 \
  --terminal /Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/hir-arena-identity-upgrade-01/stages/unit-01/receipt.json \
  --archive /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-arena-identity-check-01/evidence.tar.gz \
  --manifest /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-arena-identity-check-01/manifest.json \
  --summary /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-arena-identity-check-01/summary.json
```

Review the produced plan and digest before a separate supervised `run` with
`--attempt native-01 --plan .../planned-native-01.json --plan-sha256 REVIEWED_SHA`.
No native qualification or performance result is claimed by this source handoff.
