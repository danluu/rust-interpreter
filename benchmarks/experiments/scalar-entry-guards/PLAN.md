# Size scalar entry guards before direct effects

The transactional scalar and compact store-log prototypes passed strict
qualification but failed their real-edit primaries. The adopted backend's global
register model changes only two values in one scalar body and is deferred.
Investigate a different effect strategy with a restrictive static admission rule.

This branch restores the exact archived store-log bytecode source at
8f51e4c31912728fec71b8c71f81227bc0a52967 solely to reconstruct its closed scalar
plans and native words. Main remains on the adopted runtime. Do not install or
benchmark this restored prototype as a new candidate. Its 245 body observations
are explicitly the parked prototype's scope, never today's 137 adopted bodies.

The first stage is a test-only eligibility census, with no change to emission.
Require every live external Read/Write address to be a constant or captured
8-byte input plus a constant offset modulo 2^64. Only the existing exact 64-bit
alias forms may be followed; memory-loaded roots, phis, base/frame addresses,
narrow casts and variable offsets decline. Record every required nonempty range
and read/write permission; cap distinct ranges at 128 and retain the existing
16-store and scalar shape limits.
These are symbolic address expressions, not permission to dereference them.

A prospective native entry would check all these ranges against stable backing,
the pre-Call linear prefix, null rules and write protection before any store.
Untaken ranges may decline the optimization and replay the original Call before
effects. Actual execution must retain original effect order and arbitrary read/
write aliasing. Captured input values remain immutable even if guest memory
containing their original argument slots is overwritten.

Also require that no reachable path can encounter a potentially failing integer
division/remainder, Assert or Trap after any external Write. Propagate may-have-
written state through the complete CFG and respect computation/effect order
within each original PC. Range checks would be discharged at entry; all other
eligibility failures must remain before the first effect. The first-stage result
does not implement those guards or prove an emitter has no extra failure path.

This condition could allow direct stores without a private log or rollback.
Never replay a Call after a committed store. Do not assume an error discards
observable effects, weaken strict checking, change guest budgets, omit original
faults or infer addresses from numeric ranges. A later model must establish full
memory, alias, failed-entry, fault-order, budget, padding, fresh-frame and private
state behavior before native wiring and a new real-edit primary.

Qualify symbolic identity and rejection cases, and compare the CFG failure rule
with an independent forward-path oracle. Reconstruct all closed store-log scalar
bodies exactly, report all eligible/rejected functions and successful PC weights,
then join eligible functions to the already closed adopted native samples. Count
coverage without claiming removable time or an end-to-end improvement.

Use the existing ROOT target, shared lock, two Cargo workers/test threads,
conservative max(14 GiB, 8 GiB + twice allocated target) build admission and an
8 GiB child floor. Freeze the restored sources and new observer separately from
the old qualification; retain and close every command. No new guest or executable
publication is part of this census.

Run seven controls in debug and release (including a 512-case independent
forward-path oracle), then one ignored release census of 111/124/10 exact
archived bodies. Use fresh run ID scalar-entry-guard-census-01. No timer gate
or native execution is included.
