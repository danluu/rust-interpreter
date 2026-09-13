# Native capture rejection diagnostic

This is a bounded diagnostic on the existing task-owned compiler checkout. It
builds the checked phase-reporting checkpoint, verifies the resulting compiler
identity, then compiles one byte-identical fixture in a fresh owned directory.
It does not run the produced binary, VM, run-make history or benchmark, and cannot
qualify native cache reuse. Every compiler and raw diagnostic output is retained.

The actual source is `0bc623ee4860082df9d1d2216aefad9abb42990d`, parent
`3d7ad8282c5695196f4a4dcfd0bdceacac3f79b9`, from checkpoint
`3b34821e313fc9ea68917897648c9322c4cca067`. The exact upgrade plan is
`5d79e14e09d124dac64afcb24a5ddf9037fbaf1ab59ccb48f7a66b45bfec507f`;
source receipt is `bd53da0a1d70e560a362699ef7c789fab303e18da25dee669b28996529388ec0`.
All completed apply/check/unit receipts, all 26 unfiltered unit names, child
commands/environments/raw outputs and outer supervisors are required. The
322-member terminal archive is pinned to
`eb4f4157bc0c1e35d44f6364b6be0e315ce02e7c853d6a3c24b96b59f2bf0985`.
Its source and text payloads are separate from four fully verified historical
archives: ReadyHit324, failed-native203, cold314 and failed-prepared318. Historical
tar paths appearing in the upgrade's frozen input map are checked as explicit
references, without requiring nested copies in the current archive.

The one run sequence holds the existing canonical workload lock throughout:

1. `./x build --stage 1 compiler/rustc library --jobs 2 -vv`.
2. The resulting stage1 `rustc -vV`, `--print sysroot` and `-Zhelp` probes.
3. One direct stage1 compilation of the exact checked `fixture.rs`, copied as
   `input.rs`, using the original fixture's capture=true/info=true options.
   `-Zincremental-info` enables the new phase diagnostics. Reuse stays off.

The original bootstrap profile, configuration, archive seeds, Cargo offline
policy and HIRC child environment are unchanged. That environment has no
`RUSTC_FORCE_RUSTC_VERSION`; no override is removed from or added to a supplied
environment by this driver. The production anti-spoof guard is untouched.
The direct command is frozen in the plan before execution, including its output,
metadata and fresh incremental directory. No user application is modified.

There is one 16 GiB admission check for the whole run, a 9 GiB between-child and
active-child stop guard, and the existing 8 GiB floor. Prior host free-space deltas
are not peak bounds or reuse credit. The fresh full stage2/package 36 GiB gate is
unchanged. Planning itself requires the normal 8 GiB floor. Original and copied
seeds, full source/backtrace/configuration and exact fixture bytes are guarded;
after the build, the full compiler/native-std inventory is checked around each
subsequent child and at completion. Every failure retains its receipts. A new
run requires a fresh fixture directory; this driver performs no cleanup.

The expected command counts are five Git source guards for planning, and twenty
children for the run: five guards, build, five guards, three probes, direct
compile, five final guards. No option or native reuse test is silently counted.
Terminal `diagnostic-completed` means the diagnostic compiler returned zero and
all source/artifact guards passed. Missing records and phase rejections remain
explicit observations; successful capture records also leave `native_qualified`
and `executed_native_binary` false. The original native qualification stays failed.
The parser preserves complete raw lines and rejects stale aggregate body-tree
messages, malformed IDs or unexpected reuse claims.

Five prepared Python controls exercise actual report grammar, rejection/no-record
semantics, fixed reviewed command/capacity/test scope, complete successful history,
and separate predecessor tar evidence. Their execution requires independent
canonical admission; no result is inferred from the source.

After those controls and root review, create a plan (metadata/archive verification
only) with the existing supervisor. The current archive may be supplied from its
verified evidence worktree or the identical integrated PRIMARY copy:

```sh
python3 scripts/supervise_experiment.py --run-id hir-diagnostic-native-plan-supervisor-01 -- \
  python3 experiments/hir-diagnostic-native/check.py plan --attempt plan-01 \
  --write-plan /Users/danluu/dev/rust-interp-hir-diagnostic-native-20260913/experiments/hir-diagnostic-native/planned-diagnostic-01.json \
  --terminal /Users/danluu/dev/rust-interp-hir-fixture-env-upgrade-20260913/.work/hir-fixture-env-upgrade-01/stages/unit-01/receipt.json \
  --archive /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-fixture-phase-check-01/evidence.tar.gz \
  --manifest /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-fixture-phase-check-01/manifest.json \
  --summary /Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/hir-fixture-phase-check-01/summary.json
```

Review the complete plan and its SHA before the separate `run --attempt run-01
--plan ABSOLUTE_PLAN --plan-sha256 REVIEWED_SHA` command. Do not run a native
qualification or publish an installed compiler based on this diagnostic receipt.
