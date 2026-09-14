# Demand-region fixture qualification

Use immutable candidate e5ddb4243a9062d03d2cacae1749d805b5a72f436838891e3f434b854a8dbf00
with the exact adopted exporter/wrapper. All selected demand runs use explicit
resumable/persistent/scalar/demand flags. Preserve the existing interpreter and
ordinary JIT fixture controls, native comparisons, full compiler checking and
source edit/restoration protocol.

Run the established 121 fixture/cache commands with demand execution selected
where the candidate was selected, plus one independent rejection of a genuinely
partial-validation artifact using demand mode without scalar mode. Verify 122
command outcomes, original/helper-edit/restored outputs and artifact identities,
unreachable type/borrow errors, automatic-cache fallback and restoration. Record
launcher demand selection. These are correctness fixtures, not timings of a
large project's changed-source development loop.

Original project profiles will use versioned demand operation maps, exact
per-PC logical counts and the saved entropy tapes. The adopted control profiles
remain immutable and independently bound. Performance commands use ordinary
entropy and exclude code-dump/profile I/O.
