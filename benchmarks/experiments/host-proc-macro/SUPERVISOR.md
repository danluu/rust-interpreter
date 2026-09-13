# Publication support handoff

The pure validator and its five boundary tests are in commits `f8c46ef` and
`7d6dc95`; root ran them together with the saved assessor's controls under the
canonical lock (16 tests passed). This is correctness evidence for the Python
provenance checks, not qualification of the macro compiler policy.
Root subsequently ran the updated validator, publication and assessor controls
(21 tests, zero skips) before plan03, then the five updated publication controls
before plan04. The five updated logical-loader validator tests passed, followed
by all eight retained rustc inspector records replayed under the canonical lock
(supervisor93504, replay child94349, zero new inspector/compiler children).
These are preflight correctness controls for plan05, not macro qualification.

`scripts/public_tool_publication.py` supplies the build supervisor primitives:

- `build_admission(plan)` admits a fresh owned build directory under the exact
  canonical lock and bounded wait, checks space, and records the supervisor.
- `run_plan_commands(plan, inherited=..., before_command=..., after_command=...)`
  executes the frozen command vectors. `retained_command` delegates to the
  existing drain/wait guarantee before publishing stdout/stderr. Capture hooks
  collect identities and supporting records; they do not replace commands.
- `capture_library_closure` uses the existing resolver with an optional metadata
  inspector callback, retaining exact otool command/output receipts. Default
  Cargo importer behavior is unchanged. `file_identity` binds logical/resolved
  paths, bytes, hashes and full stat/symlink state.
- `compose_qualified_tools` assembles the acyclic correctness receipt and
  composition from retained payloads. Its pre-history binary hash map must
  equal the actual binaries after histories. The caller retains source/harness
  bytes, compiler/dependency inventories, metadata inspector records, command
  receipts/logs and real fixture records in the contract's payload layout.
- `immutable_publish` refuses existing destinations and ambiguous copy-time
  executable-relative library semantics. It copies the three binaries and
  provenance, invokes the shared pure validator using virtual readiness bytes,
  performs the live hash guard, and writes physical readiness last. Failed
  destinations remain for review and must not be retried as fresh successes.
- `materialize_screen_command` validates the completed publication and matching
  integrated harness, shared std and source owner before writing exact argv.
  It never launches a screen. The screen performs full source/Git preflight.

`build.py --plan <fresh-reviewed-plan.json>` is the automatic runner. It takes
the canonical lock itself, freezes source/harness bytes, captures the public
compiler/sysroot and full offline Cargo metadata/dependency checksums and file
inventories, records effective configuration, executes the eight qualification
commands, retains fixture inputs/commands, resolves all five executable library
closures, composes provenance, and publishes to both recorded owners. It binds
rustdoc as a compiler input and selects the public rustdoc explicitly; Cargo's
verbose setup logs retain the actual compiler argv. This changes setup logging,
not benchmark profiles. Configured compiler/wrapper/Rustflags/environment-table
overrides fail before qualification; configuration files and absent search
paths become guarded inputs. Registry credentials and arbitrary inherited
environment values are not copied into published provenance.
Registry archives are hashed against `Cargo.lock`, read without extraction, and
compared member-for-member with the local source tree. Cargo-generated
`.cargo-ok` and optional reconciled `.cargo-checksum.json` files are retained as
inputs; any other extra source file, missing member or changed byte fails.

The runner writes `published.json` and `result.json` with the actual tool key and
a concrete materialization command. After the exact screen harness and owned
source are prepared, run `build.py --plan <same-plan> --materialize
<build-work>/published.json` to write the screen argv under a separate bounded
lock admission. It never executes a benchmark. Any failure keeps its work and
partial publication for review. Plan03 stopped during dependency inventory;
plan04 passed that inventory and stopped at pure loader-path validation. Both
retained three successful metadata/Git commands; plan04 also retained eight
successful otool inspections. Neither started any of the eight qualification
commands. No Rust build, test, publication or benchmark has run through this
support. Five dummy-byte publication/runner boundary tests execute no Rust/Cargo
command. `replay_closure.py` uses saved inspection output without starting an
inspector, and checks current bytes against the prior compiler inventory.

`screen.py` now calls the same pure validator at macro admission. It freezes all
recursive installation provenance and the initial guard. Saved guard references
are explicit:

- `plan.public_input_guards` has policy, admission `{path,sha256}`, directory,
  `final_path` and `boundaries_per_command: 2`.
- `row.public_input_guards.before/after` point to globally ordered
  `000-before.json` / `000-after.json` through `026-before.json` /
  `026-after.json`, each with its exact SHA-256.
- `summary.final_public_input_guard` references `final.json` and its hash.

Admission and final guards rehash; command boundaries verify stat/resolution
identity. All 56 records are required. Guard verification runs outside the
timed command, alongside existing frozen-input checks, and cannot substitute
for launcher/Cargo/compiler/VM work or any of the 14 tests.

`planned-build-05.json` records the compatible runner and a 600-second canonical
admission bound. It remains unexecuted. Plans01 and02 are retained unchanged as
superseded, unexecuted plans. Plans03/04 retain both inventory/loader failures
and03's initial missing `.work` parent failure, with exact metadata commands
and receipts. Plan05 uses a fresh destination and copies prior records and the
retained closure replay into publication provenance. Loader search strings keep
their exact logical spelling, including `..`; independently resolved paths and
all byte/stat/symlink guards remain mandatory. Old harness hashes fail preflight.
Production crates remain `01e36c0`; the source input key remains `f77229…`.
No final tool key or screen argv is known yet.
