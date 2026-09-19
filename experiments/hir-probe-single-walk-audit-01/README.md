# Current-base single-walk audit and qualification recipe

This is concrete source for an **unbuilt, unrun audit compiler**. The three
compiler files in `candidate/` adapt the existing real-AST differential audit
to the held options-hash compiler. `fixtures/rmake.rs` is the runnable Rust
qualification driver, with all thirteen fixture/runner files copied exactly
from the previous audit proposal. No compiler, test, provider probe or timing
has run for this candidate.

The current identities are distinct:

- Held N: `7c6bc02810f5c3ed7cf09d4566253611a890ce51dd8e534a908862da382c39ea`.
- Performance candidate: `4ae2790b6283fd3569035c15b7b031603781f96a2dc2eca7b8631525cff55680`.
- Audit candidate: `65c516a68f274516659aa384bd9ea4e9a0df4536a2943327750156ca5953d6b7`.

Apply the held performance candidate to a fresh source tree, then `audit.patch`,
or overlay these three audit files directly on the same pinned N base. The
generator checks the complete inherited 25-file identity map and all 61 source
inputs again after copying. N, the held performance proposal, old proposals,
installed runtime, and screen packets remain unchanged. The audit identity is
never eligible for performance measurements.

For every accepted real AST, the audit calls the exact old `current_nodes`
oracle after constructing the proposed single-walk value. The oracle compares
the two normalized `Input` encodings; the audit additionally compares the
ordered `(NodeId, bool)` vectors. An error or disagreement panics. These checks
have no disabling environment variable and run with incremental-info both on
and off, whenever the unchanged capture/reuse enable gate enters `probe`.
Incremental-info controls only coverage messages. The original eligibility
gates, options-hash query, subsequent dependency observations, capture/replay
logic, trace/journal validation and poststate checks are preserved.

`source-comparison.json` binds the unchanged old audit input, exact current
oracle, current-base call replacement and all fixture identities. The audit
restores the extra traversal for comparison; the performance candidate removes
it. Its duplicate internal trace/debug events, interner occupied lookups and
possible capacity allocations are not semantic diagnostics and are not claimed
identical. O's dependency review is retained by reference at
`/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/hir-probe-single-walk-dependency-source-review-01.json`
(`43b794e7ff26cd7c00cf4604e2661dab7ca5d47e0b087d723fe0898aaff2d2bf`).
Normalized input bytes and the key recipe stay equal; the new source identities
deliberately change complete persisted keys.

The runner first invokes every inherited run-make assertion: edit/restore,
resolution, corruption, lint, diagnostic, version override and behavior checks.
Added real Rust covers literal normalization, patterns, local/external
resolutions, imported traits, exact rejected syntax/hygiene, and the existing
literal/source/node/depth/identifier budgets. Separate fresh incremental
directories prevent whole-crate freshness from replacing coverage. Info-off
compilations compare complete unfiltered JSON diagnostics across off, capture
and reuse modes; valid programs also compare behavior. Malformed internal IDs,
fabricated resolver data, placeholder parameters and parented spans remain
explicitly outside this ordinary-source fixture coverage.

The source-derived schedule is 309 nested commands: the inherited 230 plus
79 added calls, comprising 188 compiler calls and 121 native executions, with
48 expected compiler failures. These are expectations, not actual counts.
Any fixture mismatch is a retained qualification failure; cases must not be
dropped to make the audit pass. The inherited test-name reader is copied as
`compiler_test_source.py`. `current_compiler_test_source.py` changes only the
old fixed revision association to an explicit actual new revision argument;
its adjacent diff preserves the exact module/test derivation. The future
catalog must be bound to the new source paths and hashes before it runs.

`qualification_recipe.py` renders the two ordinary direct-run-make commands
from the authenticated, previously passed D2 compile/E2 execute recipe. It
retains D2, the unchanged support providers, compiletest environment and loader
ordering, but selects the fresh audit E2 and fresh recipe/output directories.
It has no process API. To inspect the concrete unbound commands:

```sh
/opt/homebrew/bin/python3 -B experiments/hir-probe-single-walk-audit-01/qualification_recipe.py
```

The output intentionally has null actual build, native identity, provider
closure and qualification fields. Reusing a saved provider pathname is not a
claim that its current payload has been checked. The existing bounded native
preparer/monitor must bind these actuals and the finite input table before
executing either row. No new supervision framework is introduced here.

`build-route.json` gives separate fresh X `.work` namespaces for audit and
performance, each with its own source, Cargo home, target, temporary files and
new source commit. Reuse only admitted offline seed archives, their actual
source closure and read-only D2/support providers. Do not share writable
targets or source inodes, reuse retired stage1-rustc intermediates, rebuild
LLVM, download dependencies or forge the prior compiler revision. The exact
ordinary lowering check, lowering tests, compiler/library build, version,
sysroot/help and interface test arguments are retained. Support is already
D2-produced and may be reused after current verification; its old unsupported
`./x build ... run-make-support` command is not included.

The existing build policy remains 24 GiB entry, 14 GiB aggregate namespace,
256 MiB evidence, 9 GiB stop/8 GiB floor, jobs=2 and canonical admission bounded
to 600 seconds. Only one build runs at a time. Before materialization, a finite
source/seed allocation projection and current admission must fit those limits.
The existing build/native source guards need a fresh finite binding and normal
parent wait; this source packet does not pretend that preparation already ran.

X's saved readback `323b15dd1d65b7b5dcd5122628bace04f7f5ec334dc527dfcffe7deb4332fc7d`
is copied as `saved-build-resources.json`. Across 217 saved samples in 26
children, the maximum whole-N allocation was 8,610,234,368 bytes and evidence
14,979,072 bytes. The saved stage1-rustc allocation before retirement was
6,098,370,560 bytes. Five successful ordinary build/test commands totaled
932.509 seconds; compiler/library build accounted for 427.332 seconds and
interface tests 351.408 seconds. All reused prior stages. Samples are not a
continuous peak, and these times are not cold-build estimates. The largest
single reported rustc RSS was 1,691,424 KB; aggregate concurrency, memory and
swap remain unmeasured. Two simultaneous build namespaces are not justified
by these observations.

The attribution erratum remains immutable in the performance proposal:
`attribution-erratum.json`, SHA
`ac1205993b6857afbcde0f7a23ffae2b2861f97944cf631b1e5f0879b0a4801a`.
The repeated 1,510 capture messages in each warm strict call were Cargo replay
from fresh dependencies. Actual warm Ruff work produced 1,411 hits and zero
new captures. This candidate targets a source-proven redundant walk during
each eligible probe; it does not claim those replayed messages are fresh work.
The older self profiles are a different compiler context and provide no
measured speedup for this candidate. Performance is unmeasured.

The first source-only route generator stopped on an absent `component` field
in an inactive historical archive row. Its source and three completed metadata
copies are retained under `history/route-01-missing-inactive-fields`. The
correction keeps inactive archives explicit and still requires complete active
seed fields. No workload or provider payload was touched.
