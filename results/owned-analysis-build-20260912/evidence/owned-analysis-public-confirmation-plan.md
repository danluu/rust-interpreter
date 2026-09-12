Owned-analysis public confirmation plan, 2026-09-12

Prepared from source, fixed plans and earlier public storage evidence only.
No owned-analysis screen timing was inspected to choose this protocol. No source
clone, build, test, benchmark, dependency fetch or process control was performed.
The JSON companion fixes exact argument vectors, test names, counts, tool/source
identities and hashes. Nothing in this plan has been executed.

Decision already implied by the prior plans

The inherited published plans require the original Ruff default and Nushell
public generic-interface confirmations, each within 5% paired build-wall and
build-CPU regression. They do not set confirmation cycle counts. The earlier
pre-candidate3 proposal, .work/scalar-plan-public-confirmation-20260912.md
(SHA-256 0079aba7d68a960bb67ac4049277b1de6ab159203dffd9f334fd5907af883bbf),
already chose one THREE-CYCLE history per confirmation. Carry that choice forward.
The three separately initialized histories in the inherited fixed plan apply
to the token/pgrust screen; they do not require three fresh Ruff/Nushell caches.

Thus fix exactly these two histories before any confirmation observation:

- owned-analysis-confirm-ruff-20260912-01: three cycles, original default five
  cumulative production edits, initial native/baseline/candidate order. Fifteen
  edited pairs; 66 primary commands, 22 independent checking controls, 44 artifacts.
- owned-analysis-confirm-nushell-generic-20260912-01: three cycles, original one
  public-interface edit, initial baseline/candidate/native order. Three edited
  pairs; 30 primary commands, 10 checking controls, 20 artifacts.

The three cycles rotate each mode through each edit's three order positions.
Nushell's three pairs supply less evidence than Ruff's fifteen; do not present
these as equal statistical evidence. Do not shorten Nushell to one cycle, change
it to the parser-default workload, or choose a new cycle count after observing
results. Do not introduce a per-cycle speed gate or a pooled Ruff/Nu median:
the inherited confirmation guard is each complete case's median paired wall and
CPU ratio <=1.05. A complete passing token/pgrust screen remains a prerequisite,
with its original >=5% token wall gain, improving CPU and all regression guards.

Require both confirmations to complete regardless of an unfavorable first
confirmation unless correctness, artifact, infrastructure or storage controls
fail. Preserve all measurements and failures. An infrastructure-aborted history
is incomplete; retain it separately and prospectively fix any replacement's
complete unchanged protocol before observing a performance decision. Never retry
an unchanged performance-rejected binary for a pass or splice partial histories.

Pinned public source preparation requirements

