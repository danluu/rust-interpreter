# New fixture failed before scalar execution

All 345 existing debug tests pass; the three new tests fail because their shared
fixture has no eligible memory plan. A partial write left the rest of its
16-byte result outside the planner's initialized-byte proof. The new graph and
native checks therefore did not execute. Release was not started. Closure
retains the exact source, one command and both logs (231 bindings).

Initialize the complete result to a visible sentinel before the branch, so the
same proof can admit every partial-width case and preservation of untouched
bytes is observable. Add an explicit planner diagnostic, retain this failure
and rerun under a new identifier. Do not weaken production admission.
