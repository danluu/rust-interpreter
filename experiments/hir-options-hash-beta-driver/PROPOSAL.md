# Candidate beta sysroot and hash-driver continuation

Source proposal only: no compilation, composition, loader probe or driver
execution has occurred for this proposal. No future output is frozen.
This qualifies the independent options-hash candidate; it does not combine
packed storage or single-Walk changes, install a runtime, publish tools, or
establish the 0.5-second application target.

X = `/Users/danluu/dev/rust-interp-runtime-exporter-20260918`.
N = X/.work/hir-options-hash-compiler-01; S = N/source; B = S/build.
The acquired candidate commit is `4de35bdacef0e3cd18a66bc30b5459c19e09b118`.
H = `aarch64-apple-darwin`; D2 = B/H/stage0; E2 = B/H/stage1.
B3 is the proposed fresh N/beta-sysroot. These are roles and owned destination
names, not evidence that any unobserved output already exists.

## Role contract

| Role | Compiler/data | Required separation |
| --- | --- | --- |
| Build compiler | Actual D2/bin/rustc from pinned beta provider | Executes compilation of native control programs |
| Build sysroot | B3 beta libraries plus the complete new candidate private stamp | Supplies beta-compatible compiler-private metadata and link artifacts |
| Runtime compiler | Actual E2/bin/rustc and E2/lib driver/LLVM closure | Supplies candidate compiler behavior and real source identity |
| Application sysroot | E2 | Used by embedded compiler calls and their fixture compilations |
| Auxiliary objcopy | B3/lib/rustlib/H/bin/rust-objcopy | Loads its matching beta LLVM from B3/lib/rustlib/H/lib |
| Hash control executable | Newly compiled unchanged controls/driver.rs | Links the new E2 driver; exactly two execution processes |

B3 is not a substitute application sysroot. It must never be mislabeled as
E2, R, a complete stage2 compiler, or an installed runtime. Existing B2/R/std/
exporter/VM files and their readiness records remain unchanged. Historical B2
manifests, private files, driver hashes and compatibility results are recipe
references only; none qualifies B3.

## Prerequisites and actual discovery

Require actual passed acquisition, metadata, eight-stage compiler build and
independent build verification for this candidate. The unchanged run-make
recipe has its own source proposal and actual qualification; do not rerun it
inside this continuation or treat a source review as its result. The complete
candidate correctness gate requires both run-make and these native controls.

The metadata phase must discover and freeze the following from the completed
build, before assembly or control compilation is authorized:

- Exact candidate source/blob inventory, regenerated SOURCE_IDENTITY,
  bootstrap configuration, build environment and actual compiler commands.
  Retain the full producer command mapping from the successful native build,
  including commit and source-remapping definitions. No favorable filename
  or timestamp can substitute for producer association.
- The actual native `.librustc-stamp`. Bootstrap derives its location from
  cargo_out(build_compiler, Mode::Rustc, H); for the planned native stage1 build
  this is B/H/stage1-rustc/H/release/.librustc-stamp. Confirm the actual profile
  and output paths from the successful command before selecting it. A check
  stamp, test-only artifact or old C stamp is not interchangeable.
- Every NUL-delimited stamp entry, including its h/t/s tag, complete path,
  size, SHA-256 and current file identity. Reconcile all entries with the
  actual producer outputs. Host proc-macro files are included, not filtered
  out because they are outside the target release directory.
- The actual new driver dylib and matching rmeta pair used by the new
  rustc_main consumer. Preserve both explicit externs and their order. The
  old native005 command index, driver suffix and metadata hashes are not
  candidates for reuse. Require the stamped dylib to match the installed E2
  runtime driver's bytes; require its rmeta to be the paired candidate output.
- The exact two already acquired beta rustc/std archives, their full hashes,
  member tables, and archive-to-D2 provider association. No acquisition is
  requested here. An absent/changed archive is a failure requiring a separate
  decision. Do not copy a preexisting assembled B2 directory.
