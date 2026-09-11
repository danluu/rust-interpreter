# Branching leaves: saved-trace call coverage

The earlier straight-line classification excluded branches and traps. This analysis allows the current native operation set plus Return and Trap, while retaining a separate category for leaves that need other VM operations.

| Workload | Direct calls | Calls to leaves with supported operations plus Return/Trap | Other leaf calls |
|---|---:|---:|---:|
| word64-inline8 | 17,360,078 | 8,678,263 | 831,791 |
| sha1-inline8 | 5,539,697 | 2,424,692 | 2,033,189 |

Source-op counts and dynamic call counts are not CPU-time attribution.
Profiles precede block linking; no assertion about current transition costs.
Return and Trap would require explicit native-call protocol; minimum block lengths and control-flow assembly are not proven by this classification.
All cold error paths remain semantically required.

A bounded inlining prototype must additionally prove call-site eligibility and initialization behavior, preserve cold failures, and measure code/storage growth. These counts are not a speedup prediction.
