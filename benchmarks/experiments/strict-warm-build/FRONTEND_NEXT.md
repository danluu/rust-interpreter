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
An exporter built for the final runtime path and application correctness remain
the next gates; these setup results establish no application latency gain.

The ordinary edit workflow can now compare application compiler flags with the
runtime, exporter, VM and prepared std held fixed. Flags are applied after tool
and std validation, and the runner supports the canonical shared workload lock
from a separate installation checkout. Its 67 focused controls passed, including
a synthetic complete edit history and mutation rejection. See
[workflow controls](../../../results/runtime-workflow-controls-03/README.md).
These controls do not replace a real cache-off/cache-on application history.

[Target selection](TARGET-SELECTION.md) retains Ruff as the immediate measured
development target, adds pinned Oxc as another development target, and keeps
Nushell for regression/stress coverage. Oxc's pinned source, registry and native
toolchain acquisition are complete. Its full library-test crate compiled and
the three unchanged plugin tests passed in the original, three edited and
restored states; the deliberately wrong edit failed all three assertions.
However, the installed auxiliary stripping executable could not find its LLVM
provider. The complete history and roughly 8–12-second edited-build observations
are retained as [warning-qualified evidence](../../../results/oxc-native-compatibility-01/README.md),
not a clean performance baseline. A matching official toolchain component is
being inspected before a fresh clean history. No holdout success is claimed.
The sub-0.500-second target remains unmet.

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
Application/exporter integration and a latency gain remain unqualified; its
structural coverage remains conservative. The selected-unit lowering event
was 251.869ms; that event is not an established removable budget. The separate
[span-handle map candidate](../../../experiments/proc-macro-span-handles/README.md)
preserves macro execution and compiler API calls while changing numeric lookup.
Its four standalone controls passed, but compiler-server integration remains
unqualified. The complete selected procedural-macro event was 391.138ms over
966 calls, with no handle-table attribution. Neither candidate alone explains
how to reach 0.500s. Continue actual correctness qualification and reject gains
that skip checks, rely on known edits or change the application.
