# Opened guest descriptors: experimental Darwin primitives

This source-only checkpoint adds `open`, `write`, `close` and constant
`fcntl(F_GETFD)` lowering plus their checked runtime operations. It has not
been compiled or executed. Six new Rust controls and two native/exporter test
histories are prepared; no test or performance result is claimed.

Execution requires explicit `Limits.guest_descriptor_io = true`, or the VM's
`--guest-descriptor-io` flag. The default rejects any program containing these
operations before its first guest instruction, even when the operation is in
an uncalled function. Partial-validation programs and other guest/host targets
are rejected. This is only an AArch64 Darwin opened-descriptor contract; the
ordinary launcher gains no flag or build-script routing.

## Descriptor and memory contract

Each execution starts an empty table of 256 file slots. Guest integers 3–258
name these slots; `open` chooses the lowest vacant slot after an actual
successful native open. The stored host descriptor may have any nonnegative
number, including 0, 1 or 2. Host descriptor integers are never guest results.
No standard-stream or inherited-descriptor entries are provided. Those inputs,
and descriptor-number paths such as `/dev/fd`, need a separate program-input
contract before general applications can use this mode.

`write`, `close` and `F_GETFD` resolve the guest table. An invalid/closed guest
number yields `-1` and Darwin `EBADF`; it never addresses an unrelated host
descriptor. Closing a slot permits subsequent `open` to reuse its guest number,
as with an ordinary descriptor table. Table exhaustion is an explicit VM
resource-limit error before `open`, with guest errno unchanged. Actual OS open
errors, including the OS's own descriptor limit, retain their native result.

Every operand width, NUL-terminated path, full write buffer and writable
four-byte errno destination is validated using the existing guest memory model
before a syscall. That model checks guest arena bounds; this change does not
claim additional allocation-provenance checking. libc receives references to
checked host slices, never tagged guest addresses. A zero-byte write follows
the existing empty-range convention and passes a valid empty host slice.
Invalid memory is a VM error, not a fabricated `EFAULT` result.

There is one native `write` call per bytecode operation: no retry, buffering,
write-all loop or synthesized success. Its signed return value preserves
partial writes and errors. Before each supported syscall, the adapter seeds
the executing host thread's errno from current guest TLS, calls libc, captures
errno immediately on success **or** failure, restores the VM's host errno and
copies the captured value back into guest TLS. It does not assume successful
libc calls preserve errno. Internal cleanup also preserves host errno.

The table owns each successful open until close or execution teardown. Darwin's
reviewed `close_nocancel` routes a nonguarded valid descriptor to
`fp_close_and_unlock`, which releases its descriptor-table entry before the
file-close result is returned. Thus the adapter removes ownership and calls
close once even when close reports a file-close error. It never retries a
possibly reused host number, and teardown cannot close that number again.
This is based on [Apple XNU f6217f89, kern_descrip.c](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/bsd/kern/kern_descrip.c#L1602)
and the pinned Rust `library/std/src/os/fd/owned.rs` no-retry policy. Guest
pthreads, cancellation, signal handlers changing descriptors, descriptor guards
and arbitrary FFI remain outside this first contract. Real close-error fault
injection is not established by these unrun controls.

## Compiler and artifact boundaries

The shared foreign-call dispatcher checks the exact C ABI, return/argument
widths, pointer layout and variadic shape. Darwin's `open` mode is a promoted
32-bit C integer, even though `mode_t` itself is narrower. Both the ordinary
two-argument call and a promoted mode argument are represented; `O_CREAT`
without a mode is rejected before opening. `fcntl` requires an actual constant
`F_GETFD` and exactly two arguments during export. Other commands/dynamic
commands and incompatible signatures are export errors, including in the
existing diagnostic unsupported-call mode. No fallback is added after effects.

Four variants are appended after V5 `EnvironmentGet`; existing variant ordinals
and existing encoded programs are unchanged. Older VMs reject the new variants.
Compiler/tool source identities and existing function-cache composition remain
authoritative; old toolsets are not relabeled. Register reads/writes,
initialization, liveness and conservative memory-effect barriers enumerate the
new operations. They have no native JIT emitter: both execution engines use
the same checked dispatch path. The only `jit/local_memory.rs` change is adding
these four operations to its existing conservative barrier list.

## Required qualification, all unrun

Under a fresh canonical-lock supervisor, freeze this source, actual compiler,
exporter/VM binaries, prepared std and sanitized environment. Build with two
Cargo jobs and run the workspace correctness suite, because opcode additions
affect exhaustive visitors beyond the new module. The six new module controls
cover disabled/partial admission, encoding/register/target checks, real native
file histories, invalid memory before effects, descriptor ownership/resource
limits, and actual nonblocking pipe short writes/errors. Pipes are native test
setup only; no guest pipe operation is added.

Run `tests/test_descriptor_io_native.py` with explicit `RUST_INTERP_TEST_RUSTC`,
`RUST_INTERP_TEST_EXPORTER`, `RUST_INTERP_TEST_VM`,
`RUST_INTERP_TEST_STD_SYSROOT` and a new `RUST_INTERP_TEST_ARTIFACT_DIR`. Its first
history builds the same fixture normally and exports its checked entry, then
compares native/interpreter/JIT return values and actual file bytes through
create, append and truncate states, binary/empty writes, errors and descriptor
closure. Disabled execution must create no file. Its second history refuses
unsupported fcntl forms and bad foreign signatures during export. The caller
must retain compiler/tool/std closure identities and supervise the exact test
child; the tests retain each subprocess's PID, argv, cwd, sanitized environment,
raw outputs and terminal status. They never install tools or prepare std.

Full `std::fs`, formatted stdout, normal main/termination/flush semantics,
subprocesses, native proc macros and Cargo interpreted-host artifact routing
are separate work. This primitive is not a complete build-script runner or a
claimed reduction of Nushell's native-host compilation time.
