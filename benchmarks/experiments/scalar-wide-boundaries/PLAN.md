# Narrow the aggregate-result opportunity before implementing it

The closed structural census grouped larger frames, more registers and larger
results together: 157 functions, 11 block and 86 exhaustive samples. Partition
those exact candidates by which bound they exceed. Then compare a fixed grid of
result limits 32/64/128/256, frame limits 512/1024/8192 and register limits
512/1024/4096, keeping the 512-operation and 16-byte argument bounds. Report
unsupported scalar opcode families separately. Select no functions by name.

Reuse the closed typed metadata and original adopted sample join, checking all
hashes and reproducing the previous broad candidate set and coverage totals.
Each grid row must be a subset of that set. Category partitions must be disjoint
and exhaustive, and enlarging a limit must only add candidates. Retain all rows,
including empty and unobserved groups. No new native sample or guest run occurs.

This is still structural coverage, not memory/alias/CFG/native eligibility.
Larger results require a new bounded byte-result representation and private ABI;
raising the existing size check cannot make a u128 carry an aggregate. Before
runtime implementation, a typed proof/model must preserve every result byte,
padding, argument-copy order, alias behavior, budgets, faults and resource limits.
Use the shared lock, 12 GiB admission and 8 GiB child floor. Main remains adopted.
