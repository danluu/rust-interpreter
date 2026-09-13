# Limited native ReadyHit correctness

Source-only driver; no plan, compiler build, native test or benchmark has run.
Frozen candidate: `5cd6acd3f50912cec5fb29375b130afa70506703`, patch
`cca094ebc73f6cc7da9ea1660669a436a6900e5d9c307550435dbcd8784410f4`.
The included files come from that immutable Git commit, not the evolving candidate
worktree. This driver never modifies the compiler source or publishes artifacts.

Planning first requires the *actual*, completed ReadyHit apply/check/unit history
in the independent ready-hit-upgrade worktree: all 26 named units must pass with
zero failed or ignored tests; check and all recorded child commands must pass.
The full source inventory, truthful source commit and parent, original bootstrap
recipe, raw child outputs and frozen helper inputs are bound. A verified archive
must contain the exact plan/source/history inputs and all 25 patched source files.
The immediate ReadyHit archive does not duplicate predecessor payloads: the exact
314-member cold archive and its referenced 318-member failed-prepared archive
are independently verified against their fixed identities and required member
maps at admission, and their hashes remain guarded throughout. The old failed
capture/prepared histories remain historical failures. A successful
cold audit is not a ReadyHit prerequisite substitute.

After root reviews a generated plan, a single canonical-lock admission executes:

```
./x build --stage 1 compiler/rustc library --jobs 2 -vv
./x test --stage 1 compiler/rustc_interface --test-args test_unstable_options_tracking_hash --jobs 2 -vv
./x test --stage 1 tests/run-make/hir-body-cache-capture --jobs 2 -vv --no-capture
```

The complete sequence has one 16 GiB entry check, a 9 GiB between-child/active-child
stop guard, and the unchanged 8 GiB floor. It does not demand 16 GiB again between
commands. Any child, source guard, test-count or capacity failure ends the attempt;
there is no automatic continuation or retry. A newly reviewed attempt may later
reuse the normal Cargo target; failed evidence remains intact.

The retained Cmono stage1 build, stage1 controls, and stage2 interface-test commands
show net host free-space changes of approximately 3.548553, 0.846394 and 2.450684 GiB
(sum 6.845631 GiB). These are estimates from host free-space observations, **not**
per-task allocations or peak upper bounds. They give no credit for existing HIRC
partial dependencies/std. The full stage2/package admission remains 36 GiB.
Evidence origins are DRIVER `.work/mono-production-build-02/stages/`:
`stage1-01/commands/006`, `stage1-controls-01/commands/006`, and
`option-hash-01/commands/006`. Their unchanged bootstrap TOML SHA is
`71b495da8fc35ca1321322f56065eb149ecd82fa3c8ff7ef4d4c10ec53f0df9b`.

Bootstrap builds stage1 rustc with stage0, then native stage1 std. The interface
unit is compiled with stage0 against the new compiler source (pinned bootstrap
`test.rs` CrateLibrustc), and must log the actual option test once with one pass.
Run-make uses the new stage1 compiler/std and the unchanged real capture/reuse
recipe. Its normal prerequisites include compiletest, run-make-support and
rustdoc (`test.rs` RunMake dependency). The fixture does not request in-tree Cargo.
The third command adds only `--no-capture` to expose successful run-make
subprocess output (its verbose subprocess output is already enabled by bootstrap).
The driver requires a real verified cache-hit line as well as the one-test pass;
no-capture test-name/output/`ok` interleaving is accepted. No build dependency,
warning, compiler flag, profile, test state or source error
is skipped. The two new options remain default-off outside the recipe's explicit
capture/reuse arms; native hits run its ordinary output/raw diagnostic comparisons
and always-on tree/journal/post-state checks.

Three recorded compiler identity probes (`-vV`, `--print sysroot`, `-Zhelp`) follow
the build. They verify the truthful source commit, actual stage1 location and both
options. Exact stage1 compiler/std file inventories and the two explicitly checked
bootstrap source links are recorded after build and after testing. Existing built
files must remain byte-identical; normal added rustdoc files are allowed and fully
inventoried. This is an in-place stage1 correctness artifact, not an installed
compiler package or a performance-qualified toolset.

The original HIRC environment/TOML and six original plus copied archive seeds
remain exact. Cargo stays offline; the existing narrow `file:///dev/null`
distribution override is unchanged. This is not a complete network sandbox: CI
LLVM has a separate pinned downloader; its exact original/copied seed is checked
before every `./x` invocation. Native manifest/recipe Cargo configuration discovery
is additionally frozen. Only task-owned descendants may be stopped by the existing
capacity helper after exact process-group ownership revalidation.

Future commands, only after prerequisites exist and root admits them:

```
python3 experiments/hir-native-correctness/check.py plan --attempt plan-01 \
  --ready-plan-sha256 ACTUAL_REVIEWED_READY_PLAN_SHA \
  --terminal /Users/danluu/dev/rust-interp-hir-ready-hit-upgrade-20260913/.work/hir-ready-hit-upgrade-01/stages/unit-01/receipt.json \
  --archive ACTUAL_READY_ARCHIVE --manifest ACTUAL_READY_MANIFEST --summary ACTUAL_READY_SUMMARY \
  --write-plan /Users/danluu/dev/rust-interp-hir-native-correctness-20260913/experiments/hir-native-correctness/planned-native-01.json
python3 experiments/hir-native-correctness/check.py run --attempt native-01 \
  --plan /Users/danluu/dev/rust-interp-hir-native-correctness-20260913/experiments/hir-native-correctness/planned-native-01.json \
  --plan-sha256 ACTUAL_REVIEWED_NATIVE_PLAN_SHA
```

These placeholder identifiers are not approval or invented artifact identities.
Both invocations require an owned outer supervisor and the canonical 600-second
admission; no compiler source clone, setup duplication, target cleanup, source
upgrade, package/install, exporter/std preparation or performance screen is part
of this driver. Focused Python tests are prepared in
`tests/test_hir_native_correctness.py`; they have not run.
