# Branch-aware reservation with explicit refund costs

The check-only and fixed-chain diagnostics are closed and their standalone
implementations deferred. Extend the cursor model to the already reviewed
forward-edge DAG, retaining a4096-step cap and guarded-target/call/backedge cuts.
Reserve the maximum suffix cost on checked entry. On a chosen certified edge,
refund pending-credit minus target-credit before its fast entry. On any cut
edge, refund all pending credit before the checked/VM entry. A maximum-credit
edge requires no refund. Every early fault keeps the current-region debit and
refunds only unentered work. Larger guard failure still uses the original VM
tail. No future branch or instruction is semantically charged.

First qualify an offline model with14controls. Retain all512 three-node CFGs,
short budgets, fault prefixes, loops, external entries, guard/opaque/cap cuts
and seeded paths. Add explicit unequal-branch refunds and branch-to-backedge
refunds; verify physical cursor publication separately from semantic prefixes.
Native state/ABI qualification remains a later obligation.

Use the same closed adopted code/profile evidence. Exact four-word budget spans
and their instruction partitions remain the sample unit. Report potential fast
targets separately for those with every normal CFG predecessor certified and
those with mixed predecessors. External VM/JIT entry can still occur; even the
former is not proof a sampled visit entered fast. Calls and unsupported incoming
predecessors count as noncertified. Do not transfer entropy-bound execution ratios
onto partial ordinary-entropy samples or infer constant-load latency from PCs.

Count costs conservatively. A nonzero edge refund may need ADD-immediate plus a
branch thunk: charge two additional executed words, even where a future emitter
could need only one. The cap keeps each refund within an unshifted12-bit ADD.
Report normal-successor flow bounds for fast entries and refunds, plus the
resulting best/worst nominal word changes. Include checked entries (four original
words with a different constant); cold fault refunds and static code growth are
not measured by those successful-path counts. No instructions are emitted.

Only substantial sample coverage surviving the entry classification, with a
favorable conservative nominal cost bound, warrants a typed prototype. Otherwise
park the family without tuning the cap, removing guard barriers or retiming an
old candidate. A prototype still needs exact range-planning order, source-aware
link relocation, all native refund/fault/ABI controls, original Rust tests and
the unchanged real changed-source primary followed by every project guard.

Shared lock45s,12GiB initial/8GiB per-case floor. No Rust build, guest, cache
mutation or executable publication. Bind the closed fixed-chain result and
freeze sources through independent recomputation. Preserve any admission failure.