- Current D2 and E2 versions/sysroots, complete current Mach-O declarations
  and non-system loader closures, and the selected SDK/linker/objcopy provider
  routes. Bind the candidate build's final inventories and recorded owned
  hardlink changes; do not relax file identity checks inside this operation.

Use exact membership, not a newest-file glob. Private outputs may have owned
bootstrap hardlink aliases: record their actual identity and complete source
association, then make ordinary distinct-inode copies into B3. Do not edit,
strip, chmod or remove source build artifacts to manufacture nlink=1.

## Fresh B3 composition

The reference is the beta auxiliary compositor, with its explicit archive
copy support, not the earlier compositor without that feature. Its historical
SOURCE/TREE/STAMP constants bind C and must be replaced by an explicitly
reviewed successor or parameterized adapter bound to the actual new producer.
Do not import the old module and silently rewrite globals or identity labels.

Preserve the reference's complete-input and output rules:

1. Parse all stamp entries. h maps to host lib, t to target lib, and s to the
   target self-contained subtree, as bootstrap add_to_sysroot does. Here host
   and target are both H. Restrict all sources to the new owned native build
   roots. Reject malformed tags, unterminated/invalid paths, duplicate source
   or destination, and file/directory ancestor collisions.
2. Select the complete `lib/` payloads of both pinned beta components, not a
   handpicked std subset. Reject selected symlinks, hardlinks, sparse/special
   members, duplicate/escaping paths and mode anomalies. Bind bounded member
   count and expanded payload from the actual archives, with streamed hashing
   and the existing seed-inspection bounds. Never call extractall.
3. Add the complete approved new private stamp. Preserve bootstrap's
   rustc_* ambiguity check, including its rustc_hash exception and its boundary
   over the stamped private crate set. Do not weaken it or extend a beta
   dependency collision rule without source justification.
4. Preserve the explicit ordinary-copy mapping from beta `lib/libLLVM.dylib`
   to `lib/rustlib/H/lib/libLLVM.dylib`, after confirming the actual beta
   objcopy's relative loader edge requires it. The source member and both
   destinations have identical bytes but separate inodes. This is a beta
   auxiliary provider, not E2's potentially different LLVM library. Repeated
   archive members require explicit destination mappings.
5. B3 and its external evidence directory must both be fresh under ordinary
   owned parents after canonical admission and immediately before creation.
   Copy only the frozen plan, check capacity around each MiB, fsync/read back,
   and retain all partial output on failure. All B3 files are ordinary,
   uniquely owned copies with full inventory and source-to-destination proof.
6. The entire resulting membership, bytes, modes, archive mappings and private
   stamp must match the reviewed plan. Do not hardcode the historical 335
   files/256 private entries as the candidate's count. Recheck every input and
   the full source/compiler/provider closure afterward. Initial status is
   assembled-unqualified, with metadata outside B3 to avoid self-reference.

## Auxiliary loader and real strip controls

Reuse the reviewed B2 strip recipe and its parser tests with actual B3/D2
paths and hashes. A version string alone is insufficient.

- Inspect actual B3 objcopy and copied beta LLVM Mach-O load commands. Separate
  LC_ID_DYLIB from real dependencies; preserve raw declarations and source-bound
  parsing. Require exact current edges and provider identity.
- Run B3 objcopy --version with DYLD_PRINT_LIBRARIES=1 and the explicit clean
  environment. Require the actual matching beta LLVM at its B3 host-lib
  destination. Reject foreign private loads, wrong PID, missing provider,
  unknown diagnostics and loader errors. Preserve the declared system dyld
  cache/platform assumption separately from private file hashes.
- Compile a fresh debug-bearing object with D2, --sysroot=B3, --emit=obj,
  -Cdebuginfo=2, -Cstrip=none, -Csplit-debuginfo=off and -Copt-level=0 using the
  unchanged small strip fixture. Do not link and then assume DWARF is embedded.
- Run objcopy --strip-debug from before.o to a distinct fresh after.o, again
  with actual loader tracing. Require zero exit and no strip warning/failure.
  Parse bounded arm64 Mach-O sections: nonempty __DWARF/__debug_info before,
  no debug sections afterward, strictly smaller result, and exact equality of
  every nondebug section's identity, flags, size and payload hash. The source
  and original object remain unchanged. An object is not executed.

