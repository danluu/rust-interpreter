# Exact owner-input coverage diagnostic

Source-only, uncompiled and unrun. This standalone `rustc_driver` tool answers
whether the candidate's **input gate** accepts meaningful numbers of owners on
ordinary code. It measures neither cache hits nor time saved. It creates no HIR
sidecars and does not enable the compiler patch.

`main.rs` imports the actual candidate `input.rs` byte-for-byte. A const check
compares that input against the generated snapshot, so a changed gate cannot
silently compile with stale instrumentation. `prepare.py` first verifies the gate
against `../patch.json`, then generates only failure-site instrumentation. The
instrumented copy records the first `None`/`?` rejection's original source line;
the normal gate remains authoritative. Every visited item requires identical
acceptance, full encoded inputs, owner identity and current span between copies.
A discrepancy is retained as an invalid report after ordinary compilation.
`generated.json` maps all 85 failure sites to exact gate source/methods and binds
the generated files. It is not a regex estimate of application syntax.

The nine unchanged interfaces in `api-source-proof.json` were compared byte-for-byte
at the pinned public commit `cea272fa356e94bd2ee2cadf376630aa0683867a` and the
candidate base `58e1e1f5311f4424ea81def4763081f6da62d9b3`. This is source evidence,
not proof that the new driver builds or that an arbitrary installed binary is
that compiler.

The pinned driver finishes resolution before `after_expansion`. The callback
borrows both `Steal` values immutably, visits them, and drops the visitor and guards
before returning `Compilation::Continue`. The original query providers are kept.
It does not steal the resolver, consume lint/disambiguator state, request HIR or
analysis, mutate AST nodes, or stop compilation. The gate's local `def_path_hash`
read does not force HIR. Early lints and all later checking/codegen/linking remain
in their stock order. `after_analysis` also returns `Continue`.

The later stock AST indexer replaces nested item/use structures. Accepted scalar
functions contain none of those structures, so their gate inputs survive indexing
unchanged. The visitor follows ordinary items, associated/foreign items, crate and
nested use owners; it skips attribute expressions just as the indexer does. It
retains resolver-owner and unvisited-owner totals rather than silently treating
all definitions as free functions. Output-capture guards are not run by this tool:
input eligibility is an upper bound on eventual cache coverage.

The report is written to a new PID/time-named JSON file in an explicitly supplied
existing owned directory **after `run_compiler` returns**. It includes normal
compiler success, after-expansion/analysis observations, per-kind eligible/fallback
counts, exact rejection sites, per-owner DefPathHash, source-span sizes, full
resolved-input encoded sizes, and candidate key sizes/budget acceptance. The key
size uses the actual public session version/options and the candidate codec digest;
it is not an asserted byte-identical cache key for a different custom compiler.
Only `coverage_usable=true` records with no problems may inform a coverage decision.
Failed checking and dep-info-only/no-analysis/probe invocations cannot pass that
gate. Diagnostics and stdout remain untouched; all raw compiler output must be
retained by the outer runner.

The driver changes only its relocated executable's **default** sysroot to the
build-bound stock sysroot. Explicit `--sysroot` survives, as do all input compiler
flags, feature/checking settings, Cargo/backend/linker jobs and profiles. Wrapper
mode removes Cargo's one compiler-executable argument after an exact path check;
it launches no subprocess and does not bypass a downstream compilation step.
It is an ordinary compiler replacement for an isolated diagnostic workflow, not
a replacement for the interpreter/exporter's production route or a timing sample.
No project name or application-specific condition occurs in the mechanism.

## Future admission and qualification (not executed)

1. Under the canonical absolute workload lock, use the existing pinned public
   rustc/rustc-dev installation. Retain its full `-vV`, executable, compiler/private
   and dynamic-library identities and this directory's complete source inputs.
   Regenerate/compare `generated.json`; preserve every candidate module referenced
   by `include_str!` as well as the gate. The actual binary identity is assigned
   after building; no source hash is called a tool key.
2. Build `main.rs` directly with that exact rustc, edition 2024, and the normal
   rustc-driver native rpath (`-L native=<PUBLIC>/lib` and, on this Mac,
   `-C link-arg=-Wl,-rpath,<PUBLIC>/lib`). Set compile-time
   `HIR_COVERAGE_PUBLIC_SYSROOT=<PUBLIC>` and
   `HIR_COVERAGE_PUBLIC_RUSTC=<PUBLIC>/bin/rustc`. No Cargo dependency build or new
   compiler clone is needed. Record the complete command/profile/environment and
   output identity. The linked-version check is an extra guard, not a substitute
   for the full build identity receipt.
3. Run `fixture.rs` through both the public compiler and the new driver with
   otherwise identical native arguments and separate fresh incremental/output
   directories, then execute both artifacts and compare output. Require exact
   gate/instrumented equality, an accepted `anchor` owner, fallback for calls,
   generics, attributes/macros and associated items, and no unexplained owner gap.
   Repeat one actual body edit plus an earlier Unicode source shift and compiled
   restoration; compare acceptance/byte distributions and native output. There
   are no expected cache-hit claims because this tool never reuses HIR.
4. Compile the same fixture with each existing `--cfg type_error`, `borrow_error`,
   `const_error`, and `panic_error` through both routes. Require matching raw
   structured diagnostics and failure, unusable coverage, followed by compiled
   restoration. Also retain ordinary version/dep-info-only probes with unusable
   coverage rather than treating them as compilation controls.
5. Only then admit an isolated existing workload under its unchanged compiler
   arguments. Set `HIR_OWNER_COVERAGE_OUTPUT` to the owned report directory. For
   Cargo set the exact build-bound public `RUSTC`, this binary as `RUSTC_WRAPPER`,
   and `HIR_OWNER_COVERAGE_WRAPPER=1`; preserve all other Cargo inputs/configuration
   and record the wrapper change as diagnostic instrumentation. Every compiler
   operation/check stays inside its ordinary complete command. Count reports only
   after overall workflow success and frozen-source/compiler checks. This is
   coverage evidence, not a latency measurement or a final-target qualification.

Use `/Users/danluu/dev/rust-interp/.work/benchmark.lock` for the future build and
controls, with existing bounded admission/owned-child receipts. No build, test,
project compilation, new holdout inspection or active compiler mutation occurred
while preparing these sources.
