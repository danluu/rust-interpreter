# Next experiment: calls inside ordinary generated regions

The first complete-tree integration still enters a tree through the VM Call
handler. The folded-trie three-cycle result misses its gate: 2.603 s candidate
versus 2.559 s baseline, with a +73 ms median paired difference. Its saved-artifact
smoke has 11.53 million host tree entries and only 2.62 million nested generated
Calls. Token's complete-command comparison improves 14.4% paired, below its 20% target. This motivates the
already planned next step; it does not establish where all the regression occurs.

Keep source/tool `09de2a9` / `c98d995b` available as a separate comparison. Preserve
the original 20% token / 10% folded gates against b2aa6efe, rather than resetting
the required gain to the new intermediate version. No default retention follows
from making one workload faster. Measure the seven held-out workflows before
retaining a final candidate, plus the broader execution qualification.

## Implementation outline

Start with a compiled stub for an eligible direct Call, linking it to existing
ordinary regions. Reuse the complete tree emitter for its callee. This removes
the VM's outer argument/frame setup and return dispatch without requiring native
execution of recursion or unsupported operations. Preserve the current explicit
option while developing the new mode; no guest LLVM fallback.

Before emitting a caller, prepare its eligible bounded direct-call dependencies.
A failed/declined dependency leaves that Call in the VM. Publish words, entries
and fault identities atomically in the existing arena. Record additional cold
preparation/code costs; eagerly encountering cold eligible callees is a cost,
not free reuse. Do not resolve targets from guest data or patch live code.

A stub has the ordinary C wrapper (saved x19/LR), then an internal entry that
checks whole-call budget and host readiness. Use the existing 64-byte tree host
frame for call setup and a BL to the prepared child's internal entry. On success,
restore caller x0/x1/profile and x20–x22, pop the 64-byte frame, and branch to the
next ordinary region's internal entry. Keep the outer 16-byte x19/LR frame alive
for all linked regions. Fault exits must pop BOTH frames; calling the tree's
existing epilogue alone would return with a corrupted stack. The caller's guest
Return remains an ordinary VM operation, including root and TLS completion.

The codegen's internal-entry map must include these one-operation stubs. Their
minimum entry budget is `1 + callee.instructions`, distinct from the one ordinary
Call operation charged to the caller. A budget decline returns the Call PC before
progress. If reached from previous native blocks, their earlier progress remains
charged. An external zero-progress decline must fall through to interpretation
of that instruction, without re-entering the same stub or inventing a guest fault.

## Storage and cursor contract

All regions that can link to a Call stub need a host cursor large enough for
native descendants. Keep the existing prefix, but derive the raw pointer from
the complete cursor allocation before casting to the prefix type; do not create
a narrow mutable reference to only the prefix and then access sibling fields.
Ordinary mode must retain its original small-cursor contract. Enabling stubs
therefore belongs to JIT construction, before any function is published.

Compute each ordinary caller's maximum ready direct-child alignment, frame span,
register slots and native depth. Before a region entry, conservatively prepare
initialized backing from the CURRENT live end, not merely caller frame size:
earlier VM calls may have retained larger alignment padding. Sibling native
calls round at most to their largest direct-child alignment. Check active VM
registers plus maximum child slots, current heap/auxiliary memory and VM depth
against guest limits. No allocation or protection change may occur in generated
code. A failed preparation sets a host readiness flag that every reachable stub
checks before progress; other ordinary regions can still run. A per-function
maximum can decline a cold large path, so report lost coverage and allow the VM's
existing per-callee tree hook to handle smaller actual calls.

Heap allocation, TLS bookkeeping, VM calls and returns can change readiness.
Fresh region entries must re-establish it; cached preparation is valid only with
explicit invalidation or checked state keys. Generated children may change caller
memory, so no forwarding fact crosses a Call. Every argument is copied in order
after exposing the initialized callee frame; result copy precedes truncation.

## Accounting and qualification

The caller stub's Call belongs to ordinary block counts. Descendant operations
belong to tree blocks. To count tree instructions without adding counter updates
to every tree block, save the remaining budget in the stub's unused host-frame
slot at offset 56, then accumulate its change after the child returns. Root tree
execution through the VM can continue deriving its count from the whole entry.
Count every generated Call separately from host tree entries. Keep total JIT
instructions/entries/bytes and the separate ordinary/tree compilation metrics
consistent with those definitions.

Tests must link ordinary blocks to stubs and back across loops and branches;
exercise direct external stub entry, budget points below/at/above the child bound,
all readiness declines and later recovery, heap growth between regions, retained
padding, caller registers/facts, ABI copies, nested faults and mixed VM/TLS calls.
Extend the assembly probe to cover these mixed exits, ensuring SP, LR and x19–x22
survive every fault and decline. Use profile sums to detect omitted/double-counted
Call or Return instructions. Then use the same real edited sources and artifact
identity checks, with separate baseline/candidate Cargo histories and all outliers.

## Implemented follow-up — September 11

The `experiment/native-region-calls` branch implements this path behind
`--jit-native-calls --jit-native-call-stubs`. The default mode and the earlier
complete-tree mode remain separate execution specializations. All 231 workspace
tests pass, including mixed native-frame ABI checks at up to 64 child levels,
linked Call loops, all existing integration budget/fault/profile cases in both
modes, heap growth and larger padding retained by a VM callee. Seven CLI checks
pass. Optimized and real-workflow qualification is next; no new speedup claim.

Call stubs enforce the full budget internally. A direct entry that cannot fit
returns its own PC with zero progress, and the VM executes that instruction once.
This keeps the existing Block representation unchanged. The expanded cursor is
used only for functions with prepared Call stubs; other ordinary functions keep
the existing region transition. Internal stub success pops its 64-byte frame
before linking to the next ordinary region. Faults pop it plus the outer 16-byte
wrapper. Root and TLS returns remain in the VM.

Readiness caches function identity, active register count, VM depth, fixed
heap/auxiliary bytes, and an aligned live-memory ceiling. It retains no pointers.
Repeated native sibling calls cannot exceed that ceiling; later VM allocations
or larger retained padding cause a miss. Initialized backing vectors never shrink
during execution and pointers are obtained fresh for every entry. Working-memory
and depth declines still use the original VM path. Region preparation costs remain
inside execution timing. Nested code-generation time is not counted twice.

The caller's Call is counted in ordinary profile blocks; descendants are counted
in tree blocks. `jit_stub_calls` counts successful outer generated Calls, while
`jit_tree_calls` counts all generated Calls (including those outer stubs).
`jit_tree_entries` remains the number of complete trees entered through the VM.
`jit_call_stubs` counts published stub sites. A saved remaining-budget value in
the stub frame measures descendant instructions without per-tree-block additions.
