The lifetime census supports a correctness prototype, not a speed claim.
In admitted functions, token virtual storage falls from 944,299 slots to 58,046
(93.9%), folded from 234,644 to 13,134 (94.4%), and pgrust from 6,079 to 712
(88.3%). These are sums across functions, not peak live host memory.

Estimated additional native-resident reads are 3.60% for token block boundaries,
2.55% for token exhaustive semantics, 0.85% for folded and zero for pgrust. The
estimate omits cache, call/setup and transfer costs. Declined functions account
for 0.57% of native operations in the first token profile, 0.0034% in the second,
and zero in the two others. No elapsed-time improvement follows from these counts.

The offline tool passed 346 Rust tests in both profiles and four typed censuses
bound to the current saved programs and matching profiles. It neither executes
a guest nor changes a saved artifact. Duplicate function names are handled by
index and exact code/shape matching. The proof uses full CFG liveness, initial
zeroes, dead writes and closed intervals, with conservative bounded declines.

Next qualify actual remapping against both engines and native Rust assertions,
then run one fixed complete-command screen. The old gap-removal compaction and
all other parked candidates remain separate. This allocation merges disjoint
register identities; it does not merely renumber them.
