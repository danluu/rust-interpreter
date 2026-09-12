Public scalar-plan confirmation proposal, 2026-09-12

Prepared by /root/binary_codegen from source and existing public reports only.
No source clones, builds, tests, benchmarks, cache operations, or process controls
were performed. The commands below are a proposal, not executed commands.

Root has approximately 5.3 GiB free. Do not admit either confirmation on that
basis: historical caches plus headroom exceed it. The proposed running floor is
1 GiB, matching the current screen; that floor alone does not reserve space.

Proposed fixed confirmation configuration

Use the scalar screen's existing frozen tools, VM, JIT flags, worker counts,
native profile, guest MIR flags, limits, and validation flags unchanged. The
case-specific historical alternative is default guest MIR and 1e9 instructions,
but changing to it is a separate predeclared confirmation configuration. The
commands below deliberately keep the actual screen configuration.

Tool receipts read from the root-owned worktree:

- .work/build-general-20260912/current-baseline-tools.json:
  key 851ddd5f33e18954b586ec081af021778407efddf843afdaae88ec1f6647c527
- .work/build-general-20260912/scalar-plan-tools.json:
  key eb6c524082894f10291d09e6b63f7b04e1750b2406aaab802b27ac458d81c2af
- Both VM SHA256:
  03d401c1df926f99941cdd5325c2d58848d25e3b774ffa7f27db20b448c65a20
- Both rustc-wrapper SHA256:
  56fec5a315571ba8308f5c2b637aff8b8be200ba84cde1ba7c606f61e47606d3

Run each case sequentially in the root-owned worktree after storage admission,
fresh owned source snapshots, and existing immutable tool/std-MIR setup are
verified. Keep distinct fresh run IDs and the common harness's separate
baseline/candidate namespaces. Do not import run_scalar_screen.py to obtain its
configuration: that file executes its controller at import time.

Propose three cycles per case as a confirmation guard: Ruff has 15 edited pairs;
Nushell has only three edited API pairs. This is not equal statistical evidence.
If fifteen API pairs are required, predeclare --cycles 15 for Nushell before
starting; its historical storage requirement is substantially larger.

```sh
cd /Users/danluu/dev/rust-interp-perf-20260912
confirmation_common=(
  --cycles 3 --jobs 18 --native-jobs 18
  --native-profile repository --native-test-threads 1
  --check-floor --minimum-free-gib 1 --lock-wait-seconds 300
  --baseline-tool-key 851ddd5f33e18954b586ec081af021778407efddf843afdaae88ec1f6647c527
  --candidate-tool-key eb6c524082894f10291d09e6b63f7b04e1750b2406aaab802b27ac458d81c2af
  --comparison-engine jit
  --baseline-jit-resumable-calls --baseline-jit-persistent-registers
  --candidate-jit-resumable-calls --candidate-jit-persistent-registers
  --batch --inline-leaves --baseline-inline-leaves
  --trap-unsupported-calls --run-try-callbacks --std-mir
  --instruction-limit 100000000000 --allocation-limit 150000
  --guest-mir-opt-level 3 --guest-mir-inline-scale 8
  --build-tool-opt-level 0
  --expect-identical-bytecode --build-metrics --verify-restoration
)
python3 scripts/bench_e2e_workflow.py \
  --run-id scalar-plan-confirm-ruff-20260912-01 \
  --project ruff --workflow default \
  --initial-mode-order native,baseline,candidate "${confirmation_common[@]}"
python3 scripts/verify_repeated_workflow.py \
  results/scalar-plan-confirm-ruff-20260912-01/summary.json --wait-for-lock 300
python3 scripts/bench_e2e_workflow.py \
  --run-id scalar-plan-confirm-nushell-generic-20260912-01 \
  --project nushell \
  --case-file benchmarks/experiments/interface-edits/nushell-generic-list.json \
  --initial-mode-order baseline,candidate,native "${confirmation_common[@]}"
python3 scripts/verify_repeated_workflow.py \
  results/scalar-plan-confirm-nushell-generic-20260912-01/summary.json --wait-for-lock 300
```

