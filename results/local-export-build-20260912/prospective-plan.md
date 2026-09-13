# Candidate5: fixed build-readiness adoption protocol

Prepared from the published candidate3 protocol and original public source
controls before candidate5 adoption timing. Root review is required before
freeze/execution. No workload, checker import, build, test or cache inventory
was performed during this preparation. The 24-launch three-arm phase/census
diagnostic is diagnostic evidence only and supplies **zero adoption samples**.

Baseline is published tool/source key
`eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d`;
candidate5 is `14af97a36405cc925ce89529e5bc9ff2db9ecdbd0f8b816095ace66235fc4c75`.
Both arms select VM SHA-256
`03d401c1df926f99941cdd5325c2d58848d25e3b774ffa7f27db20b448c65a20`
and wrapper `56fec5a315571ba8308f5c2b637aff8b8be200ba84cde1ba7c606f61e47606d3`.
The candidate-built VM is not substituted. This is an exporter build-latency
comparison with identical executed artifacts, not a runtime optimization trial.

Before `run_local_export_adoption.py freeze`, require actual terminal receipts:

- `local-export-qualification.json`: 408 passed, zero failed, one ignored in
  each debug/release profile; full validation 23,727 commands with raw records.
- `local-export-{reuse,dependency,cache}-passed.json`: actual original checker
  results, respectively 337/293/98 commands, bound to these two tool keys.
- `local-export-audit-inline-passed.json`: 79 audit-artifact commands, 23 or 24
  unchanged leaf-inline commands according to its frozen optional legacy-check
  presence, and eight paired audit exports retaining eight artifact pairs.
- `local-export-panic-late-passed.json`: all 90 new commands and explicit actual
  same-block MIR / Not(64)-to-Store(8)-before-Trap coverage, with the stored value
  equal to the 64-bit complement of the helper's second argument. Require the
  four exact MAX-minus-value decimal oracles and all proof hashes. Merely
  reaching `awaiting structural inspection` does not satisfy this prerequisite.
- Preserve `local-export-panic-coverage-failure.json`, SHA-256
  `9a957ecd4af45cd659c288e13d16f73ad6618ccebc38e1921bbc48789c23f525`, and verify
  every proof it binds. The new passing receipt must reference that exact old
  failure. The original `local-export-panic-passed.json` must remain absent.

This prerequisite amendment is prospective, before any adoption freeze/timing.
All five preceding adoption drafts and hashes are retained in
`local-export-adoption-before-late-prerequisite-01`. The original panic90 passed
behavior/artifact comparisons but failed its structural target (Copy8 and a
separate formatting-call block); it is not relabeled as a pass. The separately
reviewed late-panic source/protocol changes the fixture semantics explicitly to
MAX-minus-value and retains the same-block and actual scalar Store requirements.
No adoption command, workload, sample count, runtime option or gate changes.

Freeze verifies every receipt and its proof map, all 146 candidate compiler
inputs, common measured scripts, both installed bundles and ready manifests,
the original/copy/local std-MIR proof chain and all 26 unchanged metadata files,
actual Python and resolved Git/Cargo/rustc launcher binaries, source pins and
original production/test bytes. It records concrete argv before measurements.
The std-MIR key remains
`bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef`.
Original source-ready provenance and the owned local-ready hash stay distinct.

The JSON companion `local-export-adoption-commands.json` fixes these histories:

| Phase | Fresh run ID suffix | Cycles | Edited pairs | Primary / check / artifacts |
| --- | --- | ---: | ---: | --- |
| Screen | token-20260912-01, -02, -03 | 1 each | 5 each | 24 / 8 / 16 each |
| Screen | pgrust-20260912-01, -02, -03 | 1 each | 5 each | 24 / 8 / 16 each |
| Confirmation | confirm-ruff-20260912-01 | 3 | 15 | 66 / 22 / 44 |
| Confirmation | confirm-nushell-generic-20260912-01 | 3 | 3 | 30 / 10 / 20 |

All IDs start with `local-export-adoption-`. Raw paths are `.work/runs/ID`,
reports `results/ID`. The six screen histories run token then pgrust for each
initial order: native/baseline/candidate, baseline/candidate/native,
candidate/native/baseline. Confirmation initial orders are native/baseline/
candidate for Ruff and baseline/candidate/native for Nu. Each confirmation has
three cycles in one independently initialized history, as originally fixed.
There are 240 primary commands, 80 checking controls and 160 retained artifacts
across the eight histories; 48 edited baseline/candidate pairs total. Each
history is immediately followed by the unchanged independent verifier.

Keep every original pin and test selection:

- Fre `e0df0b010b156b030a02f073588d28703f4267f3`, token-phrase-allocation,
  package fre-kernels, all three existing token-phrase tests and five cumulative
  production edits in `crates/fre-kernels/src/token_phrase.rs`.
