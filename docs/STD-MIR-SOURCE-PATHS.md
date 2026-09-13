# Explicit source-containing standard MIR

Status: source-only implementation, not executed or qualified. The compiler in
the earlier integration03 cannot use this policy: its native std and decoder
were built without bootstrap source remapping. No new compiler, std build,
benchmark or diagnostic qualification is claimed here.

This implements the prepared-std portion of the reviewed production source-path
plan (commits `e1f30d0b4a1f17c418970f003965baf430c34234` and
`208c1537a18f484fcf74ad46a83f64dfbf021f6a`,
`experiments/stable-cgu/SOURCE-PATHS-PLAN.md`). The pinned recipe implementation
is Cargo commit `3c0b534756e166d12eb9fd2e1abfe5b42ac6101e`; preparation uses the
actual dated public Cargo executable, recording its full version, hash, rustup
route and dynamic-library closure. It does not claim to rebuild Cargo.

## Selection and namespaces

The current `metadata-sysroot-v1-release-backtrace` policy, default CLI, flags,
keys and automatic preparation are unchanged. V2 is explicit and load-only in
the launcher:

```
--std-mir --std-mir-policy source-paths-v2 --std-mir-key PREPARED_KEY
--compiler-key COMPILER_KEY --tool-key MATCHING_TOOL_KEY
```

Custom Cargo, fetch, public compiler selection and an omitted v2 key are
rejected. The prepared key participates in the ordinary workspace identity, so
v1 and v2 cannot share Cargo freshness or incremental artifacts. V2 returns the
same `{key,sysroot,target}` launch statistic, plus its explicit policy field.

Prepare separately from the owning checkout, after the new complete stage2
compiler is installed and its native controls pass:

```
python3 scripts/std_mir_source_paths.py --compiler-key COMPILER_KEY \
  --namespace stable-cgu:off --run-id std-source-v2-off-01 \
  --workload-lock /Users/danluu/dev/rust-interp/.work/benchmark.lock \
  --lock-wait-seconds 600
```

Use a second fresh run ID and `stable-cgu:on` for the other current arm. The
module accepts a general explicit compiler-policy namespace; the forthcoming
per-Mono selector uses `stable-mono-cgu:off/on`. Both arms prepare identical MIR
with metadata-only checking; the namespace provides isolation, not an extra
partitioning flag. The current CLI still derives `stable-cgu:off/on` until the
separately owned per-Mono routing change lands.

The preparation child acquires the explicitly supplied canonical workload lock
and then the existing std setup lock. An outer supervisor must not hold another
open instance of either lock. The launcher only loads a completed key and never
starts std setup or native probes for v2. The qualification harness can consume
prepared namespaces with `--std-mir-policy source-paths-v2`,
`--std-mir-off-key KEY` and `--std-mir-on-key KEY`; it requires strict diagnostic
comparison. This selection plumbing does not add the remaining strict probes
or diagnostic-only compiler configuration described below.

## Compiler and preparation contract

The immutable compiler provenance must contain the exact capability below,
using its truthful full `source_commit` C (including a new per-Mono commit):

```json
{
  "std_source_paths": {
    "schema_version": 1,
    "policy": "bootstrap-remap-source-paths-v1",
    "remap_debuginfo": true,
    "virtual_rust_source_base_dir": "/rustc/C",
    "virtual_rustc_dev_source_base_dir": "/rustc-dev/C",
    "cargo_source_commit": "3c0b534756e166d12eb9fd2e1abfe5b42ac6101e"
  }
}
```

The compiler packager must bind this capability to the actual bootstrap
configuration and expanded build environment. The preparer also checks the
compiler version/provenance agreement and performs an unmapped native E0080
smoke probe; merely inserting a capability cannot make the old compiler pass.
No runtime `CFG_*` override, simulated rust-src base or relative path fallback
is used.

The new policy is `metadata-sysroot-v2-source-paths-release-backtrace`. Let W be
`.work/std-mir/KEY`. A typed pre-key recipe expands to the exact pinned Cargo
executable followed by:

```
check --manifest-path W/library/Cargo.toml -p sysroot --release
--target HOST --features backtrace --locked --offline --jobs 2
--target-dir W/target -Zroot-dir=W -Ztrim-paths
--config profile.release.trim-paths="all"
--config profile.dev.trim-paths="all"
```

