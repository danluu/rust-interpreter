Implement the committed caller-value contract in isolated source copied from
native ABI tool 5ce80a8a. Append the typed CallValue opcode, share ordered VM
argument handling, tag return destinations explicitly, validate native caller
register destinations, and extend the existing resumable emitter. Native tree
modes remain rejected; existing indirect calls use the address bridge.

Qualify 319 debug/release workspace tests (one ignored): eight new value-call
tests and one native-boundary test on top of the prior 310. Cover all 80 scalar
width/storage combinations with real hot native transition counters; recursion;
mixed direct/indirect calls; reused frame tags; input/result aliases; TLS callback
calls; serialization and malformed version/width/register checks; per-PC profiles;
every instruction budget; and code/memory/depth limits. An independent adapter
materializes version-5 caller slots for value checks. Preserve both original
real version-5 artifact roundtrips. No compiler-generated CallValue yet.

Freeze recipe/source and record every owned process. Serialize with the
nonblocking benchmark lock; require 12 GiB free before building and retain the
8 GiB floor. Preserve any failed run before revising the recipe. Do not publish
a runtime or claim performance until compiler promotion and real-workflow gates.

Revision 2 preserves the first compiler failure and adds explicit CallValue
cases to the local-memory barrier and both old local-address analyses. A value
destination kills any prior Local fact; an address destination is not a register
write. A regression test checks that an old Call following a value return cannot
reuse the destination register's obsolete local-address proof.
