# Exact source-observable transport correction

The retained `mono-production-source-observables-01` attempt stopped at command
38, `off-unmapped-exported`. Cargo and MIR export succeeded; `println!` reached
the VM's unsupported `pthread_mutexattr_init` stdout-locking path. This is not a
source comparison result. The original failed attempt, its 37 completed controls,
and its exported artifact remain unchanged.

This unexecuted correction uses `std-source-observables-v2` and the explicit
transport `native-rows-exact-guest-bitmask-v1`. It preserves native raw output for
`file!`, proc-macro `Span::file`, `Span::local_file`, line and column, at both the
main and std-looking application source locations. It preserves all original
diagnostic, copy, invalid-source and four-phase controls and all compiler flags.

The native program still prints its actual observations. The exported entry
instead compares each actual string byte and coordinate to a generated table
derived from the matching independently checked native phase. It returns ten
comparison bits through the existing integer-return ABI. Success requires all
ten bits (1023); a hash is never used for semantic equality. Native `main` and
exported `entry` call the same observation functions, with stdout reachable only
from native `main`. The shared immutable fixture template binds this distinction
in both the producer and the archived validator.

Each exported phase retains its exact expectation JSON and generated Rust
source, the native command it came from, the actual compiler argv, the actual
RBC bytes/hash and the actual numeric stdout. The validator reconstructs the
table from the raw native rows, verifies the generated source exactly, and binds
the comparison to the existing launcher/compiler/std/artifact proofs. The table
and the main phase marker are restored using `SourceEdit`; final fixture bytes
must equal the original template.

Two extra real exported controls per mode deliberately change one expected
filename byte and one expected line coordinate. Each must return the precise
corresponding missing comparison bit. The existing restored phase then checks
the complete correct table again. Thus the fresh history has **61 commands**:
all original 57 plus four explicit negative executions. It does not omit a
control to preserve the previous command count.

Planned affected files are a small shared fixture/transport module,
`qualify_std_source_observables.py`, `std_source_observables.py`, their focused
tests, the mono screen/assessor boundary tests and this handoff documentation.
The screen and saved assessor already consume the shared typed validator; their
production selection logic should need no duplicate transport implementation.
Prepared tests will cover changed expected bytes/coordinates, a fabricated
all-bits result for a negative control, incomplete masks, changed generated
source, and rejection of the old policy. No changed tests have run yet.

Only qualification fixture/harness sources change. The actual compiler
`f9fb3e5f...`, interpreter tool `45aadeaf...` and prepared std keys `4634cc1a...`
and `d0be7498...` remain byte-identical and need no recompilation. The successful
strict36 receipt remains its historical source/provenance record; it is not
rewritten as execution of the new fixture. Root integration, focused tests and
a fresh `mono-production-source-observables-02` execution are required before
any mono performance screen. All work and tests remain unexecuted until their
canonical-lock admission is coordinated after the host-target retirement.