Run the verifier after the harness exits; do not nest it inside another holder
of the same benchmark lock. Root's owned lock symlink already provides the
shared coordination mechanism. Existing default native/reference gates remain.
Suggested confirmation guard, to be fixed before timings: each case's median
paired candidate/baseline build wall ratio and build CPU ratio must be <=1.05.
Use comparison.pairs baseline/candidate_build_to_ready_seconds and
baseline/candidate_build_to_ready_cpu_seconds. CPU is measured
build_to_ready_cpu.total_seconds. Do not substitute exporter phase timings,
Cargo-only CPU, whole-command CPU, or launcher-minus-execution estimates.

Every cycle includes original source, a compiler-success/runtime-failure wrong
production edit, and each correct production edit. The final restored-original
phase occurs after SourceEdit exits and must freshly rebuild and execute all
original assertions. It is excluded from edited medians and pair counts.
Ruff three cycles plus restoration: 66 primary commands, 22 independent checks,
44 custom artifacts, 15 edited pairs. Nushell three cycles: 30 primary commands,
10 checks, 20 artifacts, three edited pairs. Nushell fifteen cycles: 138 primary
commands, 46 checks, 92 artifacts, fifteen edited pairs.

Minimal dependency targets and original assertions

Ruff revision d136bd8d002a648de5f344df602e492658306f1e:

- Package ruff_linter, library test target only; production file
  crates/ruff_linter/src/registry.rs. No --workspace, --all-targets, --tests,
  --all-features, or Ruff CLI binary build is required.
- All six existing registry::tests entries run at every step: documentation,
  rule_naming_convention, check_code_serialization, linter_parse_code,
  rule_size, linter_sorting. Their assertions cover every rule having an
  explanation, rejecting disallowed name patterns, round-tripping rule codes,
  reconstructing parsed linter codes, sizeof(Rule)==2, and case-insensitive
  alphabetical linter order. Test source remains unchanged.
- The wrong edit makes every optional rule-code match false, exercising the
  original serialization assertion. Five cumulative valid refactors are the
  exact default WORKFLOWS['ruff'] history in scripts/workflow_cases.py: explicit
  optional-code match, explicit name conversion, explicit prefix-result match,
  named code suffix, explicit search loop. Do not add --vary-selection.
- Normal dependencies and dev-dependencies, including proc macros, parser/AST
  support, insta and test-case, remain required by the libtest compilation.

Nushell revision 9d3157963241cf89447119d34d6e887859f5e7e8:

- Package nu-protocol, library test target only, default features unchanged;
  production file crates/nu-protocol/src/ty.rs. The exact fourteen test names
  and production replacements are in the frozen nushell-generic-list.json.
  They cover OneOf relations/flattening/deduplication, table/list covariance,
  Any as top type, number supertype, reflexivity, and widening shortcuts.
- Wrong edit changes the Any relation from Subtype to Supertype. Historical
  native execution compiled successfully and failed the unchanged
  test_reflexivity and test_any_is_top_type assertions. Correct edit generalizes
  Type::list(Type) to Type::list(impl Into<Type>) with inner.into().
- This package uses harness=false and nu_test_support::harness::main; it is not
  a standard automatically generated libtest harness. Historical common native
  --exact selection ran exactly fourteen tests. Keep native stdout validation.
- nu-protocol's dev-dependency nu-test-support enables os; its normal dependency
  graph includes nu-command, nu-cli, nu-engine, nu-parser, nu-std and other shell
  libraries. Consequently --package nu-protocol --lib still has large native
  and metadata dependency caches. Removing that dev-dependency or compiling a
  hand-extracted ty.rs changes the workload and assertion harness.

