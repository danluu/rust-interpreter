# Checked-in changes

## 2026-09-11 current decisions

- Aggregate relocation was integrated as `5b2330c/9637b0ac` after both primary gates and seven held-outs passed.
- Budget-register, call-slot and whole-call experiments were parked after their declared token gates failed. Their failures remain recorded.
- Scalar value calls now live as normal Rust source on `experiment/scalar-value-abi`, measured commit `840fdb5`. Compiler/runtime qualification passed 334 debug and release tests, frontend/Cargo controls and original fre assertions.
- The scalar short edit screen failed its 8% target: token paired wall −0.74%, folded −0.41%. Full A/A and held-out runs are stopped; next work targets export costs and stronger native controls.
- The source branch adds release readiness checks, terminal-fault documentation, custom default workspace members, automatic Python/format checks, a dedicated rustfmt commit and shared 18-worker benchmark defaults.

[Current status](STATUS.md) · [Scalar decision](results/scalar-edit-smoke-01/assessment.md) · [Review](docs/SUGGESTIONS-REVIEW-20260911.md). Earlier entries below describe their historical state.

## 2026-09-11 held-out and interface qualification

- The resumable/bulk candidate now independently passes native, TLS and fresh
  fre body coverage. Seven held-out cases verify 588 commands/105 edited pairs/
  294 artifacts across two histories, with no paired wall regression above 5%.
  Both original token gates remain failed; options stay experimental.
- Preserved an interrupted disk-full run and restored its exact benchmark edit.
  Source restoration is staged before mutation; source/receipts publish
  atomically and child processes are drained/waited on receipt failure. Ten
  fault checks pass, including three real child processes.
- Added validated public case files and independent reconstruction of source
  states/selections/orders. Pgrust and Nushell generic API qualifications pass
  original assertions and wrong-edit controls. Fifteen pgrust API-edit cycles
  verify 180 commands and 90 paired artifacts; repeated Nushell work follows.

- Native region Call experiment `26833c3` / `2f31c6a0`: 231 workspace tests pass
  in debug/release; repeated real edits improve token 19.3% paired and regress
  folded 1.4%. Both original gates fail. Preserve 168 commands/84 verified artifacts
  and keep the options experimental. Added reproducible gate evaluation and fresh
  owned-process sampling to select the next runtime change.


## 2026-09-11 bounded-call experiment

- Added active-prefix linear memory with initialized spare storage. Guest bounds,
  budgets, reuse zeroing and alignment padding remain explicit. The initial
  storage check passed 206 workspace tests.
- Added conservative instruction/depth/register/frame bounds for native call
  trees, using the actual emitter support rules. The expanded check passed 212
  workspace tests. Native Call/Return emission is still pending; no new runtime
  performance result is claimed.
- Added a reusable test driver that records source snapshots, commands, child
  identity, terminal status and logs under the benchmark lock.

## 2026-09-10 review follow-up

- Completed the repeated stronger-native corpus: 756 commands, 189 independent
  checks, 378 artifact checks and restored pins for all five projects. Token and
  folded retain substantial compute gaps. Updated generated status/evidence.
- Added typed native-call eligibility and whole-tree budget censuses (eight and
  nine diagnostic tests), then selected a bounded native call-tree experiment
  with explicit terminal traps. Runtime implementation is still pending.
- Fixed corpus recovery receipts so each new case clears the previous child's
  identity and exit fields; the measured run finished before this script change.
- Native controls: configurable profile, build jobs, test concurrency and exact
  compiler arguments, with a separately timed Cargo-check reference and nested
  exporter-stage reporting. Two three-cycle pgrust qualifications completed
  168 commands; nine helper tests pass. Added a serial corpus runner and durable
  supervisor, plus a Git-backed index for three exact tool builds.
- `a2a0e04`: known JIT branch/assertion limits decline before code publication;
  internal relocation errors remain errors. Explicit unsafe entry/thread contract.
  Five new tests; workspace check: 188 bytecode, 11 exporter and 3 cache tests pass.
- `93abea7`: repeated real-edit cycles, balanced mode positions, child CPU time,
  source transitions and per-edit spread. All 63 token commands completed.
  Paired artifacts match; stronger cross-history identity failed and is retained
  as an unresolved diagnostic. The retained engine remains slower than native.
- Current documentation now separates mechanisms, measured status, upcoming work
  and historical narratives. The results index is generated without deleting or
  relocating existing evidence. Every external suggestion has a recorded decision.

## Earlier retained work

- `9358c2b`: tracked token workflow, allocation-limit flag and reproducible launcher.
- `a01ad19`, `641867b`, `58657e0`, `d3983e2`: typed MIR/frame inventories and
  owned-process CPU sampling; argument-only zero elision was parked.
- `6b2c61f`: retained local-memory forwarding in the custom JIT; source `57a54edd`
  reproduces measured `af9aa691` production binaries exactly.
- `32f5e2f`: initialized local Git with the prior engine, benchmarks and evidence.

Historical experimental details remain in [results](results/INDEX.md) and
[the pre-review documentation](docs/history/README-20260910-before-review.md).

### Bounded native emitter experiment

Implemented complete direct AArch64 call trees with shared immutable code,
checked dependency readiness, ABI copies/zeroing, return truncation and named
fault propagation. Direct-entry differential checks and a 64-frame callee-saved
register/stack probe pass; 219 workspace tests pass in total. The normal VM path
is not connected yet, and no new performance result is claimed.

### Opt-in VM native calls

Connected complete trees through `Limits.jit_native_calls` and CLI
`--jit-native-calls`; added separate tree profiling/stats and candidate-only
benchmark forwarding. Whole-tree readiness/limit declines preserve VM fallback;
root/TLS completion stays in the VM. Fixed heap detection for C allocation
operations. All 225 workspace tests and seven CLI checks pass. Added optional
release tool publication after the recorded workspace check. No speedup result
yet; the path remains experimental and disabled by default.

### First native-call E2E result

Source `09de2a9` / tool `c98d995b` passes 225 debug/release workspace tests and
all 168 repeated real workflow commands (84 paired artifacts). Token improves
14.4% paired; folded regresses 3.0%. Both original gates fail, so the option
remains experimental. The next step is native Calls inside ordinary regions,
with the same correctness and full-command performance requirements.

### Native Call stubs in ordinary regions

Implemented optional linked outer Calls, readiness caching without retained host
pointers, complete-cursor raw pointers, and mixed 16/64-byte native frame exits.
Preserved exact VM fallbacks and separate ordinary/tree profile accounting; fixed
nested preparation timing double-counting. All 231 workspace tests and seven CLI
checks pass. Release and real edit/build/test qualification are next.
