# Pgrust catalog correctness across real source edits

All 32 commands pass: 21 native/fresh/prepared commands across the original,
deliberately wrong and five distinct production edits; seven independent Cargo
checks; and four restored-source commands. Original tests remain unchanged.
The wrong edit fails the same assertions in all modes. Four tests are selected.

All fourteen primary bytecode/catalog pairs and both restored pairs are retained.
Each catalog is hashed, bound to the exact bytecode, and matched to the executed
function IDs and requested names. Fresh/prepared bytecode is identical at every
source state. Source restoration is verified.

This qualifies catalog behavior, not a new performance claim. The earlier
single-cycle timing result remains descriptive; this follow-up was not a
predeclared performance confirmation. Native tests run in separate processes.
The first attempt stopped at the initial space guard before any workload child.
The successful run retained the same 8.125 GiB admission and 8 GiB per-child floor.

[Counts and receipts](isolated-assessment.json) · [Verification](verification.json)
