# Unapplied integration draft

These patches were prepared while model02's closer could not acquire the shared
lock. The passing model's Rust/controller inputs remain unchanged. Apply only
after model02 is closed against its exact original source hashes. Do not compile
these copies or treat this draft as qualified. Preserve closer02's lock timeout.

Ordinary function emission owns one bounded pool of facts, definition membership
and live-in membership. Move it into each ordinary region, clear touched values
and membership, then reclaim empty capacities for the next region. Other emitter
paths keep sparse defaults. Sorted flush predicates preserve visitation/emission
order. Early refusal/error drops the function-local pool; no cache survives it.
Combined dense payload is at most4MiB; each map also verifies actual Vec capacities
against its assigned sub-budget, with optional allocation failure falling back
to its original sparse collection. The bound excludes ordinary sparse allocations
and allocator overhead. No new guest limit or allocation-success guarantee.

Before admission, add combined-memory and dense-vs-sparse exact emission controls
with loops, joins, memory facts, assertions, profile/register modes and code
capacity refusal. Keep a cfg(test) sparse switch for the independent adopted
path. Full saved-program reconstruction must compare words, entries, resumes,
assertion identities and operation maps, including current scalar target bytes.
Then full workspace/Python controls and real strict/cache outcomes, followed by
one prospective genuine-edit primary. No performance claim yet.