These are structured argv entries; the quotation marks delimit TOML strings.
Cargo runs from W and receives the unchanged
`RUSTFLAGS=-Zalways-encode-mir=yes -Zforce-unstable-if-unmarked` plus
`__CARGO_RUSTC_BOOTSTRAP_WS_REMAP=/rustc/C`. In particular, root-dir is W, not
W/library. Required checking, MIR flags, release/backtrace features, lockfile,
offline policy and profile selection remain intact. Setup jobs2 is recorded
separately and receives no warm-performance credit. Ambient conflicting flags,
trim/root overrides or inherited Cargo rustflags are rejected. Other existing
Cargo configuration is bound by file identities and absent-path guards.
Top-level Cargo `include` is rejected, including optional/table forms: the
initial policy does not track the transitive included-file configuration.
Conflicting override variables are rejected by presence, even with empty
values: empty `CARGO_ENCODED_RUSTFLAGS` would otherwise suppress the required
MIR flags. Empty wrapper variables remain allowed. Home overrides must be
absolute and nonempty so changing the child cwd cannot change their meaning.

Publication contains every metadata file and a complete materialized source
copy at `W/sysroot/lib/rustlib/src/rust/library`. The immutable compiler source
inventory must equal the build snapshot before and after checking, and both
must equal the published source tree. Metadata must include exactly one each
of core, alloc, std, test and proc_macro; duplicate basenames, missing crates,
empty inventories, extra files and symlinks fail. Full hashes are checked at
publication and available again with `load(..., rehash=True)`. Ordinary loading
checks complete file/directory inventories and read-only device/inode/mode/
size/mtime/ctime stamps for metadata, published sources, build snapshot and
retained evidence, including absent Cargo overrides. This detects local
mutation; it is not authentication of adversarial manifests.

An unmapped prepared-sysroot E0080 smoke probe must expose both core panic and
std macro expansion sources, with actual nonempty JSON snippets matching the
installed bytes and byte/Unicode-character coordinates. The verifier compares
the raw text; it never fills, renames or substitutes diagnostics. Its small
source-coordinate validator rejects unsupported BOM/CRLF normalization cases.
Rustc's own ordinary external-source content-hash validation remains unchanged.

All discovery, loader inspection, checking and probe children use safe capture
and completed process receipts. An 8 GiB free-space check precedes every child.
Attempts retain exact argv, relevant environment, full environment digest,
stdout/stderr, raw JSON, ownership, source inventories and failures. Readiness
is published only after complete immutable trees and validated receipts exist.
A failed identity directory is never resumed or overwritten: retain it and use
a new explicitly recorded namespace after a diagnosed correction. No automatic
cleanup, downloading or source edits are performed.

## Required future qualification

Neither successful setup nor these two smoke probes is strict presentation
qualification: every ready/result explicitly says
`full_presentation_qualified=false`. Before accepting timings or adoption:

1. Build and qualify the complete new production stage2 compiler/native std/
   rustc-dev with actual remap environment evidence, full source inventory,
   matching LLVM/support tools and the existing native/CGU/strip controls.
2. Run unmapped native and prepared core/std E0080 probes through cold, real
   source position edits and restoration. Verify complete expansion chains,
   snippets, source hashes and Unicode coordinates, including a second owned
   installation prefix. Test missing/corrupt source, wrong root, duplicate or
   missing metadata and escaping links only in fresh disposable copies.
3. Add the reviewed equal **diagnostics-only compiler** mappings to the real
   qualification fixture for public/native/prepared source roots and all Cargo
   host and guest roles. Retain raw JSON and the strict existing comparator;
   do not call the preliminary source-derived comparison mode. The 36-command
   custom integration, native host scripts/proc macros, uncalled errors and
   source-edit/restoration histories must pass with zero presentation gaps.
4. Qualify native/exported `file!()` and proc-macro span/file observables with
   and without the diagnostic-only mapping, including application files with
   std-looking names. No diagnostic mapping enters performance commands.
5. Freeze the new compiler, matching tools, both std keys and fresh workspaces,
   then compare off/on with the same production compiler/profile. No old
   preliminary compiler or source-derived diagnostic result satisfies this
   gate, and setup/profile/remap changes receive no grouping-speedup credit.

Prepared tests cover recipe/namespace identity, compiler/Cargo rejection,
conflicting configuration, raw snippet integrity, mutation and incomplete
publication, fail-before-ready histories, v1 dispatch and launcher selection.
They have not been executed. Run them under the canonical workload lock before
the first actual v2 preparation; then perform the compiler-backed gates above.

Cargo `[env]` entries receive the same presence-based loader and flag checks as
ambient settings, for both string and `{value, force, relative}` forms. Configured
compiler/toolchain/home route changes are rejected before launching a child.
Unrelated build-script environment inputs remain allowed and are bound by the
complete configuration digest. The focused forced-loader regression is prepared
but has not been run.
