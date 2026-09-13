# Compose memory operands with cached compiler identity

The completed memory-only comparison passes462 expected commands. Token
improves6.60% wall/5.93% CPU versus the wide control and passes; folded passes.
Pgrust misses the CPU guard because its1.02027 ratio to the fixed anchor plus
3.361% A/A exceeds1.05. Keep that failed adoption decision. The earlier lookup
candidate improved pgrust but failed its private/Nushell noise guards. Neither
completed trial is rerun or relabeled, and historical gains are not multiplied.

This distinct composition uses the qualified memory VM and enables the
existing cached identity path on the candidate launcher. It targets both
compute execution and frontend startup. The control uses the wide VM with
fresh identity lookup. Both retain the exact same exporter and wrapper,
strict compiler checking, automatic compiler-proven function reuse, guest
options and prepared test isolation. No new interpreter/JIT implementation,
lazy checking, compiler cache format or runtime fallback is introduced.

Immutable tools:

- Wide control: f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8.
- Memory candidate: f0af2e3e4c1093fd0e7bb5a5a53dd8e72b305d7e1536ea9c4b999ba2acaa965a.
- Fixed compute-suite anchor: fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e.

Reuse the428-per-profile memory runtime build and its7/9/203/3 real execution,
suite, cache and profile qualifications. No Rust input or binary changes.
Run138 Python checks (123 existing plus15 composition checks), then20 actual
Cargo/identity commands using the memory tool in fresh and cached modes.
Require unchanged original assertions, valid/wrong/restored edits, identical
artifacts and standard-MIR identity, and uncalled E0308/E0499 before execution.
This verifies the combined route rather than assuming independent proofs compose.

The identity cache binds compiler installation, proxy, libraries, settings and
environment stamps. It skips the two identity-discovery invocations only;
strict Cargo/rustc checks and every existing artifact validation still run.
Unknown or changed installations preserve the existing fallback/invalidation
behavior. A measured candidate that does not report a validated hit stops
the comparison instead of being silently treated as the intended optimization.

Freeze five real changed-source cases and all evidence before timing. Nushell
type-relations runs first because its existing six-cache estimate requires
about47.03GiB free. Private rg-aot follows, then the twelve-test token primary,
folded and pgrust. All five are mandatory regardless of individual performance
gates. Public summaries for the private project remain aggregate-only.
The complete schedules and gates are in [WORKFLOW.md](WORKFLOW.md).