Retain the before/after objects, raw declarations, loader traces and section
proof. This proves the new auxiliary route; later Cargo builds still must
reject actual strip failures. It does not replace native behavior controls.

## Native compiler-role controls

Adapt the unchanged successful embedded stock-compiler recipe with exact new
producer bindings. D2 compiles S/compiler/rustc/src/main.rs against B3. Use the
actual ordered driver dylib+rmeta extern pair, `-Lnative=E2/lib`, the qualified
clang linker, and runtime rpath E2/lib. Preserve `--print=link-args` and bind
the actual resulting linker invocation. Its RUSTC_BOOTSTRAP=1 build environment
does not become permission to introduce compiler-version overrides.

The newly built stock compiler's actual -vV and loader trace must prove the
E2 version, commit, driver and complete private runtime closure. D2/B3 belong
to its build; E2 belongs to its runtime. Do not merely accept an rpath string
as evidence that the intended driver was loaded.

Retain the reference's complete 18-command stock history with paths/identities
rebound: D2/E2 identity probes, one stock compiler build, static/actual loader
checks, ordinary positive compilation, cold/repeated HIR reuse behavior,
native `42\n` executions, real uncalled E0308 with exact ordinary/embedded raw
JSON parity, a hit in the failing run, and source restoration with behavior.
Each executed program's actual binary bytes are retained. This history is a
native correctness check, not an application performance sample.

Add explicit negative role controls using a small fixture and E2/bin/rustc,
then the new stock compiler, with B3 supplied as application --sysroot. Each
must reject incompatible beta metadata, emit ordinary compiler diagnostics
rather than ICE/loader failure, and leave no successful output. Compare raw
diagnostics where the commands are otherwise identical. Do not substitute a
missing-file failure for metadata-role rejection. Exact diagnostic criteria
must be derived from the candidate source and frozen with the actual command
plan; historical error text is not guessed. These controls are separately
listed in the final command count, not hidden inside the old 18.

## Compile the unchanged hash driver once

Source: X/experiments/hir-options-hash/controls/driver.rs and fixture.rs, both
unchanged and independently hashed. Use one fresh native output location and
ordinary fixture copy under N/native-controls. No driver source patch is
proposed. Freeze actual build inputs before executing.

The reviewed command will follow this role template:

```text
D2/bin/rustc --sysroot=B3 --edition=2024 --crate-name=hash_cache_control_driver
  --print=link-args X/experiments/hir-options-hash/controls/driver.rs
  --extern rustc_driver=ACTUAL_B3_DRIVER_DYLIB
  --extern rustc_driver=ACTUAL_B3_DRIVER_RMETA
  -Lnative=E2/lib -Clinker=ACTUAL_CLANG
  -C link-arg=-Wl,-rpath,E2/lib -o FRESH_HASH_DRIVER
```

The new complete B3 private metadata resolves rustc_data_structures,
rustc_interface and rustc_middle; their actual identities must match the same
candidate build, including the new public incremental_options_hash method.
Preserve the exact actual extern pair/order and linker proof. Use
RUSTC_BOOTSTRAP=1 only as needed to compile rustc_private control source.
Record the fresh driver binary and static Mach-O closure after compilation.

The driver has no metadata-only CLI. Do not execute it with --version or
dummy arguments as a loader probe. Its actual loader qualification occurs in
the two required real runs below, with DYLD_PRINT_LIBRARIES=1, clean explicit
environment and exact private library allowlist. No extra execution of main
is permitted to discover the loader set or warm the compiler.

## Exactly two processes, eight contexts each

Run the same newly built driver once with each argv:

```text
FRESH_HASH_DRIVER E2 FRESH_FIXTURE SERIAL_OWNED_OUTPUT serial
FRESH_HASH_DRIVER E2 FRESH_FIXTURE PARALLEL_OWNED_OUTPUT parallel
```

