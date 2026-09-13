# Opt-in host proc-macro code generation

Status: source-only candidate design, 2026-09-13; not qualified or timed.
This is an explicit amendment for this separately selected mechanism to the
fixed-profile comparison rule. The intended transformation is to compile
eligible macro implementations with codegen opt-level 1. Application manifests,
Cargo profiles, build-script environment, features, checks, required units and
macro invocations remain the baseline inputs. It is not a compiler-query reuse
or proc-macro result cache. In particular, `-Zcache-proc-macros` stays disabled.

## Evidence and scope

The saved first cold diagnostic compiled 33 actual host `proc-macro` targets at
opt-level 0. Their `syn`, `quote`, `proc_macro2` and other host library dependencies
were also unoptimized. Warm edits reused these libraries but still executed
macros. The second diagnostic measured 966 selected-unit `expand_proc_macro`
events totaling 0.391138496 seconds of self/inclusive event time. Other processes
overlap, so their event durations are not additive wall time or process CPU.
These instrumented observations suggest a candidate, not a speedup estimate.

Optimize only an actual, unselected Cargo host invocation with exactly one
`--crate-type proc-macro`, no explicit target, exactly one ordinary source input,
and one definite `--emit` containing `link`. Do not infer this role from crate
names or the absence of `--target` alone. Ordinary host libraries, build-script
executables, guest units, selected exports, metadata-only jobs and metadata
probes retain baseline arguments. Transitive macro dependencies stay unchanged.

Use one public-pinned exporter/VM/wrapper build for off/on/off comparisons.
`--host-proc-macro-opt=on` requires complete std-MIR routing and a supporting tool
capability; it cannot combine with a custom compiler, custom Cargo or borrowck
query-cache policy in this first experiment. Std-MIR preparation occurs before
this application-only wrapper environment is set, so the existing same std-MIR
installation is deliberately shared. Project caches include the policy identity;
turning the option off restores the original workspace identity.

## Pinned compiler boundary

The public nightly's Rust revision is
`cea272fa356e94bd2ee2cadf376630aa0683867a`. Inspection used the independently owned
stable-CGU derivative checkout; `session.rs`, `config.rs`, the inspected MIR
policy files, and the metadata encoder have no Git diff from that public base.
`options.rs` differs only by the added stable-CGU flag declaration; its inspected
boolean parsers and option defaults are unchanged. The derivative's
`73a11f167216d3955c277ed47f9b8cc68208105b` identity is not a public nightly source
revision. The following are relevant upstream source paths:

- `rustc_session/src/config.rs`: opt-level 0 defaults debug assertions to true;
  MIR level is 1 at O0 and 2 otherwise; generic sharing stays enabled at O1.
- `rustc_session/src/session.rs`: overflow and UB checks default to effective
  debug assertions; optimized compiles otherwise enable local ThinLTO; codegen
  unit defaults depend on incrementality/target, not this opt-level change.
- `rustc_mir_transform/src/inline.rs`: O1 keeps the ordinary MIR inliner disabled
  at levels 1 and 2, including per-function `#[optimize]` overrides that select 2.
- `rustc_mir_transform/src/pass_manager.rs`: per-function optimization attributes
  retain their own MIR level overrides.
- `rustc_metadata/src/rmeta/encoder.rs`: proc-macro metadata skips `encode_mir`.

For an eligible invocation with no explicit optimization or MIR policy, append
`-Copt-level=1 -Zmir-opt-level=1 -Clto=off`. If debug assertions are unspecified,
append `-Cdebug-assertions=yes`. If overflow checks are unspecified, append their
original effective value (the original effective debug-assertions value).
Preserve explicit debug/overflow booleans, their ordering and all original flags.
UB checks consequently retain their effective default. Preserve panic strategy,
debuginfo, split-debuginfo, codegen units, incrementality, cfgs, lints and features.

Fail explicitly rather than overriding user optimization: reject eligible
invocations containing `-O`, any explicit opt-level (including zero), LTO,
LLVM-pipeline/profile instrumentation overrides, or any unstable `-Z` option.
The initial grammar accepts a documented ordinary Cargo argument/codegen subset;
unknown or ambiguous eligible arguments fail closed. Response files fail closed
for the enabled policy because they can hide both role and conflicting flags.
All long/short, joined/separate spellings and underscore aliases of codegen
options must be handled. Metadata probes and definite noneligible roles are
bypassed without injecting flags. Missing policy context is an explicit error.

This does **not** promise identical internal optimized MIR or native debug info.
`Session::emit_lifetime_markers` depends directly on codegen opt-level: O1 keeps
storage lifetime markers which O0 normally removes. Backend attributes, native
optimization and generated code also differ. The checking/analysis pipeline,
normal MIR optimization level, source cfg and runtime checks are preserved;
the retained lifetime metadata is a codegen difference after checking.

## Qualification fixtures and future decision

Before any timing, run small routing contracts and real histories with the
shared lock. Route contracts cover exact proc-macro role, probes and unrelated
host/guest/build-script roles, explicit booleans, malformed/duplicate options,
response files, flag aliases/conflicts, missing context and compiler identity.
Mocked launcher checks cover off/on/off workspace identity, shared std identity,
Cargo-only environment propagation, capability/combination rejection and default
compatibility. These are source-only until a coordinated execution window.

Real pinned-Cargo fixtures should include a proc-macro plus ordinary shared host
dependency and build scripts recording `OPT_LEVEL`/`DEBUG`; native expansion and
selected guest bytecode must match off/on. Exercise debug assertions, cfg, checked
overflow, generic/inline helpers, const values, drop behavior and source spans.
Compile uncalled type/borrow/constant-panic errors in the macro and an invalid
generated item, followed by restoration. Change both macro implementation and a
declared external input with the normal Cargo invalidation contract, and compare
current output after each edit. Keep command/role arguments and diagnostics.

No adoption or 0.5-second claim follows from fixture success. The full required
Nushell command, all original tests, cold costs, five fresh edits, wrong-result
controls, separate baseline duplicate, CPU/latency and prior-use/fresh-holdout
rules still apply. Macro dylib optimization may increase cold builds and may
save little when unoptimized dependency bodies dominate execution. Keep this
candidate separate from the already qualified Cargo-info-cache implementation.
