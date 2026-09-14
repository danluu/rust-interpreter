# Concrete retained-value model passes

All four controls pass in debug and release. The corrected wide fixture supplies
three uses before the unknown write, so its benefit exceeds two capture words.
The first failed run remains intact; no planner fix was needed for that failure.

The model compares every frame byte, guest register, executed-step count and
error across every instruction-budget prefix, four arbitrary initial bit patterns,
nine unknown-address cases and 0/1/2/15 capture slots. Fixtures include 4/8/16-byte
values, seven partial-write widths, overlapping copies, unknown aliasing reads
and writes, readonly/out-of-range pointers, full-width-to-narrow truncation through stored
bits, register-output aliases, division/assertion faults and live-slot pressure.

All original Memory writes remain immediate. Only complete captured read values
are substituted; each substitution is additionally checked against a fresh
original Memory load. No production runtime or executable code changed.

Proceed to an exact saved-body coverage check for the profit-filtered model,
then audit and implement direct native retention only if coverage remains useful.
Native fault/budget/ABI correctness, strict project tests and the changed-source
primary remain prerequisites; this model establishes no end-to-end speedup.

Source `6fe57bd5`; [summary.json](summary.json) and [closure.json](closure.json)
bind both command logs and all model/controller inputs.
