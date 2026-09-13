# Stable placement of monomorphized roots

This is an **unbuilt source-only experiment**, based on compiler commit
`73a11f167216d3955c277ed47f9b8cc68208105b`. The patch has not been applied to
that checkout. Its compiler, standard library, package05, and package06 remain
unchanged. The new tests have not run. There is no performance or 0.5-second
claim.

Root review and an independent source review found no remaining source-level
blocker in this draft. Those reviews do not establish that the new compiler or
its proposed controls compile or pass.

The earlier stable-module policy can stabilize merges but cannot subdivide a
large source CGU. Saved host-object inspection found thousands of small Rust
functions in two expensive objects, including many drop-glue roots. That
motivates trying stable placement of individual monomorphizations. It does not
establish query reuse or a timing improvement: common raw instruction extents
were compared, while relocations and debug information were not. Historical
object hashes were not recorded at the original command; the evidence binds
retained objects to recorded command and modification-time windows instead.

## Proposed behavior

`-Zstable-mono-cgu-partitioning=yes` is a separate, default-off, tracked option.
Enabling it together with `-Zstable-cgu-partitioning` fails during option
construction, including metadata-only invocations. There is no launcher or
wrapper change in this experiment.

Activation requires incremental compilation, coverage disabled, no collected
global-assembly item, naked function or explicitly linked item, and more
`GloballyShared` roots than the configured CGU count N. All other cases retain
ordinary grouping. The
pre-scan examines every collected item before choosing the policy, including
items after the root count first exceeds N. An inactive option returns before
that scan. The existing collector-owned sorted vector is borrowed, not copied.

An active invocation creates exactly N buckets, including empty buckets. Their
crate-qualified names contain `stable-mono-cgu-v1`, N, and the bucket index.
Including N matters because the existing `-Ccodegen-units` option is untracked.
Every bucket receives the normal mangled CGU symbol name. The policy hashes
each root with the compiler's existing `MonoItem::to_stable_hash_key` and takes
the result modulo N. This key includes the stable item definition, instance
kind, and generic arguments; it does not use the function body, estimated size,
numeric session IDs, source paths, or benchmark identity. A hash chooses a
bucket only. The complete `MonoItem` remains the map key, so collisions cannot
deduplicate different functions.

Only the root's destination name changes inside ordinary placement. The same
root linkage, visibility, internalization eligibility, size computation, and
complete transitive `LocalCopy` reachability closure are used. An active
invocation skips both merge implementations, which would otherwise regroup or
rename those buckets. It keeps ordinary size calculation, name sorting,
internalization using the unchanged usage graph, primary-CGU selection, symbol
collision checks, and codegen dependency tracking. The collector's existing
stable item ordering also preserves deterministic insertion into item maps.

The root-count threshold permits a large flat module to split and avoids
creating N empty-heavy objects for tiny crates. Crossing that threshold, or
changing N, deliberately changes grouping. A fixed N and an unchanged eligible
root identity keep that root's bucket stable. This does not promise that only
one object changes: modified generic instances, LocalCopy dependencies, spans,
types, or compiler-generated definitions can legitimately affect others.

## Pinned safety boundaries

All pointers below refer to the unmodified base `73a11f`:

| Interface | Preserved contract |
| --- | --- |
| `rustc_middle/src/mono.rs:143` | Existing exactly-once and LocalCopy classification, including entrypoints, statics, generics, and drop glue. |
| `rustc_middle/src/mono.rs:237` | Explicit linkage is detected before splitting any group; it retains the stock path. |
| `rustc_middle/src/mono.rs:329` | The existing stable MonoItem key supplies identity-sensitive placement. |
| `rustc_middle/src/mono.rs:346` | CGU contents, size, primary and coverage flags remain stable-hashed. |
| `rustc_middle/src/mono.rs:601` | Sorting remains by the CGU's name string. |
| `rustc_monomorphize/src/collector.rs:1941` | Incoming monomorphizations already have deterministic stable order. |
| `rustc_monomorphize/src/partitioning.rs:257` | Existing root linkage and visibility are calculated after choosing placement. |
| `rustc_monomorphize/src/partitioning.rs:278` | Existing transitive LocalCopy closure is copied into each root's actual destination. |
| `rustc_monomorphize/src/partitioning.rs:590` | Existing internalization examines actual final placement and users. |
| `rustc_monomorphize/src/partitioning.rs:1228` | Collection, target checks, constant-evaluation failures, and duplicate-symbol checks remain in their normal order. |
| `rustc_codegen_llvm/src/base.rs:64` | Compilation still enters the ordinary CGU dep-task and reads its current contents. Stable names do not authorize reuse. |

