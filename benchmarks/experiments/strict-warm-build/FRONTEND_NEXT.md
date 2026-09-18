# Remaining repeated work after the development screens

September 18 continuation: the native HIR compiler has been rechecked on the
updated host and installed as an ordinary immutable runtime. Both the fresh
28-command readmission and the 28-command final-path installation passed;
all 3,709 installed files were independently rehashed. See
[installation evidence](../../../results/runtime-installation-r-02/README.md).
This establishes compiler/source installation, not application latency.

The source-containing std CLI and ordinary launcher now have explicit native
runtime selectors. The launcher requires a separately keyed tool composition
with matching recorded exporter/wrapper compiler roles. The actual installed
runtime has now prepared the shared source-containing std sysroot; all seven
children and all published source/metadata bytes were independently verified.
See [std preparation evidence](../../../results/runtime-std-preparation-01/README.md).
The beta auxiliary build sysroot also passed its real debug-stripping control.
A fresh exporter and wrapper built for the final runtime path have passed
frontend diagnostic/bytecode parity and all 23 installation checks. The
ordinary launcher accepts the installed composition; its VM, compiler, sources
and prepared std identities are recorded separately. See
[exporter installation evidence](../../../results/runtime-exporter-publication-01/README.md).
These setup results establish no application latency gain.

The ordinary edit workflow can now compare application compiler flags with the
runtime, exporter, VM and prepared std held fixed. Flags are applied after tool
and std validation, and the runner supports the canonical shared workload lock
from a separate installation checkout. Its 67 focused controls passed, including
a synthetic complete edit history and mutation rejection. See
[workflow controls](../../../results/runtime-workflow-controls-03/README.md).
The first actual Ruff cache-off/cache-on history subsequently passed its six
unchanged tests, five production edits, intentional failure and restoration.
Cache-on regressed the diagnostic complete-command median from 3.348 to 4.253
seconds; exporter frontend time rose from 2.318 to 3.121 seconds. Only the
selected `ruff_linter` compiler ran on each warm custom call. Its direct output
reported 1,411 reuse hits and zero captures; 1,510 apparent captures in aggregate
Cargo stderr were replayed dependency diagnostics. The preserved correction
and raw evidence are in the
[Ruff diagnostic](../../../results/runtime-ruff-hir-diagnostic-01/README.md).
These instrumented, trap-enabled observations are not strict latency results.
A continued selected-process self-profile now preserves both complete profiles,
all successful child histories and the two earlier collection failures. In its
single instrumented edited pair, incremental-session directory preparation took
0.000954 seconds with the cache off and 0.383906 seconds with it on; the number
of hard-linked files rose from 3 to 1,414. Lowering self time also rose from
0.296 to 0.467 seconds. Type-checking and other phases varied, so these differences
are not a causal decomposition of total wall time. The reader's total is a sum
of per-thread elapsed spans, not CPU time. See the
[Ruff self-profile](../../../results/runtime-ruff-hir-self-profile-01/README.md).

Two independent compiler candidates address repeated work without changing the
application. A source-only [options-hash candidate](../../../experiments/hir-options-hash/README.md)
stores the immutable incremental-options hash once per compiler context while
preserving its wire encoding. It has not been compiled or measured. Separately,
a packed body-cache representation is being developed to reduce filesystem work
while preserving record keys, checksums, reconstruction and validation. Neither
candidate has established a performance gain.

[Target selection](TARGET-SELECTION.md) retains Ruff as the immediate measured
development target, adds pinned Oxc as another development target, and keeps
Nushell for regression/stress coverage. Oxc's pinned source, registry and native
toolchain acquisition are complete. Its full library-test crate compiled and
the three unchanged plugin tests passed in the original, three edited and
restored states; the deliberately wrong edit failed all three assertions.
The initial history's missing LLVM provider remains preserved as
[warning-qualified evidence](../../../results/oxc-native-compatibility-01/README.md).
A separate toolchain composition with the matching official LLVM component
subsequently passed its actual native stripping control. The unchanged Oxc
history then passed all 64 children without warnings or loader diagnostics:
three production edits took 11.918, 11.757 and 8.326 seconds, and only the
`oxc_linter` library-test target rebuilt. See the
[clean native history](../../../results/oxc-native-compatibility-02/README.md).
The 0.192-second already-built original state is not an edited-build result.
These are three configuration tests compiling the full test crate, not lint-rule
coverage. Its independent source copy and all 323 offline registry packages are
now admitted under the runtime owner; the acquisition passed 17 controls and
all nine planned commands without compiling or running the application. See
[runtime source acquisition](../../../results/oxc-runtime-source-acquisition-01/README.md).
The same source history then passed all 16 interpreter/JIT calls: the three
unchanged tests passed on the original, edited and restored states, and all six
individual wrong-edit assertions failed as expected. Every artifact reported
zero unavailable call sites. This first recipe enabled unavailable-call traps
and try callbacks, so its 5.715–5.953-second edited build-to-ready observations
were diagnostic. See the
[runtime compatibility evidence](../../../results/oxc-runtime-compatibility-01/README.md).
A fresh strict history then passed the same 16 interpreter/JIT calls with both
flags removed, including all six intentional assertion failures. All 16 strict
bytecode artifacts matched their diagnostic counterparts. The three edited
builds took 5.895–6.265 seconds for the interpreter and 5.759–5.948 seconds for
the JIT. These build-to-ready observations exclude VM startup/execution and
come from one correctness history, not the repeated latency protocol. See the
[strict runtime history](../../../results/oxc-runtime-strict-compatibility-01/README.md).
It remains a development target, and no holdout success is claimed.
The sub-0.500-second target remains unmet.

