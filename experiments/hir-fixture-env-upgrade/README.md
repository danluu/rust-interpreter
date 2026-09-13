# Fixture environment and rejection-phase continuation

This source checkpoint prepares an in-place diagnostic continuation from actual
SOURCE `3d7ad8282c5695196f4a4dcfd0bdceacac3f79b9`. No upgrade plan, compiler-source
mutation or compiler command has run for this context. Plan creation and source
application are separate explicit commands; application requires the exact
reviewed plan SHA. The actual compiler remains unchanged while prior diagnostic
archives are completed.

The pinned checkpoint is `3b34821e313fc9ea68917897648c9322c4cca067`, with patch
`211425be515befb15594afaf9a1e5338569e605bb5cc92d5d71f66fd5c1f6ed2`
(194,952 bytes, 25 files) and source identity
`1cffd7526fd7d5415407a8d8ec333f1eae5dc06239189f0121bc6455759fceaf`.
All 26 unit controls are unchanged. Relative to the previous ReadyHit checkpoint
5cd6acd3, exactly rmake.rs, body_cache/mod.rs and generated source_identity.rs
differ. Immutable Git payloads and their origins are recorded in inputs/.

The run-make fixture removes the compiletest-only RUSTC_FORCE_RUSTC_VERSION from
ordinary, capture and reuse histories, then runs additional explicit empty and
nonempty override controls with real output and raw E0308 comparison. The
production override fallback is unchanged. The compiler diagnostic change keeps
all six fallible capture checks in order, adds the first failed phase to existing
incremental-info messages, and returns the same already-lowered value on failure.
It does not repair the observed body-tree rejection or establish any native hit.
The separately preserved direct probe compiled successfully but reported 24
rejected body trees and zero hits; it did not execute the produced binary.

The unchanged UpgradeContext engine retains the successful ReadyHit selected
check and all 26 units (324-member archive), plus the failed native run
(203-member archive). The earlier 314/318 archives remain separately verified
references. Partial native build/probe/option success remains distinct from the
failed run-make and zero capture/hit messages. The immediate engine archive is
ReadyHit324, whose required members are its own source/check/unit inputs and
25 patched source bytes. Failed-native203 is pinned by its exact three file
hashes and verified in full at stage admission. Archive bytes bind the superseded
native parser rather than requiring its old live source to remain installed.

All plan/apply/check/unit stages retain the 16 GiB entry, 9 GiB capacity stop,
8 GiB floor, canonical 600-second admission, and fixed bootstrap commands. The
normal existing build targets and offline seed/configuration guards are retained.
The original upgrade engines and full fresh-compiler 36 GiB driver are unchanged.
Stage2/package admission and installation are separate; this context qualifies
no interpreter performance or native cache hits by itself.

Four Python controls cover the exact three-file/26-test checkpoint, preserved
failed-native source/terminal/archive association, complete separate historical
archive verification, and fixed command/capacity/test/plan-digest rules. Their
execution evidence is recorded separately; no test result is inferred here.

After source review and controls, the concrete plan command (not yet executed) is:

```sh
python3 scripts/supervise_experiment.py --run-id hir-fixture-env-upgrade-plan-supervisor-01 -- \
  python3 experiments/hir-fixture-env-upgrade/upgrade.py \
  --write-plan /Users/danluu/dev/rust-interp-hir-fixture-env-upgrade-20260913/experiments/hir-fixture-env-upgrade/planned-upgrade-01.json \
  --attempt plan-01 \
  --terminal /Users/danluu/dev/rust-interp-hir-native-correctness-20260913/.work/hir-native-correctness-01/stages/native-01/receipt.json \
  --archive /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-ready-hit-check-01/evidence.tar.gz \
  --archive-manifest /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-ready-hit-check-01/manifest.json \
  --archive-summary /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-ready-hit-check-01/summary.json
```

The driver owns canonical admission; no outer nested lock is used. The resulting
plan must be reviewed before separate apply, check and unit stages. A new native
correctness driver must then bind the resulting source/check/unit archive and
corrected actual span-range parser. Neither the failed old native receipt nor a
successful diagnostic compile can admit the later stage2 sequence.
