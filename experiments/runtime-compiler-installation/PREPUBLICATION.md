# Explicit validation before runtime publication

This successor adds an optional pre-publication validator to the
existing runtime installer. The original RUNTIME source and its fourteen-control
evidence remain unchanged. The synthetic qualification passed all three
complete modules: thirteen custom-compiler controls, twenty runtime controls
(including six new validator controls), and eighteen std-source controls. These
fifty-one controls passed in one unfiltered process with no skips against source
`a05f4e4f05858cd343261706f5eb579edb54c872`. The [retained evidence](../../results/runtime-prepublication-controls-01/README.md)
includes the original source checkpoint and pre-execution plan, raw results,
process associations and every source snapshot; all 170 archive members were
independently read back. There is no real installation or native compiler
execution in this checkpoint.

A specification may declare:

```json
{"prepublication_qualification": {"policy": "native-source-paths-v1"}}
```

The declaration is part of the admitted identity and therefore the final key.
It requires a callable `validate_before_publication(compiler, environment)` supplied
to `install_runtime_compiler`. Conversely, a validator without a declaration is
rejected before any input or destination work. Specifications without either
retain their existing identity, installation and lookup behavior.

The hook runs explicitly after the normal final-root loader/version/sysroot/
option probes, before the original source-input and pre-probe output-stamp
barrier, chmod, or `ready.json`. It receives the bound final-root RuntimeCompiler
and a separate environment copy. There is no temporary ready record and its
ordinary `revalidate` method cannot be used before publication. A task-specific
validator must use the already admitted files/stamps and recorded commands; the
installer repeats its original full input/output checks after the hook.

The validator returns only `{path, sha256}` identifying its completed, ordinary,
nlink=1 external receipt below the owned root and outside the installation. The
receipt must bind:

```json
{
  "schema_version": 1,
  "status": "passed",
  "policy": "native-source-paths-v1",
  "key": "<exact final runtime key>",
  "owner": "<owned root>",
  "sysroot": "<exact final sysroot>",
  "source_commit": "<actual admitted compiler source commit>"
}
```

Additional command/source/diagnostic evidence belongs in that receipt and the
separately frozen qualification controller. This general installer verifies the
receipt's identity/binding; a supplied success field is not independent proof
that an arbitrary validator checked the promised behavior. The validator's source,
inputs, policy and required commands remain part of actual workload admission.

The installer reads the receipt through a stable no-follow descriptor, under the
existing capacity guard, with a 32 MiB bound. It makes an exclusive fresh copy at
`qualification.json` and independently reads it back. The copied proof is readonly
and its exact hash/reference/seven-field file identity are recorded in readiness.
The callback cannot change nested compiler/admission dictionaries: their digest
must still equal the original key immediately afterward and before readiness.
The existing copied runtime stamp baseline is never replaced by a post-callback
snapshot. Callback errors, failed/mismatched receipts, changed inputs/output or
identity, and receipt copy corruption retain failure before any ready record.

Warm lookup checks the declared policy/reference/digest shape and the proof's
ordinary, nlink=1, readonly, exact no-follow file identity. It does not open or hash
the receipt contents and does not depend on the original external receipt. This
uses the same trusted immutable installation/inode/ctime contract as native
payloads. The source controls forbid proof reads on successful lookup and require
rejection of a same-size mutation with restored mtime.

The hook adds no source-path capability and does not set application qualification
true. In particular, `std_mir_source_paths.compiler_sources` remains unchanged.
A proposed E-first sequence is:

1. Qualify the already frozen E compiler's actual bootstrap/source-path behavior
   against its bound source-link targets and exact known source bytes. Retain raw
   uncalled E0080 diagnostics and a separate no-local-translation control proving
   the actual virtual `/rustc/<E commit>/library` identities. This does not pretend
   the original linked source root is an ordinary installed provider.
2. Review that actual receipt and create a separate specification with the
   explicitly qualified capability and this declared pre-publication policy.
   Metadata03's original candidate remains unchanged; no identity is augmented
   after installation.
3. Install once. The explicit validator compiles the existing native source probe
   at the final root and calls unchanged `validate_probe` against the ordinary
   installed library files. Raw JSON must contain the correct source bytes and
   both core/std expansion sources. Failure leaves no ready record. Native type,
   borrow, const, proc-macro, build-script and full application/std-MIR histories
   still require their separately prepared qualification.

Only this hook and its synthetic controls are implemented here. The E preflight
and final-root validator controllers/commands still need their own concrete source
checkpoint and admission before execution. No process or qualification is hidden
inside the ordinary `-Zhelp` subprocess callback.
