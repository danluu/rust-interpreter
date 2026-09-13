# Prospective full scalar Copy operand comparison

The40-command screen passes with wall−5.46% and CPU−3.47% against current
main d4a6ff9a, beyond4.84%/2.57% A/A. This is preliminary evidence only. The
full comparison uses new namespaces and complete fresh source histories;
none of those five screen pairs enters its result. Runtime185cc7b9, source
c37367f, retains exact e729a493 exporter/wrapper binaries. Baseline and duplicate
use qualified d4a6ff9a throughout, including the same disabled operation-map
infrastructure. All three have automatic function caching and cached lookup.
Fixed anchor fe9dcae0 retains its original options. The parked shift and
arithmetic candidates are absent. The baseline proof join is identical to
WORKFLOW.md: seven unprofiled tests, three exact adopted-code/per-PC controls,
436 tests/profile and the prior203-command cache proof for unchanged exporter
bytes. The new VM receives441 tests/profile and fresh203 cache checks.

Run cases in this fixed order: token, folded, pgrust, private rg-aot, Nushell
(type-relations). Stop before starting the next case if any complete case
fails its gate or a correctness/admission check fails. Keep every command and
failure. No repeat, pair splicing, native-setting change or gate adjustment
after observation. Adoption requires all five cases and final source/input
verification. A storage admission failure before a case starts permits a new
admission after safely retiring completed caches; it adds no timing samples.

Each case runs three cycles of original/wrong/five cumulative valid production
edits, then a final original restoration. Keep all original tests unchanged:
token12, folded18, the established pgrust selection, private1 and Nushell14.
Only the15 valid edits enter paired ratios. Use two Cargo workers, two prepared
custom workers (one for the private single test), normal OS entropy, and native
libtest default concurrency. Preserve pinned sources, guest MIR flags and
runtime limits from the recorded cases. Strict checking remains mandatory.

Token/folded/pgrust:154 commands each, four custom modes (baseline, duplicate,
candidate, fixed anchor), ordinary native Cargo, native line tables, and Cargo
check. Use the retained four-order Williams custom schedule and alternate
native placement. Nushell/private:132 commands each, baseline/duplicate/
candidate plus those three native controls; the retained six-order custom
schedule balances the15 edits. Capture Cargo unit timing reports there.
The full maximum is726 commands. The exact executable schedules and all
inputs are frozen before the first command.

Compute candidate/control ratios at each edit before taking the median.
The A/A envelope is the maximum, across the five edit positions, of the
absolute deviation from1 of the three-cycle median duplicate/baseline ratio,
separately for wall and CPU. This is an engineering margin, not a confidence
interval. Primary token must satisfy candidate/adopted-baseline wall<1−AA,
candidate/fixed-anchor wall<=0.92, CPU ratios to both controls<=1, and the
worse of those CPU ratios plus CPU A/A<=1.05. Fixed-anchor improvement includes
already adopted work and cannot substitute for the incremental primary gate.
Folded/pgrust require the worse candidate/baseline and candidate/anchor ratio
plus the corresponding A/A<=1.05, independently for wall and CPU. Nushell and
private require candidate/baseline ratio+AA<=1.05 for wall and CPU. There is
no extra independent A/A ceiling or undeclared held-out CPU ceiling.

Each complete case holds the shared benchmark lock with45-second admission.
No other own build, test, profile or cleanup overlaps it. Free-space admission
is14GiB for each fre case,10GiB for pgrust,8GiB for private. Nushell retains its
recorded conservative cache estimate:8GiB reserve plus1.2 times six native-cache
estimates (50,500,745,555 bytes with the retained estimate). Require8GiB before
every command. Check the independent sampler and ownership before admission;
headroom may change because other sessions are active. Retire only exact
completed public compiler intermediates under the retention policy if needed.
Do not control another session, delete private caches, or start a new cleaner.

Prerequisites:441 Rust tests per profile,125 current harness checks, seven
exact real selections, nine suites,203 strict native/cache checks, three
profiles preserving per-PC work/memory/entropy and exact operation-map reconstruction, and the complete passing
screen. All source, tool and harness identities are recorded. Private source,
test names and raw data remain local; published private results are aggregates.
