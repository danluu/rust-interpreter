# Entry-root range groups: complete bounded census

The corrected diagnostic passes 466 workspace Rust tests per debug/release
profile and twelve offline executable controls. Three saved adopted profiles
are hash- and shape-validated. Both earlier CLI modes produce byte-identical
reports, seven invalid/overwrite cases are rejected, and no guest code runs.
The first compilation's three unsupported opcode equality expressions are
retained in the failure receipt; variant matches fixed them without changing
the core opcode type. No analysis function is excluded in the completed census.

| Profile | Unknown fixed addresses | Entry-root addresses | Best-group addresses | Conditional redundant checks |
| --- | ---: | ---: | ---: | ---: |
| token block | 637,176,732 | 207,211,968 | 36,330,192 | 24,339,008 |
| token exhaustive | 189,791,893 | 78,656,319 | 565,613 | 383,172 |
| folded | 50,349,317 | 29,768,857 | 1,335,602 | 993,253 |

A group needs at least three accesses and at most 4 KiB of enclosing extent.
Only the strongest group in each recorded interval enters the last two columns;
all-group counts remain separate in JSON. The last column subtracts one check
per selected group, assuming a successful stronger preflight. It does not account
for preflight instructions, translation/base reuse, success rates, branch costs
or elapsed time. Top-site lists are explicitly capped at 64 entries without
changing complete counts. No check-removal implementation is approved by a
symbolic count alone.

The largest groups are in generic regex determinization and SipHash. In the
block profile, SipHash c_rounds has 36 unknown accesses per invocation and
d_rounds has 108, but the strict entry model links only the first three of each.
Their first pointer write invalidates local-slot knowledge: without another
proof, the pointee could alias the current frame's slot holding that pointer.
Ignoring that possibility would be incorrect, even for normally valid Rust input.

Do not implement this narrow census as a performance candidate yet. Next count
one explicit stronger condition: a chosen entry-root pointee range is disjoint
from the entire active frame. Under that guard, writes through that root cannot
change its frame-resident pointer value. Other roots, unmodeled effects and
known overlapping local writes must still invalidate knowledge. A guard failure
must execute the original ordered operations, preserving partial writes and
errors. The conditional census will remain separate from these unconditional
entry-value counts and will not add guest executions or timing samples.
