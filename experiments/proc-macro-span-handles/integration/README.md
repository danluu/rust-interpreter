# Bridge integration qualification fixtures (unrun)

These files prepare qualification for the unchanged `../span-handles.patch`.
They have not been compiled or executed. The historical four standalone handle
tests remain container evidence only. No compiler checkout, package, application,
benchmark target or holdout has been changed by this addition.

## Two actual bridge consumers

`bridge.rs` is a Rust test executable using `proc_macro::bridge::Client::run1`,
the stock `ExecutionStrategy`, the real serializer/dispatcher and the real
`HandleStore`. Its small `Server` supplies observable span values and owned
token-stream values with a destructor log; unsupported server methods panic.
The candidate store is not copied or mocked. Four tests cover:

1. 1,024 distinct spans, duplicate interning, reverse reads and exact method
   counts in both ordinary same-thread and forced cross-thread strategies.
2. A safe thread-local `Span` retained from a completed same-thread invocation
   is rejected by the next dispatch **before** its server method executes.
   Equal expansion globals in the two invocations ensure that resetting or
   incorrectly sharing per-store numeric handles would be caught. A subsequent
   successful expansion proves TLS/panic recovery. `Span` is `!Send`; this test
   does not fabricate handles or transfer spans unsafely between threads.
3. Real token-stream clone/drop RPCs and intentionally retained client handles
   produce exact server destructor order `[3, 2, 4, 1]` in both strategies.
   This exercises the unchanged token-stream BTreeMap while span storage changes.
4. Nested `expand_expr` executes a second real client through the same bridge
   executor. Its thread differs from the outer client's, its span allocation
   interleaves with the outer store, and the outer span remains valid afterward.
   Deliberate client and server panics retain exact payloads and are followed by
   successful calls. Neither TLS guard nor panic boundary is bypassed.

The methods used here necessarily reach `server.rs:55–64` and the changed
`InternedStore`: span encoding allocates/interns, and `span_end/start/line`
decoding performs reverse lookup. `Span::eq` alone would not prove this, so the
controls also require thousands of actual line RPCs. Function-item clients are
zero-sized, as required by `Client::expand1`'s selfless reifier.

`macros.rs` is an ordinary proc-macro dylib. `main.rs` and `errors.rs` invoke it
through **rustc_expand's actual server**, independently of the test Server.
They exercise nested token groups, repeated spans, group endpoints, file/local
file, byte ranges, line/column, source text, hygiene preservation, warnings,
explicit errors and a panicking macro. Nested `inner!()` also checks that saved
outer identifiers/literals survive symbol-store invalidation in the inner
client. Every probe reads a tracked environment variable and tracked file,
performs ordinary filesystem I/O, and appends ordered events to an owned log.
There is no macro-result cache. `expectations.py` checks exact invocation/event
counts and computed native values; retain and compare the complete raw event
bytes in addition to these assertions.

## Proposed real run, after explicit admission

Use one freshly created owned source directory for both compiler arms so raw
application/auxiliary paths are identical. Compiler binaries, outputs and
incremental directories are separate and fully identified. Copy fixture bytes
there, preserve every source state, and never mutate repository fixture files.
For each **stock/patched compiler × same-thread/cross-thread** pair:

- Compile the native `bridge.rs` test executable with the matching native
  sysroot and `--test --edition=2024`; run all four exact names with
  `--test-threads=1`. Its internal serial lock also protects shared test state.
- Compile `macros.rs` with `--crate-name bridge_fixture --crate-type proc-macro`.
  Compile the caller with `--extern bridge_fixture=ACTUAL_DYLIB`, ordinary link
  emission plus `--emit=link,dep-info`, JSON diagnostics and one explicit
  `-Zproc-macro-execution-strategy=same-thread|cross-thread`. Preserve the
  original debug/overflow/optimization policy equally in both arms.
- Set `BRIDGE_LOG` to a fresh per-command output, `BRIDGE_DATA` to the owned
  copy of `data.txt`, and `BRIDGE_VALUE=7` initially. Freeze source/environment
  and loaded native library identities before/after each command. Record actual
  post-wrapper compiler argv if a wrapper is involved.
- Execute the nine positive states in `expectations.HISTORY` in order. Insert
  two blank lines at `POSITION_EDIT` for the position edit; change only the
  exact `MACRO_OFFSET` declaration for the macro edit. Rebuild the macro dylib
  for cold/macro-edit/macro-restore states. Always compile and run the caller;
  no cache hit permits skipping macro execution in this qualification. Each
  caller compile must emit exactly 50 events and one explicit fixture warning.
  Results are 63 normally, 79 for file/macro edits and 83 for the env edit.
