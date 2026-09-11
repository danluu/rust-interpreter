# Resumable native Calls over an explicit guest frame stack

**Implementation status:** `5574d10` / `e1bec3e` connect native Call/Return
emission and VM integration; `001065a` adds exact bulk initialization, tool
`78e60cdd`. All 257 debug/release tests, 12 CLI controls and both original
artifacts pass. [Two fixed-tool E2E runs](../../../results/resumable-bulk-replication-01/assessment.md)
improve folded 19.51%/19.15% and token 19.95%/19.97%, with CPU improving.
Both narrowly miss token's original 20% target; neither failure is waived.
The option stays experimental. Full native differential and TLS qualifications
now pass, as does fresh fre body replay (382 passed, seven ignored). Seven
held-out workflows follow.
[Broader qualification](BROADER-QUALIFICATION.md). The initial rationale and
requirements below remain the qualification contract.

The preceding custom JIT (`d664bce` / `e89de7f8`) improves token real edited commands
23.6% paired and folded 4.2% against `b2aa6efe`. Token passes its original gate;
folded misses 10%. Fresh folded profiles attribute 11.6% to native-boundary self
and 11.9% to dispatcher self; token has 11.5% and 11.0%. These are partial,
perturbed windows, not removable-time or speedup predictions.

Private-array reuse is now parked: the qualified typed census finds an additional
0.0000073% of folded direct-call frame bytes and 0.1233% of token. Larger aggregate
reuse still needs a padding/alias/lifetime proof. Do not replace that proof with
a broader type predicate, weaken frame initialization or tune isolated zero/copy
opcodes as the default next direction.

The selected implementation replaces the **complete-tree eligibility requirement**
with explicit native-to-VM continuations. A generated Call may enter a function
with loops or interpreter-only operations; it exits to the VM only when that
execution reaches a missing native entry, unsupported operation, budget tail or
storage-preparation boundary. Direct guest recursion uses bounded guest frames,
not nested host Calls. This develops the broader alternative already recorded in
`docs/NATIVE-CALL-EXPERIMENT.md`.

## Storage and publication contract

1. Give guest frames a documented host-only `repr(C)` representation and stable,
   initialized backing with an independent active length, as memory/register
   storage already has. Preserve function ID, PC, frame/register bases, return
   destination and the TLS-callback flag. Native-created frames have a valid
   false flag; all backing elements are initialized Rust values before exposure.
   Check exact offsets, alignment and commit bounds. Default VM/TLS behavior
   must remain intact. A storage refactor alone is not a performance result.
2. Prepare bounded spare frames, register slots and linear bytes outside native
   execution. Speculative initialized capacity must not increase guest live
   memory, allocations, call depth or address bounds. No allocation, Vec growth,
   lazy compilation or MAP_JIT publication occurs while emitted code runs.
3. Publish immutable per-function native entry metadata atomically. Direct Call
   targets and Return continuations come only from trusted emitted metadata;
   guest values cannot become host code pointers. A cold/unprepared target
   declines before Call progress and lets the VM prepare it. Keep typed codegen
   limits and code-capacity fallback. Compile one body per function where possible;
   do not require a second complete-tree copy.

## Call, Return and continuation contract

4. Use one external C-ABI frame per native entry. Preserve x19–x28 and LR/SP;
   every function can use a different persistent-register assignment. A native
   function transition saves live caller values to its initialized register array
   and establishes the callee's assignment. Return reloads the caller's values.
   Same-function native edges retain their existing fast assignment path. Memory
   facts cannot cross Calls. Keep full u128 values and alias write order.
5. Before a generated Call, prove its target and initialized backing are ready
   and all speculative bounds fit. If any prerequisite fails, resume that Call
   in the VM before consuming it. Preserve the actual VM error order: frame
   reservation, register-size/working-memory checks, argument copies, then depth
   checking and register initialization. In particular, do not raise a depth
   error ahead of an earlier argument-copy error. On the native path, initialize
   exactly the range the current frame reservation would initialize, expose
   that live extent, copy arguments in order, initialize registers according to
   the existing proof, save caller PC+1 and push the callee. Charge Call once.
