# Publication support handoff

The pure validator and its five boundary tests are in commits `f8c46ef` and
`7d6dc95`; root ran them together with the saved assessor's controls under the
canonical lock (16 tests passed). This is correctness evidence for the Python
provenance checks, not qualification of the macro compiler policy.

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

These are support functions, not an automatic eight-command build runner. A
reviewed supervisor must populate the specified inventories and command/fixture
payloads and use them in the order above. No build, publication or benchmark has
run through this support. Three new dummy-byte publication boundary tests are
prepared but unrun; they execute no Rust/Cargo command.

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

The support changes update harness bytes recorded by `prepare_plan.py`. Thus
retained `planned-build-02.json` is also not directly executable after this
checkpoint: its source input key remains correct, but its old harness hashes
must fail preflight. Keep it and plan01 unchanged. Once support review is
complete, generate a new plan at a fresh output path and record the prior plans
as superseded before any workload. Production crates remain `01e36c0`; the
source input key remains `f77229…`. No final tool key or screen argv is known yet.
