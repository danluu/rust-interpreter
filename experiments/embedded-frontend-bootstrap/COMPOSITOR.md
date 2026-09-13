# Beta-built tool with the qualified stage1 driver

This source checkpoint prepares a separate build sysroot. No assembly, compiler
probe, tool build, or eight prepared Python controls have run for this checkpoint.
It does not qualify exporter compatibility or speed. It does not change the
existing stage2-only installed-compiler policy.

The three roles are explicit:

| Role | Input | Purpose |
| --- | --- | --- |
| D | Downloaded beta `SOURCE/build/aarch64-apple-darwin/stage0/bin/rustc`, with its actual default sysroot and loader closure | Compile the private tool |
| B | Fresh owned directory containing the complete beta archive `lib` subtrees plus the full private build stamp | `D --sysroot=B` metadata/link inputs; B needs no executable |
| E | Qualified `SOURCE/build/aarch64-apple-darwin/stage1`, source `7efc0d9484da82cd327deb3b48616f8ec81eaf8d` | Driver embedded by the tool, native standard library for later compilations |

Here `SOURCE` is `/Users/danluu/dev/rustc-hir-capture-check-20260913`.
`INPUTS.json` pins both beta archives, the original successful native005 build,
the source record, pinned bootstrap sources, and all 64 archived E runtime file
hashes. Its 219 saved `--extern` paths (203 rmeta, 8 dylibs, 8 rlibs) are observed
references, not a complete stamp inventory. Actual D version/executable/default
sysroot probes and the current stamp hash remain explicitly pending.

Pinned bootstrap `compile.rs:776–802` supplies the ordinary downloaded beta
libraries for stage0. `RustcLink` at 1508–1568 overlays the full compiler stamp;
`ToolRustcPrivate` at `tool.rs:1360–1440` separates build and target compilers.
`add_to_sysroot` at `compile.rs:2570–2610` routes h to host lib, t to target lib,
and s to target lib/self-contained, preserving each basename. Host equals target
here. All entries matter, including host proc macros, native/debug files, private
rmeta and the special public/bridge/jemalloc rlibs. A library-looking filename
does not prove successful native build ownership.

The entire beta `lib` subtrees retain beta codegen-backends and loader libraries.
Only the exact E driver named by the private stamp is overlaid into B's target
library directory. E's CI LLVM must not replace D's beta LLVM. The exporter
runtime rpath names E/lib; actual loader closure must still be checked. Bootstrap
`compile.rs:2338–2373` describes its driver as statically linking std, while
`cargo.rs:1434–1437` adds prefer-dynamic only for Mode::Std. This recipe does not
prescribe `-Cprefer-dynamic` for a ToolRustcPrivate equivalent. B's beta std and
E's native std are distinct inputs, not interchangeable artifacts.

`compose_sysroot.py` has two callable boundaries and no CLI or subprocess code:

1. The admitted outer runner reads the exact `.librustc-stamp` at
   `build/HOST/stage1-rustc/HOST/release/.librustc-stamp`, retaining its bytes and
   reconciling **every** entry with the saved successful build, complete current
   source state, producer artifacts, and qualified runtime. It passes
   `inspect_inputs(archives=..., stamp=..., approved_private_files=...,`
   `build_compiler=..., runtime_source_commit=..., runtime_driver=..., proofs=...)`.
   Each file record has absolute path, SHA-256 and optional size;
   `approved_private_files` is the complete path -> `{sha256,size}` map.
   `proofs` contains exact small source/build/runtime/qualification metadata to
   preserve. The compositor checks membership, original bytes and identities,
   both pinned archive hashes, archive member safety, h/t/s routing, driver
   agreement, ordinary beta std presence and ambiguous private crate names.
   It rejects any destination collision, including identical-byte collisions.
2. Freeze the returned plan's `encoded(plan)` SHA-256. The admitted runner calls
   `assemble(plan, expected_plan_sha256=..., destination=B, evidence=EVIDENCE,`
   `capacity_guard=...)`. Both directories must be fresh and independent.
   The caller's capacity guard is required before/after each copy and every MiB
   written; enforce the admitted running floor, normally 8 GiB. The outer
   supervisor/owned_stage supplies the canonical bounded lock, initial disk
   admission, source/runtime checks and retained failure receipts. A failure
   keeps partial output; there is no deletion or automatic retry.

The compositor copies ordinary files to fresh inodes, rechecks all inputs, and
hashes the complete output. It emits `private-sysroot.json` in EVIDENCE using the
role-binding `PrivateSysroot` schema, plus the complete input/copy/output proofs.
The final marker says **assembled-unqualified**. All metadata is outside B,
avoiding a manifest self-reference. No current mixed `stage0-sysroot` is read.
Selected archive links, directories used as stamped files, unknown stamp tags,
duplicate destinations and paths outside the two exact stage1-rustc release
roots fail closed. If the real stamp contains legitimate stage1-std or another
root, preserve the exact failure/stamp and revise the recipe after source
review; never silently omit the entry. No stamp or target inventory has yet
established whether that additional case exists.

The smallest subsequent compatibility smoke uses the unchanged pinned
`compiler/rustc/src/main.rs`. It retains `rustc_private`, the stock driver main
and its allocator override. Proposed build shape (not executed):

```text
RUSTC_BOOTSTRAP=1 D --sysroot=B --edition=2024 --crate-name rustc_main \
  SOURCE/compiler/rustc/src/main.rs \
  -C link-arg=-Wl,-rpath,E/lib -o OWN/smoke-rustc
```

The genuine beta compiler needs `RUSTC_BOOTSTRAP=1` for this stock private-tool
source. Version overrides remain prohibited. Invocations of the relocated
`OWN/smoke-rustc` that compile fixtures must explicitly pass `--sysroot=E`, so
their native standard library is E's rather than an inferred adjacent directory.
The outer driver must first probe D/E and bind their actual executable and
loader closures, then retain the actual link command and any missing native
link requirements. The smoke must report E's truthful version, load the exact
qualified E driver, compile an ordinary valid fixture, and produce the same raw
diagnostic for an uncalled type error as E at the same source path and semantic
flags. A real exporter build and separate capability/identity/checking controls
follow only if this succeeds. These probes cannot be replaced by metadata name
rewrites, a fake rlib, a source-fingerprint label, or a version override.

Prepared synthetic controls cover h/t/s routing; malformed, duplicate and
out-of-scope stamps; file/directory collisions; private crate ambiguity;
complete copies and the external manifest; missing membership and postfreeze
mutation before output; archive symlinks; and per-chunk capacity failure. The
tests create only tiny synthetic archives when eventually executed under the
existing canonical test runner. They do not inspect the real compiler tree.
