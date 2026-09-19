# Cost of preparing templates for the current program

The diagnostic replay points to key serialization/hashing as a useful bounded
component to improve, while emission on misses remains the largest measured
preparation component. For the ten worker records across five valid cached edits:

| Phase | Median elapsed ms per worker |
| --- | ---: |
| Key serialization/hash | 8.883 |
| LRU lookup | 0.426 |
| Validation/restoration | 1.463 |
| Emission after a miss or key decline | 25.681 |
| Capture and insertion | 1.186 |
| Independent verification | 0 (disabled) |

The enclosing ordinary-preparation median is37.913ms. Worker intervals overlap;
these are not CPU or command savings. Medians do not add exactly. Both workers'
key intervals sum to a median17.974ms per request, which is also not wall time.

Sourcee3feaebf adds six fixed counters under jit-preparation-observer; each observed
expression executes exactly once, including failed Results. No key, emission,
relocation, admission or cache-limit policy changes. Feature-off fields/clocks
are absent. All22model and33integration controls pass in each profile;32feature-off
integrations pass. Qualification01's controller expected33feature-off tests, but
one test exists only with the observer. It is closed with all five tests commands
successful. Recovery02 incorrectly parsed a hash-matched intentionally malformed
JSON fixture, stopping before any build. It is closed with zero new workload.
Recovery03 hashes opaque fixture outputs, reuses all five completed tests and
binds separately built diagnostic release binaries. Source52d0d158 completes
13211/13214, closed14683/14686. No tests were rerun for either bookkeeping correction.
[Qualification](../results/session-template-phases-qualification-03/summary.json).

Actual parser replay7db32707 completed16413/16416, closed26524/26527. All16suites and
1,824invocations match original outcomes and exact wrong-edit failure text, with
16,333observed hits. Verification is off for attribution; the preceding ordinary
candidate replay independently verified16,865hits. Phase sums stay inside ordinary
preparation, all limits and bounded histories hold, and kernel CPU reconciles.
[Replay](../results/session-template-phases-parser-01/summary.json).

Next test buffering the many small bincode writes into SHA256. Preserve the exact
serialized key bytes, v3 domain, complete current inputs, per-write size limit,
trusted-memory-only templates and all restoration checks. Qualify segmented writes,
flush/finalization and rejected writes against direct SHA256 before actual parser
verification. Do not promise an end-to-end gain from these diagnostic intervals.
The full digest guard remains unmeasurable; no unchanged repeat or adoption.
