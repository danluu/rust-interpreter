The exact retained 6bf10fda VM completed the original token-phrase tests while a three-second diagnostic sampled its main thread. The follow-up captured the live executable arena before sampling; every reported generated PC lies inside that same process’s arena. The first sample is preserved separately because its VM exited before the later mapping request. Neither run is a performance comparison.

| Disjoint category | Samples | Share |
|---|---:|---:|
| generated code | 1017 | 40.9% |
| dispatcher self unresolved | 669 | 26.9% |
| frame reservation inclusive | 237 | 9.5% |
| local argument copies | 200 | 8.0% |
| return result copies | 129 | 5.2% |
| heap management | 96 | 3.9% |
| general argument copies | 59 | 2.4% |
| other memory copies | 57 | 2.3% |
| memory store | 10 | 0.4% |
| switch lookup | 8 | 0.3% |
| jit compilation | 3 | 0.1% |

Host call-site roles are checked against the exact retained binary disassembly. Nested clearing and copy frames are included in their parent category, never added again. These shares do not predict optimization gains. Generated code and dispatcher self remain substantial unresolved categories. Next, add an isolated diagnostic native-address map, prove emitted words identical, and resolve sampled PCs to original bytecode operations before choosing another change.
