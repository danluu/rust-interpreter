# Fresh real-export smoke

Both original workloads export changed bytecode and pass all selected assertions
with the candidate VM: eighteen folded tests and three token tests. Source remains
at its original pin; MIR/runtime flags remain unchanged. No JIT function declines.

| Workload | Logical instructions | Native Calls | Native bytes |
| --- | ---: | ---: | ---: |
| Folded | 4,320,679,029 | 14,079,238 | 6,333,036 |
| Token | 13,855,159,290 | 72,422,547 | 15,361,176 |

Inlining removes many calls but adds logical operations and emitted bytes. Token
uses real randomness, so its counts should not be equated to another execution's
path. Both artifacts, complete logs and compiler relocation receipts are retained.
These are fresh correctness smoke commands, including cold caches; their times
are not paired performance evidence. Strict native/VM differentials and fixed
real-edit command comparisons still determine whether the change is useful.
