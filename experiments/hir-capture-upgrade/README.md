# Sequential limited HIR source upgrade

This runner upgrades only the task-owned compiler checkout
`/Users/danluu/dev/rustc-hir-capture-check-20260913` after its original history
has reached a recorded terminal state. The original driver, plan, source record,
receipts, failed attempts and archive remain unchanged. A failed compiler check
is repairable; it never becomes a passing historical qualification.

The frozen replacement is source checkpoint
`33f4c4e4b0675578f92f2442de92de8232f30eeb`, including the three borrowed numeric
sort-key corrections, typed body validation, normalized entry inputs and owned
prepared values. It still always lowers normally: there is no cached HIR hit or
materializer. The replacement patch, manifest and checkpoint README are copied
from that immutable Git commit and bound in `inputs/origin.json`.

Planning requires the original passed prepare, actual failed check (or failed
unit / completed successful unit history), full source identity, all referenced
child receipts/raw outputs, and an independently verified archive containing
those exact bytes plus the original patched source and frozen inputs. Archive
member names must match their recorded absolute origins without the leading
slash. Every member is verified; a summary claim alone is insufficient.

The plan phase rechecks the original live source, reads the affected file union
from its retained base Git commit, and applies the replacement patch in a tiny
scratch directory containing only those files. It produces an old-to-new delta
and checks that delta against the live checkout without applying it there. This
creates no new compiler clone, Cargo target, or bootstrap installation. Root
reviews the resulting plan and supplies its SHA256 explicitly for every later
phase; commands, test sets, source identity and capacity policy are also checked
against fixed values. The whole plan hash is rechecked before each child.

The `apply` phase checks/applies the reviewed delta with `git apply --index`,
verifies all resulting file hashes and commits a truthful new source revision.
The original ownership marker remains bound to the original owner and plan.
The new source record and apply/check/unit completion history live only in this
worktree's `.work/hir-capture-upgrade-01`. An interrupted or failed apply retains
its exact state for diagnosis; the runner does not reset files or clean caches.

The same existing source/build/Cargo directories are reused with ordinary Cargo
invalidation. No timestamps are preserved, compiler versions overridden,
outputs relabeled, profiles changed, or compiler artifacts published. Check and
unit use exactly the original stage1 selected-crate commands. Unit requires all
five original and fifteen additional named tests to appear as actual successes;
it does not filter out other selected-crate tests. This qualifies compilation
and unit controls only, not execution of the capture hook in a new compiler.

Every phase uses the canonical lock with a 600-second admission limit, an
explicit 16 GiB starting allowance and the existing exact-owned-process capacity
guard: request stopping its own child near 9 GiB, retaining the 8 GiB running
floor. This is an in-place upgrade budget, not a lowered fresh-clone or full
compiler-package budget. All original/copy archive checks, Cargo offline policy,
distribution-only local fallback constraint and unchanged production bootstrap
bytes remain required. CI LLVM's separate downloader limitation remains.

Source-only CLI examples (not executed):

```sh
python3 experiments/hir-capture-upgrade/upgrade.py --write-plan "$ABS_PLAN" \
  --attempt plan-01 --terminal "$OLD_FAILED_CHECK_RECEIPT" \
  --archive "$VERIFIED_ARCHIVE" --archive-manifest "$ARCHIVE_MANIFEST" \
  --archive-summary "$ARCHIVE_SUMMARY"

python3 scripts/supervise_experiment.py --run-id hir-upgrade-apply-supervisor-01 -- \
  python3 experiments/hir-capture-upgrade/upgrade.py --plan "$ABS_PLAN" \
  --plan-sha256 "$REVIEWED_PLAN_SHA256" --stage apply --attempt apply-01
```

Run check and then unit with separate supervised `--stage check --attempt
check-01` and `--stage unit --attempt unit-01`, using the same reviewed plan hash.
No upgrade planning, application, compiler command or Python test has run at this
source checkpoint. Six focused Python controls are prepared in
`tests/test_hir_capture_upgrade.py`.