Use root workspace /Users/danluu/dev/rust-interp-perf-20260912. Its .work/sources/
ruff and nushell directories did not exist at preparation of this plan. The
existing public originals below were read-only checked at the exact corpus pins
with no tracked changes. They remain user-owned; do not edit them or their
markers. Under the task's existing shared preparation lock, create full new
owned source snapshots using the existing preparation command:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/prepare.py ruff nushell --source ruff=/Users/danluu/dev/rust-interp/.work/sources/ruff --source nushell=/Users/danluu/dev/rust-interp/.work/sources/nushell
```

This is a proposed setup command, not an executed command. scripts/prepare.py
fetches the exact commit from the local original into a new independent Git
repository, checks out detached HEAD and writes .rust-interp-owned.json with
owner equal to the root workspace's absolute path and the pinned revision.
No source directory may be a symlink into the original checkout or a copy of its
old ownership marker. If a destination appeared meanwhile, inspect its ownership,
HEAD, tracked cleanliness and original file hashes; do not reset or overwrite it.

- Ruff: d136bd8d002a648de5f344df602e492658306f1e, package ruff_linter, lib test
  target, production crates/ruff_linter/src/registry.rs.
- Nushell: 9d3157963241cf89447119d34d6e887859f5e7e8, package nu-protocol, lib test
  target, production crates/nu-protocol/src/ty.rs. Case file
  benchmarks/experiments/interface-edits/nushell-generic-list.json has SHA-256
  109ecc7c03981cdb3bd3f38e67a3130562e2d5e60a63fb57fe9b41ae12f822d3.

Retain the complete pinned workspaces, Cargo.lock, manifests, build scripts,
proc macros, test resources and normal/dev dependencies. Preparation may fill
missing registry/git dependency sources outside measurements, but must not
prebuild or import any measured native/check/baseline/candidate target cache.
All measured commands retain --locked --offline through the common launcher.
Before a history, both its .work/runs and results paths must be absent; each
comparison mode gets run-id:mode as a new namespace and a distinct actual Cargo
workspace. Do not share targets across arms or cases. Toolchain and reusable
std-MIR provisioning remain setup outside edit timers; use the existing pinned
nightly-2026-09-08 and unchanged installed std-MIR identity.

Ruff must execute these six original test bodies at EVERY source state:

- registry::tests::documentation
- registry::tests::rule_naming_convention
- registry::tests::check_code_serialization
- registry::tests::linter_parse_code
- registry::tests::rule_size
- registry::tests::linter_sorting


The wrong edit rejects valid rule codes and must compile before failing the
original serialization assertion. Five correct edits remain exactly the default
WORKFLOWS['ruff'] history in scripts/workflow_cases.py. Do not use --vary-selection.

Nushell must execute these fourteen original test bodies at EVERY source state:

- ty::tests::oneof::oneof_lhs
- ty::tests::oneof::oneof_rhs
- ty::tests::oneof_flattening::test_oneof_creation_flattens
- ty::tests::oneof_flattening::test_oneof_deduplicates
- ty::tests::oneof_flattening::test_widen_flattens_oneof
- ty::tests::subtype_relation::table_list_oneof_covariance
- ty::tests::subtype_relation::test_any_is_top_type
- ty::tests::subtype_relation::test_list_covariance
- ty::tests::subtype_relation::test_number_supertype
- ty::tests::subtype_relation::test_reflexivity
- ty::tests::widen_shortcuts::test_chain_shortcut
- ty::tests::widen_shortcuts::test_glob_string_union
- ty::tests::widen_shortcuts::test_list_table_widen_preserves_list
- ty::tests::widen_shortcuts::test_widen_subtype_shortcut


The wrong edit reverses the Type::Any relation from Subtype to Supertype. The
correct edit generalizes Type::list(Type) to impl Into<Type> with inner.into().
Preserve the harness=false nu_test_support::harness::main entry; historical
--exact execution selected fourteen tests. Verify exact native selection/output.
nu-protocol's nu-test-support/os dev dependency brings nu-command, nu-cli,
nu-engine, nu-parser and nu-std libraries into the lib-test dependency graph;
removing those dependencies or extracting ty.rs would change the workload.
No --workspace/--all-targets or full Ruff/Nu CLI build is part of this protocol.

Frozen compiler and VM

Baseline tool key: 851ddd5f33e18954b586ec081af021778407efddf843afdaae88ec1f6647c527
Candidate tool key: eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d
Candidate compiler source: 04bb082113ae6fc04eee4ea0c370cdf1f5b34648.
Selected VM SHA-256 (both arms):
03d401c1df926f99941cdd5325c2d58848d25e3b774ffa7f27db20b448c65a20.
Selected wrapper SHA-256 (both arms):
56fec5a315571ba8308f5c2b637aff8b8be200ba84cde1ba7c606f61e47606d3.
Candidate exporter SHA-256:
2a33492691a047483e010314a215bc3861ca733225fc8d9cac14b85cc289065c.

Use the candidate bundle's SELECTED frozen VM, not the newly linked candidate
build's VM (hash 1301b8b...). The manifest explicitly distinguishes them.
Retain exact screen jobs, native repository profile and one native test thread,
JIT resumable calls/persistent registers, MIR3/inline8, toolopt0, leaf inlining,
std-MIR, unavailable-call traps, try callbacks and explicit limits on both arms.
Strict ordinary frontend checking and default-off function-payload reuse remain.
Do not substitute historical default MIR flags or smaller limits on a failed
confirmation; the earlier proposal explicitly retained actual screen settings.

Exact measured commands, in order

Execute directly from root workspace, sequentially, after source/tool/space
admission. The harness and verifier acquire the shared lock themselves; do not
nest either under another holder of the same lock. Preserve each command's
start/finish identity, exact arguments, output and return code in a controller
receipt fixed before the first command. Wait <=300 seconds through the existing
options. A capacity admission check belongs immediately before each history.

```sh
cd /Users/danluu/dev/rust-interp-perf-20260912
/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/bench_e2e_workflow.py --run-id owned-analysis-confirm-ruff-20260912-01 --project ruff --workflow default --initial-mode-order native,baseline,candidate --cycles 3 --jobs 18 --native-jobs 18 --native-profile repository --native-test-threads 1 --check-floor --minimum-free-gib 1 --lock-wait-seconds 300 --baseline-tool-key 851ddd5f33e18954b586ec081af021778407efddf843afdaae88ec1f6647c527 --candidate-tool-key eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d --comparison-engine jit --baseline-jit-resumable-calls --baseline-jit-persistent-registers --candidate-jit-resumable-calls --candidate-jit-persistent-registers --batch --inline-leaves --baseline-inline-leaves --trap-unsupported-calls --run-try-callbacks --std-mir --instruction-limit 100000000000 --allocation-limit 150000 --guest-mir-opt-level 3 --guest-mir-inline-scale 8 --build-tool-opt-level 0 --expect-identical-bytecode --build-metrics --verify-restoration

