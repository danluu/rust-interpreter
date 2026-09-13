The saved-evidence join passes two controls and reconciles all 433 / 499
native transition samples in the two adopted token captures. Every direct native
Call is joined by its typed callee ID; Return samples belong to the returning
function. No guest command or Rust build was run. Complete frozen-input and Git
source bindings are recorded in the summary and source-bindings files.

Copy precondition checking is the largest combined Call/Return group in both
captures: function 21 has 32 of 1,651 generated samples in block and 64 of 1,439
in exhaustive. Its frame is 304 bytes; the bound-entropy profiles separately
record 4,301,249 and 11,912,383 native incoming direct calls. The alignment helper
is next in block (28 samples, 128-byte frame). Exhaustive also has comparison
wrappers, partitioning and verification among the expensive call groups. Costs
are spread across many callees. No single function-specific replacement follows.

The two sampled windows and whole-test profiles use different entropy and have
different scopes. Incoming native direct calls exclude interpreted/indirect
entries, and whole-function instruction totals are not per-call costs. Rendered
operation labels are descriptive; they prove no alias, initialization or
inlining property. Samples are not an end-to-end gain or retired instructions.

Next inspect a bounded interprocedural frame-initialization proof. The older
proof resets at every basic block and treats every Call as an unknown memory
effect; its tiny measured coverage correctly prevented adoption. A stronger
analysis may retain definite initialization across CFG joins and admit a direct
callee only when a typed summary proves it cannot inspect the caller outside
explicit argument reads. Copy order, result padding, unknown pointers, cycles,
zero-size frames, error paths and analysis limits must remain conservative.
First measure proof coverage on these exact artifacts and PCs. No runtime clear
may be removed before that evidence and differential qualification.
