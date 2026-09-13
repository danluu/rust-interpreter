# Explicit compiler frontend workers

This is a source-only experiment. Its Rust routing tests, mocked launcher
tests, and actual compiler/VM qualification driver have **not run**. No tools,
standard-library metadata, compiler packages, or existing benchmark workspaces
were rebuilt or changed while preparing it. No speedup is predicted or claimed.

The launcher accepts `--frontend-workers=1` or `--frontend-workers=2`.
Omission preserves the existing path, whose pinned compiler frontend default
is one, including compatibility with old immutable tools. An explicit count
requires the new capability and creates its own Cargo/incremental namespace;
explicit one is isolated from both omission and explicit two.

The light wrapper appends exactly `-Zthreads=1` or `-Zthreads=2` for every Cargo
compiler invocation, including host libraries, build scripts, proc macros,
guest dependencies, the selected export and metadata probes. The exporter
receives the original wrapper invocation and applies the shared router once.
Native units keep the light route. Standard-library preparation happens before
the worker environment is introduced and retains its existing policy.

Cargo's `--jobs`, compiler backend/linker worker flags, profiles, codegen-unit
counts, dependency MIR retention, selected-entry checking and VM behavior are
unchanged. User response files, explicit frontend flags, and rustc's all-role
`--jobs`/`-j` options are rejected when this policy is selected. The latter
would also select frontend concurrency, unlike `--jobs-backend` and
`--jobs-linker`, which are preserved. Rustflags from Cargo configuration are
checked by the wrapper after Cargo resolves them; obvious environment conflicts
are rejected before tool/std preparation. No Cargo configuration is rewritten.

Custom compiler/Cargo selectors, stable-CGU policies, proc-macro optimization or
execution policies, and borrow-check cache callbacks cannot be combined with
this initial experiment. Function-cache `auto` remains supported: ordinary
analysis completes before the export callback opens its cache and drains its
serial work queue. This does not establish deterministic output under the new
count; the prepared real qualification explicitly checks that.

## Pinned implementation contract

The source baseline for this worker setting is stock
`cea272fa356e94bd2ee2cadf376630aa0683867a` (nightly-2026-09-08).
The owned stable-CGU compiler and its package are not inputs to this experiment.

| Pinned source | Consequence |
| --- | --- |
| `rustc_session/src/options.rs:2907` | `-Zthreads` is the compatibility frontend-count spelling. |
| `rustc_session/src/config.rs:1738` | `-Zthreads=2` changes `Jobs.frontend` only. |
| `rustc_session/src/config.rs:1760` | Backend and linker defaults are calculated separately. |
| `rustc_interface/src/interface.rs:382` | Dynamic synchronization follows the frontend setting. |
| `rustc_interface/src/util.rs:209` | The worker-local frontend pool uses the requested count and a jobserver proxy. |
| `rustc_data_structures/src/jobserver.rs:87` | The proxy accounts for the process's implicit Cargo token and borrows additional tokens. Two requested workers do not promise two active workers. |
| `rustc_driver_impl/src/lib.rs:294` | Resolution/expansion precedes ordinary analysis. This setting does not change the SameThread proc-macro bridge strategy. |
| `rustc_expand/src/proc_macro.rs:16` | Macro bridge thread selection depends on the separate proc-macro execution strategy. |
| `rustc_driver_impl/src/lib.rs:316` | The analysis query completes before the single mutable `after_analysis` callback. |
| `crates/mir-export/src/main.rs:258` | That callback invokes ordinary strict export. |
| `crates/mir-export/src/lower.rs:166` and `:315` | The function cache and pending export queue belong to this serial export invocation; there is no new parallel cache callback. |

Worker settings are untracked by rustc, so namespace separation is mandatory.
The change adds no analysis bypass, altered query identity, or unchecked cache
result. HIR prefetch and macro expansion contain substantial serial work;
parallel helpers in later checks do not establish a whole-build improvement.

## Tool capability and receipts

The package build script records its compiler's exact commit. The exporter
advertises the pinned policy, supported counts and flag, while the light wrapper
has its own capability probe. Tool publication runs both probes and binds the
matching wrapper capability to the wrapper SHA256 in `capabilities.json`.
An explicit worker selection requires the expected stock commit and matching
exporter/wrapper hashes. An older wrapper paired with a new exporter fails this
check instead of silently leaving host units on another policy.

The ordinary tool publisher calls
`frontend_workers.bind_wrapper_capability(directory, manifest, capabilities)`.
Any separate immutable tool builder used for qualification must call the same
helper after capturing exporter capabilities and before publishing `ready.json`.
These probes are setup work. Launcher invocations only validate their recorded
capability and binary hashes. Launch statistics record the exact count, compiler
flag/commit, wrapper binding, Cargo scope and unchanged std/backend/linker policy.

## Prepared controls

`crates/mir-export/tests/wrapper_route.rs` exercises host/guest/proc-macro/native
routing, preserved flags, exactly one appended frontend flag, pinned executable
selection and rejected conflicts. `tests/test_frontend_workers.py` mocks every
process and checks namespace separation, capability failures, legacy omission,
function-cache auto, unchanged Cargo jobs, and no VM execution after a failed
check. These tests have not run.

`qualify.py` requires one already installed matching toolset and already prepared
stock std-MIR metadata in the executing checkout. It fails before any project
build if that std preparation is missing or changed, validating the complete
metadata inventory, required crates, hashes and stamps. It never silently
invokes the existing four-job preparation path during a two-job qualification.

Under the canonical shared lock, the proposed driver copies its local fixture
to a fresh owned run directory and executes complete cold/edit/restoration
histories at explicit one and two, using unchanged Cargo profiles, two Cargo
jobs and function-cache auto. A shared dependency is used by the guest, a native
build script and a native proc macro; its 3→7→3 edit changes all three inputs to
the expected result. The selected function mutates a heap allocation and a
mutable static. Exact selected bytecode must match across worker counts and
after restoration. The fixture contains an empty global assembly item, while
selecting its inline-assembly function must fail instead of executing stale
bytecode.

Uncalled type, borrow and constant-evaluation errors must fail in both launcher
histories; each subsequent restoration must recover the original bytes. Direct
pinned native compiler controls compare complete structured diagnostic records
including source spans, as a multiset because independent diagnostics can be
delivered in different orders. They use raw rustc JSON and do not mistake
Cargo's rendered-diagnostic mode for structured stderr. Raw output is retained.

All started children get exact argv/cwd/PID receipts and are drained before a
source restoration or lock release. Receipts also preserve the relevant
compiler/Cargo environment and profile settings. Failed attempts and sources are preserved;
there are no retries, cache deletions, holdout accesses, or peer workload changes.
The driver requires the shared lock and at least 8 GiB free. Tool builds and std
preparation require separate coordinated setup windows and matching build
profiles before this driver may run. Process durations in its receipts are
correctness provenance, not benchmark samples.

The concrete unexecuted build and final-key qualification handoff is in [PUBLICATION.md](PUBLICATION.md).
