# Retained exporter: measured cost breakdown

Seven original token commands completed: an initial build, the deliberately wrong production edit and five real edits. All seven artifacts were byte-identical to retained-compiler snapshots. Original assertions and source restoration passed. This is instrumented attribution, not a speedup comparison.

| Exclusive emit stage | Median over five edits |
| --- | ---: |
| lower_graph | 691.0 ms |
| validation | 5.1 ms |
| serialization | 14.0 ms |
| bytecode_publication | 30.4 ms |
| call_report_hash | 48.6 ms |
| remaining | 3.0 ms |

The lower_graph interval contains the following inner stages. Do not add the two tables.

| Exclusive lowering stage | Median over five edits |
| --- | ---: |
| entry_selection_and_registration | 8.0 ms |
| reachable_mir_and_local_passes | 464.3 ms |
| adapters_and_program_assembly | 7.4 ms |
| aggregate_relocation_and_reports | 96.8 ms |
| call_optimization | 60.8 ms |
| control_flow_optimization | 54.0 ms |

Aggregate capture accounts for 95.8ms inside reachable MIR/local passes; finalization accounts for 96.8ms in aggregate relocation. These are nested timings, not additional costs.

The observer passed 39 exporter package tests. Retained/off/on fixture artifacts match exactly; 18 interpreter/JIT/native comparisons and two uncalled type/borrow rejection checks passed. The observer uses the retained VM and wrapper binaries. Its source is ordinary Git code at `7b5062a`, branch `experiment/export-costs`; no guest backend changed.

Decision: do not start another full primary for serialization, validation or publication micro-optimizations. Together, validation, serialization, publication and the artifact hash cost about 98ms—roughly 2% of the last complete token command, even if eliminated entirely. Graph lowering/reuse is the substantial frontend opportunity. The next control work compares native debuginfo settings before further adoption claims, then evaluates reuse at function/Cargo-target granularity.

The pinned pgrust and Ruff manifests already request line-tables-only debuginfo, and pgrust requests unpacked split debuginfo. The current comparisons override optimization and incrementality, so the next native study must record effective test flags instead of assuming every baseline uses full debuginfo.

Preserved setup failures: the first build driver expected the wrong test count, although all 39 tests passed; the first profile passed transparency checks but failed space admission before any real workload edit. A single completed 103.5MB logical host compilation cache was removed after ownership/open-file/protected-evidence checks; no archive was created. The successful workload retained all samples and reused existing byte-identical snapshots.
