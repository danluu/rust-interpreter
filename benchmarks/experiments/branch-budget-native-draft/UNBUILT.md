# Native integration draft: not applied, built, or executed

The typed planner at 825fe65b still awaits its first focused qualification.
The shared benchmark lock belongs to a peer's Ruff experiment. Preserve that
workload and complete the planner gate before applying this patch.

The patch proposes feature-only checked/fast entries and exact suffix refunds,
plus seven native controls. Its source hashes are in receipt.json. Positive
refunds use non-flag-setting ADD x22 and a local branch thunk. Source-associated
links require their certified target; missing native entries reject unpublished
staging rather than entering a VM tail that would refund twice. Fault/VM tails
refund pending suffixes; budget/range declines do not. Call/Return links stay on
checked entries. A distinct BudgetEdge map kind describes the hot refund thunks.

The controls cover each ordinary external entry in an unequal diamond, every
short budget, both profile/register modes, duplicate/wide switch selectors,
exact fault budget and state, ABI/backing canaries, guarded preflight declines,
code-capacity refusal, map reconstruction, ADD encodings and long initializer
credit-cap boundaries. These are authored controls, not passed tests.

Still needed: a new qualified map reader, both-profile native qualification,
default-disabled emission comparison, workspace/strict/original-project suite
qualification, and the preregistered changed-source primary and full guards.
The installed engine and archived observer sources are unchanged. The patch's
blank context lines are literal unified-diff data; preserve their exact bytes.
