# General environment reads for custom Rust execution

The full original114-test gram_core selection now compiles with the coordinated
function capacity. Seven custom tests pass;107 stop at the same unsupported
foreign getenv call. Preserve these outcomes, all source/assertions and the
successful native114 proof. Do not replace reads with a hard-coded missing value.

Add an appended bytecode EnvironmentGet opcode for the checked C getenv ABI.
Its input is a guest NUL-terminated name and its result is a stable guest pointer
or null for an absent/invalid name. Preserve Unix raw bytes, empty values,
first matching entry and repeated-pointer stability. No host pointer enters
guest memory. Keep writes/setenv/removeenv/environ enumeration unsupported.

Capture the actual child-process environment once per execution owner (once per
prepared worker), only for programs containing the opcode. Copy the immutable
name/value blob into each fresh guest state's read-only prefix before allocating
frames. Program-data offsets stay unchanged; frame bases already use the live
prefix length. Existing readonly checks then protect imported values in both
interpreter and JIT; ordinary allocator operations cannot free them. Account for
the imported bytes and index storage in memory admission. No environment values
or hashes of the ambient environment are written to reports.

Treat the opcode as an interpreter boundary with explicit register reads/writes,
conservative fact invalidation and no deferred stores. Keep old opcode encodings
and unsupported foreign-call traps. Audit every exhaustive visitor and ABI
signature. Successful reads do not establish unwind/backtrace or general OS
support. A process-level snapshot is explicit; guest environment mutation and
concurrent host environment changes are outside this primitive's contract.

Test synthetic snapshots without mutating the shared host environment: absent
versus empty, raw non-UTF8 names/values, duplicate names, embedded equals, invalid
guest pointers/unterminated input, readonly writes and frees, overflow and memory
admission, budget/alias handling, and independent fresh guest state with prepared
code. Compare a Rust std::env fixture against native child processes with the
same explicit synthetic environment overrides, including non-UTF8 var_os and
VarError, across interpreter/JIT and cache modes. Retain native/default behavior
for the complete parser rerun and every original test.

Build/check the complete workspace under the shared45-second benchmark lock,
two Cargo jobs and conservative disk admission;8GiB per command. Reuse exact
unchanged proofs where valid. Broaden to real project assertions and changed
source commands before adoption; no speedup claim from support checks or
unchanged builds. Do not change other sessions or the paused goal.
