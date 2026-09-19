# Matched N proc-macro clients

This is an unrun, source-only package for a client-only Arena04 candidate. It
uses the existing options-hash N compiler revision
`4de35bdacef0e3cd18a66bc30b5459c19e09b118`, its complete unchanged runtime, and
freshly compiled libraries. No installed nightly artifact enters these commands.

`proposal.json` preserves the preceding source-only deployment proposal.
`source-bindings.json` records 47 exact ordinary source copies and their original
paths, hashes, and identities: 18 files per proc_macro arm, two literal dependency
files, and nine real compiler fixtures. The two proc_macro arms differ only in
`src/bridge/arena.rs` and `src/bridge/symbol.rs`. Both use the same normal real
rustc-literal-escaper 0.0.8 dependency and codegen options. Explicit crate metadata
and output routes distinguish the arms; their source remap destination is equal.
These are new component builds, not claims of byte-identical bootstrap outputs.

The 27 fixed commands in `plan.json` are:

1. Build the normal literal dependency, stock proc_macro, and Arena04 proc_macro.
   All three preserve separate rlib/rmeta outputs with normal Rust dependency
   checks enabled.
2. Compile and run each complete real proc_macro crate as a test harness. Stock
   has zero source tests, so its result is compilation and loader smoke evidence
   only. Candidate must run all 13 existing Arena/Interner tests without filtering
   or skips. No test or shim is added to either library source.
3. Build each real macro dylib and run the same nine caller cases using the closed
   compiler02 fixture: exact value/string expansion, attribute and derive use,
   diagnostics, macro panic, type/borrow errors, stale symbols, and recovery.
   Default strategy remains default; only the explicitly declared TLS cases and
   additional success case select the existing same-thread strategy.

The new native test processes receive `DYLD_LIBRARY_PATH` containing only the
fully bound N target library directory. All children receive an explicit locale,
system PATH, owned TMPDIR and the SDKROOT from the saved N build record. Neither
the inherited shell environment nor any T library path is used. The SDK is an
external existing system provider; this package makes no new SDK qualification
claim and does not copy it. The source and all 65 N runtime entries remain live.

`runtime-inventory.json` binds the complete old compiled.stage1 table and original
compiler/source proof references. The runner hashes all 63 runtime files to EOF,
validates both exact source links without traversing them, and records complete
directory membership before and after execution. Every child is preceded by a
runtime identity/membership check; every generated library/test binary/dylib is
hashed before and after subsequent children. Binary dep-info must show the
selected matched client and literal pairs, and the caller's exact dylib. Stock
and candidate diagnostic stable fields must agree.

The observer is derived from the closed compiler02 runner. It owns only fresh
WORK and result directories, uses the existing canonical lock with a 600-second
wait, and records every child's actual return/closure and raw output. It sends no
signals and makes no retries. A child still live at its finite observer deadline
prevents success and every later command; the inherited lock remains with that
child. Admission requires 14 GiB free, observation stops new work below 9 GiB,
and the policy retains an 8 GiB floor. WORK plus results are limited to 256 MiB;
each child has a 64 MiB file limit, fixed CPU/observer bounds, and core dumps off.
This phase-specific entry policy budgets 8 GiB for the retained floor, 0.25 GiB
for the complete owned-output allowance, 4 GiB as an explicitly unmeasured
RSS/swap allowance, and 1 GiB for the live-stop cushion: 13.25 GiB, rounded to
14 GiB with 0.75 GiB additional margin. It does not lower full compiler,
application, or runtime-installation policies. The old 16 GiB runner, plan,
README and source review remain preserved under
`.work/proc-macro-arena-n-client-before-entry14-01`; `proposal.json` remains
unchanged historical source, including its original 16 GiB recommendation.

This is a reviewed planning allowance, not a measured peak-memory bound.
The five matched N builds use opt-level 3 and 16 codegen units; internal codegen
and linker concurrency can consume memory even though top-level commands are
sequential. Earlier installed-nightly opt-level 0/codegen-unit 1 tests provide
small-artifact provenance, not a peak estimate for this build. No RSS/swap or
address-space bound is claimed. WORK plus results are checked before/after each
command and on one-second observations; their 256 MiB total is a sampled
postcondition, not a hard filesystem quota. On a resource observation failure,
the runner records failure and refuses subsequent commands while allowing the
current child to close within its existing finite observation contract, without
sending signals. The 64 MiB per-file limit remains enforced. OS swap or tool
cache side effects and unrelated concurrent disk growth are not reserved by
this admission check. No measurement or workload was run to choose this policy.

The sole proposed invocation, after source review and root authorization, is:

```
cd /Users/danluu/dev/rust-interp-semantic-reuse-20260913
/opt/homebrew/bin/python3 -B experiments/proc-macro-arena-n-client-01/run_once.py
```

WORK `.work/proc-macro-arena-n-client-01` and results
`results/proc-macro-arena-n-client-01` must both be absent. No compiler or test has
been invoked by this package. Successful results would qualify these real N
external clients and fixtures only. The unchanged embedded builtin-quote client
is outside the optimization. A separately keyed runtime composition, complete
holdout/application semantics, and independent saved readback remain necessary.
Any native Ruff frontend screening is a later separate phase; this package has
no timing commands or performance claims.
