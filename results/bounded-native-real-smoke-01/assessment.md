# Real-artifact execution smoke check

Source `09de2a9`, tool `c98d995b`, passes the saved folded-trie and token-phrase
test artifacts with native calls enabled. The retained `b2aa6efe` JIT also passes.
Original assertions remain enabled. These are four execution-only commands,
not edited-source latency measurements or retention evidence.

| Workload | Host tree entries | Nested generated Calls | Peak guest bytes |
| --- | ---: | ---: | ---: |
| Folded trie | 11,534,091 | 2,619,337 | 102,369 |
| Token phrase | 32,269,405 | 57,181,465 | 8,170,193 |

Guest peaks agree with the baseline. Folded executes exactly 4,138,403,285
bytecode instructions in both modes. Token executes 13,369,545,479 baseline
versus 13,369,542,540 candidate instructions; this workload uses guest random
bytes, so independent processes do not have identical instruction traces.
Passing original assertions is not proof that the trace difference is caused
by randomness; the counts and inputs are retained for further diagnosis.

The single folded command was 1.578 s baseline / 1.793 s candidate (CPU
1.568 / 1.632 s). Token was 5.094 / 4.153 s (CPU 5.089 / 4.149 s). These
unrepeated timings are diagnostic only. They justify continuing with the
predeclared paired edit/build/test benchmark, whose results decide the direction.

The gap between host tree entries and nested Calls is material: entering an
eligible root still performs VM call setup and a host transition. Census
eligibility must not be reported as the number of VM calls eliminated. If the
complete-command gates fail, the planned next architectural step is native Call
stubs inside ordinary generated regions, with equivalent readiness/budget/live
memory guards and a valid VM continuation when a stub declines.
