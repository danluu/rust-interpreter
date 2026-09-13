# Production standard-library source paths

Status: source-only amendment. No compiler/configuration, package, standard
library, launcher or comparator has been changed or executed by this plan.
The frozen qualification compiler is `73a11f167216d3955c277ed47f9b8cc68208105b`
over Rust base `cea272fa356e94bd2ee2cadf376630aa0683867a`. Its bootstrap file
SHA256 is `1962bcb231d2136d1d87ad081329d88348e921b56bc06675170d9f38378034a2`.
Source review uses PRIMARY `4ec11d3df02d3a9f817fcf950112dac764920b9c` and the
exact Rust gitlink Cargo `3c0b534756e166d12eb9fd2e1abfe5b42ac6101e`.
The reviewed file hashes are in `source-paths-review.json`.

## What must be repaired

The current compiler correctly rejects E0080. Its native std reports names such
as `library/core/src/panic.rs`; prepared std reports `core/src/panic.rs`, with
empty JSON `text` arrays. The public toolchain supplies absolute installed
rust-src names and real snippets. `verified_std_diagnostics.py` preserves those
raw gaps and can derive a preliminary comparison view from identical source
bytes. That view is expressly insufficient for strict production qualification.

There are three independent causes/constraints:

1. Bootstrap defaults `rust.remap-debuginfo` to false. The current configuration
   therefore neither remaps std into `/rustc/<commit>` nor builds the compiler
   with the matching virtual-prefix decoder constant.
2. The prepared std build uses neither Cargo's bootstrap remap policy nor a
   source-containing sysroot. Its selected exporter receives `--sysroot` pointing
   at metadata alone. Rustc discovers rust-src only under that effective sysroot.
3. Correct absolute paths in independent public/custom/prepared installations
   are different. The current strict comparator removes `rendered`, sorts whole
   records while retaining duplicates, and replaces only PRIMARY's prefix. It
   cannot make different installed roots equal, even after snippets are fixed.

The Rust encoder comment promises absolute imported paths, but the pinned code
only clones `RealFileName` and removes its local component. For unremapped
relative names, `local_path()` returns the relative name, not its separately
stored working directory. External-source loading reads that path in the
downstream working directory. Merely copying rust-src into package06 cannot
repair these serialized names or its compiler's missing prefix constant.

## Native compiler and std: a new production build

Use the proposed `bootstrap-production-source-paths.toml` with the existing
production-profile plan. Its path-repair addition is exactly:

```toml
[rust]
remap-debuginfo = true
```

For the truthful source commit `C=73a11f167216d3955c277ed47f9b8cc68208105b`, stock
bootstrap then does all of the following; do not manually impersonate the public
base commit in these values:

| Bootstrap input or generated setting | Value / purpose |
| --- | --- |
| Cargo root | `-Zroot-dir=<owned Rust source root>` |
| Compiler environment | `CFG_VIRTUAL_RUST_SOURCE_BASE_DIR=/rustc/C` |
| Compiler environment | `CFG_VIRTUAL_RUSTC_DEV_SOURCE_BASE_DIR=/rustc-dev/C` |
| Native std Cargo environment | `__CARGO_RUSTC_BOOTSTRAP_WS_REMAP=/rustc/C` |
| Compiler Cargo environment | `__CARGO_RUSTC_BOOTSTRAP_WS_REMAP=/rustc-dev/C` |
| Both Cargo modes | `-Ztrim-paths --config profile.release.trim-paths='all' --config profile.dev.trim-paths='all'` |

Capture the actual expanded environment and Cargo/rustc commands, not just these
expected values. Cargo's exact relative-member rule maps `library/core` to
`/rustc/C/library/core`; an absolute-only Rust flag would leave the pinned
relative `RealFileName.name` problem unresolved. Cargo also handles registry,
build-output and installed-sysroot paths; retain its stock order and behavior.

Rebuild the complete matched stage2 compiler/native std/rustc-dev components in
the new owned directory. Keep the compiler source patch and qualified CI LLVM
fixed. Build with at most two jobs and existing disk/lock admission. Package the
verified full rust-src tree at `lib/rustlib/src/rust/library` and rustc-dev's
matching source layout. Retain the exact CI `rust-objcopy` support tool and loader
closure from the package06 process. No stage1, old driver or old native std
component is substituted by presumed compatibility.

This is necessarily a rebuild for the supported repair. Changing a launch-time
`CFG_*` environment variable does not change a baked `option_env!` constant.
`-Zsimulate-remapped-rust-src-base`, broad relative-name file-loader fallbacks,
metadata-byte rewriting, or source aliases placed inside application directories
are not this plan. Ordinary remap-aware compiler decoding and its existing
source-content hash check supply the source text.

## Prepared std MIR: new policy, metadata and source publication

Introduce a separate preparation policy, proposed
`metadata-sysroot-v2-source-paths-release-backtrace`. Retain the current required
MIR flags, release/backtrace features, checking, dependency selection and profile
semantics. Do not mutate or reuse v1 ready directories.

