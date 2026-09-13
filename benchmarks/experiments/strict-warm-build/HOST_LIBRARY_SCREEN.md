# Host-library O1 mechanism screen

This is a separate candidate in the existing strict 27-command screen. It
changes no production source based on a benchmark name, path, crate or edit.
The opt-in wrapper policy is generic: only unselected, linked ordinary native
Cargo lib/rlib units in an explicit public std-MIR route receive O1. All original
units, source checking and side effects remain required. Native proc-macro and
build-script executable arguments, target guest arguments, Cargo profiles,
build-script OPT_LEVEL/DEBUG, Cargo jobs and backend/linker job policies stay
unchanged. Effective debug, overflow and UB checks are preserved; MIR level
stays 1 and LTO is explicitly off for eligible units.

The public compiler, Cargo, exporter, wrapper, VM and prepared std are identical
across all arms. The sole added launcher argument is `--host-library-opt off`
for baseline and duplicate, and `--host-library-opt on` for the candidate.
Each arm has its own fresh Cargo workspace/cache. No worker, proc-macro,
custom-compiler/Cargo, borrow-check reuse, sparse-query retention or compiler
argument recording can combine with this screen. Recording occurs only in the
separate real qualification.

Before admission, the shared pure public validator must accept the actual tool
key under `host-library-public-build-v1`, scope `host-library-real-histories`.
Its nine commands include all Rust workspace tests, five launcher controls,
five publication controls, both actual capability probes and three actual
native/exported histories. It binds actual binary hashes and the compiled
sysroot, full build inputs and library closures, the unchanged prepared std,
and the exact qualification harness. Legacy macro or worker receipts cannot
be relabelled as host-library qualification.

Screen admission validates that PRIMARY's launcher, routing helpers, screen,
assessor and their source dependencies equal the qualified harness bytes.
Every file read during typed publication and runtime-harness validation is
recorded with a tagged hash of those same bytes. The final frozen inventory
must match those hashes before the first command. That inventory includes the
publication/capability proofs, all published fixture receipts and bytecode
envelopes, policy documents, source marker and unchanged project files.
Standard-library artifacts retain their existing identity checks. Compiler,
Cargo, tools, dependencies, configuration and library inputs receive the
existing full admission/final guards and two saved guards per command.

The timing and source-state loop is unchanged: three cold commands; deliberate
wrong-result edit; compiled recovery; five cumulative, first-seen valid edits;
compiled final restoration. Every arm runs all 14 original selected tests in
all nine states. The full launcher/Cargo/VM/test/receipt command is timed, and
waited-child CPU is recorded. Setup-only input audits remain outside that
clock as in the other candidates; no launcher work moves into setup. Matching
stdout, outcomes, bytecode and entry catalogs are required across all arms.
The saved assessor checks the exact command order and arguments, final
launcher policy, actual wrapper capability, complete timing and all 56 input
guard records, using retained proof bytes without invoking tools.

The existing workload has four Cargo jobs and two suite workers; tool builds
and qualification use the separately recorded two-job setup policy. The
screen requires the canonical campaign lock explicitly, with at least 8 GiB
free at admission and each command. No screen starts from the build driver.
After the actual immutable publication, the materializer writes a command
using its final tool key, both policy arms and the canonical lock. It requires
the exact integrated runtime harness and a separately prepared owned source
checkout before writing that handoff. Root reviews and admits it separately.

O1 can reduce time spent executing host libraries used by proc macros and
build scripts. It can also make cold or edited native-library compilation
slower, change cross-crate inlining/code size and expose existing undefined
behavior. These are ordinary compiler optimization effects; the histories
test observable defined behavior and preserve the configured checks. No speed
gain, sub-0.5-second result, adoption or holdout generalization is claimed by
this implementation or by a single future mechanism screen.

Five routing/admission/materializer tests and four saved-assessor tests are
prepared in `tests/test_host_library_screen.py` and
`tests/test_owned_host_library_screen.py`. Their inputs are synthetic and
their compiler/Cargo/VM boundaries are mocked. They have not been executed
for this source-only change.