/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/verify_repeated_workflow.py results/owned-analysis-confirm-ruff-20260912-01/summary.json --wait-for-lock 300

/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/bench_e2e_workflow.py --run-id owned-analysis-confirm-nushell-generic-20260912-01 --project nushell --case-file benchmarks/experiments/interface-edits/nushell-generic-list.json --initial-mode-order baseline,candidate,native --cycles 3 --jobs 18 --native-jobs 18 --native-profile repository --native-test-threads 1 --check-floor --minimum-free-gib 1 --lock-wait-seconds 300 --baseline-tool-key 851ddd5f33e18954b586ec081af021778407efddf843afdaae88ec1f6647c527 --candidate-tool-key eb91912d5eb6d06fde8e873404b7235a62ad4527a4dfef9e84de093a917e974d --comparison-engine jit --baseline-jit-resumable-calls --baseline-jit-persistent-registers --candidate-jit-resumable-calls --candidate-jit-persistent-registers --batch --inline-leaves --baseline-inline-leaves --trap-unsupported-calls --run-try-callbacks --std-mir --instruction-limit 100000000000 --allocation-limit 150000 --guest-mir-opt-level 3 --guest-mir-inline-scale 8 --build-tool-opt-level 0 --expect-identical-bytecode --build-metrics --verify-restoration