Let `W` be the new owned std-work directory, with the unchanged source snapshot
layout `W/library`, and let `C` be the selected compiler's recorded full commit.
The exact new setup command recipe is:

```text
cargo +nightly-2026-09-08 check
  --manifest-path W/library/Cargo.toml -p sysroot --release
  --target HOST --features backtrace --locked --offline --jobs 2
  --target-dir W/target -Zroot-dir=W -Ztrim-paths
  --config profile.release.trim-paths='all'
  --config profile.dev.trim-paths='all'
```

Use structured argv; the displayed quotes denote TOML strings, not literal shell
quoting to pass through another shell. Custom-compiler selection retains the
existing exact `RUSTC`/loader environment. Setup environment retains:

```text
RUSTFLAGS=-Zalways-encode-mir=yes -Zforce-unstable-if-unmarked
__CARGO_RUSTC_BOOTSTRAP_WS_REMAP=/rustc/C
```

The explicit root is `W`, not `W/library`: relative inputs then begin with
`library/`, matching the native bootstrap scheme. Cargo's member rule generates
the required relative and absolute mappings. This internal Cargo contract is
permitted only for the recorded pin whose source implements it. Reject a
missing/unknown compiler commit, incompatible Cargo identity, ambient trim/root
overrides and conflicting encoded Rust flags. Do not set `CFG_*` at std setup
and assume it changes the already-built compiler.

The example uses the task's two-job setup cap. The current helper hardcodes four
jobs; parameterize setup concurrency and record the chosen count separately from
the path repair. This is setup work, not a measured warm-build improvement.

After checking the snapshot is unchanged, publish both:

* Metadata at `W/sysroot/lib/rustlib/HOST/lib/*.rmeta`, as before.
* A full materialized copy of the identical verified snapshot at
  `W/sysroot/lib/rustlib/src/rust/library`.

The second tree lets `real_rust_source_base_dir` resolve the overridden sysroot.
Prefer materialized, read-only files with complete source inventory and hashes;
no live directory symlink or source file may escape its recorded owner. The
compiler installer already requires materialized directories. A future prepared
source-link alternative would need exact immutable target/key, symlink text,
resolved identity, target inventory/stamps and relocation checks; it is not
necessary for this repair and is not the proposed first implementation.

The new ready identity must bind compiler key/full version/commit and source
digest, exact Cargo identity, MIR flags, the trim/root recipe and virtual prefix,
policy version, and existing stable-CGU off/on namespace. Represent `W` in the
pre-key recipe as a typed std-work placeholder to avoid a circular key; record
and validate the expanded absolute argv after computing the key. Retain separate
complete inventories for metadata and published sources, with hashes and fast
stamps, owner, snapshot digest, actual command/environment and completed process
receipts. Validate required crates, source files and absence of extras; a blank
inventory must fail. Rebuild both off/on prepared namespaces and all downstream
qualification workspaces from new keys.

## Strict comparison with real compiler output

First require an **unmapped** native and prepared E0080 probe. Every standard
span must already have the correct installed/source-containing-sysroot filename,
nonempty real JSON text where the public diagnostic has source text, and the
same independently verified byte/character coordinates. The compiler's own
`SourceFile::add_external_src` hash check remains intact. This gate proves the
distribution repair; a later display mapping cannot hide missing sources.

For strict cross-installation comparison, the parent approved an explicit equal
**correctness-only** compiler configuration. Map each verified standard-library
root (public, custom native, prepared off and prepared on) to one common absolute
diagnostic namespace `D=/rust-interp-std-source/<full-source-digest>/library`:

```text
--remap-path-scope=diagnostics
--remap-path-prefix=PUBLIC_LIBRARY=D
--remap-path-prefix=CUSTOM_LIBRARY=D
--remap-path-prefix=PREPARED_OFF_LIBRARY=D
--remap-path-prefix=PREPARED_ON_LIBRARY=D
```

Supply the same complete ordered argument list in every compared compiler
invocation. No mapping targets `/rustc/C`, so the decoder's guard against
unmapping std while still building std does not suppress translation. After
translation, `to_real_filename` keeps the actual local filename while changing
only its diagnostic display name; external-source loading reads the local file.

RUSTFLAGS alone with Cargo `--target` does not cover host build dependencies.
Use a generated, owned qualification-fixture `.cargo/config.toml`, copied with
the fixture, containing top-level `target-applies-to-host=false`, `[unstable]`
`host-config=true` and `target-applies-to-host=true`, plus the identical argument
arrays in `[host].rustflags`, `[host.HOST].rustflags` and
`[target.HOST].rustflags`. Cargo prefers an existing `[host.HOST]` table over
`[host]`; explicitly populate the exact selected triple and reject conflicting
inherited host tables/environment. The pinned Cargo supports those flags through
its unstable config table. Clear conflicting ambient Rustflags and record the
exact file/environment. Check verbose argv for
both real native host and guest roles; do not infer coverage from guest success.
Direct native probes receive the identical explicit argument list.

