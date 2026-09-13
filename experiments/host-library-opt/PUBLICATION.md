# Host-library public build and qualification

This is an explicit `host-library-public-build-v1` extension of the existing
public-tool publisher. It uses the public pinned compiler and the already
prepared public std MIR. It does not prepare std, alter application sources,
change Cargo profiles, or run a performance screen.

The plan fixes nine commands, in order:

1. Public rustc `-vV`.
2. Public Cargo `-vV`.
3. `cargo test --release --locked --offline --jobs 2 --workspace` in a fresh target.
4. Release build of all three interpreter tools with the same flags and target.
5. Five host-library launcher contracts.
6. Five host-library publication contracts.
7. The actual exporter's capability probe.
8. The actual wrapper's host-library capability and compiled-sysroot probe.
9. Three real host-library histories with those exact binaries and prepared std.

The Rust workspace includes the five new Rust routing controls, alongside the
unchanged existing macro and worker controls. The real histories reuse the
existing macro/native fixture machinery without changing the macro tests. They
cover ordinary O1 native libraries, shared proc-macro/build-script dependencies,
edits/restoration, unused-body type/borrow/const/lint errors, raw diagnostic
structure, source positions, generics, drop effects, debug/overflow/UB-check
defaults, original build-script OPT_LEVEL/DEBUG, and actual forwarded arguments.
Valid edited/exported artifacts execute; original/restored bytecode is compared.
No skipped Python history qualifies. The complete Rust output records any
deliberately ignored tests separately; a failed Rust suite never qualifies.

The exact compiled binary hashes are captured after the release build and
checked again after all histories. The correctness receipt binds those hashes,
all workspace sources, the test/launcher/publisher harness, public compiler and
Cargo identities and library closures, effective Cargo configuration and
dependencies, capability output, and the existing std's complete metadata
artifacts. The pure validator accepts this policy only when explicitly selected.
It requires the nine commands, exact six-variable real-history tool/std/capture
environment, both matching capability probes, and the required harness files.

The correctness receipt has no final tool key. The existing publisher computes
that key from the actual binaries and complete source/build/correctness payloads,
then installs those proved bytes in both owned roots. This avoids a final-key
self-reference. Its published capability adds the actual wrapper hash, exact
host-library capability, and compiled sysroot. Old macro and worker publication
policies retain their existing command sets and qualification scopes.

All native history input snapshots, raw JSON receipts, NUL-separated final
compiler argument records and exact bytecode are retained. Bytecode uses a
small JSON base64 envelope with its raw size and SHA-256 because the shared
provenance reader already requires textual payloads. Cargo targets and native
executables remain in the owned raw history directory; publication does not
copy their caches. Raw historical command records remain review evidence; the
typed qualification relies on the successful exact frozen tests, as the existing
macro publisher does.

`prepare_plan.py` is a separate source-metadata freeze, under the canonical lock.
It requires committed sources, existing public std and new receipt/plan/build
destinations. It runs no rustc/Cargo/probe/test. The shared build later acquires
the same canonical lock, retains each owned process receipt, uses two jobs,
requires at least 12 GiB before admission and at least 8 GiB for each child,
and preserves any failed attempt. Root must assess projected disk space before
admitting a real build. No compiler or std source is changed by this handoff.

The checked-in `build-plan-draft.json` is deliberately **unfrozen and not
executable**. After root review and lock admission, prepare the real plan using:

```sh
python3 experiments/host-library-opt/prepare_plan.py \
  --screen-root /Users/danluu/dev/rust-interp-semantic-reuse-20260913 \
  --std-mir-ready /Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/std-mir/bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef/ready.json \
  --run-id host-library-build-01 --lock-wait-seconds 600 \
  --output experiments/host-library-opt/planned-build-01.json
```

Review the resulting immutable plan and its source-metadata receipt before
admitting the actual build:

```sh
python3 experiments/host-library-opt/build.py \
  --plan experiments/host-library-opt/planned-build-01.json
```

Before that build, the five shared archive tests, five shared publisher tests,
two existing worker-publication tests and five new library-publication tests
are the focused compatibility selection. These tests are prepared, not run.
The full build adds five launcher checks and three real histories; counts and
every result must come from actual retained output.

This handoff makes no performance claim. A later host-library screen still
needs an explicit off/on/off policy, same newly qualified tool key, source and
std guards, fresh isolated caches, complete build-to-validated-artifact timing,
and saved assessment. `materialize_screen_command` rejects this new policy
until that separate screen implementation and review are complete. Source
integration into PRIMARY and any timing admission remain root-owned steps.
