# Per-MonoItem production compiler: implementation and admission plan

Status: **source-only, unexecuted**. No new compiler checkout, build, prepared
standard library, or benchmark has started under this plan. The reviewed
per-item patch remains unapplied. The completed stable-module screen activated
its policy but showed no whole-command improvement; see
[retained activation evidence](../../results/stable-cgu-activation-01/README.md).
This follow-on may also fail. The 0.5-second strict target remains unmet.

This plan combines the published per-item draft at rust-interpreter commit
`5ceb66ce409db78df86959180d13b89e27d648c9` with the separately proposed
[production profile](PRODUCTION-PLAN.md) and
[source-path repair](SOURCE-PATHS-PLAN.md). It does not change the immutable
`73a11f` qualification compiler, package06, installed compiler `60096d7e...`,
or any current tool/std cache. Native std assertions and overflow checks are
explicitly off in this new production package. User-code profiles, required
analysis, Cargo units, native helpers, proc macros and validation stay intact.
Profile and source-path changes cannot be credited to per-item partitioning.

## Exact ownership and identity

Reserve these paths only after setup admission; none is created by this plan:

| Purpose | Planned owned path |
| --- | --- |
| Rust-interpreter worktree and branch | `/Users/danluu/dev/rust-interp-mono-production-20260913`, `perf/mono-production-20260913` |
| Independent Rust source repository | `/Users/danluu/dev/rustc-stable-mono-production-20260913` |
| Compiler build root | `/Users/danluu/dev/rustc-stable-mono-production-20260913/build` |
| Setup receipts | Interpreter worktree `.work/mono-production-setup-01/` |
| Build/test/dist receipts | Interpreter worktree `.work/mono-production-build-01/<unique-attempt>/` |
| Composed prefix | Interpreter worktree `.work/mono-production-build-01/packaged-stage2-01/` |
| Final installation | `/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/compilers/<installer-key>/sysroot` |
| Final tools | PRIMARY `.work/interpreter-tools/<complete-tool-key>/` |
| Strict qualification | PRIMARY `.work/mono-production-qualification-01/` |
| Matched screen | PRIMARY `.work/strict-warm-stable-mono-screen-01/` |

Create the interpreter worktree from then-current main plus reviewed necessary
experimental infrastructure. Record its exact commit and keep compiled sources
frozen through tool construction and qualification. Use an independent local
Git clone of the owned old Rust source with `--no-hardlinks --no-checkout`, then
check out `73a11f167216d3955c277ed47f9b8cc68208105b` on a new branch. No shared
build directories, object alternates, directory links or writes to the old
source repository are needed. The old history includes the genuine upstream
base `cea272fa356e94bd2ee2cadf376630aa0683867a` needed for CI LLVM discovery.

Apply `experiments/stable-mono-cgu/rustc.patch` from `5ceb66c`, first checking
SHA256 `d797202ccd8c0a6d619d63c730587edae646414ddc6092611292e1dbdfc449cc`
and every base/patched file hash in that commit's `source-identity.json`.
Run focused formatting only when admitted. Commit the resulting exact source
as **C_mono**, recording any formatting-only delta separately. C_mono is a
future real Git commit, not a chosen constant. No compiler version, commit or
stable identity is overridden. Freeze its full tracked source and submodule
inventories before compiling; any substantive correction requires a new
commit, package identity and appropriate repeated controls.

The original stable-module implementation remains in this source. Both
partitioning options are off while building the compiler and its native std.
Every later per-item comparison arm must explicitly retain
`-Zstable-cgu-partitioning=no`; only `-Zstable-mono-cgu-partitioning=no/yes/no`
varies. The new tracked option rejects simultaneous enablement, including
metadata-only invocations. Existing linkage, LocalCopy reachability,
internalization, query checking and conservative fallbacks remain as reviewed.

## Required source and prebuilt dependencies

Materialize `library/backtrace` at the exact gitlink
`d902726a1dcdc1e1c66f73d1162181b5423c645b`, independently under the new source.
Record its recursive source inventory. Compiler-builtins, stdarch and
portable-simd are already tracked library source at this pin. The completed
prior build required no Cargo/LLVM/docs submodule checkout: `src/tools/cargo`
and `src/llvm-project` remained empty. Preserve that scope; this compiler build
does not build Cargo, documentation, GCC or Enzyme. If bootstrap requests an
additional source dependency, record and materialize its exact gitlink before
proceeding. Never substitute a peer's modified checkout. The reviewed Cargo
source recipe pin is `3c0b534756e166d12eb9fd2e1abfe5b42ac6101e`.

