# Cargo timing cycle after the Nushell API edit

The complete instrumented cycle passed all fourteen original assertions and
wrong-edit controls: nine primary commands, three independent checks, six paired
bytecode artifacts and nine preserved Cargo HTML snapshots. The source was
restored and all ten frozen script/case hashes matched. Ordinary workflow
verification ran before [unit analysis](../interface-nushell-unit-analysis-01/assessment.md).
The qualified parser retained all units, features, sections and overlap.

All three edited commands rebuilt 19 units. Native's largest reported unit was
`nu-command` at 6.57 s, compared with 1.12 s baseline and 1.24 s candidate checks.
Both custom histories also rebuilt a host `nu-protocol` library (1.77/1.99 s),
an ordinary checked library (1.24/1.42 s), and the selected test target
(1.38/1.39 s). The [separate fingerprint inventory](../compiler-unit-fingerprints-01/assessment.md)
records distinct features/profiles/target contexts. The host theme-generator
dependency is real; units cannot be merged by crate name.

Reported intervals overlap. Their union was 11.49 s native, 4.98 s baseline and
5.19 s candidate; complete command times were 12.125, 5.539 and 5.830 s. Neither
interval sums nor unit unblocking lists are CPU times or a causal critical path.
These are single instrumented samples from fresh caches, kept separate from
the fifteen-cycle performance comparison. Timing generation is included.

The next bounded pipeline experiment removes the heavy exporter from ordinary
compiler routing while preserving all required Cargo units, strict checks,
std-MIR flags and host build tools. The separate version-probe diagnostic puts
current routing overhead near 9.7 ms per invocation, which is useful scope for
cold builds but cannot explain most of this warm command's latency.

[Workflow samples](summary.json) · [Verification](verification.json)
