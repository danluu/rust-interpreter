# Single input walk on the current options-hash compiler

This is an isolated **source-only, uncompiled, unqualified, unmeasured** candidate. It changes no held compiler checkout, installed runtime, screen input, or previous candidate. `candidate.patch` changes `input.rs`, the caller in `mod.rs`, and the required source identity. The existing options-hash query and every later lowering/replay check remain byte-identical.

The constructor design is reused from `../hir-input-walk`; its real-AST qualification proposal is reused from `../hir-input-walk-audit`. Those older artifacts are also unqualified. The new patch applies to the exact held N options-hash sources, not their older base. `prepare_source.py` checked the entire inherited 25-file acyclic identity map before and after writing these separate copies.

`input::probe` already builds both normalized `Input` and `Walk::ordered`. The old caller immediately reconstructs the same walk in `current_nodes`, encodes both inputs, compares them, and returns the second node vector. The candidate returns the first two products together through private `ProbedInput` fields and consumes them with `into_parts`. Only successful completion of the original gate constructs that value.

## Source equivalence and its limits

`source-comparison.json` records exact byte comparisons, and `source-proof.json` pins the supporting compiler sources.

- The entire `Walk` implementation, `Atom`/`Input` encoding definitions, `Probe` statistics and first-pass gate are byte-identical. Node checks insert the ordinal and ordered node together. `resolved` traverses a clone of that same order and does not alter the original vector. There is no second constructor that can pair unrelated products.
- The only production call pair is consecutive, with the same immutable AST/resolver references and no intervening lowering, user code or query. Accessed resolver maps and trait slices are ordinary immutable data; the resolver's separate `Steal` fields are unused.
- `TyCtxt::def_path_hash` uses `definitions_untracked` or `cstore_untracked`. Local hashes index the current definition table; external hashes read the current metadata table. This repeated walk does not add a semantic query/dependency observation. All first-pass reads remain. Local hash lookup does have optional internal trace instrumentation.
- Span position access can trigger `SPAN_TRACK` for parented spans. Both the owner and every accepted visited span reject a parent before position access; `parent()` itself is untracked. The original first-pass checks and rejection boundaries remain, including partially visited rejected bodies. Source-map snippet reads occur only in `probe` and remain unchanged.
- Literal validation is **not entirely side-effect-free**: escaped strings, byte/C strings and underscored numbers can intern normalized bytes. The first walk keeps every conversion, error/panic boundary and insertion in the same order. The removed walk sees already interned bytes; the locked occupied-entry path returns the existing index and does not append an interned symbol. It can still reserve hash-table capacity before finding that entry. Removing duplicate temporary allocations and capacity bookkeeping is permitted; identical allocation/OOM timing is not claimed.
- Numeric literal helpers and local definition hashing can emit internal debug/trace events. The candidate removes their duplicate events when such logging is enabled. It does not promise byte-identical internal compiler logs. These are distinct from user diagnostics, warnings, tracked feature uses and HIR effects. If exact internal trace-event multiplicity is required, this consolidation is unsuitable and must not be adopted under that requirement.

The source argument establishes identical normalized input bytes and ordered nodes for the same accepted compiler input, and the same first rejection for invalid inputs. It does **not** replace actual differential qualification. The removed `qualified-walker-disagreement` check is a redundant-construction check, not a relaxed eligibility gate: its invariant now follows from returning both values from one walk.

The `Input` encoding and later key recipe are unchanged. Full persistent keys intentionally differ because `SOURCE_IDENTITY` is recomputed from the current complete closure; claiming full key equality across compiler identities would be incorrect. For qualification, compare normalized input bytes and key bytes with only that required identity component normalized. Old cache records must not be admitted to the new compiler identity.

`mod.rs` is byte-identical after reversing the single call-pair replacement. This preserves ordinals, binding/trait flags, kind classification, resolutions, entry binding, the options-hash call, journal/tree/current-context validation, cold materialization, and hit trace/recapture/poststate checks. Parsing, expansion, resolution, ordinary fallback lowering, diagnostics, type checking, borrow checking and downstream dependency handling are not bypassed.

## Qualification before any build or measurement

`qualification-plan.json` binds the existing real-source fixtures and exact old `current_nodes` oracle. No tests have run here. A separately identified audit compiler must execute the old function on each actual accepted AST, compare its encoded input and ordered nodes with the new constructor, and fail on disagreement. The audit compiler must never be used for timing.

Reuse the complete existing capture/reuse run-make controls, including cold/edit/restore histories, trait changes, invalid/corrupt records, diagnostics and source/compiler identity checks. Reuse the existing accepted literal/resolution/pattern fixtures, rejected syntax/hygiene fixtures and fixed resource-boundary fixtures. Compare unfiltered JSON diagnostics and behavior with info reporting disabled. Unconstructible malformed AST/resolver cases remain source invariants until separately reviewed internal fixtures cover them; ordinary Rust files do not prove those branches ran.

Only after that actual qualification may a separately built performance identity run the ordinary strict application checks and a reviewed measurement. No new build, benchmark, provider probe or holdout read is authorized by these files.

## Why this is only a candidate

`attribution-erratum.json` is the exact `ac120599…` sidecar. The historical 13,491 capture messages include 10,570 replayed dependency messages. Actual cold captures were 2,921; each of seven warm Ruff invocations had 1,411 actual hits and zero new capture messages. The unchanged original eligibility report remains bound by screen03. Replayed diagnostics are not a lowering-work optimization target.

Older saved profiles place expansion, including 2,396 procedural macro expansions, ahead of lowering in total frontend cost. They use an older compiler and cannot quantify this candidate's cost or speedup. This proposal only removes duplicate input preparation on eligible bodies; it neither caches macro results nor claims the complete application target is reached.
