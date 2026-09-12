# Conservative capacity credit for native calls

Design only, following the qualified integrated tool49746a22. The previous
target-retention/frame-clear candidate's complete token gain was below its
A/A envelope. Its result is final. Before implementing this larger change,
inspect the pending whole-process instruction diagnostic. No timing prediction
or adoption decision follows from the source audit below.

For one uninterrupted resumable native entry, let M and R be live linear
bytes and register slots, E and S their prepared bounds, and W the guest
working-memory budget after fixed heap/auxiliary accounting. Boundary::new
validates these values; backing, bounds and fixed accounting remain unchanged
until control returns to Rust. Guest writes cannot address host descriptors.
Ordinary emitted operations do not grow M or R. Allocation, TLS callbacks and
unsupported operations return to the VM before changing fixed accounting.

Maintain a private unsigned credit K with the invariant:

```
0 <= K <= min(E - M, 16 * (S - R), W - M - 16 * R)
```

The external entry seeds K=0 after saving the host link register. A checked
slow Call performs every original capacity and overflow check, then refreshes
K from the three exact post-call slacks. A callee with frame size F>=1,
validated power-of-two alignment A>=1 and N register slots has conservative
cost C=F+(A-1)+16N, computed with checked host arithmetic. If C overflows,
retain the original checked path for that call.

When K>=C, subtract C and compute the actual aligned frame base. Alignment
padding P lies in [0,A-1]. The new extents are M'=M+P+F and R'=R+N. Because
C>=P+F, C>=16N and C>=(P+F)+16N, the decremented credit remains a lower bound
on all three post-call slacks. The same inequalities prove that each addition
and alignment intermediate fits: M+(A-1)+F<=E, R+N<=S and
M'+16R'<=W. Register backing is a valid initialized Vec<u128>, so multiplying
its bounded length by16 cannot overflow.

A Return truncates M to the returned frame's base and R to its register base.
Both decrease, even when pre-frame alignment padding remains. Do not refund
credit. Every slack grows or stays unchanged, so the invariant survives all
return/alignment histories. This avoids relying on the caller's original
extent or subtracting a guessed allocation cost. Exhausted credit takes the
ordinary checked Call and refreshes K without an extra VM exit.

Keep ready-target and effective frame-depth checks independent. Keep charging,
clear-before-argument-validation, argument checks/copies, return-address checks,
descriptor publication and logical counters in their existing order. A fault
after private credit changes exits to the VM; a later external entry resets
credit. Do not defer descriptors or argument validation based on this proof.
The first candidate does not combine vector counter batching or a new memory
model with the capacity change.

## Register and control-flow audit

Candidate register: x30, only between the resumable external prologue and
epilogue. `resumable_save_host` already saves/restores x19/x30 in the96-byte
host frame. x29 retains its existing frame-pointer role; x18 is untouched.
`values::external_entry` has a distinct resume point after host setup. Direct
Call/Return targets use that resume point; intra-function edges use internal
entries. Initialize credit before both points, so only external Rust entries
reset it. Every normal, budget, unsupported-operation, assertion and address
fault exit reaches `return_to_vm`, which restores the saved host x30 before RET.

`new_resumable` creates ordinary JIT options with native stubs disabled and
does not create the old tree engine. Resumable Calls and Returns emit BR;
local edges emit B/B.cond. The tree implementation's BL and link-register
spills are therefore outside this execution mode. Existing physical guest
assignments use x23..x28, instruction budget x22, cursor x19, descriptors x20,
callee base x21, target x16 and register cursor x17. Shared scalar, copy,
zero, memory, profile and register-array helpers do not currently use x30.
Audit emitted instructions and ABI probes after implementation; a source
search alone is not a runtime proof.

Slow-path scratch allocation can use the already loaded bound in x10 and
post-call lengths in x11/x17 to form each slack. Retain x16's existing callee
target rule, including reload for caller registers beyond2048. Do not overwrite
x17 after preparing the callee register base or assume arbitrary helpers
preserve a new scratch value. The credit is native-private and adds no cursor,
RBC format, cache key schema or serialized guest-state field.

## Qualification and decision

Use independent arithmetic oracles for retained-padding return histories,
mixed memory/register ratios, tiny/exact/near-maximum limits, checked cost
overflow, and repeated credit refresh. Exercise valid JIT programs that take
both fast and slow paths, exhaust credits repeatedly, cross VM exits and
return through ancestors. Preserve reference values, exact logical instruction
counts, memory peaks, limit errors, TLS behavior and host ABI. Retain the
existing high-register, dirty-frame, generated-CFG and native differential
checks. Do not run a memory-corruption reproduction or the held old VM.

After correctness qualification, freeze one candidate and a prospective
complete edit/build/test comparison. Use fifteen edit pairs, an independent
same-source A/A cache, fixed selected-suite anchor, repository native,
line-tables native and check; retain folded/pgrust guards. Both baseline and
candidate must use the same integrated exporter for mechanism attribution.
Also report composed gain against the fixed anchor separately. Preserve all
failed outcomes/noisy observations; do not rerun an unchanged candidate to
cross a threshold. Source-to-native instruction inflation can guide this
choice, but it does not replace the end-to-end result.