- pgrust `38d2517d3e09168a8fe222837730d435238ff358`, default hashfn workload,
  all four existing tests (including the 100,000-iteration roundtrip loop) and
  five production edits in `crates/common/hashfn/src/lib.rs`.
- Ruff `d136bd8d002a648de5f344df602e492658306f1e`, default ruff_linter registry
  workload, all six original tests and five production edits.
- Nushell `9d3157963241cf89447119d34d6e887859f5e7e8`, the original public
  generic-interface case, all fourteen nu-protocol type-relation tests and its
  one Type::list generalization. Keep the original wrong Any relation control.

The complete test names, wrong/original/edited source-state hashes, case hashes,
production paths and exact argv are in the companion. Keep pinned workspaces,
Cargo.lock, manifests, build scripts, proc macros, resources and normal/dev
dependency graphs. No extracted source fixture or rewritten assertion is used.
Existing owned source snapshots must be clean at the pinned HEAD, with their
root-owned marker and original production/test bytes. No reset, source clone or
cleanup is performed by these controls. Fresh run paths and each exact derived
custom workspace must be absent before freeze and history admission; native and
check targets remain inside each new raw run. Namespace strings are ID:mode.

Every measured command retains `--jobs 18 --native-jobs 18`, repository native
profile, one native test thread, strict ordinary frontend checking, default-off
function-payload caching, batched original tests, both arms' resumable JIT calls
and persistent registers, both arms' leaf inlining, std-MIR, explicit unavailable
call traps/try callbacks, MIR optimization 3 and inlining scale 8, host tool
optimization 0, logical instruction limit 100,000,000,000 and allocation limit
150,000. Native/check profiles and dependencies stay intact. There are no
selection changes, native rustflag overrides, isolated-batch changes or Cargo
timing reports. Ordinary launcher `--build-metrics` stays enabled; function
census, dependency/replay observers and optional exporter timing diagnostics
remain **off**. No selected-Cargo observer shim or diagnostic environment is
used. Existing ordinary pass summaries are not additional phase observations.

Run from the root worktree using the same Python executable used for freeze:

1. `run_local_export_adoption.py freeze` after all qualification receipts pass.
2. `run_local_export_adoption.py screen`; all six histories and their verifiers.
3. `assess_local_export_adoption.py screen`; refuse incomplete results.
4. Only after screen PASS, `run_local_export_adoption.py confirmation`; both
   original confirmations and verifiers, regardless of an unfavorable first
   case unless correctness or infrastructure prevents continuation.
5. `assess_local_export_adoption.py confirmation` after both complete.

Do not wrap these commands in run_locked.py. The controller briefly holds the
original shared benchmark lock for each history's admission/source/proof checks,
spawns the unchanged self-locking harness, and releases admission before waiting
for child output. Harness and verifier each retain their own original lock and
300-second wait. Admission remains 3 GiB for screen histories, 7.34 GiB for Ruff
and 21.74 GiB for Nu; every benchmark command retains its 1 GiB floor. The larger
confirmation figures are the inherited historical admission guides, not current
measured cache bounds or a reservation. Check actual capacity before launch;
do not reduce jobs, cycle counts, dependencies or correctness checks to fit it.

The adoption metric is the median of every edited pair's candidate/baseline
`build_to_ready_seconds`, and separately its
`build_to_ready_cpu.total_seconds` (launcher self plus waited children before
VM execution). It is not exporter stage time, cargo CPU alone, wall minus VM,
full-command timing, a cold build, or a speed claim against native Cargo.

The inherited fixed screen gate is unchanged: all 15 token pairs together must
have median wall ratio **<=0.95** and CPU ratio **<1.0**. Every one of the six
individual histories and aggregate pgrust must have wall and CPU medians
**<=1.05**. Both confirmations then independently require their complete case's
wall and CPU median ratios **<=1.05**. Do not pool Ruff/Nu, add a per-cycle
confirmation gate, subtract A/A noise, discard outliers, select favorable
histories, or claim equal precision from fifteen Ruff versus three Nu pairs.

The assessor joins every paired value back to the raw launch receipt, checks
the unchanged independent verifier, source states/test lists, exact jobs/options,
selected tools/wrapper, namespace, bytecode and complete counts, and retains all
individual ratios. Cold/anchor/wrong/restored states remain controls and are
excluded from edited medians. Every wrong edit must compile then fail an original
assertion; every correct edit and the post-context restored original must freshly
compile and execute. Source restoration must be complete at each history end.

A started failure stops and preserves the controller and every raw result; this
controller has no continuation/retry/reclamation mode. Any genuine infrastructure
recovery must be prospectively documented against the preserved failed history
before a new unchanged complete-history replacement, without seeing a performance
gate or splicing partial pairs. Never retime an unchanged performance-rejected
candidate for a pass. No cache maintenance runs during timing; no out-of-scope
process is signaled. Publication requires final evidence/source review after
all fixed gates, not merely a favorable initial screen.
