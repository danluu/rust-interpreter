# Limited HIR capture compiler check

This source-only plan is pinned to capture checkpoint
`3f3e9c28704a7866f72ad0974336d79671714ae9`, not the evolving codec branch.
`inputs/origin.json` binds the exact committed patch, patch inventory and
production bootstrap configuration. No compiler checkout or check has run.

After the current shared-std/36/61/Mono27 sequence finishes, the proposed owned
source is `/Users/danluu/dev/rustc-hir-capture-check-20260913`. Independently clone
the completed Cmono source at `58e1e1f5311f4424ea81def4763081f6da62d9b3`, without
hard links or alternate object stores; independently populate its pinned
`library/backtrace` submodule. Apply only the retained capture patch, verify
every original and resulting file against its manifest, and record a truthful
new source commit. Do not change the completed compiler checkout or package.

Reuse the exact recorded stage0 archives from 2026-08-30 and managed CI LLVM
archive, copied into the new source's own cache. Keep the production bootstrap
configuration byte-identical: two jobs, assertions off, source remapping on,
no downloaded compiler and no bootstrap submodule updates. Cargo runs offline
with the locked dependency graph. The new serde/serde_json edges use versions
already present in that graph. One exact cache-path mapping drives copying,
plan metadata, and validation of all six copied seeds immediately before each
`./x` command and after completion. Missing, non-file, symlinked (including
ancestor directories), or hash-mismatched archives fail before bootstrap starts.
The original archives are independently checked at each stage too.

`RUSTUP_DIST_SERVER=file:///dev/null` constrains **distribution** fallback only.
Pinned Python bootstrap reads this variable at `bootstrap.py:596` and delegates
a missing component to curl with that local URL. Pinned Rust bootstrap reads it
at `core/download.rs:837`; its downloader rejects `file` at line 1028 before the
HTTP path. This intentionally makes an unexpected distribution request fail,
rather than replacing any required component or changing build flags.

CI LLVM uses the baked `src/stage0` artifact server directly
(`core/download.rs:371-392`) and has no supported environment server override.
The matching seeded CI archive prevents its ordinary download path; this driver
is **not a complete network sandbox**, nor a protection against concurrent cache
mutation after preflight. No bootstrap/compiler source or production bootstrap
configuration is changed. Downloads remain outside the authorized check scope;
missing Cargo dependencies fail through `CARGO_NET_OFFLINE=true`.

The first two actual commands are:

```sh
./x check --stage 1 compiler/rustc_ast_lowering --jobs 2 -vv
./x test --stage 1 compiler/rustc_ast_lowering --jobs 2 -vv
```

At this pin, compiler check and compiler unit-test stage 1 use the stage0 beta
compiler (`check.rs:526`, `test.rs:3357`). The first command checks the selected
crate and required dependencies. The second builds and runs its actual unit
tests, including the five new journal/storage controls. This does not require
building a complete new rustc driver. It also does not execute the capture hook
inside a newly built compiler or qualify a cache hit: this patch has no hit path.

The separate later native fixture sequence would require a real stage1 compiler:

```sh
./x build --stage 1 compiler/rustc library --jobs 2 -vv
./x test --stage 1 tests/run-make/hir-body-cache-capture --jobs 2 -vv
./x test --stage 1 compiler/rustc_interface \
  --test-args test_unstable_options_tracking_hash --jobs 2 -vv
```

Those later commands are outside the limited check driver. Full packaging keeps
its existing 36 GiB entry requirement and all native/strip/source qualifications.

The limited prepare/check/unit history requires a fresh 24 GiB free baseline,
the exact canonical workload lock with a 600-second bounded wait, retained
supervisor/child/source/environment/archive receipts and an 8 GiB running floor.
The previous full Cmono stage1 took 398 seconds with a net host free-space drop
of 3.56 GiB; the existing option-hash unit step took 355 seconds and 2.46 GiB net.
Neither is a peak-space bound or a timing estimate for this smaller check.
No Cargo/compiler output from the completed compiler is reused as proof for
the new source. Failed destinations and receipts remain intact.

The runner is `check.py`. After source review, freeze its metadata plan under
the canonical lock, then run each stage through the existing external
supervisor. These commands remain unexecuted:

```sh
python3 experiments/hir-capture-check/check.py --write-plan \
  /Users/danluu/dev/rust-interp-hir-capture-check-20260913/experiments/hir-capture-check/planned-check-01.json

python3 scripts/supervise_experiment.py --run-id hir-capture-prepare-supervisor-01 -- \
  python3 experiments/hir-capture-check/check.py \
  --plan experiments/hir-capture-check/planned-check-01.json --stage prepare --attempt prepare-01
python3 scripts/supervise_experiment.py --run-id hir-capture-check-supervisor-01 -- \
  python3 experiments/hir-capture-check/check.py \
  --plan experiments/hir-capture-check/planned-check-01.json --stage check --attempt check-01
python3 scripts/supervise_experiment.py --run-id hir-capture-unit-supervisor-01 -- \
  python3 experiments/hir-capture-check/check.py \
  --plan experiments/hir-capture-check/planned-check-01.json --stage unit --attempt unit-01
```

Only start a later stage after the preceding one passed. The unit stage requires
all five named new controls to appear as actual passing tests; it does not filter
away the crate's other tests. Bootstrap source edits and unit-test sidecar writes
are confined to this future owned checkout and its disposable test directories.
The ordinary existing owned-stage capacity guard controls only its exactly
created process group if space approaches the running floor.
