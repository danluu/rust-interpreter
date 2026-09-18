# Existing scalar bodies retain their instruction counts

All137 common bodies (60/69/8) have exactly the same word count. Every changed
word is a64-bit SP-relative load/store immediate increased by48 bytes; no other
word differs. There are2,139 such static sites across the three captures. This
is a structural observation, not semantic equivalence or a model of cache or
stack-footprint cost. Twelve Python controls pass, including512 enumerated DAGs.

Added successful Calls number36,736 /5,133,472 /1,063,647. The exhaustive
increase is dominated by4,926,856 Calls to `token_phrase::verify`, followed by
206,544 Calls to the vector constructor. The analyzer declines verify because
its syntactic machine CFG is cyclic. This is the same conservative limitation
previously encountered at an unconditional Trap. Preserve the decline and add
an exact unique-predecessor CMP-XZR proof before reporting those path bounds.
The zero-success feature-detection functions retain their explicit no-success
decline; never turn a decline into zero cost.

The existing counted new constructors take260 words for One,394 for Two and528
for Three along successful profiled paths. These are not hardware counts or
speedup estimates. General byte packing warrants inspection, but its small
block coverage alone cannot justify a timing candidate. The indirect-call lead
was previously tested in separate qualified candidates and remains parked.

No guest executes, no code is published, and no performance gate is changed.
[Result](summary.json), [closure](closure.json).
