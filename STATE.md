# Current state — September 14, 2026

Manual optimization continues indefinitely. The saved goal remains paused.
The task is a general custom Rust interpreter/direct AArch64 JIT, guided by
real changed-source build/test commands across small and large projects.
Private repository: `danluu/rust-interpreter`. Qualified changes go to main.

The scratch-value/scalar-call composition is adopted with the current compiler.
It combines bounded scalar native calls and private value transfers with reuse
of checked memory values still held in x9. Writes, aliases and register clobbers
invalidate reuse conservatively. Type and borrow checking finish before guest
execution; partial-demand artifacts cannot use the scalar calling path.

Use explicit `--jit-scalar-calls --jit-resumable-calls
--jit-persistent-registers`, prepared isolation and the measured two-worker
configuration. The 16 MiB default arena remains. There is no LLVM, Cranelift or
foreign-interpreter fallback for guest execution.

All five predeclared performance guards pass across 726 complete commands:

| Selected workload | Wall / previous custom | Wall / ordinary native |
| --- | ---: | ---: |
| fre token | 0.9370 | 1.5714 |
| fre folded matching | 0.9689 | 0.9181 |
| pgrust hashfn | 0.9939 | 0.8466 |
| private rg-aot | 1.0048 | 0.4097 |
| Nushell type-relations | 1.0000 | 0.6363 |

Token improves 6.30% wall and 6.51% child CPU, beyond 1.41% wall A/A variation.
Folded improves 3.11% wall. Differences for pgrust, rg-aot and Nushell establish
no speedup over the previous custom runtime. These are complete changed-source
commands, with 15 valid edited pairs per case. Wrong edits and restoration
retain their original assertions. The two independent 88-command full-parser
histories also pass: 114 original tests, no established parser speedup, and
1.140× native wall under the repository profile / 1.263× matched incremental.
[Full results and limits](results/scratch-memory-values-full-01/ASSESSMENT.md).

Qualified tool `df4006e0` preserves measured VM `6ac4dd9e`, exporter `cf4b3499`
and wrapper `45bca4f2`. All Rust/Cargo/configuration inputs match the measured
candidate. The integration retains main's optional runtime-compiler validation
and restores the scalar launcher test; 407 merged Python tests pass, 22 declared
compiler/native tests are skipped. The closure binds 1,460 source files.
Prior 608 workspace tests per profile (13 ignored), 121 strict/cache commands,
six exact profiles, 13 original selected/prepared controls, the full-parser
compatibility and performance histories are reused through exact source/binary
and closed-evidence bindings. The integration repeats no guest timing.
[Integration](results/scratch-scalar-main-qualification-01/assessment.md).

This is still a selected-function/test-body engine. Complete Rust application,
libtest, thread/OS/FFI and real unwinding support remain open. The parser and
token native gaps still guide optimization; no complete database/shell coverage
or isolated scratch-cache speedup is claimed.

The current manual branch is `experiment/scalar-aggregate-model-20260914`.
Main still adopts df4006e0; the aggregate runtime is experimental. Prior
path/store-log and narrower scalar variants failed their predeclared changed-source
performance gates and remain parked. No unchanged-build timing is an adoption
measure.

The exact wider-boundary census identifies 132 structural candidates. Typed
confined proof with ordinary Call zeroes admits 32, retaining 3 block and 66
exhaustive samples. The combined graph preserves full result bytes and every
original PC against independent projections and byte oracles. Six native ABI
controls and 367 bytecode tests pass in debug/release, with 16 existing diagnostics
ignored. The custom emitter now has a private 64-byte payload and one body
execution; this qualification did not widen production selection.
[Combined census](results/scalar-aggregate-census-02/assessment.md),
[native ABI qualification](results/scalar-aggregate-abi-01/assessment.md).

The complete aggregate Call bridge passes seven focused controls and374 bytecode
tests/profile, including complete memory on error exits. The final census retains
all32 candidates in the combined native ABI in both profile modes (28,904
unprofiled bytes; maximum368-byte spill frame). Immutable tool3081569232 /
VM5fd0c1c7 retains the adopted compiler/exporter/wrapper. It passes637 workspace
tests/profile,407 Python tests with22 declared skips,121 strict/cache commands,
and three exact original profiles/code reconstructions. All stages are closed.
No performance improvement or adoption follows from this qualification.

The exact exhaustive test passes alone for original source and fails alone for
the deliberately wrong edit. Sixteen protocol and three observation controls
qualify the prospective40-command changed-source primary:
`scalar-aggregate-screen-exhaustive-02`. Use the original exhaustive test alone,
normal entropy, two Cargo workers and complete Cargo/build/run latency. The
previously declared A/A wall and CPU gates remain unchanged. If it passes, freeze
the full exhaustive history and all existing project/parser guards before running
them; the full token suite is a regression guard because block is its critical
path. Main remains df4006e0 until every required gate passes.
[Build](results/scalar-aggregate-build-01/assessment.md),
[strict checks](results/scalar-aggregate-qualification-01/assessment.md),
[profiles](results/scalar-aggregate-profile-01/assessment.md),
[prospective screen](benchmarks/experiments/scalar-aggregate-screen/SCREEN.md).

The compiler/Cargo/parser-exporter investigation belongs to the other session.
Preserve its worktrees and all user-owned processes. Keep the global benchmark
lock, two Cargo workers, the shared owned build target, conservative reservations
and the 8 GiB child floor. The disk monitor is read-only for this task; do not
start a competing repair or cleaner. The saved goal stays paused while manual
optimization continues.

The September 13 12:45 suggestions were re-read on September 14 and their SHA
remains unchanged: 4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f.
[Review and dispositions](docs/SUGGESTIONS-REVIEW-20260913-1245.md).