- Run all five error configurations from `expectations.ERRORS` against
  `errors.rs`. Require compilation failure, the expected code/message, exact
  invocation events, complete snippets and byte/character coordinates. These
  retain uncalled type, move/borrow and constant errors. Compare **full raw
  diagnostic JSON**, including nested spans/children/duplicates, between matched
  arms; only the separately saved human-rendered field may be excluded by the
  existing strict diagnostic comparator. Never reconstruct missing snippets.
- Recompile/run the original positive caller after the failures; require the
  original source bytes, result and event stream. A failed command cannot be
  called a restored or passed state. Preserve all attempts and raw receipts.

This is 9 positive + 5 error + 1 final recovery compilations per pair, with 10
native executions and 3 macro dylib compilations: **28 commands per pair**,
plus the bridge-test build/run. It is a proposed correctness count, not a run
receipt or a performance protocol. Actual run-make/UI tests below are separate.
Reuse the existing supervisor/canonical lock and evidence capture machinery;
do not build a new publisher or run a benchmark from this fixture directory.

For each positive compile, dep-info must contain the exact tracked data path
and `BRIDGE_VALUE` value. Raw dep-info includes arm-specific output paths, so
retain it verbatim and compare its parsed dependency/env sets while separately
binding those output paths. Event logs and diagnostic spans must change by the
actual two-line source movement and return on restoration. Their hashes alone
do not prove coordinates; validate spans against the frozen source bytes.
The five negative fixtures must also execute the warning macro exactly once.
Within a matched state compare full events byte-for-byte; do not normalize
source paths or generated results into equality.

Also run pinned compiler UI controls `span-api-tests`, `span-preservation`,
`mixed-site-span`, `subspan`, `expand-expr` (including nested symbol retention),
and existing proc-macro panic controls with the actual patched server. Select
their required auxiliary files through ordinary bootstrap/compiletest, without
blessing or editing expected diagnostics. Run both execution strategies where
the suite accepts an explicit override. The new fixtures supplement these tests.

## Minimum build and truthful identity prerequisites

`compiler/rustc_proc_macro/Cargo.toml` compiles
`library/proc_macro/src/lib.rs` as the compiler-server crate and has `test=false`.
Thus `./x test compiler/rustc_proc_macro` is not proof that the bridge ran, and
rebuilding only the public native proc_macro rlib does not patch rustc_expand's
server. The smallest actual-server check requires a separately committed source
patch and a compiler/driver containing the new rustc_proc_macro implementation.
`./x build --stage 1 compiler/rustc` is the first setup goal to review. Its
bootstrap-provided native client/sysroot must be identified exactly; an unchanged
stage0 client is a legitimate **explicitly recorded mixed-stage bridge control**
because this patch changes no wire layout, but cannot be called a complete new
distribution. Verify the actual bootstrap dependency plan before execution.

The separate direct `bridge.rs` test needs a native proc_macro library containing
the candidate server module as well: build the required stage-1 native library
target through bootstrap before running that test. Linking it against the old
native proc_macro would exercise the old store and is not candidate evidence.
Do not infer client/server source identity from a toolchain alias or copy a lone
rlib into an old install. The compiler-private crate has no separately usable
unit-test target.

The standalone `bridge.rs` test links the **new native proc_macro library**;
the macro/caller fixture tests the **new compiler's rustc_proc_macro server**.
Both candidate server implementations must be bound to the exact handle patch;
any bootstrap client retained from stage0 is identified separately. Receipts prove
which compiler built each native library and macro dylib, native linkage must
be closed within the declared distribution/runtime, and the off/reference arm
must retain its own unchanged identities. No altered execution-strategy flag
may leak into later timings: it is untracked and requires separate experiment
namespaces here. The current production compiler/package remains immutable.

Before native/exported equivalence or any timing, complete stage-2 packaging,
matching rustc-dev/exporter/VM tools and prepared standard MIR are still required.
The old `public library bytes == custom library bytes` check will correctly
reject this patch: library/proc_macro is changed. Introduce a separately reviewed
source-composition policy proving **exact baseline inventory + exact reviewed
handle.rs diff == full candidate inventory**, with every other library byte
equal. Keep full source inventories, truthful new Git commit, compiler/library
artifact digests and patch provenance in new keys. For diagnostics, only map
actual byte-identical source files to a common comparison namespace; any span
inside changed proc_macro source must be compared against its actual arm's
verified bytes and explicitly handled by the new qualification policy. Do not
weaken existing production manifests or source checks to accept this candidate.

After that boundary is implemented, run the ordinary full native/exported
correctness suites and these same fixture states through the actual matched
exporter/VM, preserving generated artifacts and original/restored output. These
files do not claim such a tool association exists today. There is no supported
speedup estimate: the saved 391ms macro event includes all user macro work.