The common launcher already selects exactly cargo check --package PACKAGE --lib
--profile test --locked --offline (plus the reusable std-MIR target). Native is
cargo test --package PACKAGE --lib --locked --offline with --exact names. An
independent --check-floor keeps its own native-check target. Do not prebuild or
share the measured arm target directories. Toolchain/dependency fetch and
reusable std-MIR setup are separate preparation; the historical std metadata
receipt was 112,958,025 bytes. Preserve source resources and workspace manifests.

Historical storage evidence

All cache counts below are unique logical bytes, deduplicating hard links by
device/inode in the original inventories. They do not promise APFS physical
allocation or future peak sizes. Three independent fresh histories would need
their own additional caches; the proposal above is one repeated history/case.

| Public history | Baseline GiB | Candidate GiB | Native GiB | Check GiB | Total GiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ruff, three cycles, full objects | 1.033 | 1.033 | 2.217 | 0.792 | 5.075 |
| Nu generic, one-cycle qualification, full objects | 2.658 | 2.658 | 4.337 | 1.652 | 11.305 |
| Nu generic, fifteen cycles, full objects | 2.698 | 2.698 | 10.023 | 1.653 | 17.072 |

Ruff total = 5,448,717,543 bytes. Nu qualification total = 12,138,874,247 bytes.
Nu fifteen-cycle total = 18,331,056,142 bytes. There is no measured exact
three-cycle Nu generic inventory in these references. Use a qualified estimate,
not interpolation presented as evidence; the fifteen-cycle history is a more
conservative retained-cache reference.

Using historical cache bytes *1.20 + root's 1 GiB running floor + 256 MiB evidence
allowance requires 7.339 GiB for Ruff, 14.816 GiB for Nu one-cycle qualification,
or 21.737 GiB for the Nu fifteen-cycle reference. These totals exclude source
clones, new tool setup, archive staging, unrelated-volume growth, and retained
earlier-case caches. Ruff without the optional check cache would still require
6.389 GiB under that formula; the proposal retains --check-floor.

Current profile uncertainty matters: these historical references used native
O0/incremental, 18 native jobs/default native test threading, four custom jobs,
default guest MIR and no explicit build-tool optimization override. Proposed
confirmation instead retains the current screen's native repository profile,
18 custom jobs, MIR3/inline8 and build-tool opt0. Ruff's pinned repository dev
profile sets opt-level=1, line-tables-only debug, lto=off, and package overrides.
Nu has no root dev/test opt override, but selected dependencies/build scripts
still matter. Historical inventories are useful admission evidence, not an
upper bound for these different settings or the newer exporter.

Exact source paths and hashes (all SHA256)

Ruff completed inventories, each results/<name>/summary.json:

- resumable-bulk-heldout-01-ruff-baseline-archive-01:
  de9f55f5f467136ee17fb1a615a1c270269f471aaf607d0b3c6c375949f31faf
  unique_original_bytes=1108777863
- resumable-bulk-heldout-01-ruff-candidate-archive-01:
  d46ab3f1a3b2a74e8ab4cedda611f6689f99e11b136ceb1095cb40ad42647af5
  unique_original_bytes=1108777858
- resumable-bulk-heldout-01-ruff-native-archive-01:
  0348bdf1c9d342b6affa1b571afdc3654627a8bf3654bca264784d1b3036fcaf
  unique_original_bytes=2380539355; this inventory retained native objects
- resumable-bulk-heldout-01-ruff-check-archive-01:
  85c6e6ce74183bb56f3466c4f2c17d00d8642e2eec31d26f2310e917430bbd3a
  unique_original_bytes=850622467

Nu qualification completed inventories, results/<name>/summary.json:

- interface-nushell-qualification-baseline-cache-archive-01:
  1f378d54880b9adedf5200dfa75e09d8670b7fb7e2a699fb8afe96fa4cba1ea6
  unique_original_bytes=2853814877
- interface-nushell-qualification-candidate-cache-archive-01:
  e72950f4b8cb28607189c7728b1902e586dd2e95425b3e336e1e3113b00ed45d
  unique_original_bytes=2853814858
