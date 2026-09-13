# Current Cargo interval attribution — draft, not executed

The complete composition retained Cargo timing HTML for Nushell. Reuse those
frozen same-tool edited observations first; no new compiler or guest run is
needed. The current pgrust comparison has no per-unit captures, so this audit
must not manufacture a pgrust unit split or attribute its residual to startup.

Reuse the qualified `cargo_timing_data.py` JSON-only parser and preserve every
unit ID, feature set and target label. In each command, compute the union of
reported unit intervals, the span from first to last interval, internal uncovered
gaps and the combined time outside that span relative to measured Cargo duration.
Cargo and the enclosing launcher have different clock origins. Preserve the
reported first-start label, but do not split the combined boundary time into
startup and finalization without aligned timestamps. Detect a reported span
longer than the enclosing duration and retain the inconsistency; do not clamp
a contradiction to zero.
These are measured scopes with an unexplained component, not a proof that
startup, fingerprinting, scheduler or I/O owns every gap.

Separate unit labels only when Cargo reports an explicit checked target or
build-script role. Unknown/empty target strings remain unknown. Category
unions overlap; report overlapping combinations or separate nonadditive
unions, not independently summed medians. Cargo unit duration is elapsed
process work, not CPU time. Existing exporter frontend/lowering measurements
are nested within the selected compiler process; no start timestamp means
one cannot position those subphases on the Cargo timeline.

Verify the complete case summary, plan/records hashes and every retained HTML
hash under the shared lock, then summarize all15 valid edited observations
per mode. Preserve wrong, original and restored captures as controls excluded
from edited medians. Freeze the audit source and inputs before running. Use
this to choose a targeted pgrust/current-unit capture only if missing data
would change the next implementation; it does not rerun a completed benchmark.

Only custom commands expose a separately measured Cargo stage. Native full
command time includes test execution, so do not use it as Cargo wall time.
Native unit distributions may be shown separately without that residual.

The retained comparison uses f0af2e3e (candidate) and f8713aaa
(baseline/duplicate), not the subsequently rebuilt main exporter. Report these
identities explicitly and keep this historical composition attribution distinct
from a fresh current-tool observation. Recheck its saved summary/plan/records,
all HTML hashes and custom launch keys. Analyze the45 valid edited custom rows;
retain other records as excluded controls. The active scalar Copy campaign
runs first, with no concurrent audit or tests.
