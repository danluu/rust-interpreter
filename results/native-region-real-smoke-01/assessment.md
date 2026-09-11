# Native region Call smoke check

Source `26833c3`, optimized tool `2f31c6a0`, passes both saved real test artifacts
with `--jit-native-calls --jit-native-call-stubs`. Baseline `b2aa6efe` also passes.
All four commands preserve original assertions and frozen artifact/binary hashes.
These execution-only checks establish exercised behavior, not end-to-end speedup.

| Workload | Baseline JIT entries | Candidate JIT entries | Outer stub Calls | VM-entered trees | Peak guest bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Folded trie | 43,732,357 | 22,293,876 | 11,532,049 | 2,042 | 102,369 |
| Token phrase | 244,306,014 | 57,897,006 | 32,013,663 | 255,554 | 8,170,193 |

Guest peaks match the baseline. Folded executes exactly 4,138,403,285 bytecode
instructions in both modes. Token executes 13,369,595,048 baseline versus
13,369,516,349 candidate instructions. Its guest random inputs can differ between
processes; this does not establish the cause of this observed trace difference.
All counts and raw output remain in [the command records](summary.json).

Generated Calls include 14,151,386 folded and 89,195,546 token Calls; outer stubs
are a subset of those counts. Descendant tree instructions total 1,594,204,600
and 6,111,508,629 respectively. Published stub sites are 491 and 933. Code bytes
increase from 3,533,256 to 3,928,624 folded and 8,674,972 to 9,386,616 token.
Preparation and extra native code remain costs inside execution measurements.

Unrepeated wall times are 1.597/2.008 seconds baseline/candidate folded and
5.046/3.922 seconds token; child CPU is 1.589/1.591 and 5.042/3.918 seconds.
These diagnostic timings are not retention evidence. The unchanged predeclared
three-cycle source-edit/build/test comparison against b2aa6efe is the next gate.
