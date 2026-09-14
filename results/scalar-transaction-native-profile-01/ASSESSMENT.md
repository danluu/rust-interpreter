# Original tests confirm native store coverage

Three new candidate profiles match three exactly bound adopted-VM profiles.
Original assertions, complete per-PC logical counts, peak guest memory and
entropy consumption agree. Every same-process operation map reconstructs the
actual emitted bytes. The closure verifies 65 frozen inputs and 24 artifacts.
Three observation and seven launcher controls are reused through exact source
and evidence bindings; they are not newly run tests.

| Original test | Adopted scalar Calls | Candidate scalar Calls | Adopted native bytes | Candidate native bytes |
| --- | ---: | ---: | ---: | ---: |
| Token block | 11,227,102 | 27,650,466 | 11,952,720 | 11,976,076 |
| Token exhaustive | 16,298,574 | 16,416,150 | 14,508,196 | 14,536,728 |
| Folded | 1,585,153 | 1,585,160 | 1,978,352 | 1,961,780 |

Block scalar logical instructions rise from 1,147,704,517 to 3,442,636,379;
the total remains 15,849,531,246. The candidate removes 44 interpreted boundary
instructions in block, 47 in exhaustive and two in folded, preserving the exact
overall counts. Profiled code sizes include instrumentation.

Checked entropy replay is diagnostic only. These observations establish
execution coverage, not speed. Proceed to fresh complete commands under normal
OS entropy and the unchanged primary performance gate.
