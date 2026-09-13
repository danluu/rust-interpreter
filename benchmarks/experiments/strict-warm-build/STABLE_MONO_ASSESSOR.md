# Saved per-MonoItem screen assessment

This extension is prepared source only. Its focused tests have not been run,
and no compiler, std preparation, qualification or Nushell screen has been
executed by this change.

`assess_owned_screen.py` accepts the separately typed `stable-mono-cgu` policy.
It preserves the existing module, Cargo and host proc-macro policies. All 27
commands retain the original 14-test workflow, edits and controls, four Cargo
jobs, two suite workers, profiles, flags, limits and complete-command timing.
Every MonoItem command must explicitly name its compiler, unchanged module-off
policy, MonoItem off/on/off policy, `source-paths-v2` selection and the correct
prepared std key. Effective launcher settings must agree, including the actual
wrapper, owned compiler lookup and absence of qualification instrumentation.

`scripts/owned_mono_screen.py` validates saved bytes through a callback. It never
invokes a compiler, Cargo, a live installation loader or std preparation. The
two std namespaces must share the same compiler, source files, Cargo identity,
configuration and preparation recipe. The validator reconciles each immutable
ready identity, owner marker, complete source/metadata inventories and read-only
stamps, artifact proofs, setup command/environment and completed child receipts.
It verifies native-before-build and prepared-after-build unmapped E0080 probes,
including the original compiler-produced snippets against exact hashed source
bytes and byte/character coordinates. Setup readiness still has
`full_presentation_qualified=false`; it is not silently relabeled qualification.
Live loading and every operational cache-validity check remain unchanged.

Admission reuses `stable_mono_qualification.validate_qualification` with the
saved-byte callback. The entire 36-command history, linked raw/compiler argument
records, source snapshots, diagnostics and bytecode evidence are retained. The
same compiler/tool/std keys must appear in that checked result and the screen.
The actual native-host and selected-guest arguments in both modes remain bound
to the recorder's NUL-delimited bytes.

An independent source-observable prerequisite is mandatory. Its agreed consumer
API is `std_source_observables.validate_source_observables(path, owner,
compiler_key, tool_key, stds, *, compiler_sysroot, read_bytes)`, returning the
same `{path, sha256, result, evidence_files}` shape as the strict integration
validator. The screen must freeze that complete returned record as
`plan.source_observables` and freeze every linked evidence path. Until the typed
validator and receipt are available, MonoItem assessment fails closed. The
36-command integration is never substituted for that prerequisite.

The archive retains exact UTF-8 members as before and uses base64 for binary
qualification members that cannot be decoded as UTF-8. SHA256 and byte length
are checked on decoded bytes. Frozen-input validation uses the same exact bytes;
base64 is only an archival encoding. The previous UTF-8-only archives remain
readable. Compiler/tool binaries and project caches are still omitted, while
linked qualification bytecode is preserved. All setup and qualification paths
must be in the screen's frozen input inventory; additional standard source
snippets are accepted only through the compiler/std file hashes.

Future validation handoff:

1. Integrate the independent typed source-observable producer/validator and its
   screen admission/frozen-path binding. No passing fallback is provided here.
2. Under the canonical workload lock, run the prepared
   `tests/test_owned_mono_screen_assessment.py` together with the existing
   `tests/test_owned_screen_assessment.py` and MonoItem screen contracts. Tests
   use saved synthetic bytes and must not start compiler/Cargo/VM children.
3. After the new compiler and all real prerequisites pass, assess the saved
   strict 27-command screen, verify every archive member independently and
   preserve any failure under a new attempt identity.

Input-identity audits and archive verification are benchmark harness work. They
do not enable the compiler optimization and remain outside measured commands.
Production launcher, Cargo, compiler, VM and operational validation work stays
inside the full-command timer. This assessor makes no final latency, adoption or
holdout-generalization claim.
