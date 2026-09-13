# Complete native recipe replay

The original arena native attempt remains failed. Its stage1 build, three compiler
identity probes, tracked-option test, and complete run-make recipe returned zero.
Compiletest truncated the recipe's stderr after 524,288 bytes, removing the later
cache-hit records required by the outer checker. This adapter retains that exact
failed receipt and runs the same already-built `rmake` binary in one fresh owned
directory, copying only the unchanged `fixture.rs`. No compiler rebuild, source
edit, fixture change, synthesized test footer, or output normalization is involved.

The final executed compiletest command in the saved output supplies the recipe
environment. The earlier preview command is rejected. The adapter applies the
exact `run_make.rs` runtime environment changes, including the support-library and
stage0 loader paths. `RUSTC_BOOTSTRAP=1` and `RUSTC_FORCE_RUSTC_VERSION=compiletest`
remain inherited by the recipe; its existing common compiler constructor removes
the version override, and its explicit empty/nonempty negative controls restore it.
Only the recipe working directory and resulting local cache/output paths are fresh.

The metadata plan binds the original successful 27-unit history, current334 and
six historical archives, failed21 command receipts and raw output, frozen source
inputs, actual stage1/compiler/std and stage0 runtime/support files, and the recipe
binary. Existing `NativeContext`, full source guards, inventories, and `owned.run`
are reused through the unchanged native worktree. The stage1 inventory must still
contain every original built byte. The final inventory, source guard, and restored
fixture/input comparison are required after the replay. Primary's old native
engine remains authoritative for its historical inputs and is not modified.

Planning runs five source-guard commands. Execution holds the canonical lock for
five source guards, three identity probes, one complete recipe, and five final
source guards: 14 commands. The existing 16 GiB admission, 9 GiB stop, and 8 GiB
floor are retained. Child output is written directly to ordinary files without
compiletest's capture layer. A zero recipe return means all original assertions
ran, including native output/raw diagnostic equality, source edits/restoration,
trait and lint changes, corruption controls, and version overrides. The outer
adapter additionally requires raw cold/repeated capture records, all required hit
roles with valid S/E intervals, and raw error/override evidence. This is separate
direct-recipe evidence; it never relabels the original failed native attempt.

Four focused Python controls are prepared, unrun. No replay plan or workload has
been launched. After source review, use the existing supervisor for these commands:

```sh
python3 experiments/hir-arena-native-replay/check.py plan --attempt plan-01 --write-plan /Users/danluu/dev/rust-interp-hir-native-controls-evidence-20260913/experiments/hir-arena-native-replay/planned-replay-01.json
python3 experiments/hir-arena-native-replay/check.py run --attempt run-01 --plan /Users/danluu/dev/rust-interp-hir-native-controls-evidence-20260913/experiments/hir-arena-native-replay/planned-replay-01.json --plan-sha256 REVIEWED_SHA256
```

The frozen recipe's assertions and source are unchanged. A passing replay can
support a future explicit stage2 prerequisite together with the original build
and option-test receipts; it is not a performance result or package publication.