Both output directories are fresh, ordinary and separate. The source and
output path stay constant across all eight contexts within a process. Keep
RUSTC_FORCE_RUSTC_VERSION, ambient rustflags/wrappers and self-profile paths
unset. The fixture does not need RUSTC_BOOTSTRAP at runtime. Candidate source
supports the needed nightly flags. No incremental directory or profile output
is requested by these hash-only controls.

Do not merge the runs into one process: rustc's DYN_THREAD_SAFE_MODE is
process-global and only permits repeated initialization to the same mode.
The serial driver asserts it is false; every context in the parallel driver
uses -Zthreads=2 and asserts it is true. Its barrier and par_join require two
distinct worker threads. No candidate accessor is called before the first
parallel pair: HIR capture/reuse are both false, and production body-cache
prepare returns before hashing in this policy. GlobalCaches::default creates
a fresh OnceLock for each GlobalCtxt.

Require exactly these eight JSON observations, in order, and one terminal
JSON record per process:

| Label | Required hash relationship to base-first |
| --- | --- |
| base-first | Initial context |
| base-repeat | Incremental and crate hashes equal |
| tracked-change | Both differ after -Copt-level=1 |
| base-after-tracked | Both restored |
| non-crate-tracked-change | Incremental differs, crate hash equal after lint change |
| base-after-lint | Both restored |
| untracked-change | Both equal with self-profile-events=default and profiling off |
| base-final | Both restored |

Every accessor read is asserted equal to that context's original uncached
dep_tracking_hash(false); the crate hash is computed with true independently.
Serial checks 64 reads per context. Parallel checks 64 per worker per context
and distinct worker IDs. These checks reject a stale process-global cache,
caching the true variant, and cross-context lint/option confusion. Do not
require hashes to match between the two processes, whose output paths and
thread options differ.

The parser must reject duplicate/missing/unknown records and duplicate JSON
keys, validate u64 values, status/worker counts and terminal contexts=8 plus
the selected parallel boolean, and independently repeat all equality and
inequality relationships. Preserve raw stdout and stderr. Separate only
strictly recognized actual DYLD lines; reject unexpected diagnostics or any
foreign private provider. Both traces must load the new driver/LLVM closure.
No output truncation, failure hiding, HIR eligibility claim or timing claim.

## Bounds and admission still required

Keep canonical benchmark.lock/600 seconds, 24 GiB entry, 9 GiB active stop,
8 GiB running floor, the 14 GiB aggregate N allocation and 256 MiB aggregate
evidence budget unless a separate explicit successor is reviewed. Count B3,
native fixtures, driver binaries and all continuation evidence. Derive actual
copy/retention reservations from the completed build and composition inventory;
do not count old B2 as free storage for the new candidate.

Reuse the existing supervisor and source/provider/namespace guards. Bind the
exact Python/import closure, executors, environments, ordered child list, cwd,
input copies, source proofs and every preceding actual receipt. Sample free
space and owned allocation during copies and children. Recheck full bytes and
identities at stage boundaries; preserve all failures and partial outputs.

The parallel barrier requires an explicit finite wall-clock bound. The
existing compiler helper samples capacity but has no absolute child deadline;
it cannot be reused unchanged for this guarantee. Propose a 120-second limit
for each actual hash-driver process, with a separately reviewed narrow helper
adaptation and pure deadline/ownership controls before launch. Bound any
graceful-stop wait as well; do not leave an unbounded wait after a timeout.
Any timeout handling may affect only the newly created, exactly revalidated
owned process group. Record PID, parentage, start, argv, cwd, terminal and group
membership before a signal; preserve the reason and raw outputs. Never touch
another agent's or user's process to satisfy capacity or a hang bound.

Freeze runnable metadata/composition/strip/native/hash stages only after their
actual dependencies exist and parent review has accepted the concrete plan.
No admission or execution is authorized by this document. A passing result
would qualify this compiler mechanism and its build/runtime role composition;
new runtime installation, exporter composition and fresh application histories
still require their own actual evidence.
