# Ordinary native register calculations

Extend the qualified scalar word recognizer to a conservative saved-code census
of ordinary native operation spans. This is not the parked private-leaf runtime
candidate. Start with both exact adopted, unprofiled token captures already used
for the memory census. Preserve their complete same-process operation maps and
sample attribution; do not compile or execute any guest or machine code.

Analyze each operation span separately. Every machine register, SP, NZCV and the
recognizer's vector state is live at the end. Branches, calls, returns, unknown
instructions and unreviewed vector instructions are full barriers. Recognized
direct branch targets also cut propagation, including targets reached from
outside the span. Remove conceptually only pure definitions overwritten before
any use; preserve every memory operation and all control effects. No cross-block
or ABI liveness assumptions are made. Reuse the source-frozen recognizer and its
nine controls, plus five controls for barriers, entry points, memory and flags.

Report static candidate words and same-process self-PC samples at those words.
Collapsed samples count as certain only when every listed PC is a candidate;
retain ambiguous counts separately. Sample shares do not predict speed or prove
retired instruction counts. Detailed sites stay in a hash-bound local artifact.
Reconstruct all original attribution totals. Use the shared lock and an 8 GiB
floor. No runtime change follows unless coverage justifies a separate qualified
implementation, including independent encoding, faults, budgets and relocation.
