# Limited ReadyHit continuation

This source-only third context advances the existing owned compiler from
actual cold-audit revision `9d21c2bae5edcfd6cae6e96f38731a740b7acc9e` to the
immutable ReadyHit checkpoint `5cd6acd3f50912cec5fb29375b130afa70506703`.
The shared upgrade engine and both earlier contexts are byte-identical to the
previously checked versions. Source, build and Cargo directories are retained
with ordinary invalidation. There is no compiler clone, target cleanup, profile
change, installation or rewrite of a historical receipt.

The cold predecessor passed its plan, apply, selected-crate check and unit
stages. All 22 unit controls passed with no ignored or filtered tests and no
compiler warnings. Its 314-member archive is
`55061f25443157ef7ea125a1cad8920ce18d895f9c6f9a99d480df804b188f73` in
`results/hir-cold-audit-check-01`. It retains all 61 commands and four
supervisors, the full source inventories and all 24 affected source payloads.
Its plan hash is
`04e5e73dc76f20a0b7e809fe5d4d38e9f5d35b9fbecc635e3d328bc4090934a2`.
The previous compiler source parent remains `3c40bed885cee37e422be334d0e1b9403225f833`.

The 314-member archive references the earlier 318-member failed-history
archive rather than duplicating its payload. Every stage separately verifies
that exact archive, manifest and summary and every required member from the
fixed cold plan. The required archive is
`53a8fa2fab9504a8dbef7a44fbe26bf094a254bf8443f0cda43c9fe35eacaf54` at
`/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-upgrade-check-failed-01`.
The normal shared engine then verifies every member and required current-cold
payload in the 314-member immediate archive. Neither archive can substitute
for the other. The oldest 158-member failed-history reference remains intact.
The new plan records these separate historical member maps.

The new patch has 25 files and 191,677 bytes, SHA256
`cca094ebc73f6cc7da9ea1660669a436a6900e5d9c307550435dbcd8784410f4`.
It adds exclusive replay preflight and cached-body materialization, keeps reuse
off by default, preserves the existing eligibility grammar, and retains
always-on tree/journal/post-state verification. This uses a trusted local
producer/cache boundary. Valid-checksum malformed structures are tested; a
semantically forged but structurally valid payload with a recomputed checksum
is outside that boundary. No native hit or performance result is claimed here.

All 22 predecessor controls plus four new replay controls must pass, without
filtering the selected crate. The two unchanged compiler commands are:

```text
./x check --stage 1 compiler/rustc_ast_lowering --jobs 2 -vv
./x test --stage 1 compiler/rustc_ast_lowering --jobs 2 -vv
```

The canonical lock wait remains 600 seconds, with 16 GiB entry, the existing
exact-owned-child 9 GiB capacity stop and 8 GiB running floor. Configuration
absence, original/copied archive, offline Cargo and bootstrap guards remain
unchanged. A full compiler package still requires its separate 36 GiB gate.
A subsequent native correctness stage must use the newly produced source and
actual successful check/unit receipts, not the historical cold qualification.

Root must review the source and run the six original, four cold and four new
Python controls canonically before planning:

```text
python3 -m unittest discover -s tests -p 'test_hir_*upgrade.py'
```

Then this concrete plan command may run through the supervisor from the new
owned worktree. It verifies and constructs the delta in a small text scratch
directory; it does not apply the delta to the compiler.

```sh
python3 scripts/supervise_experiment.py --run-id hir-ready-hit-upgrade-plan-supervisor-01 -- \
  python3 experiments/hir-ready-hit-upgrade/upgrade.py \
  --write-plan /Users/danluu/dev/rust-interp-hir-ready-hit-upgrade-20260913/experiments/hir-ready-hit-upgrade/planned-upgrade-01.json \
  --attempt plan-01 \
  --terminal /Users/danluu/dev/rust-interp-hir-cold-audit-upgrade-20260913/.work/hir-cold-audit-upgrade-01/stages/unit-01/receipt.json \
  --archive /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-cold-audit-check-01/evidence.tar.gz \
  --archive-manifest /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-cold-audit-check-01/manifest.json \
  --archive-summary /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-cold-audit-check-01/summary.json
```

After root reviews the resulting plan and its SHA256, each phase runs under a
fresh supervisor using `--plan` with that path, `--plan-sha256` with the exact
reviewed digest, and respectively `--stage apply --attempt apply-01`,
`--stage check --attempt check-01`, and `--stage unit --attempt unit-01`.
Application preserves the actual cold parent and records a truthful new Git
commit. Failed attempts remain available. No plan, source upgrade, Python test,
compiler check or unit command has run for this source checkpoint.