Keep `--diagnostic-comparison=strict`; do not call the preliminary helper's
comparison function, fill `text`, rename JSON fields afterward, drop expansion
frames, deduplicate warnings, or weaken the comparator. Validate raw nonempty
snippets against the verified source bytes before comparing complete structured
records, and retain raw stderr/Cargo diagnostic files. Existing checkout-root
normalization and whole-record sorting remain unchanged.

This deliberately changes compiler diagnostic path presentation only during
correctness tests. `--remap-path-scope=diagnostics` excludes macro, object,
debuginfo, coverage and documentation scopes, so this additional display mapping
must not change `file!()` or proc-macro source-file observables. Native/std
preparation's **all-scope** distribution remap does affect embedded source-path
strings, as the public distribution's ordinary remap does; record the truthful
compiler-specific virtual prefix and qualify those observables. Do not claim
that all path-valued runtime strings from differently located compilers are
identical. No qualification display mapping enters performance measurements or
the default launcher.

## Required controls and release gate

All controls below remain unrun. Use fresh owned attempts under the canonical
lock, at most two jobs, sufficient projected space plus the 8 GiB floor, exact
process receipts and original failed-attempt retention.

1. Retain all current compiler/CGU/native/strip controls for the new production
   artifact. Inspect real native core/std commands for both absolute and relative
   Cargo remap pairs and the correct baked source prefixes. Record compiler,
   bootstrap, LLVM, source, support-tool and all installed component hashes.
2. Unmapped direct native and prepared-sysroot probes must exercise E0080 panic
   expansions into both `core/src/panic.rs` and `std/src/macros.rs`. Check cold,
   edited span position and restored source histories, bytes/Unicode columns,
   complete expansion-chain snippets, correct rejection and no stale guest run.
3. Validate source publication and integrity failures without changing any live
   immutable installation: use separate disposable copies with a missing source,
   changed byte, wrong source root, duplicate/missing metadata and an escaping
   link. The publisher/loader must fail closed; full presentation cannot pass
   using `text=[]`. Restore ordinary successful histories afterward.
4. Run the existing complete custom-compiler integration in strict mode with
   the equal diagnostic-only configuration. Cover host and guest uncalled type,
   borrow, lifetime and constant errors, real native build scripts/proc macros,
   edit/restoration, exact selected bytecode and every structured diagnostic.
   Expected presentation-gap count is zero; preliminary integration03's passing
   mechanism verdict and 18 retained gaps are not reused as strict evidence.
5. Add native and exported `file!()` plus proc-macro span/file controls before
   and after applying only the qualification display mapping. Check ordinary
   application files with std-looking relative names to prove no file-loader
   alias substitution exists. Repeat unmapped probes from a second owned
   installation prefix to establish source lookup is independent of build cwd.
6. Freeze fresh compiler/tool/std/workspace keys, then run stable-CGU off/on
   within the same production compiler/profile and unmapped measured policy.
   Profile changes, source-path repair, two-job setup and cold/setup durations
   receive no credit as CGU-grouping gains. No final timing or adoption claim
   precedes successful strict qualification.

## Pinned source anchors

| Source | Contract |
| --- | --- |
| Rust `src/bootstrap/src/core/config/config.rs:1567` | remap default is false |
| Rust `src/bootstrap/src/core/session.rs:963` | truthful `/rustc/` and `/rustc-dev/` prefixes |
| Rust `src/bootstrap/src/core/builder/cargo.rs:955,1160` | root-dir, trim flags and baked decoder environment |
| Cargo `src/compiler/trim_paths.rs:34,65,176` | bootstrap env, all-scope flags, relative-member and absolute rules |
| Cargo `src/util/workspace.rs:128` | compiler cwd and relative source argument under root-dir |
| Cargo `src/compiler/fingerprint/mod.rs:1653` | active trim policy and bootstrap prefix enter the profile fingerprint |
| Rust `compiler/rustc_metadata/src/rmeta/encoder.rs:562` | pinned source-name serialization |
| Rust `compiler/rustc_span/src/lib.rs:394,477,2292` | local name, metadata update, content-hash-checked source loading |
| Rust `compiler/rustc_span/src/source_map.rs:1096,1230` | source loader and retained local name after diagnostic remap |
| Rust `compiler/rustc_session/src/config.rs:1378,2960` | scope parser and source root under effective sysroot |
| Rust `compiler/rustc_metadata/src/rmeta/decoder.rs:1702,1722,1834` | virtual-prefix guards, local source translation, user remap |
| Cargo `src/compiler/build_context/target_info.rs:795,906` | explicit-target host flags use host configuration |
| Cargo `src/context/target.rs:83,101` | unstable host gating and triple-specific table precedence |
| Cargo `tests/testsuite/config.rs:1235`, `rustflags.rs:1662` | unstable config table and host rustflags controls |