Global and naked assembly conservatively disable the policy for the entire
collected crate because arbitrary assembler state and raw labels are not fully
represented by the usage graph. This includes imported naked instances when
they are collected locally. Explicit linkage also disables the policy: an
explicitly internal static or function can require co-location with its users,
and retaining its linkage while splitting that group could break linking.
The initial fallback covers all explicit linkage kinds rather than claiming
that every non-internal kind has been qualified. Coverage uses stock grouping
to preserve the
existing selection of a linker-retained CGU for unused-function records. This
experiment neither removes checks nor saves an unchecked analysis result.

## Prepared qualification

The patch adds one codegen-unit expectation and one run-make fixture, plus the
tracked-option hash assertion. These are proposed controls, not passing results:

- A flat module with two roots and a shared inline body exercises placement
  even when source-module merging would not activate.
- Edited/restored native results exercise generics, drop glue with observable
  destructor effects, referenced statics, TLS, multiple buckets, and optimized
  and unoptimized downstream compilation.
- Same-width body edits check stable item placement and some unchanged CGU
  reuse; appended roots check the placement of existing roots. These are
  narrow identity controls, not substitutes for later real edits that move spans.
- On/off transitions and changing N share caches; threshold histories use
  exactly N-1, N, and N+1 simple roots. A larger flat no-std crate exercises
  empty buckets and links a real consumer.
- Coverage, nonincremental mode, explicit internal linkage, and supported-host
  global/naked assembly compare
  ordinary and option-on placement. Unused type/borrow errors still fail and
  restoration succeeds. Simultaneous policies fail even for metadata emission.
- Actual option-on native executables retain and run their entrypoints across
  edits, independently of a consumer compiled with the option disabled.

Before building, review this patch, then apply it only to a new owned compiler
checkout. Use the existing exact-base CI LLVM and a separate build/package key.
Formatting, focused tests, native controls, complete distribution support-tool
qualification, and interpreter integration are required before a matched
whole-command screen. Builds and tests need the shared lock, a two-job limit,
recorded process identities, and the existing projected-space plus 8 GiB guard.
No setup or qualification run is authorized to change another workload.

## Costs and limitations to measure

The pre-scan adds classification work; active roots are stable-hashed again
after collection. Random placement may duplicate more LocalCopy code and debug
types, reduce same-module inlining, make cold builds and linking slower, or
hurt runtime and code size. Fixed buckets can remain imbalanced or empty. An
individually large function cannot be split, and changes to a widely used
generic can still invalidate many buckets. Threshold crossings discard the
placement benefit. Ordinary debug information and all downstream profile
settings must remain equal in any comparison.

The current stable-module compiler is an optimized, assertions-on qualification
build. A later production-profile compiler is a separate experiment. Comparing
off/on in one identical compiler isolates placement; comparing qualification
and production profiles does not. This patch must not receive credit for a
compiler-profile change, omitted Cargo unit, skipped check, precomputed answer,
or narrower definition of edited build-to-validated runnable artifact.

## Reproducing the patch without changing compiler sources

Run `python3 experiments/stable-mono-cgu/make_patch.py /absolute/frozen/compiler`.
The generator requires the exact clean tracked base, reads its four compiler
files, and writes only this directory's patch and source identity. Adjacent
test files are the source for the two new tests embedded in the patch.