Copy and verify the existing owned CI LLVM archive:

```
/Users/danluu/dev/rust-interp-stable-cgu-20260913/.work/stable-cgu-compiler-setup-01/rust-dev-nightly-aarch64-apple-darwin.tar.xz
SHA256 0035445cb01c652999862c240d3c8ce663247abdc410482dde10f9e9c264bf8f
```

It is 54,314,276 compressed bytes (294,279,869 unpacked bytes), from the actual
upstream base's Rust CI URL, LLVM `23.1.1-rust-1.100.0-nightly`. Seed only the
new bootstrap cache at
`build/cache/llvm-aarch64-apple-darwin-cea272fa356e94bd2ee2cadf376630aa0683867a-false/rust-dev-nightly-aarch64-apple-darwin.tar.xz`.
Let normal bootstrap unpack it into the new `build/<host>/ci-llvm`; verify the
observed selected upstream SHA, headers, library, executables and download
stamp. Do not manufacture freshness stamps. If CI discovery selects another
archive or cannot establish the base, stop that attempt and diagnose source
history; do not silently build LLVM from source or borrow a peer cache.

Use the unmodified `src/stage0`: beta compiler/Cargo dated 2026-08-30, compiler
commit `cbae9b4cae2b108f6a3d18cfe6075714bb739463`, and the pinned formatter.
Copy immutable matching archives from owned earlier setup only after checksum
verification, or download the exact stage0 manifest entries into the new owned
cache. No stage1/stage2 native std or rustc-private objects are reused from the
assertions-enabled build. Record SDK, Apple linker/toolchain, deployment target,
actual stage0 identities and sanitized environment. Network fetch is setup,
never a measured edited build.

## Disk and lock admission

The parent's latest observation was about 16.5 GiB free. That is insufficient
for this proposed fresh build. No setup allocation should start before a new
capacity receipt and parent-coordinated task-owned retirement establish space.
Only completed, explicitly owned Cargo/project screen caches may be candidates
for retirement after logs, receipts, source histories, artifact copies and all
promised evidence are archived and hashed. The root owns that action; this plan
does not authorize deleting compiler sources, old compiler build trees,
packages, installations, evidence, reserved holdouts or any peer cache.

Require **at least 36 GiB free before setup/build admission**, representing a
28 GiB initial incremental-allocation budget plus the 8 GiB floor. Budget 2 GiB
for independent source/stage0/LLVM preparation, 20 GiB for compiler stages and
focused test dependencies, and 6 GiB for dist components, one composed prefix
and one immutable installation. These are conservative planning allowances,
not measured exclusive disk costs. Prior host free-space deltas include other
work and cannot prove an exact new footprint. The prior stage2 runtime inventory
was 596,151,953 logical bytes and package06 has 6,983 inventoried paths; new
exact inventories replace these estimates at each gate. Do not assume APFS cloning or hard links reduce
logical materialization requirements.

Re-admit tools/std/qualification with at least 8 GiB of projected new space plus
the 8 GiB floor; re-admit the three-cache 27-command screen with at least 12 GiB
projected plus the floor. These later budgets are additional phase allowances,
not permission to consume the reserved floor. Before each step use the larger
of the listed allowance and an estimate from actual remaining component sizes.
If retained outputs make the next phase inadmissible, preserve them and resolve
capacity separately. Reducing workload scope, profiles or validation to fit is
not an option.

Use only the canonical lock
`/Users/danluu/dev/rust-interp/.work/benchmark.lock`, with a recorded background
supervisor and bounded 600-second admission. Yield tool waits for progress
updates; no compiler/test child starts until admitted. Macro qualification has
the next workload window. Max two build/test jobs, no workload overlap, and no
controls on other processes. Record PID/parent/start/cwd/argv, full selected env,
source/config/tool hashes, before/during/after disk samples, exact stdout/stderr
and exit status for every attempt. Preserve failures and wait timeouts. Adapt
the existing owned supervisor's low-space guard without broad process matching;
any stop must revalidate the exact task-owned process group and preserve the
8 GiB floor. Always wait for owned children before releasing the lock, including
receipt-writing failures.