- interface-nushell-qualification-check-cache-archive-01:
  084aaaf8d97f13da6bcb93e8c779cf8beee10ffff161244d411a961072b10971
  unique_original_bytes=1774282945
- interface-nushell-qualification-native-cache-archive-01:
  082a86fa30e154b8f5ad7850170dcb11643cfb3f8dd5e4548b88df351a76cdb8
  unique_original_bytes=3375225343 AFTER object reclamation; do not use as the
  complete native cache. Original full native inventory is
  /Users/danluu/dev/rust-interp/.work/reclaims/interface-nushell-qualification-native-objects-01/plan.json,
  SHA256 6909776085d6596c2b26727deda0fbe33a2d23fd64cf3b89b6d4d451e40fb4df.
  Sum entries by unique (device,inode): 4656961567 bytes, of which 1281736224
  were unique removable object bytes. Completed public receipt is
  results/interface-nushell-qualification-native-objects-01/summary.json,
  SHA256 a7cd938000727d7615f39dd5213599a531fbbc1864df5f42c707f814ac11107a.

Nu fifteen-cycle completed inventories, results/<name>/summary.json:

- interface-nushell-baseline-cache-archive-02:
  3e9c2ee046a755465bdb5158dd2271fca01a3895b648acd6b40f661cce69bf30
  unique_original_bytes=2896989978
- interface-nushell-candidate-cache-archive-01:
  ea3292b1a3af26fdd1f7e682352b01cce4dd8e939a6107e53912252ce30cd4c0
  unique_original_bytes=2896989979
- interface-nushell-check-cache-archive-01:
  f62fe3815d81627b7990630c65e39513be769c763de3c34f41b74905c36cd6ad
  unique_original_bytes=1774543196
- interface-nushell-native-cache-archive-02:
  83403c4d569bffcdf0c147e779d35212cedf1aa806e0e7d21dec3ecaa478017f
  unique_original_bytes=3375484037 AFTER object reclamation. Original full native
  inventory is /Users/danluu/dev/rust-interp/.work/reclaims/interface-nushell-native-objects-01/plan.json,
  SHA256 39f0d6db29e3f9e8516d44456e262b88853748f1ea78fc3c37030c13b9bf2797.
  Unique entries total 10762532989 bytes, including 7387048952 removable object
  bytes. Public receipt results/interface-nushell-native-objects-01/summary.json,
  SHA256 f301b6b92c5ab445bdb6eefc71b8e7c27292dc085aa9ebbf07ec3d34541af35f.

Artifact identity caveats

Keep strict paired bytecode identity for this source-only redundant-analysis
candidate. Every sample, including wrong source and final restored source, must
bind native execution and custom receipts to their actual selected assertions.
Do not waive a mismatch merely because the selected tests pass.

Historical Ruff paired and repeated artifacts were identical. Historical Nu
generic artifacts matched between baseline/candidate in every pair, while
original-source and wrong-edit bytecode changed between cycle zero and later
cycles. The generic-edit bytecode itself stayed identical. The detailed reports
results/interface-nushell-artifact-diff-01/assessment.md and
results/interface-nushell-literal-history-01/assessment.md show unchanged
function headers/opcode shapes but 415 immediate changes across 115 functions
and readonly data 10720->10736 bytes. A second copy of "Expected OneOf" appeared.
This suggests allocation-sharing history, but is not an equivalence proof.

Cross-cycle equality and paired equality are different checks. The verifier
records cross-cycle differences; it does not demand cold-original == final
restored-original bytes. Require fresh correct rebuild and matched final arms,
retain all exact artifacts/catalogs, and investigate any new paired mismatch.
Do not compare current artifacts to old runtime-candidate report hashes as a
gate: the exporter, controls, and catalog support changed. Do not normalize
addresses, constants, source assertions, or allocation data to force equality.
