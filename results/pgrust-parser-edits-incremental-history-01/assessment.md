# Full parser edits with matched incremental compilation

The custom engine remains slower for this complete parser workload. Across 15
changed-source pairs, the median paired custom/native ratio is **1.230304 wall**
and **1.240211 child-tree CPU**: 23.03% slower and 24.02% more CPU.

| Quantity | Native | Custom A | Custom B |
| --- | ---: | ---: | ---: |
| Median complete edited build/test wall | 1.293799 s | 1.589814 s | 1.577664 s |
| Median child-tree CPU | 1.352339 s | 1.681546 s | 1.670008 s |

These independent command medians differ from the paired-ratio aggregation.
Identical custom B/A has median ratios 1.002833 wall and 1.002059 CPU. Maximum
absolute per-edit median deviations over three cycles are 3.8584% wall and
0.8718% CPU. These describe observed variation, not confidence intervals or
native-control uncertainty. This is a baseline comparison, not an optimization
adoption decision.

Both paths explicitly set `CARGO_INCREMENTAL=1`; other repository profile
settings remain unchanged. All 114 original gram_core tests run at every state,
including `tests_dump::c_reference_vectors`. Three cycles each contain original,
wrong initial-lookahead and five cumulative production-source edits, followed by
one final original state. Both paths use two Cargo workers. Native libtest keeps
its default test threads; custom execution uses two isolated prepared workers.
The five valid edits, not unchanged builds, supply the 15 timing pairs. Original,
wrong and restored states are correctness/cache-history controls. Installed
toolchains, standard MIR and downloaded dependencies predate fresh namespaces;
initial observations are not a completely cold-machine measurement.

The earlier 22-command experiment remains failed under its cross-cycle artifact
identity rule. After independently tracing the layout change to rustc allocation
sharing with function-template reuse disabled, a separate, prospectively revised
protocol requires exact custom A/B bytecode and catalog identity within each
cycle/state and records cross-cycle histories. Its audited 22-command prefix is
retained; only 44 unstarted commands run, totaling 66. Native/custom outcomes
agree, including wrong edits. Source and assertions restore; 4,928 frozen inputs
verify. No constant merging, address normalization or engine change hides the
layout difference. This does not prove arbitrary program equivalence across
compiler histories. [Allocation diagnosis](../parser-allocation-origins-01/assessment.md).

Custom-A median Cargo time is 1.137791s, its build-to-ready boundary is 1.170220s,
and execution is 0.386698s. Frontend and lowering medians are 0.200035s and
0.438694s. The exporter reuses a median 11,784 bodies and lowers 32. Prior-binding
time is 0.091000s and template decoding 0.035851s; their nested scopes must not be
summed as a disjoint decomposition. Native has already completed its build and
tests in about the time custom reaches execution. Guest runtime is therefore a
material part of the remaining complete-command deficit.

Both paths are faster in absolute terms than the separately observed repository
nonincremental profile, but these are separate comparisons, not a paired
cross-profile treatment estimate. The supported parser selection does not
establish whole-database coverage. Investigate the dominant reference-vector
test and the existing compilation decline before expanding JIT capacity.
