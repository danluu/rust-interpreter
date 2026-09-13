# Limited cold-audit continuation

This source-only successor advances the existing owned compiler checkout from
actual prepared-value revision `3c40bed885cee37e422be334d0e1b9403225f833` to the
warning-fixed cold-audit checkpoint `60d5be4532b260f2aea03226f463dccc83391266`.
It retains the same source, build and Cargo directories and ordinary
invalidation. It does not clone a compiler, change profiles, clean targets,
rewrite historical receipts or publish a compiler. Active HIRC and predecessor
UP worktrees remain unchanged.

The predecessor actually passed its plan/apply stages and failed its sixth
check command because 21 warnings were denied by the unchanged bootstrap
policy. No predecessor unit test ran. The new manifest fixes the warnings and
adds a cold allocation-and-recapture audit, while always preserving stock
lowering. There is still no cached-body replacement or cache-hit path.

The shared upgrade engine now accepts an explicit source-defined context. Its
original defaults remain intact. This successor supplies only its owned output
paths, fixed checkpoint, complete input inventory, predecessor-history reader,
required controls and exact predecessor archive hash. The original source
guard, delta generation/application, truthful parent commit, canonical
serialization, supervision and command execution are reused.

Admission binds the actual predecessor plan SHA
`463bc86d99ec036de27e31fa892e8d080b31b51fe35e29bfa6c93cd7da4342cc`, source receipt,
apply completion, terminal compiler command/raw outputs, all frozen input files
and all 23 predecessor patched source files. The required archive is
`53a8fa2fab9504a8dbef7a44fbe26bf094a254bf8443f0cda43c9fe35eacaf54` from
`results/hir-upgrade-check-failed-01`; every member and required origin is
verified. Its reference to the original 158-member failed-history archive is
preserved. A self-consistent replacement archive or an unfinished passing
check cannot substitute for this reviewed history.

Planning constructs and verifies the old-to-new delta in a tiny text-only
scratch directory. It does not apply that delta to the compiler. Every later
phase requires root's reviewed full plan SHA256, checked before each child.
Application verifies all resulting bytes, creates a new commit whose parent is
the exact predecessor revision, and keeps its own source/completion records.
Failed or interrupted attempts remain available; there is no automatic reset.

Check and unit use the same two commands as the original driver:

```text
./x check --stage 1 compiler/rustc_ast_lowering --jobs 2 -vv
./x test --stage 1 compiler/rustc_ast_lowering --jobs 2 -vv
```

Unit requires all 20 earlier controls plus the two cold-audit controls to pass,
without filtering other selected-crate tests. The entry allowance remains
16 GiB, with the existing exact-owned-child 9 GiB capacity stop and 8 GiB
running floor. The canonical lock wait remains 600 seconds. All configuration
absence, original/copied seed, offline Cargo and bootstrap guards remain in
force. Fresh clone and full-package capacity gates are unchanged.

Root must first review this source and run the six original plus four new
Python boundary controls under canonical serialization. Then planning can be
supervised with `experiments/hir-cold-audit-upgrade/upgrade.py --write-plan`
pointing to a fresh `planned-upgrade-01.json` in this directory, the exact
predecessor `stages/check-01/receipt.json`, and the archived summary, manifest
and tar paths. Root reviews that emitted plan before separate supervised
`--stage apply`, `--stage check`, and `--stage unit` invocations, each with
`--plan-sha256` and a fresh attempt ID. No plan, compiler mutation, test or
compiler command has run for this successor source checkpoint.
