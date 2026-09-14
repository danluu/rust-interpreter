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

Fresh owned native-PC samples and exact memory/call protocol reconstruction are
closed. The scratch source/width extension has too little sampled coverage to
justify its own implementation or timing. Current Call/Return costs point to
frame handling. The virtual-zero census admits 15 additional leaves but covers
no current transition samples, so that policy stays parked. The typed current-call join is closed. The read-only scalar model passes 48 controls and covers 95 block samples
across transitions and bodies, with none in exhaustive. The native prototype now passes 359 bytecode tests per profile, admits
392 functions and preserves 71 existing scalar bodies byte-for-byte. The immutable
candidate passes 622 workspace tests/profile, 407 Python tests (22 skips), all
121 strict/cache commands and three original profiles. Token block scalar Calls
rise from 11.23 to 18.95 million with exact logical counts, memory and entropy.
The complete 40-command primary fails: wall ratio 0.999836 and CPU 0.999544
are inside A/A variation. Park this candidate and cancel larger comparisons.
The emitted-body census closes with limited duplicate-read coverage. A subsequent
structural census gives external-write leaves the strongest block-test coverage
(153 samples). The bounded private-store model now passes 369 bytecode tests
per profile, including exact error-exit memory and non-idempotent replay controls.
Its census retains 168 plans and 138 block samples. Next implement and independently
qualify native stores; production admission remains closed and no speedup is claimed. [Next work and evidence](RUNTIME-NEXT.md). The compiler/Cargo/parser-exporter investigation
belongs to the other session. Preserve its worktrees and all user-owned
processes. Keep the global benchmark lock, two Cargo workers and conservative
initial reservations plus the 8 GiB child floor. The disk monitor is read-only
for this task; do not start a competing repair or cleaner.

The unchanged September 13 12:45 suggestions were re-read on resumption.
[Review and dispositions](docs/SUGGESTIONS-REVIEW-20260913-1245.md).
[Prior state and parked experiments](docs/history/STATE-20260914-before-scratch-scalar-integration.md).
[Next-work history](docs/history/RUNTIME-NEXT-20260914-before-scratch-scalar-integration.md).
