# Exact heap ownership metadata experiment

The candidate changes the live-allocation ownership table from BTreeMap to the
standard seeded HashMap. All uses are exact-key lookups, insertion, removal and
count/emptiness checks. Guest address selection still uses the original ordered
free-range tree and its lowest-address first-fit policy. Allocation, alignment,
coalescing, zeroing, static prefixes, budgets, errors and reallocation bodies are
unchanged. The feature is explicit and disabled by default; the installed adopted
runtime remains unchanged. No earlier rejected optimization is composed here.

The hypothesis comes from closed adopted sampling (73/155 heap-context self
samples in the two partial windows). Those samples do not establish a speedup.
Only original source-edit end-to-end comparisons can admit this candidate.

Qualification retains the byte-identical adopted heap implementation as a test
reference. Sixteen heap controls and six C allocator controls passed in debug and
release, including128000 generated operations/profile comparing exact returned
addresses, errors, live layouts and all guest bytes. Whole-workspace qualification
passed618 Rust tests with13 ignored in each profile, and446 Python tests with22
skipped. A disk admission stop preserved that passing prefix; only the unstarted
VM build resumed. Its hash is8705a17ea9b2d909d834fdc1850835d18f08b596772dc112a817262cb3472e02.

Three original fre assertions passed with exact per-original-PC counts, memory
peaks and entropy. Logical instruction totals are15849531264,13363262210 and
4291122869. Generated code sizes are11952720,14508196 and1978352bytes. The emitter
itself is unchanged. Scalar calls embed absolute entry addresses, so raw bytes
vary with ASLR. The initial overly strict byte-equality failure is preserved.
A separately qualified verifier proves each address is exactly that process's
arena base plus the mapped entry for the original Call's callee, and requires all
remaining instruction bits and semantic maps to match. Nine adversarial controls
reject incorrect targets/registers/opcodes/branches, noncanonical immediates,
changed maps/callees and invalid entry/span bounds. It verified427/532/21 scalar
relocations. The first passing guest execution was reused without replay.

Explicit tool da177909 composed the retained VM with byte-identical adopted
compiler tools and revalidated the121-command strict/cache frontend proof. All17
benchmark-controller controls passed. The original40-command changed-source primary
and2unreachable type/borrow rejections passed their correctness requirements.
Its median candidate/adopted wall ratio was0.981239792, with A/A variation0.051989623;
ratio plus margin1.033229416 failed the original wall gate. CPU ratio0.979778617
and margin1.020337664 passed their ceilings. The candidate/native wall ratio was
1.625525. The nominal improvement does not establish a speedup.

PARKED. All unstarted larger guards are canceled; no unchanged rerun or relaxed
gate. Default/runtime source remains adopted. The candidate and complete evidence
remain available on experiment/heap-layout-table-20260919. See
results/heap-layout-screen-token-01/assessment.md for the closed measurement.

Closed receipts: heap-layout-table-focused03, heap-layout-workspace02,
heap-layout-native-comparison01 and heap-layout-profile03 under results/.
Earlier failed attempts remain separate and source-bound, including the filter
count error, lock timeout, disk admission stop, stale observer import, and raw
ASLR-address comparison. Tests/guests that passed were not replayed for reporting.