An independent launcher improvement preserves every runtime file/directory
collision check while replacing path-object construction with string ancestor
walking. All 22 controls and all 12 paired installed-runtime/std lookups passed;
the median component time fell from 144.822 to 118.937 milliseconds. See the
[lookup evidence](../../../results/runtime-lookup-paths-01/README.md). This is
a component measurement, not an application build-time gain. The first runtime
Ruff diagnostic keeps its already frozen launcher source so this separate
change cannot confound the HIR cache-off/cache-on comparison.

A subsequent direct POSIX-path predicate candidate passed its 22 controls but
failed the predeclared consistency threshold: only eight of twelve paired
lookups improved, against ten required. The source was restored and all
observations retained in the
[unadopted comparison](../../../results/runtime-lookup-relative-01/README.md).
Its favorable median does not establish an adopted performance gain.

The strict target is still unmet. The latest complete screen has a 5.3454s
candidate median and no candidate edit below 0.500s. No single proposed change
has evidence supporting the remaining order-of-magnitude reduction.

The earlier [self-profile diagnosis](../../../results/strict-warm-self-profile-02/assessment.md)
records 18 compiler invocations, one build-script execution and five compiler
information probes. Its host nu-protocol interval is 3.610094s and nu-command
interval is 2.333229s. These are instrumented, overlapping intervals from an
older history, not additive components of the current 5.3454s measurement.
The [Cargo diagnosis](../../../results/strict-warm-cargo-profile-03/assessment.md)
retains the complete unit graph and readiness boundary.

Most downstream semantic queries already reuse results. Host and ordinary
nu-protocol each have 15 typeck_root executions and 10,128 hits; nu-command has
21 executions and 1,715 hits. nu-command optimized_mir records no provider
execution but 130.820ms of incremental loading. On pinned compiler
58e1e1f5311f4424ea81def4763081f6da62d9b3, dep_graph::alloc_and_color_node
(compiler/rustc_middle/src/dep_graph/graph.rs) already propagates unchanged result
fingerprints. A new coarse interface hash cannot be credited with eliminating
these already-reused queries.

Expansion, AST indexing, lowering and analysis retain eval_always query
boundaries in compiler/rustc_middle/src/queries.rs. The crate hash includes
owner/body hashes, source and owner spans, upstream crate hashes and options
(compiler/rustc_middle/src/hir/map.rs); full-MIR metadata contains actual bodies
(compiler/rustc_metadata/src/rmeta/encoder.rs). Metadata lookup validates the
complete crate hash (compiler/rustc_metadata/src/locator.rs). Skipping a Cargo
unit or substituting an old metadata artifact after a body edit is therefore
not a qualified optimization.

The saved host profile also contains 46 LLVM object-emission events: 1.121397s
LLVM_passes self time, 0.622037s object-emission self time and 0.317635s link_rlib
self time. The stable placement screens did not establish a gain. Equal machine
text would not establish equality of relocations, debug information or embedded
type/source data.

The existing tracked -Zhint-mostly-unused option defers native code generation,
but it removes ordinary exported roots before complete concrete-instance
validation. An uncalled public function can still trigger a monomorphized const
assertion or backend/target diagnostic. MentionedItems traversal alone does not
preserve the full ordinary used graph and validation obligations. Do not adopt
that flag on the native host route without preserving every original check.

The current HIR experiment has passed all 27 compiler controls and the
unchanged native fixture, with 335 verified cache hits under the required tree,
journal and poststate audits.
[Native qualification evidence](../../../results/hir-arena-native-qualification-01/README.md).
Application/exporter integration now has the bounded Ruff correctness evidence
above, but no latency gain; its structural coverage remains conservative.
The earlier Nushell selected-unit lowering event
was 251.869ms; that event is not an established removable budget. The separate
[span-handle map candidate](../../../experiments/proc-macro-span-handles/README.md)
preserves macro execution and compiler API calls while changing numeric lookup.
Its four standalone controls passed, but compiler-server integration remains
unqualified. The complete selected procedural-macro event was 391.138ms over
966 calls, with no handle-table attribution. Neither candidate alone explains
how to reach 0.500s. Continue actual correctness qualification and reject gains
that skip checks, rely on known edits or change the application.
