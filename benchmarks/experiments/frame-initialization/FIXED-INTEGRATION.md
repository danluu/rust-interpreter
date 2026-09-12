# Combining fixed clearing with the newer interpreter

The original fixed-clear comparison uses runtime source `6f9e148`. Main has
since retained the same-frame interpreter loop and complete scalar/integer
helper inlining. These touch the reference interpreter and host code generation;
their saved-runtime results do not qualify the combined executable.

Freeze main `ae0a49e` and candidate `46134e4`. Across the Cargo workspace, their
only source differences must be the two fixed-clear Rust files, unchanged from
`6f9e148`. Build both snapshots at the same absolute source and target paths,
with the pinned nightly, two host workers, no incremental compilation, dev/test
debuginfo disabled and release line tables. Run the entire workspace in debug
and release: baseline 297 passing tests and one ignored, candidate 300 and one
ignored. Preserve immutable VMs and both source manifests. Compose them with
the exact already-qualified exporter and wrapper; this isolates runtime changes
and does not claim a newly built frontend is qualified.

Before merging the runtime, require the following additional checks:

1. Run the existing full native differential validator (47,004 commands), TLS
   validator (245 commands), all 382 fre bodies with seven ignored, and all 52
   integration assertions on the combined candidate. Preserve native controls,
   errors, source pins, limits and strict frontend checks.
2. Compare the original fixed-clear candidate and combined candidate on the
   retained original artifacts of all nine library cases, in both engines.
   Use six alternating pairs after one warmup pair. Require unchanged outputs,
   instruction counts and peak guest memory. Fail any per-case wall or CPU
   regression exceeding both 5% paired median and 5ms between marginal medians.
   This material guard handles very short process executions; it does not alter
   the original complete-command 5% library gates. Publish private aggregates only.
3. Repeat the three complete es8 edit histories with the new main/candidate pair,
   rotating initial mode order. Keep the original 8% paired wall improvement
   and lower CPU requirements across 15 edited pairs. Do not pool the earlier
   confirmation. Original/wrong/edit/restoration controls and identical paired
   bytecode are mandatory.
4. Compare the combined candidate with the best retained fixed-clear candidate
   on token and folded fre using the original three-cycle, five-edit workflows.
   Require at most 4% paired wall and CPU regression on each primary, matching
   the upper measured A/A envelope. Do not infer cumulative gains by multiplying
   results from different sessions.

The original nine library gates remain required. Eight pass; Nushell type
relations still needs its recorded storage admission. Composition work may
proceed while that case is waiting for space, but cannot replace it. Keep any
failed or incomplete result and park the runtime if a gate fails. No threshold
changes or retries of executed failing timing gates. This is one integration
qualification, not a new optimization search.
