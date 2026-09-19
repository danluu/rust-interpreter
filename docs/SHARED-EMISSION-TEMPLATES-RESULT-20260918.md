# Shared emission templates: qualified, performance gate failed

Sharing native-emission templates between prepared suite workers did not clear
the changed-source pgrust parser speed gate. The32-command comparison preserves
all114 original test outcomes, the deliberately wrong edit, strict checking,
matching candidate/control artifacts and final source restoration.

| Five valid edited pairs | Candidate / adopted | A/A envelope | Ratio + envelope | Gate |
| --- | ---: | ---: | ---: | --- |
| Complete command wall time | 0.999311805 | 0.044733804 | 1.044045609 | Fail: must be below1 |
| Child CPU time | 0.997671428 | 0.045325435 | 1.042996863 | Pass: ratio at most1 and margin at most1.05 |

The observed wall improvement is0.07%, compared with4.47% control variation.
The median paired candidate/native wall ratio is1.332915. These engineering
gates are not confidence intervals, and failure does not prove the optimization
has exactly zero effect. It does rule out adoption under the frozen protocol.
Larger comparisons are cancelled; this unchanged candidate will not be retimed.
[Closed result](../results/shared-emission-templates-parser-screen-incremental-01/summary.json).

The experiment uses the same fully checked immutable Program within one suite.
Workers share bounded immutable emission templates, then copy/rebind words into
their own native arenas. Scalar admission and budgets, scalar target addresses,
assertion indices and guest state remain per owner. Normal publication alone
installs code. A changed immediate width, incompatible emitter option, full
store or other mismatch falls back to ordinary preparation. The option is
explicit and default off; one effective worker uses ordinary preparation.
There is no persistent native-file cache or skipped frontend checking.

Qualification passes635 Rust tests in each profile,434 Python tests,121 strict
native/reference/cache/Cargo commands and13 original-suite/CLI checks. Native
fixtures require real hits with simultaneously live separate arenas, and cover
limits, original faults, static/TLS reset, capacity fallback and concurrency.
In the original-suite compatibility run, the full parser restores797 templates
(3,799,956 native bytes); the wrong-source suite restores53. The original store
charges37,929,344 bytes within64MiB. Those counts establish actual reuse, not
time saved or allocator RSS. The one-entry private rg-aot suite correctly
stays inactive with two requested workers.
[Suite evidence](../results/shared-emission-templates-suite-01/ASSESSMENT.md).

The primary uses original source edits and independent native, adopted,
adopted-duplicate and candidate caches. All modes use two Cargo workers and
two test workers; all construction, population, locking, copying and reporting
remain inside command timing. Ordinary OS entropy stays enabled. The five valid
edits enter the gate; original, wrong-source and restored anchors do not.

Experimental tool:
`7a4e2bc034fc55c0ca89e174b0d403d0af8174eb8046443e09b11311d52af4ca`.
VM: `d071c9123c40cd9ee9ad4dd1bb13faed046373a7d743ebc85919b08c029e8ebd`.
The adopted exporter/wrapper are unchanged. Implementation and evidence remain
on `experiment/shared-emission-templates-20260918`; no experimental runtime is
merged to main. This remains a selected-function/test-body engine, with the
existing limitations on complete application threads, unwinding and OS support.

Next inspect preparation and constructor costs in the saved comparison receipts.
Overlapping worker durations cannot be added as command savings. Sharing ordinary
emission leaves scalar proof/lowering/emission and per-owner metadata work in
place, and constructing the shared scope adds validation. Those are hypotheses
to measure before another change, not an explanation established by this result.

The subsequent closed audit of all15edited custom receipts finds median summed
compiler intervals209.8ms adopted,211.9ms A/A and200.9ms candidate; largest-worker
intervals122.5/123.0/116.8ms. Owner constructor sums are44.0/44.2/43.7ms, with
another5.6ms of candidate store construction. These descriptive, overlapping
intervals do not change the failed paired gate. The next diagnostic will
attribute preparation by phase and function on the adopted runtime before
choosing another mechanism. [Audit](../results/shared-template-costs-01/ASSESSMENT.md).