/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/verify_repeated_workflow.py results/owned-analysis-confirm-nushell-generic-20260912-01/summary.json --wait-for-lock 300
```

Verification and final assessment

Keep the existing verifier invocation unchanged after each complete harness run.
It must verify fresh package compilation, compiler-success/runtime-assertion
failure for wrong edits, native and strict VM success for every correct edit,
unchanged tests, paired source/bytecode identity, source transitions, CPU sums,
distinct caches, preserved artifacts and exact mode order. Each cycle includes
its original anchor and wrong edit. AFTER SourceEdit.__exit__, cycle3/state-2
must freshly rebuild and execute the actual restored original in all three modes
and the checking reference. Exclude cold/anchor, wrong and restored controls from
edited pairs and medians.

A separate read-only assessor is needed because the common verifier validates
controls but does not decide this fixed build-performance gate. The assessor
must consume the two exact summaries and verification.json files, bind their
hashes and original planned commands, require their cases/test arrays/options/
tools/counts to match the JSON companion, and require the complete original
owned-analysis screen assessment to have screen_pass=true with all six planned
histories. Recompute ratios from the copied raw row's launch metrics and require
that they equal comparison.pairs before calculating medians. For each case:

  wall = median(p.candidate_build_to_ready_seconds /
                p.baseline_build_to_ready_seconds for every edited pair p)
  cpu  = median(p.candidate_build_to_ready_cpu_seconds /
                p.baseline_build_to_ready_cpu_seconds for every edited pair p)
  case_pass = wall <= 1.05 and cpu <= 1.05
  adoptable = original_complete_screen_pass and ruff_pass and nushell_pass

CPU is build_to_ready_cpu.total_seconds (launcher self plus waited children),
not cargo_cpu, full-command CPU, exporter phase timing or wall-minus-execution.
Use all fifteen Ruff and three Nushell pairs, and retain individual ratios and
per-cycle values descriptively. Do not subtract A/A noise or change the guard.
Save the assessor source/hash before confirmation, and its result afterward at
B/owned-analysis-confirmation-assessment.json. A sensible exact planned command,
after root implements this small read-only assessor at that fixed path, is:

```sh
python3 .work/build-general-20260912/assess_owned_analysis_confirmations.py
```

No such new assessor was implemented or executed by this read-only planning task.
The exact existing verifier commands above are ready. Root should finish/freeze
the assessor and its binding/controller checks before any confirmation starts.

Bytecode caveat and performance scope

Require exact corresponding baseline/candidate .rbc identity for every state,
including wrong edit and final restored original. Historical Nushell generic
pairs matched, but original/wrong-source artifacts differed between the cold
cycle and later cycles: 415 immediate changes across 115 functions and readonly
bytes10720->10736, with another Expected OneOf literal. Historical reports
results/interface-nushell-artifact-diff-01/assessment.md and
results/interface-nushell-literal-history-01/assessment.md retain that evidence.
This is not permission to waive a new paired mismatch. The common verifier
reports cross-cycle equality separately and does not require cold-original
bytes to equal freshly restored-original bytes. Retain exact artifacts and
investigate any newly different paired output; never normalize constants/data
or alter tests to make them match. The confirmation measures build readiness;
it does not establish runtime, cold-build, whole-command or holdout performance.

Storage admission

Root reports approximately33GiB free after an external capacity change. This
creates room to assess admission; it is neither reserved capacity nor proof of
future peak demand. Recheck capacity and planned-source/copy overhead under the
shared lock immediately before each history, while preserving all completed
screen evidence and earlier confirmation caches. Never run cases concurrently.

Historical logical-byte guides, including all four caches, 20% cache headroom,
1GiB running floor and256MiB evidence allowance, remain:

- Ruff three cycles:5,448,717,543 cache bytes ->7.339GiB admission guide.
- Nu one-cycle qualification:12,138,874,247 bytes ->14.816GiB guide.
- Nu fifteen-cycle history:18,331,056,142 bytes ->21.737GiB guide.

The14.82GiB number is only the historical one-cycle Nu qualification guide;
there is no exact three-cycle Nu inventory. For this fixed THREE-cycle history,
use21.74GiB as the more conservative retained-cache planning reference, not a
proven upper bound. Retained Ruff caches, new source clones, tool/std-MIR setup,
archive staging and unrelated-volume growth are additional. Do not start Ruff
based solely on a1GiB or3GiB floor; the per-command1GiB floor stays unchanged.
Do not lower the guard or reduce history length to fit a capacity shortage.

The original source/storage report at
.work/scalar-plan-public-confirmation-20260912.md preserves all exact public
inventory paths/hashes, pre-object-reclamation native totals and profile caveats.
Historical Ruff and Nu cache counts used native O0/incremental, four custom jobs,
default guest MIR and default native threading. This confirmation retains the
screen's repository native profile,18 custom jobs,MIR3/inline8 and one native
thread. Thus these are admission guides, not bounds or physical APFS reclamation
claims. No source/cache cleanup or compression was performed for this plan.
