# Current state — September 18, 2026

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

The current manual branch is `experiment/guarded-capture-census-20260918`.
Main still adopts df4006e0. The aggregate and native-indirect compositions remain
archived after failing their original changed-source wall gates. The indirect
composition passed all correctness controls, 122 strict/cache commands and three
exact profiles, then completed the full 40-command token primary with wall ratio
1.00299236, CPU ratio 0.99040808 and wall A/A envelope 3.379272%. It was parked;
no larger comparison or unchanged retry was started.
[Indirect assessment](results/scalar-indirect-screen-token-01/ASSESSMENT.md).

Three disabled observers now narrow the next runtime work. Exact re-emission
attributes ordinary code generation mainly to region emission and liveness,
but its total warm host cost is only 66–114ms in these captures. Existing known
immutable Load/Copy operands account for 0/5/3 block/exhaustive/parser samples.
Guarded external value forwarding has only 2/2/0 available sites and no selected
samples. None warrants a runtime implementation or new timing screen yet.
[Emission stages](results/jit-emission-stages-01/ASSESSMENT.md),
[immutable reads](results/immutable-read-census-01/ASSESSMENT.md),
[guarded values](results/guarded-value-census-02/ASSESSMENT.md).

The resumed September 18 inspection confirms the last census finished and its
closure is intact. No unfinished command from this run was inferred to be active.
Suggestions remain unchanged. The independent disk monitor reports stale status;
this task uses fresh disk admission checks and does not repair or restart it.
The completed indirect primary's compiler intermediates were already retired:
3,147 files, about 1.47GiB actual space, all 2,532 protected hashes unchanged.

The smaller range-admission census is also complete: 43/59/7 new groups but
only 14/0/0 block/exhaustive/parser samples. It preserves exact original code and
all previously selected proofs. Defer smaller runtime guards and keep the
threshold of eight. Frame-initialization review confirms prior proof extensions and clearing rewrites
already address that area; register-array zeroing is absent in retained profiles.
[Range admission](results/range-admission-census-01/ASSESSMENT.md).

A bounded scalar call-chain census passes after two retained diagnostic failures.
It admits 57 additional initialized/confined direct-call DAGs but selects no
Call/Return samples in either current token capture. Defer parent scalar graphs.
Four private external payload slots find 99 reuses in three functions, but only
15 block source-address/load samples and none in exhaustive/parser, before capture
cost. Defer this new runtime cache too.
[Call-chain scope](results/scalar-chain-census-03/ASSESSMENT.md),
[external captures](results/guarded-capture-census-01/ASSESSMENT.md).

Next qualify a new composition of native indirect transitions, successor-only
spilling and checked readonly scalar leaves on the adopted scalar/scratch runtime.
Keep all isolated failures; infer no additive gain. Require new complete memory,
fault, profile, strict/cache and original-test qualification, then the unchanged
full-token changed-source primary. No aggregate output expansion, new memory
capture policy or smaller range guard is included. Preserve current main's peer
compiler-selection fixes when publishing or integrating launcher changes.

The compiler/Cargo/parser-exporter investigation belongs to the other session.
Preserve its worktrees and all user-owned processes. Keep the global benchmark
lock, two Cargo workers, the shared owned build target, conservative reservations
and the 8 GiB child floor. The disk monitor is read-only for this task; do not
start a competing repair or cleaner. The saved goal stays paused while manual
optimization continues.

The September 13 12:45 suggestions were re-read on September 18 and their SHA
remains unchanged: 4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f.
[Review and dispositions](docs/SUGGESTIONS-REVIEW-20260913-1245.md).

## 2026-09-19 runtime scheduler qualification (experimental branch)

Duration-based session ordering remains on experiment/session-duration-order-20260919.
Full qualification passes679Rust/profile17ignored,39diagnostic,10feature-off
session,31ordinary-model/defaultVM and hash-boundPython442+22skip. A disk stop
after the two full profiles was preserved; recovery reused the completed commands.
Actual parser replay passes1824invocations with19597independently regenerated hits.
Diagnostic replay passes1824/19964observedhits. Independent saved-report audit
checks prior-duration ordering and exactcoverage on16requests. The longest test
starts first in all ten valid edited reports; cached worker median264.122→242.255ms
in separate instrumented observations. Its own interval increases, so this is only
mechanism evidence. No command speedup or default adoption; changed-source primary06
remains required. Runtime source is deliberately retained on its experimental branch.
Exact primary05 retired compiler intermediates cleaned15152files/2,991,235,194bytes;
11410protected hashes unchanged, independent closure complete. Neverrepeatcleanup.

## 2026-09-19 scheduler changed-source screen passes

Primary06 is closed:40actualsource commands plus two strictrejection controls,
114originaloutcomes/artifacts/source restoration. Median candidate/adopted wall
0.9311698739+A/A0.0308233457=0.9619932196;CPU0.9104683898+0.0308595313=
0.9413279211. Bothgates pass. Nativewall1.2718753876; defaultunchanged. Tool
60bc004658a1db09e1c905eed50e25062f1ff8ae27811331aed9ad51b206a5a5 uses
qualified normal scheduler VM/server with adoptedcompiler tools. Fullthreecycle
110command guard is next; no adoption until it and laterprojectguards pass.
Primary06 closedcache cleanup15152files2991235289bytes,11413protectedhashes
unchanged and independentlyclosed; neverrepeat. Runtime source remainsbranchonly.

## 2026-09-19 full scheduler parser comparison passes

Full03 closed:110realchangedsourcecommands+2strictrejections,15editedpairs,
114originaloutcomes/artifacts/source restoration,22requests/session andcomplete
CPU accounting. Wallratio0.924398703+maximumA/A0.045926122=0.970324825;CPUratio
0.902712343+0.039480337=0.94219268. Bothgatespass. Nativewall1.249979858.
Priorfull02 wasnotadmitted because protocol01 froze previouscandidateselection;
zero workload/timingcommands. Sameeightcontrols requalified asprotocol02 before03.
Savedcosts: candidatebuild1223.803ms/exec267.423ms/longest210.638ms/preceding0/
serveroutside29.520ms. Durations overlap andmediansarenotadditive. Next verified
fre token artifactreplay, then remainingprojectguards; runtime/defaultunchanged.
Additionalclosedsetupcachecleanup941files438200579bytes,2209protectedhashes
unchanged andindependentlyclosed. Neverrepeatretirement; nopeerworktouched.
