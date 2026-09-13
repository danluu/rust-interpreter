# Guard rule discrepancy found before either held-out case

Recovery inspection found that the frozen executable held-out CPU rule differs
from the prospective WORKFLOW.md and the plan emitted by that same executable.
The document requires maximum paired CPU ratio plus CPU A/A envelope <=1.05.
The code requires maximum paired CPU ratio <=1 and the sum <=1.055. Neither
rule implies the other. The primary token rule is consistent and its failed
decision remains unchanged.

Before any folded or pgrust guard commands start, retain both rules explicitly:
record the frozen executable's output without alteration, and compute the
documented rule separately from the same complete fifteen pairs. A guard is
accepted only when both rules pass. This conservative intersection does not
relax either frozen criterion. No observations will be excluded or retimed.
The full candidate cannot be adopted because its primary gate already failed.

The 126 hashed harness inputs remain unchanged for these measurements. After
both cases, correct the rule in the next candidate's harness and add boundary
tests for a slight CPU increase within the documented noise margin and for a
sum between1.05 and1.055. Preserve this discrepancy with the original results.
