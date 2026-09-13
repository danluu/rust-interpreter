# Immutable external trait-name index

Unapplied, uncompiled source prototype against compiler
`58e1e1f5311f4424ea81def4763081f6da62d9b3`. It has no measured coverage or speed
result. The active MonoItem compiler, tools, standard library and Nushell source
are unchanged. No holdout was inspected.

`rustc_resolve/src/lib.rs::trait_may_have_item` scans every binding key of an
external trait whenever a field or method name is considered. Repeated requests
for the same trait therefore repeat the scan. The candidate stores an exact
set of `(Symbol, Namespace)` pairs when that immutable external table is first
queried by this predicate, then performs ordinary set membership.

The experimental `-Zindex-external-trait-items=yes` option is tracked and off by
default. The patch adds its unrun assertion to the compiler's existing tracked
option test. Both paths first call the ordinary `resolutions` method, including its
lazy metadata/reduced-graph construction. External resolution tables are
published through `OnceLock`; `resolutions_mut` rejects external tables. Only
the immutable binding-key projection is retained for this compiler session.

The predicate deliberately includes all keys, even when no best declaration is
available, and deliberately ignores hygiene and underscore disambiguators, as
the original scan does. Namespace is part of every lookup. Local modules retain
the current scan, including misses, because expansion and import resolution can
still change their tables. Trait aliases and unspecified item names still pass
through the original conservative `true` branch.

Every scope walk, trait order, hygiene/type check, import traversal, glob-map
update, unused-import mark, diagnostic and macro invocation remains in the
ordinary compiler. The patch does not cache trait-candidate results, metadata
across sessions, expansions, or build outcomes. Index allocation and creation
are part of the compiler command. The extra once-cell can enlarge the resolution
enum, including local modules; memory use and small-table overhead must be
measured alongside any reduction in repeated scans.

The saved Nushell self-profile attributes 119 ms of self elapsed time to selected
test `late_resolve_crate`, but does not attribute time to this predicate. It
cannot establish the proposed saving. This patch alone is not evidence of a
route below 0.5 seconds.

Before a compiler build, independently review the immutable-table proof and
prepare native off/on controls for present and absent names, all namespaces,
hygiene/disambiguator projection, aliases, macro-created local traits, reexports,
unused imports and ambiguous methods. The eventual full compiler needs its own
identity and ordinary option-hash, raw-diagnostic, native/edit/restore and strict
export qualification. An exact predicate shadow check can establish actual
equivalence during qualification; timing must use the ordinary fast path with
no shadow work. Those compiler builds and controls remain unrun.
