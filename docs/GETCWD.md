# Opt-in Darwin current-directory primitive

This implementation adds the actual `getcwd(char *, size_t)` C
ABI for an AArch64 Darwin guest and host. Execution requires the separate
`Limits.guest_getcwd` capability or `--guest-getcwd`; descriptor access does not
imply permission to obtain the current directory. Any program containing the
operation is refused before guest instructions when disabled, including an
uncalled operation. Partial validation is refused. Existing defaults, launcher
arguments and build-script fixtures are unchanged.

The pinned public compiler is `cea272fa356e94bd2ee2cadf376630aa0683867a`.
Its `library/std/src/sys/paths/unix.rs` calls `libc::getcwd` with a 512-byte Vec
buffer and retries only ERANGE after enlarging it. The selected libc signature
is `libc-0.2.189/src/unix/mod.rs:1108`. The installed SDK's
`usr/share/man/man3/getcwd.3` specifies that NULL allocates as necessary and
**ignores size**. The same distinction appears in
[Apple's Libc implementation](https://github.com/apple-oss-distributions/Libc/blob/main/gen/FreeBSD/getcwd.c):
nonnull size zero fails EINVAL; positive insufficient buffers fail ERANGE;
NULL starts an internal allocation and can grow it. NULL with zero, one or
maximum `size_t` is therefore supported, with no artificial non-NULL restriction.

All operand widths and the writable guest errno slot are checked first.
Nonnull nonempty buffers must have a fully writable guest arena range before
libc receives a mutable host slice. This retains native bytes even on failure;
there is no fabricated EFAULT or path reconstruction. The existing empty-range
convention permits nonnull size zero without touching its address. Invalid
nonempty ranges are VM errors. These are arena checks, not a new claim of
allocation-provenance checking.

For NULL, libc's private temporary allocation supplies the actual path and
native errno. Its complete bytes including NUL are copied into an owned guest
C allocation, using the existing shared byte, register and live-allocation
budgets. Guest allocation failure returns NULL/ENOMEM. The guest result can be
freed or reallocated through the existing C allocator and never exposes a host
pointer. The native temporary remains private and is freed on every result
path, including guest allocation failure; its internal libc scratch allocation
is not a guest allocation. There is no request-size-driven host allocation:
Darwin ignores NULL's size. Host errno is restored after cleanup; native errno
is captured immediately after the call on success or failure.

`CurrentDirectory` is appended as V5 opcode 38. Existing ordinals are unchanged;
older tools cannot consume the new operation. Register visitors, scalar
promotion, inlining and JIT memory barriers cover it, and NULL allocation marks
the program as heap-using. There is no native opcode emitter: both engines use
the same checked operation. This work adds no chdir, subprocess, standard
streams, complete std::fs or Cargo interpreted-host routing, and makes no
latency or complete build-script support claim.

## Completed qualification

Source `c176cc5c` passed the release workspace suite: 540 tests passed, 10 were
ignored, and none failed or were filtered. Both native comparison tests and
all 33 child commands passed. Complete source snapshots, command/output
receipts and native comparisons are retained in the
[qualification archive](../results/getcwd-native-qualification-01/README.md).
The integrated production sources match that tested checkpoint.

Before execution, freeze the complete source and helper/test inputs, an actual
public compiler/loader closure, prepared std, sanitized environment and fresh
output directories under an owned canonical-lock supervisor. Use two Cargo
jobs, the established 16 GiB entry / 9 GiB between-command / 8 GiB running
capacity rules, and preserve any failed attempt. This document does not itself
admit a workload or reuse an old qualified tool identity.

1. `cargo test --workspace --release --locked --offline --jobs 2 --target-dir FRESH_TARGET -- --test-threads=2`
2. `cargo build --release --locked --offline --jobs 2 --target-dir FRESH_TARGET -p rust-interp-bytecode -p rust-interp-mir-export --bin rust-interp-vm --bin rust-interp-mir-export`
3. Run the two explicit tests in `tests/test_getcwd_native.py` with the actual new
   exporter/VM, public compiler, std and fresh evidence directory supplied by
   the existing `RUST_INTERP_TEST_*` variables. Require zero skips and retain
   all 33 child receipts and raw streams (29 in the first history, 4 bad ABIs).

The four new Rust controls cover pre-execution capability/partial/target/
register/encoding checks, direct native full-buffer and NULL comparisons,
invalid addresses/size/errno before changes, and shared allocation count/byte/
register budgets with cleanup. The existing memory-barrier test also includes
the new opcode. The native fixture compares every path byte and its terminator
to the independently supplied actual cwd, including spaces and UTF-8, and
returns explicit result-pointer/byte/sentinel bits plus the full errno value.
Both engines must match native across six cases and a deliberately wrong
expected path. Disabled and invalid guest pointer/size cases do not invoke a
native invalid-pointer control. Four incompatible foreign ABIs must fail export.

The sequence above completed successfully. A future unchanged-build.rs export-only
census must use the newly built and qualified tools to observe any next blocker;
the earlier census's exact `libc::unix::getcwd` reports stay historical.
