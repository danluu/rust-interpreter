# Exact entropy inputs for a runtime diagnostic

The token comparison stopped on unequal instruction counts. Two subsequent
executions of the same VM/artifact also differed; each executed three
`RandomBytes` operations backed by real CommonCrypto entropy. Preserve the
stopped comparison. Do not waive its instruction-equality guard or report it as
a completed performance qualification.

Use a diagnostic library only in explicitly launched, owned fixture/VM
processes. It records successful `CCRandomGenerateBytes` results and replays
those exact requests and bytes. The installed VMs and production randomness
implementation remain unchanged. Apple's [interposing example](https://github.com/apple-oss-distributions/dyld/blob/main/include/mach-o/dyld-interposing.h)
calls the original function from the replacement; the signature comes from the
installed SDK's `CommonCrypto/CommonRandom.h`.

Before a real VM, qualify recording/replay, empty streams, mismatched request
lengths, extra/missing requests, corrupt/truncated/trailing input, refusal to
overwrite evidence, and non-main-thread rejection. Tape creation is exclusive
with mode 0600. The diagnostic rejects failed entropy requests, excessive
requests and byte counts. Replays must consume the entire tape. It prints
aggregate request/byte counts; raw entropy stays local.

Then record two independent real token streams using the original fixed-clear
VM in JIT mode. Replay each stream on that unchanged VM and the combined VM, in
both engines. Require identical outputs, logical instructions, peak guest
memory, entropy request counts and byte counts within each stream. Check all
binary/artifact/tape hashes before and after. These commands diagnose input
equivalence; their elapsed times are not performance measurements. A mismatch
keeps composition qualification stopped.

After this diagnosis, predeclare any controlled-input runtime comparison
separately. Keep the fresh-entropy edit/build/test workflows and their existing
assertions. No program source, guest artifact, random API success semantics,
instruction limit or threshold changes are part of this diagnostic.
