# Same-tool proc-macro mechanism screen

Status: source-only harness; no qualification or timing result.

The `host-proc-macro-opt` policy uses one newly built, public-pinned
exporter/wrapper/VM installation for all three arms. Baseline and duplicate pass
`--host-proc-macro-opt=off`; candidate passes `on`. Their actual tool keys and
all binary bytes must be identical. This avoids attributing a different VM,
compiler build profile, source checkout or linker output to the macro policy.
It does not require the new VM to equal a historically installed VM.

Use `screen.py --candidate-policy host-proc-macro-opt`, identical
`--baseline-tool-key`/`--candidate-tool-key`, and one `--std-mir-ready`. There is
no candidate std override: application macro codegen is deliberately absent
during std preparation. The existing prepared public std identity is shared by
all arms. The public-tool association and `host-proc-macro-opt-v1` capability are
required before source edits. Custom compiler/Cargo selections are rejected;
actual launcher receipts must report the selected macro mode, borrowck cache
off, no independent retention setting, and the exact shared std identity.
Other screen policies reject a receipt that silently enables macro optimization.

`HOST_PROC_MACRO_OPT.md` is the explicit profile-policy amendment and is frozen
with the harness before timing. The manifest's empty `profile_overrides` means
that application Cargo profiles are unchanged; `codegen_policy_amendment`
separately records the intended native macro compiler transformation. No claim
of identical native machine code or internal optimized MIR is made.

The original 27 complete commands, all 14 original Nushell type-relation tests,
five fresh cumulative edits, wrong-result control, recovery, final restoration,
baseline duplicate, bytecode/catalog equality and CPU/wall clock remain intact.
Each arm gets its own initially empty project cache. Timing covers launcher,
Cargo, every required host/guest unit, macro execution, VM preparation, test
execution and receipt I/O. Cold commands are retained alongside edited costs.
The unchanged 0.500-second gate is not relaxed; this first screen is not the
three-history final latency or holdout qualification.

## Build and qualification handoff

`../host-proc-macro/prepare_plan.py` produces a source-only JSON handoff. It
records exact argv/environment for a new release tool build, all workspace Rust
tests, focused mocked launcher/screen contracts, and the three real compiler
histories. All commands must be executed under the existing canonical workload
lock, after the compiler integration/screen and queued Cargo-only setup/screen.
Do not acquire the lock recursively around `screen.py`; the screen owns its own
bounded admission. There are no workload commands in the plan generator.

The initial plan builds in the isolated macro worktree and proposes a later
screen in the primary worktree, using its already prepared public std. Before
that screen, integrate the reviewed harness, copy only the newly qualified
immutable tool installation with its exact source/build/correctness provenance,
and prepare an owned independent source clone at the recorded destination.
Those are explicit pending setup actions, not completed readiness. No existing
tool installation, project target, source snapshot or result may be overwritten.

Use the recorded DEBUG=1 release build profile for the entire new toolset and
the same output binaries in every arm. Record the exact public rustc/Cargo
identities, source inventory, command PIDs/receipts, test counts, capability
output, all three binary hashes and compiler dynamic-library inputs before
publication. The initial fresh target reserves 4 GiB above the 8 GiB free-space
floor; the later project screen reserves 8 GiB above that floor. These are
admission budgets to verify against current space, not measured footprints.
Tests must pass without skipping the real Cargo history or VM execution.

## Additional saved-evidence assessor requirements

Extend the existing assessor independently; do not create a second assessor.
For this policy it should reconstruct and require:

- One identical public tool key and complete binary manifest in all arms,
  no `compiler.json` association, and the bound v1 capability from frozen
  capability bytes. Verify the copied source/build/correctness provenance and
  public compiler association for this new installation.
- One identical prepared std record in every arm, no custom compiler/Cargo
  fields, exact off/on/off policy map, and the frozen explicit amendment.
  Distinguish unchanged Cargo profiles from the recorded macro codegen change.
- Exact 27 command vectors and launcher receipts, including the macro mode,
  borrowck off, no unrelated retention/custom compiler/custom Cargo, shared std
  receipt, and distinct actual workspaces. A missing policy receipt is a failure.
- Existing source freshness/restoration, original test identities and outcomes,
  whole-command wall/CPU, bytecode/catalog parity, exact archives and artifact
  hashes. Do not sum overlapping stages, subtract execution, or infer that every
  proc-macro in another project is eligible. Preserve screening/final/holdout
  limitations and record increased cold cost if observed.
