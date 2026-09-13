# Prospective five-project composition comparison

The candidate combines memory runtimef0af2e3e with cached identity lookup;
baseline and A/A duplicate use wide runtimef8713aaa with fresh lookup.
Their exporter/wrapper bytes match. Three compute cases additionally retain
the fixedfe9dcae0 anchor with fresh lookup and its original function-cache
policy. Other cached custom modes use automatic compiler-proven function
reuse. Ordinary native Cargo/libtest, line-tables native and Cargo check stay
in every case. These measurements assess the composition, not separate
component effects.

Run in storage order: Nushell type-relations, private rg-aot, token, folded,
pgrust. All five cases are required regardless of performance results. No
default or runtime-source adoption occurs until every guard and subsequent
integration verification passes. This is a new combined configuration; the
completed memory-only and lookup-only failed adoption decisions remain intact.

Each case uses three cycles of original, deliberately wrong and five cumulative
valid production edits, then compiled restoration. Only fifteen valid edited
pairs enter medians. Keep original test assertions, every A/A pair and every
expected failure. Each mode receives changed source each time; no unchanged
build/run loop is a latency sample.

Token, folded and pgrust retain the seven-mode memory comparison:154 commands
per case. Four custom orders are0132,1203,2310,3021, with0 baseline,1 duplicate,
2 candidate and3 anchor. Nushell/private use six modes and132 commands per
case, rotating custom orders012,120,201,210,102,021. Native order and placement
around each custom group alternate; check runs last. Total:726 commands,
75 edited candidate/control pairs and75 A/A pairs. Fifteen edits leave an
incomplete final block in the four-custom schedule, as in the prior comparison.

Every route uses two Cargo workers. Custom suites use two prepared workers,
or one for the singleton private selection, with fresh guest state per test.
Native uses default libtest concurrency. Existing selections, source pins,
guest flags and limits are retained from the recorded reference workflows.
The larger-case limits are100billion logical instructions,150,000 allocations,
64MiB memory and4096 frames. Custom artifacts and catalogs must match at every
state. Every candidate lookup after its first original state must be a hit;
all controls must report fresh lookup. Initial setup observations are separate.

Keep the memory comparison's engineering rules. For each wall/CPU A/A envelope,
take the largest absolute per-edit median duplicate/baseline deviation across
three cycles. The primary token requires candidate/anchor wall<=0.92,
candidate/wide wall<1−wall envelope, CPU ratios<=1 against both and the worse
CPU ratio plus its envelope<=1.05. Folded/pgrust require the worse ratio against
wide/anchor plus its envelope<=1.05, independently for wall and CPU.

Nushell/private guard the new composition against the qualified wide control:
candidate/wide ratio plus the corresponding A/A envelope must be<=1.05 for
both wall and CPU. There is no independent absolute noise ceiling. This applies
the composition margin to the new larger-case comparison; it does not change
the old lookup-only trial's4% wall/3% CPU noise limits or its failed decisions.
The envelopes are descriptive engineering margins, not confidence intervals.

Before timing require the138-test harness proof,20-command combined Cargo
proof, unchanged installed binaries and reused memory runtime qualifications.
Freeze all scripts, plans, source pins, tool bytes and proof hashes. Hold the
shared benchmark lock throughout each case, with45-second admission. Nushell
reserves8GiB plus six public caches at120% of the recorded original size,
currently47.03GiB total. Private/pgrust reserve8GiB; fre reserves12GiB. Keep8GiB
before each child and inspect the independent disk sampler. Do not assume
headroom persists or alter other workloads. Any needed retirement is limited
to exact completed disposable public outputs, preserving binaries and evidence.

Stop on unexpected outcome, provenance, lock or storage failure. Preserve the
failure without automatic retry, partial-pair substitution, outlier omission
or retiming to cross a threshold. A completed gate is never rewritten.
Report total wall/CPU, native controls and nested lookup/Cargo/export/VM stages.
Keep private source, test names, commands and Cargo unit labels local; publish
only aggregate counts, ratios and evidence hashes for rg-aot.
