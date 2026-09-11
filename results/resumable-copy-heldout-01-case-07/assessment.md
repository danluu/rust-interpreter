The private rg-aot workflow passes its held-out regression guard. All 63
primary commands, 21 independent checks, fifteen edited pairs and 42 executed
artifacts verify. Original assertions and wrong-edit controls are preserved;
tracked sources are restored. Corresponding artifacts match, and cross-cycle
identity is true. Only aggregates are published here.

| Measure | Native Cargo | Baseline b2 | Candidate 0e |
| --- | ---: | ---: | ---: |
| Median edited command, seconds | 0.538 | 0.195 | 0.175 |
| Median child CPU, seconds | 0.808 | 0.184 | 0.165 |

Paired wall changes −9.22%, CPU −10.71%; wall ratio 0.907752832
passes the original 1.05 regression limit. Most time is in Cargo. The comparison
includes frontend/wrapper changes alongside the runtime, so this improvement
is not attributed solely to native copies. Native and custom settings retain
the recorded controls. No private cache was modified or archived. Aggregate
verification of all seven histories remains a separate required step.
