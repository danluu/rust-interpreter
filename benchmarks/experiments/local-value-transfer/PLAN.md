Investigate transferring local-value references after a forwarded load. This is
an offline follow-up hypothesis, not an implementation or a timing candidate.
Finish the current guarded-local-facts comparison and preserve its verdict first.

A local-memory value refers to a virtual source register. A forwarded Load copies
that value into its destination through put(). If put() evicts the previous
cached owner, forget_cached() removes every local-memory reference to that owner.
The current implementation remembers only the local range just loaded. Other
unchanged local ranges containing the same low bytes may therefore lose a usable
value even though the new destination now holds those bytes.

Count this in the actual emitter before changing production. First reconstruct
all three saved candidate317a0bf1 code maps exactly with the observer disabled.
Then use a test-only alternative to snapshot compatible local-value references
before put() and restore them against an existing result fact afterward. Require
size <= the forwarded load width, exact original local ranges, a distinct source
and destination, and a present destination fact. Skip self-redefinition and
unavailable results initially. Keep the existing16-entry bound and replacement
order explicit. Report newly forwarded Load/Copy sites, lost sites, fact kinds,
changed native bytes, flush code, compile work and exclusions separately.

This transfers references between virtual registers; it must not create two
owners of one physical cache slot or invent a Fact::Cached/Physical alias. Loads
narrow to zero-extended low bytes, so a wider memory fact cannot move to a narrower
result. Do not read an evicted register-array slot, resurrect facts killed by a
memory write, preserve anything across a native-region boundary, alter runtime
memory checks, or change cache replacement merely to make the census favorable.
The original review-before-emission definition handling remains authoritative.

Required adversarial cases before any executable treatment: owner eviction and
spill, a dead destination, source/destination identity, high nonzero source bits,
all1/2/4/8-byte width combinations, multiple local aliases, partial overlapping
writes, unknown writes, cache pressure, physical assignments, branches and calls.
Preserve the immutable guarded-write role/disjointness proof. A result fact whose
owner later changes must invalidate transferred references through the ordinary
forget/definition path.

Profile execution counts weight emitted spans; they are not retired instruction
counts or a latency prediction. If the additional hot coverage is too small,
park the idea without a full timing campaign. Any later runtime treatment needs
strict/cache and original-test qualification, a changed-source primary screen,
then all full guards in primary-first order. Existing rejected candidates retain
their decisions. Keep the other session's compiler work and current frozen
benchmark files untouched.
