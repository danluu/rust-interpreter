# Oxc plugin-normalization development case

This adds an opt-in Oxc workflow at
`4d5c812d6b16c23fa71d106cf87f7f20ddee69b1`. It is separate from the executable
corpus and the frozen holdouts. Acquisition and the six-state native test
history passed. Debug-stripping tool warnings remain unresolved, so clean
native performance is not qualified. No interpreter/JIT timing result exists.
The original Nushell acceptance target is unchanged.

The workflow loader now accepts `--project oxc --case-file
experiments/oxc-plugin-normalization/case.json`. The project has no default
case. `--native-toolchain 1.98.1` selects native Cargo tests and the independent
check control; interpreter/JIT compiler selection is unchanged. Explicit native
setup first rejects conflicting inherited or Cargo-configured compiler/wrapper
routes, then resolves installed rustc and Cargo through `rustup which` and
records their bytes, file identities and verbose versions. It refuses a missing
toolchain before preparing interpreter tools. Actual native/check commands use
that absolute Cargo binary and explicit `RUSTC`; empty wrappers override Cargo
defaults only after the configuration audit proves no meaningful wrapper policy
is being erased. Separate receipts retain every setup and final identity child;
the final probes revalidate binaries, routing and configuration after the history,
outside measurements. No requested toolchain is installed implicitly. Omitting
`--native-toolchain` retains the existing nightly commands and environment behavior.

The selected production file, three cumulative refactors, three unchanged
tests and wrong-prefix control are the reviewed source proposal. Only the
workload description changed when copying `case-proposal.json` to `case.json`.
`proposal-source-proof.json` retains the original source derivation, including
its historical unexecuted status and original case hash. The exact source
review remains [here](../../results/oxc-target-source-review-01/README.md).

## Resource plan and staged setup

`setup-plan-01.json` contains the original resource and sequencing plan.
The acquisition controllers and their retained results are described
[here](../../results/oxc-native-acquisition-01/README.md). The first native
compatibility stage is frozen in `native-compatibility-plan-01.json` and
`native_compatibility.py`; [its test outcomes and tooling limitation are
retained](../../results/oxc-native-compatibility-01/README.md). The parent
coordinates admission with other current-task jobs.

All workload stages use the existing canonical lock at
`/Users/danluu/dev/rust-interp/.work/benchmark.lock`, with a 600-second bounded
wait. They reuse the established owned-child supervisor, including exact
process-group identity checks before its 9 GiB capacity stop, and preserve
the 8 GiB running floor. Only task-owned child processes are controllable.
The guard samples capacity; it is not a reservation against other sessions.
There is no automatic cleanup or retry after a failed admission or command.

Acquisition starts only with at least 16 GiB free and has a 6 GiB allocation
budget across its fresh toolchain, source and Cargo download directories,
plus 64 MiB for receipts. These are conservative limits, not measured Oxc
sizes. The exact upstream default-profile Rust 1.98.1 toolchain is installed
under a fresh task-owned `RUSTUP_HOME`; Cargo uses a fresh task-owned
`CARGO_HOME`. This avoids changing shared toolchain or registry state.
The checked-in Oxc `rust-toolchain.toml` and all profiles/configuration remain
unchanged. The retained lockfile declares 436 packages: 370 registry entries,
66 local entries and no Git dependency source. This is not a resolved unit
graph or a build-memory estimate.

Acquisition first performs a shallow checkout of the exact commit, confirms
all 43 retained public source hashes, records the full tracked source/symlink
inventory and verifies a clean tree. It then installs the upstream toolchain,
records the distribution checksums and complete installed identity, and uses
locked Cargo fetch/metadata for the native host. Dependency inputs, registry
checksums, build scripts/proc macros, compiler executables, SDK and loader
closure must be inventoried before native compilation. A missing dependency
or changed lockfile is a setup failure; it cannot be repaired in a timed arm.

The first native compatibility stage has a fresh 24 GiB entry requirement,
jobs 2, one target directory, a 12 GiB target budget, and 256 MiB evidence
budget. These limits can be increased before a new reviewed launch if the
acquired graph requires it. No measured result exists that would justify a
smaller budget yet. Libtest uses its upstream default scheduling. No
`CARGO_PROFILE_*`, application `RUSTFLAGS`, feature, manifest or test changes
are permitted. The complete library-test crate is compiled each time needed.

Native compatibility must retain, in order: exact test discovery; the
original three-test batch; the wrong prefix with each test's genuine assertion
failure; all three valid cumulative edits with all three tests passing; and
byte-exact restoration followed by all three tests passing. A compiler error,
missing/ignored test, timeout or unsupported operation fails compatibility.
The native executable and Cargo artifact evidence are bound to each source
state. Cold setup and compatibility controls are reported separately from
future warm-edit observations.

Only after native compatibility will an independently admitted exporter,
interpreter and JIT compatibility stage be prepared. It must record its
actual compiler separately from Rust 1.98.1 and retain all original tests and
negative/restoration controls. No compiler-matched speedup may be claimed
from different compiler versions. The eventual three-cycle development
measurement remains subject to the original proposal's whole-command timing
and source-change requirements; no 0.5-second Oxc claim is implied.

## Focused Python controls

The final control command is in `controls-plan-04.json`; the earlier preparation
plans and freezes remain retained. All 30 controls passed; the final run has no
resource warnings. [Both completed runs and source evidence are retained](../../results/oxc-workflow-controls-04/README.md).
The controls exercise
native argument routing and installed-tool identity, opt-in project/pin
validation, rejection of inherited/configured compiler overrides, preservation
of version/loader identity inputs, post-history binary mutation, unchanged
legacy/default behavior, and the saved build-workflow
verifier. Native-suite execution is mocked; no Cargo, rustc, tool acquisition,
Oxc test or benchmark is part of these controls. The first passing run exposed
an unclosed lock on an expected error; a general `ExitStack` lifetime fix and
an explicit lock-release check passed in the final run.
