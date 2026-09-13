# Custom compiler setup and qualification prefix

The optimized per-MonoItem compiler installed successfully. Its updated interpreter
tools and matched workspace passed: 505 Rust tests passed, with two pre-existing
ignored tests. Both std-v2 preparations passed all seven commands each. The strict
integration qualification passed all 36 commands, including diagnostics, actual
compiler arguments, edited execution and source restoration.

The separate source-observable qualification **failed at command 38 of 57**.
The exporter produced bytecode, but running the fixture's `println!` reached the
unsupported foreign call `pthread_mutexattr_init`. Earlier raw source/snippet,
second-prefix and invalid-source controls remain recorded; they do not make this
incomplete qualification pass. No per-MonoItem Nushell performance screen ran.
The next attempt needs a qualified fixture transport that compares each observable
byte and coordinate against independently retained native values.

Actual installed compiler key:
`f9fb3e5f59b8567fffd32c936a9864d0baee77038574236710fbcec75a57d33f`.
Actual updated tool key:
`45aadeafe86e1268c37d3c2d4344c99d3e2a8f142b1d218d484292fd0990a463`.
These are produced artifact identities, not source revisions.

The archive also preserves the first import preflight failure (queue time was
mistaken for admission time), the successful corrected import, the original tool
build, the first workspace helper's path-type failure before any test ran, and
all five passing corrected-helper controls. Failures have not been relabeled.
Fresh owned Nushell source preparation is included; it ran no benchmark.

`evidence.tar.xz` contains 2,094 members, 56,906,586 uncompressed bytes and
5,721,088 compressed bytes. SHA-256:
`edbdcc121eca6d9b8f673ecbaf9607c501d7a587fecbe45b07798941acd8f0b1`.
Every member and original selected file was rehashed after packaging. Exact
sources, plans, child/outer receipts, raw outputs, source snippets, compiler argv
and six strict-control bytecodes are retained. The bytecode from the failed
observable execution is retained too, with its actual launch hash. Compiler/native
executables, copied sysroots and Cargo target caches remain outside the archive;
the original owned data is retained. This archive is evidence preservation only,
with no new compilation or performance claim.
