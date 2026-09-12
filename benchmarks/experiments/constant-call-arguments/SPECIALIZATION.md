# Shared call signatures: first implementation qualification

Implement NEXT.md on experiment/constant-call-specialization-20260912. This
candidate removes the global folding pass from the exporter. Its initial
qualification exposes only the bytecode API and offline CLI; integrate into
export only after the differential checks and saved-program diagnostics pass.

The typed census carries an unformatted u128 value beside its existing public
hex report, so compiler decisions do not parse strings. Per Call, admit at most
eight known1/2/4/8byte arguments; signatures contain one to three arguments.
Require two distinct sites sharing the signature. Rank by static sites times
known argument count with deterministic value/ID ties, try at most eight
signatures per callee and accept at most four disjoint variants. Bound a program
to2million scanned operations,65,536sites,262,144constant facts,65,536distinct
signatures and2million signature insertions. The folder gets8million global
solver units, retaining its2million per-function limit. Keep the64-clone,
16,384-operation and5%growth caps, and require8operations/25%body reduction.

Original bodies are unchanged except selected direct-call target IDs. Clone
bodies are created before any redirect and retain their original call targets.
Indirect handles, function names, arguments, results, frames, registers, data,
statics and TLS keep their semantics. Seed argument bytes in copy order; unknown
overlapping slots erase earlier facts. The entry certificate includes the seed
and backedges can discard it. Extract the existing function-local CFG cleanup
without changing the ordinary whole-program pass.

Six differential tests cover shared/conflicting/unique values, partial overlap,
invalid argument copies, opaque caller mutation, mixed direct/indirect recursion
and decline bounds. Compare both artifacts against the interpreter, then both
JIT modes and persistent-register choices at zero/full code capacity and exact
per-artifact instruction boundaries. Retain all original memory faults and peak
memory. Use only the previously documented pair of memory-range error messages
as one JIT fallback category.

Host qualification floor: 4 GiB. Reuse the existing populated debug/release
dependency cache from build10, two Cargo workers, offline locked dependencies
and the same host profiles. Expect374workspace tests per profile (one ignored)
before publishing the prototype tools. Record free space before/after children;
there is no cache deletion or fresh real-project build in this qualification.
The next saved-program check uses retained typed programs and the exact control
VM. Actual-edit benchmark admission and adoption gates remain in NEXT.md.
