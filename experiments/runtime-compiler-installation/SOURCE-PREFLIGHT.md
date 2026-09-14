# Existing-runtime source preflight

The initial source checkpoint prepared two ordinary compiler invocations and
the corresponding final-installation hook. Subsequent execution passed all four
focused source-expectation controls and the twelve-child existing-runtime
preflight, including both compiler probes and complete before/after guards.
The independently checked receipt is
`8bd341a23550e0d77c0bf7f6472811bb1586cad1af9a214a7be1d5684a7af4dc`;
[retained execution evidence](../../results/runtime-source-qualification-01/README.md)
records the exact scope. No runtime has been installed and the accepted
metadata03 candidate is unchanged. Final-installation callback qualification
remains outstanding; the predecessor policy's 51-control result does not
substitute for that execution.

`source-preflight-plan-01.json` binds accepted metadata03, its exact complete
runtime/source/support component snapshots, the qualified source-guard inputs,
and the actual recorded Git/rustc executors. `preflight.py` reuses the existing
canonical lock and `owned_stage.run`. Its allowlist is five source Git commands
before and after the two compiler probes: twelve children total. It invokes no
bootstrap, Cargo, exporter, executable fixture, archive reader, or installer.
The existing source guard still verifies the full source revision/configuration
and runtime64 inventory; all three admitted components are separately compared
with their exact saved stamps and fully hashed before and after the probes.
The standard-source provider permissions, membership and source-link mapping
remain unchanged. Every retained input and source span payload is read back.

Both compiler commands use the existing native std-source probe verbatim:

```rust
const UNCALLED: u32 = panic!("std source lookup probe");
```

They run from the same owned probe directory with the explicit original E
sysroot, edition2024, lib crate type, metadata emission and raw JSON diagnostics.
The second adds only `-Ztranslate-remapped-path-to-local-path=no` and a distinct
output filename. Both must finish normally with exit1/E0080 and empty stdout.
No expected error is substituted for a successful or crashed compiler.

The first control accepts only the explicitly admitted E library source-link
spelling or its exact checkout target, and requires actual snippets equal to
the unchanged, inventoried source bytes. The second requires the exact
`/rustc/<E commit>/library` names. An empty snippet is allowed only in that
identity-only second control; an included snippet must still match. Both must
expose `core/src/panic.rs` and `std/src/macros.rs`. Raw diagnostic JSON is never
rewritten, normalized, or filled from the source. Wrong compiler prefixes,
unrecognized paths, missing expansions and changed bytes fail qualification.

The outer receipt is successful only after all current source/runtime/provider
guards pass again. It binds the entire candidate file-map digest, compiler
version/rustc bytes, source digest, two raw compiler receipts, ten Git receipts,
exact executors and timestamps. The inner two-probe result alone does not meet
the final hook's `full_current_guard_passed` requirement.

After the actual E result is reviewed, a separate specification can bind that
receipt as `provenance.source_preflight_sha256`, add the existing exact
`std_mir_source_paths.source_capability(E_commit)` declaration, and declare
`prepublication_qualification.policy = native-runtime-installed-source-v1`.
This must also retain the already qualified bootstrap configuration/remap and
pinned Cargo-policy provenance; the two compiler probes do not independently
qualify Cargo execution, rustc-dev source installation, or every diagnostic.
The module does not generate or augment that specification automatically.

`source_qualification.final_validator` is the explicit installer callback for
that separately keyed specification. It binds the exact final key, owner,
sysroot, entire file inventory and reviewed E receipt, then runs the same two
commands at R. The first also calls unchanged `compiler_sources` and
`validate_probe` with ordinary installed files. It returns a bound receipt to
the generic pre-publication hook; it creates no temporary readiness and performs
no warm lookup. The installer retains and verifies the receipt and repeats its
original input/output/identity barriers before publishing readiness.

The plan keeps the canonical600-second wait and an 8GiB running floor. It makes
no compiler/runtime copies; source/proof retention is bounded by the frozen input
sizes, and each source/proof read has a 32MiB limit and per-MiB capacity checks.
The existing owned child supervisor retains its standard capacity protections.
Any failed attempt keeps its outputs and receives no automatic retry. Final R
installation, application/native-loader/strip checks and std-MIR preparation
remain separate later workloads.
