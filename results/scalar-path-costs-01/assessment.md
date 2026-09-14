# Direct effects repeat work the store log already combines

The offline comparison passes eight controls, including complete path enumeration
of 512 generated DAGs. It verifies all retained input hashes and matches all
245 scalar bodies across the two parked emitters. Profiles, operation identities
and scalar hit vectors are identical. Forty-six bodies change; the conservative
machine-CFG analysis admits 41 of them. Cycles in the overapproximated CFG and
bodies without a successful return are explicitly declined. No guest runs or
Rust builds occur.

The clearest result is the generic `c_rounds` body (function 2038 in this saved
artifact): the store-log emitter has 480–488 words on a successful CFG path,
while the direct path emitter has exactly 1,289. Its saved block profile records
3,293,696 successful Calls. This is an observed cost of the emitted structure,
not a function-name optimization policy. The store log combines accesses and
overwritten stores; the new emitter checks the path and then performs the
original effects, retaining much more memory work.

The sparse-set closure has bounds 343–805 versus 382–877. The vector-extension
closure has 409–473 versus 435–461; overlapping bounds establish no ordering.
For the 19 analyzed changed block bodies, successful-call-weighted word bounds
are 3.396–5.116 billion for store log and 6.238–7.994 billion for direct path.
SP-relative store bounds are 329–408 million versus 474–620 million. The other
cases and every declined body remain in the summary and raw details.

These are **profiled machine-code CFG bounds**, allowing independent conditions
and thus infeasible path combinations. They exclude failed private attempts,
ordinary callers/fallbacks, preparation and hardware effects. SP-relative traffic
includes arguments and profiling output, not only saved values. Category extrema
need not occur on the same path. Neither emitter is adopted; this comparison
does not establish either one's advantage over main or predict elapsed time.

The prior changed-source result already fails the adoption gate. This analysis
explains why direct effects alone are an unattractive next iteration: removing
the private log also removes useful forwarding and store coalescing. Keep both
runtime revisions parked. Next narrow the existing wider-boundary structural
census to determine whether larger scalar results or frames can admit useful
read-only bodies without adding speculative stores or repeating this design.

[Summary](summary.json), [closure](closure.json),
[prospective scope](../../benchmarks/experiments/scalar-path-costs/PLAN.md).
