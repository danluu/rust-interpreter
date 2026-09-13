# Narrow the observer to eviction losses

Source review of candidate317a0bf1 narrows the hypothesis. The forwarded Load
path materializes into scratch, then put() chooses the destination's storage.
Only a cached source can lose its fact through that allocation. A distinct
immediate, local-pointer or fixed physical source is not evicted by put(). The
observer should count those exclusions rather than manufacture transfers for
them. No new guest run or emitted-code measurement supports this hypothesis yet.

Snapshot local-value entries immediately before put() only for a forwarded
Load whose source fact is Cached and whose virtual source differs from the
virtual destination. Record the original bounded order and load width. After
put(), require an existing destination fact and confirm which original entries
were actually removed. Keep every surviving reference unchanged. Transfer only
missing references belonging to that exact former source with size no greater
than the zero-extended load width. A reference removed because the destination's
old value was overwritten is never eligible. An unavailable source must never
fall back to its register-array slot; eviction may intentionally omit a spill.

The reviewed put()/remember() path can remove local-value entries but does not
insert them or write guest memory. Assert that subset property in the test-only
observer. Reconstruct the subset in original order with eligible missing entries
restored against the destination, then run the existing remember_local_memory()
for the just-loaded range. This preserves the previous sixteen-entry limit and
keeps newly loaded-range replacement in its original location in the sequence.
Do not append transferred entries as arbitrary new recent values: that would
also change replacement policy and confound attribution.

The present memory_address()/address() routines materialize/check addresses
without evicting cached facts, so scalar-Copy's captured forwarded fact remains
available during destination validation. This review found no extra mechanism
needed there. It does not authorize changing address checks or their fault order.

Adversarial emitter/VM tests should distinguish: source slot chosen versus the
other slot chosen; narrow compatible versus wider incompatible stored aliases;
several aliases with a partly full or full fact list; old destination aliases;
a dead destination; equal source/destination; fixed physical destination; wide
source with nonzero upper bits; later source/destination redefinition; partial
and unknown writes; branch/call region termination. Require baseline maps to
match exactly with the observer disabled before evaluating any treatment.

Keep the production candidate, frozen campaign helpers and installed tools
unchanged. Implement and execute the observer only after the current campaign
has a final verdict. Its coverage and emitted-byte counts guide whether another
runtime experiment is justified; they are not latency or retired-instruction
measurements.