## Build and compiler controls

Copy [bootstrap-production-source-paths.toml](bootstrap-production-source-paths.toml)
to the new source's untracked `bootstrap.toml`; its current SHA256 is
`71b495da8fc35ca1321322f56065eb149ecd82fa3c8ff7ef4d4c10ec53f0df9b`.
The default build directory is the new source's `build`, with explicit
`--stage` on every command. Keep optimize=true, debuginfo1, thin-local LTO,
16 compiler CGUs, compiler incremental=false, real commit reporting,
assertions/overflow off for compiler/tools/native std, and
`remap-debuginfo=true`. No frontend worker, macro-host optimization or custom
Cargo policy is mixed into this comparison.

Run, serially through the owned supervisor, from the new source:

```
./x fmt --check compiler/rustc_monomorphize/src/partitioning.rs compiler/rustc_session/src/options.rs compiler/rustc_session/src/config.rs compiler/rustc_interface/src/tests.rs tests/codegen-units/partitioning/stable-mono-merging.rs tests/run-make/stable-mono-cgu-partitioning/rmake.rs
./x build --stage 1 compiler/rustc library --jobs 2
./x test --stage 1 tests/codegen-units/partitioning tests/run-make/stable-mono-cgu-partitioning --jobs 2
./x build --stage 2 compiler/rustc library --jobs 2
./x test --stage 2 compiler/rustc_interface --test-args test_unstable_options_tracking_hash --jobs 2
./x test --stage 2 tests/codegen-units/partitioning tests/run-make/stable-cgu-partitioning tests/run-make/stable-mono-cgu-partitioning --jobs 2
./x dist --stage 2 rustc-dev rust-std --jobs 2
```

If the format check fails, format only those files before C_mono/source freeze
and start a new recorded check. Stage1 controls catch errors before stage2; final
stage2 controls remain mandatory. Retain all original stable grouping tests.
The new tests exercise roots N-1/N/N+1, added/restored roots, unchanged placement,
empty buckets, actual on-policy entrypoints, generics, TLS, statics, destructor
effects, unused-body type/borrow errors, optimized/unoptimized callers, option
transitions/count changes and assembly/coverage/explicit-linkage fallbacks.
No synthetic unchanged-span identity control replaces real edit histories.

The new bootstrap must demonstrably set
`CFG_VIRTUAL_RUST_SOURCE_BASE_DIR=/rustc/C_mono` and
`CFG_VIRTUAL_RUSTC_DEV_SOURCE_BASE_DIR=/rustc-dev/C_mono` in the compiler build,
and the stock workspace/trim remaps in native std. Capture the actual build
flags, not just a TOML assertion. Native unmapped E0080 probes must resolve
installed core/std sources and supply their own complete diagnostic snippets.
This rebuild fixes a decoder constant and serialized source names; a source
copy or diagnostic comparator exception alone cannot repair the old package.

## Complete package, tool and std identity

Adapt the existing stage2 composer in the new interpreter worktree. It must
bind every runtime/std/dev input to successful new build/dist receipts and
qualified post-test inventories, including any test-generated rustdoc. Preserve
all required native LLVM aliases. The first new production package is **not**
byte-equal to package06; replace the old support-only upgrade's mandatory
previous-package equality with a first-package manifest contract, while keeping
strict component overlap and stage provenance checks. Do not point that check
at a dummy receipt. Optional later additive-package comparisons stay explicit.

Include the exact configured CI `llvm-objcopy` as
`lib/rustlib/aarch64-apple-darwin/bin/rust-objcopy`, binding archive/member hashes
and its loader dependencies. Include complete materialized new rustc-dev
sources and exact library/backtrace sources at
`lib/rustlib/src/rust/library`. No live source-directory links or Cargo binary
shadowing. Native std/rustc-private/runtime bytes all come from this stage2;
matching base library source bytes may be copied only with a full source proof.
Run normal native binary and proc-macro strip controls for none/debuginfo/symbols,
real native on/off/edit/restore executions, and package identity after controls.

Provenance carries real C_mono, original upstream and73a parents, separate
module/mono patch hashes plus combined source diff, config/build/dist/control
hashes, complete file inventory and this explicit capability:

```
std_source_paths = {
  schema_version: 1, policy: "bootstrap-remap-source-paths-v1",
  remap_debuginfo: true,
  virtual_rust_source_base_dir: "/rustc/" + C_mono,
  virtual_rustc_dev_source_base_dir: "/rustc-dev/" + C_mono,
  cargo_source_commit: "3c0b534756e166d12eb9fd2e1abfe5b42ac6101e"
}
```

The Cargo source field identifies the reviewed recipe, not an invented version
of the executable used for preparation; bind that actual Cargo binary and
`-Vv` separately. The installer computes a fresh complete inventory/provenance
key, audits every required support-tool loader closure, verifies `rustc -vV`
and both option capabilities, and publishes the immutable PRIMARY prefix.
A declared source capability never substitutes for the native diagnostic test.

Add explicit default-off per-item routing/capability in the experimental
launcher, wrapper and tool publisher. Use a separate workspace identity that
includes policy/version/off-on, reject simultaneous module enablement and
conflicting user flags/response files, and route both flags identically to
native host and guest invocations. Preserve Cargo/backend jobs and profiles.
Build one exporter/light-wrapper toolset against this complete stage2 install
with `--release --locked --offline --jobs 2`, `CARGO_INCREMENTAL=0`,
`CARGO_PROFILE_DEV_DEBUG=0`, `CARGO_PROFILE_TEST_DEBUG=0`, and
`CARGO_PROFILE_RELEASE_DEBUG=1`. Bind actual compiler-private libraries,
exporter/wrapper capabilities and binaries in the final tool key. Reuse a VM
only if exact current VM/bytecode source and ABI equality are proved; otherwise
build and qualify it once for all arms. No old private-library tool is reused.

The separately implemented explicit `--std-mir-policy source-paths-v2` must
follow SOURCE-PATHS-PLAN exactly: snapshot at W/library, root-dir W, truthful
workspace virtual prefix, trim-paths=all, unchanged required MIR flags, jobs2,
and a complete immutable source-containing effective sysroot. Compiler/source/
Cargo/recipe/namespace inventories get a new key; v1 remains the default and is
not silently upgraded. Both comparison arms use the same std recipe and
compiler, with separate recorded policy namespaces where required. All setup
and source preflights complete before any measured command.

## Strict qualification and same-compiler screen

Require native and prepared-std E0080 cold/edit/restore diagnostics with
byte-verified core panic and std macro snippets, all original coordinates,
Unicode/line changes and no missing presentation. Apply an equal ordered
`--remap-path-scope=diagnostics` configuration to every correctness reference,
host and guest as specified in SOURCE-PATHS-PLAN. Include identical `[host]` and
`[host.<triple>]` flags and reject inherited overrides; retain actual argv proof.
The strict comparator may discard rendered text only. No reconstructed source
snippets, omitted frames, preliminary source-verification mode or ignored
structured diagnostic fields qualify this compiler.

Run full interpreter native-helper/proc-macro cold3/edit7/restore3 histories,
unused type/borrow/const errors and restoration, native output validation,
selected VM artifact/execution checks, and cross-arm bytecode determinism.
The native helper dependency must have more roots than configured N and a real
binary entrypoint must execute with mono policy on. Verify actual policy
activation outside timing, all native and guest flags, preservation of user
checks, standard-source integrity negatives, relocation to another owned
prefix, and file!/proc-macro path observations with diagnostic-only remapping.
Record cold build, binary/code size and available runtime-control effects as
qualification outcomes, separately from the warm target. New benchmarking of
cold/runtime regressions needs its own admitted protocol; do not infer them
from instruction extents or source review.

Only after strict qualification succeeds, freeze source/tools/stdlib/profiles
and prepare three fresh independent caches with one **identical production
compiler and toolset**: mono off / on / off. Stable-module policy is explicitly
off in all three. Use the existing whole-command 27-command screen structure,
all its edits/restoration, complete Cargo host work and validated runnable
artifact endpoint; no correctness-only diagnostic remap enters measurements.
Do not mix custom Cargo, host-macro, worker, borrow-cache or other experiments.
Preserve the five edited pairs, duplicate-baseline noise checks, raw commands,
CPU/wall receipts, exact restored source and output hashes, and own cache
ownership. The unchanged assertions-enabled result is context, never a paired
baseline. Passing this screen is still not a holdout/generalization result;
reserved holdouts remain untouched until the parent chooses a final candidate.