6. Store active guest frames throughout execution, so an exit from a descendant
   identifies the current top frame and PC. The VM must restart from that frame,
   not from the outer native-entry function. Distinguish zero-progress decline,
   a continuation after progress and a terminal fault in a typed result. Preserve
   register storage, active linear extent, memory peak and exact step counts.
   A declined operation executes once in the VM before any re-entry attempt.
7. Check budgets at region boundaries, including loops and Calls. Insufficient
   budget resumes the exact current PC for ordinary single-step behavior; there
   is no whole-callee reservation or charge for unexecuted paths. Unsupported
   operations and allocation/TLS operations use the existing VM implementation
   with their real arguments and effects. General OS/FFI/unwind semantics remain
   unsupported where the VM already lacks them; do not invent success shims.
8. A generated inner Return copies the result before truncating to the aligned
   callee base, pops the guest frame, restores caller state, and selects its next
   trusted native entry or VM continuation. Root returns and TLS completion stay
   with the existing VM; leave their Return unconsumed when handing it back.
   Faults commit only valid host extents and never execute a later return copy.

## Implementation and qualification order

First implement initialized frame storage and typed continuation invariants,
with existing interpreter/native-tree/TLS checks. Then implement the dedicated
resumable emitter and constant VM specialization behind an explicit experimental
option. Keep the existing tree/stub mode available for differential comparison.
Use named host-layout offsets and emitter helpers; do not scatter new raw ABI
assumptions through the ordinary lowering paths.

Required execution tests include native caller → native looping/recursive callee,
native → interpreted operation/child → native continuation, deep fallbacks,
multiple returns, partial budgets at every boundary, unready code/capacity,
insufficient prepared storage, depth/memory failures and argument-fault ordering,
overlapping argument/result copies, full-width caller values, memory mutation
through pointers, all callee-saved GPRs/SP/LR, and root/TLS callback completion.
Profiles must reconstruct logical counts even when frames change during entry.
Exercise both profiled/unprofiled modes and optimized builds. Native execution
must not depend on an LLVM/third-party guest compiler or another interpreter.

After optimized qualification and original saved-artifact smoke tests, use the
same three-cycle folded/token source-edit benchmarks against `b2aa6efe`. Keep
identical artifacts, original assertions, wrong edits, fixed options/limits,
source restoration and all wall/CPU samples. Measure code-generation/preparation
and VM execution inside complete commands. Initialization still costs work;
moving it into native Calls is not itself a gain.

The original targets remain −20% paired token and −10% folded, with CPU improving.
Then require the seven held-out workflows (including large-project controls),
no unresolved >5% regression and broader native/TLS/fre qualification before
retention. No production default changes merely because a prototype executes.

[Preceding E2E result](../../../results/persistent-e2e-01/assessment.md) ·
[Fresh profiles](../../../results/persistent-folded-sample-01/assessment.md) ·
[Parked array census](../../../results/aggregate-reuse-weights-01/assessment.md) ·
[Original call/ABI audit](../../../docs/NATIVE-CALL-EXPERIMENT.md)

## Groundwork completed

`fca1e96` implements initialized reusable `Frames` and moves the VM/TLS paths to
it. `1264921` implements the typed `Boundary`/`State`/`Run` publication contract.
Nine new tests cover backing reuse and checked native cursor publication; all
249 workspace tests pass in debug and release (one ignored). Boundary tests
model descriptor/cursor mutations; they do not execute resumable machine code.
The later `5574d10` implementation connects emitted execution; see the status
above and the [emitter contract](EMITTER-NEXT.md). Primary E2E gates have now
been evaluated. Native/TLS validation and fresh fre replay pass; held-out
workflows remain outstanding.
