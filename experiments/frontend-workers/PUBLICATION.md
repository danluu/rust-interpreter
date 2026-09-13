# Frontend-worker build and qualification handoff

This source checkpoint and its plan are unexecuted. The public compiler remains
nightly-2026-09-08 (`cea272fa356e94bd2ee2cadf376630aa0683867a`). No custom compiler,
custom Cargo, macro optimization, borrow-check cache or analysis bypass is part
of this experiment. Omission remains compatible with existing installed tools.

The existing public publisher now has one explicit additional policy,
`frontend-workers-public-build-v1`. Its default macro policy retains its source
revision and exact eight-command contract. Worker publication uses eight
commands: compiler/Cargo identity, the complete Rust workspace tests, release
tools, seven launcher contracts, eight worker-screen contracts, and the actual
exporter and wrapper capability probes. Both probes must match the pinned
`frontend-workers-v1` capability. Release debug info remains `1`; incremental
tool compilation remains disabled and build concurrency is two Cargo jobs.

All existing source, dependency archive, compiler/Cargo, dynamic-library,
platform, shared-std and immutable-publication validation is reused. The
composition adds the explicit policy tag, and its key is computed from the
complete post-build composition and all three actual binary hashes. The
source-input key is never treated as the installed tool key. Published worker
correctness has scope `public-build-only`; it cannot claim worker qualification.

The actual 30-command qualification remains outside that keyed composition.
It runs in the future screen owner, using that owner's existing prepared public
std. Before the handoff, the producer verifies that the screen owner has the
exact compiled crate sources and the frozen qualification/launcher sources.
If main has advanced those inputs, integration or a newly reviewed plan is
required. A different source tree is never silently accepted. No new std build
or std copy is required.

The qualifier acquires the canonical lock before source inventories or tool
input checks. It uses the shared publication validator and full input guards
before and after the existing 30 commands, retains their exact receipts and
bytecode, and calls the shared typed worker-history validator before publishing
success. Both qualifier and screen reject any substitute lock path. The complete
copied fixture inventory is bound to the published harness: every child guards
the Cargo manifests/lock, build script and proc-macro inputs, while only the two
recorded edit files may change. Exact staged restoration backups are the only
additional fixture files allowed while an edit is active. The archived consumer
rechecks those same inputs and all controlled edit/restoration hashes.
The existing 3→7→3 edit, all error/recovery controls, duplicate-preserving
structured diagnostics and bytecode parity are unchanged. Its supervisor waits
for the qualifier without holding a second lock. Qualification results and
failed destinations are retained; no automatic retry replaces them.

After separately preparing the pinned owned Nushell source, materialization
checks the actual external qualification and emits the existing 27-command
screen: explicit workers 1/2/1, identical tools and public std, four Cargo jobs,
two suite workers, all 14 original tests and the unchanged 0.500-second gate.
The build/qualification driver never executes that screen.

Plans 01 and 02 are preserved as superseded and unexecuted. The first combined
159-test run completed at source `759498fe9e187ada955eb362e374287390682cb5`:
158 passed and one publication test errored because its mock did not accept the
new explicit qualification-policy keyword. Plan 03 updates that mock to require
the keyword and assert the unchanged default macro policy; its intended rejected
publication and absent-readiness assertions remain intact. No runtime code is
changed by this correction. The failed run and all its exact sources are retained
in PRIMARY `.work/worker-prerequisite-tests-01`; a fresh full run is required.
The reviewed fixture/lock/frozen-byte checks, MonoItem source-observable gate and
corrected raw/tagged evidence validation remain required.
The source-only metadata freeze acquires the canonical lock, records its process,
and emits no compiler, Cargo, test or benchmark command:

```sh
python3 experiments/frontend-workers/prepare_plan.py \
  --run-id frontend-worker-build-03 \
  --supersedes experiments/frontend-workers/planned-build-01.json \
  --supersedes experiments/frontend-workers/planned-build-02.json \
  --screen-root /Users/danluu/dev/rust-interp-semantic-reuse-20260913 \
  --std-mir-ready /Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/std-mir/bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef/ready.json \
  --output experiments/frontend-workers/planned-build-03.json
```

After review, the corrected source tests and each actual stage need separate
coordinated admission. The fresh combined 159-test run includes both shared-public
validator/publication suites (5+5 tests), the two worker publication boundaries,
and merged launcher/screen contracts. The runner itself uses the canonical lock,
a bounded 600-second wait, a 12-GiB build entry gate and 8-GiB command gates.

```sh
python3 experiments/frontend-workers/build.py --plan experiments/frontend-workers/planned-build-03.json
python3 experiments/frontend-workers/build.py --plan experiments/frontend-workers/planned-build-03.json \
  --qualify .work/frontend-worker-build-03/published.json
python3 experiments/frontend-workers/build.py --plan experiments/frontend-workers/planned-build-03.json \
  --materialize .work/frontend-worker-build-03/published.json
```

The last command creates `.work/frontend-worker-build-03/screen-command.json`
only after strict prerequisites. Its final-key argv requires another admission;
no timing, speedup, adoption or holdout claim follows from publication.
