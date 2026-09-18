# Separate native runtime installation

`scripts/runtime_compiler.py` introduces `owned-native-runtime-compiler-v1` in
`.work/runtime-compilers/<key>/sysroot`. It does not change the complete-stage2
policy, its namespace, or any launcher/std-MIR/tool publisher. The first loader
policy supports Darwin, independently of compiler revision or application.

The purpose is to install an already qualified native compiler runtime with
ordinary source-provider files. A separate compiler can later build an exporter
against compatible private metadata while embedding this installed runtime.
Private metadata is not an application sysroot. No private metadata, new compiler
build, exporter relocation, or application qualification is implied here.

For an installed runtime owned by the same checkout, the source-containing std
preparation CLI accepts `--runtime-compiler-key` in place of `--compiler-key`.
It retains the ordinary `--namespace`, `--run-id`, and `--workload-lock` inputs,
exact source-capability requirement and final runtime revalidation. The two
compiler flags are mutually exclusive; no loader fallback or cross-worktree key
lookup occurs. [The 23 focused controls passed](../../results/std-runtime-selection-controls-01/README.md).
Application launcher/exporter integration remains a separate qualification.

The ordinary launcher also accepts the mutually exclusive
`--runtime-compiler-key` with an explicit installed `--tool-key`. Its separate
`owned-native-runtime-tools-v1` composition binds the installed runtime key,
compiler/driver paths and hashes, actual compiler version, and the full
build/runtime role record. Publication must retain matching exporter capability
and `--rust-interp-compiler-roles` wrapper probes through
`runtime_tools.bind_recorded_wrapper`; loading does not invoke another probe.
The runtime exporter still checks the actual loaded driver itself.

This initial route requires stock Cargo and excludes the other compiler routing
experiments. Standard-library MIR requires an explicitly prepared source-paths-v2
key. Neither an installation nor a matching tool manifest establishes application
qualification. [All 45 association, launcher and existing compiler/std controls
passed](../../results/runtime-launcher-selection-controls-01/README.md) with mocked
Cargo/VM children; real exporter publication and application checks remain pending.

## Admission and API

`identity_for(spec)` validates an entirely supplied specification without reading
its paths. It requires:

- `schema_version: 1`, `host`, exact actual `compiler` (`rustc -vV` stdout), and
  `unstable_options: option_proof(actual_help_stdout)`.
- `provenance`: actual `source_commit`, explicit `source_checkout`, and SHA-256
  bindings for `bootstrap_sha256`, `build_receipt_sha256` and
  `qualification_receipt_sha256`. There is deliberately no `stage` claim.
- `components`: exactly one native `runtime` with empty `destination`, plus
  ordinary `source` providers and optional `support` components. Each has an
  absolute `root`, destination relative to the new sysroot, complete `files`
  mapping (`sha256`, byte `size`, ordinary permission `mode`), and `links`. Each source provider
  also binds its `source_receipt_sha256` and a destination below a Rust source
  root. Executable source scripts retain their exact execute/read permission bits and are never
  classified as native images or passed to `otool`. Component input directories have exact full membership; this is not a
  filename search or an arbitrary subset of a larger build directory.
- `loader_policy: darwin-relative-runtime-closure-v1` and `loader`, mapping every
  executable and `.dylib`/`.so` to its ordered `rpaths` and `loads` (pairs of Mach-O
  load kind and path). Those are actual prior admitted declarations, compared
  with fresh `otool -l` results at the final installation path.

Only the runtime component may contain links, and only at
`lib/rustlib/src/rust` and `lib/rustlib/rustc-src/rust`. Each declaration contains
exact `text`, `resolved_target`, `action` (`replace` or `omit`) and nonempty
`reason`. The resolved target must equal the explicit admitted source checkout.
Both text and resolution are checked without traversing the links. Replacement
requires an ordinary provider beneath that destination; omission requires no
installed contents there. All other links fail. A native runtime originally
having no links may also receive ordinary source providers.

The caller must establish that the file maps, source-provider proof and completed
runtime qualification belong together. The module verifies their exact current
bytes and membership; a caller-supplied receipt hash alone is not an independent
verification of that receipt's claims. It never invents a bootstrap source-remap
capability from the presence of copied source files.

`install_runtime_compiler(root, spec, run=..., guard=..., environment=...)` is an
actual installation workload. Its caller holds the existing canonical lock,
binds this module/specification/Python and helper closure, records source guards,
and supervises every `run(argv, environment)` child. The callback returns exact
`{returncode, stdout, stderr}` values and retains the raw outputs and process
receipts externally. A mandatory `guard()` enforces the caller's admitted disk
floor before/after stream blocks of at most 1 MiB and around every probe. There
is no new subprocess, supervisor, lock, capacity or approval framework here.

All source bytes are checked before destination creation. Files are copied into
fresh inodes with exclusive creation. Every destination is then read back through
an ordinary, no-follow descriptor with exact size/hash, nlink=1 and before/after
identity checks, under the per-MiB capacity guard. Only after full readback and
unchanged output stamps may probes begin; input-stream hashes alone do not prove
the destinations. Components and copied files are rechecked before and after
probes. The identity is determined before copying, so the
content-addressed final sysroot path is used for every probe and is never renamed
afterwards. Unknown membership, collisions, changed links/inputs, probe errors,
loader disagreement or capacity failure preserve the partial attempt and external
receipts. An existing attempt is never overwritten or automatically retried.

Completeness requires executable rustc, a unique driver, unique native
core/alloc/std/test/proc_macro rlibs with matching companion metadata stems, and
ordinary standard source roots. It does not require rustc-dev or claim arbitrary
profiles need no auxiliary tools. Supplied rustdoc/support executables are in
the exact inventory and receive their own executable-relative loader context.
This catches, for example, a support tool seeking LLVM in a different directory
from rustc's LLVM. System load edges are allowed; non-system dependencies must
resolve uniquely inside the installation. External absolute rpaths/load edges,
unknown dylib load kinds, non-system dyld and embedded loader environment changes
are rejected. `LC_ID_DYLIB` self names are not load edges. No binary load command
is rewritten. Actual dynamic loading remains a separate native qualification.

Successful installation writes a read-only `ready.json`, native/source tree with only write permission bits removed and read-only installation directory. It records `status: installed` and
`application_qualified: false`. `load_runtime_compiler(root, key)` returns
`RuntimeCompiler(key, sysroot, identity)` only after exact policy/owner/location,
manifest, file/directory identity, permissions and probe checks. Lookup does not
reinspect the original source checkout, hash all installed payloads, or invoke a
compiler. The existing shared inode/ctime/mode checks detect incidental mutation;
this follows the trusted, task-owned immutable-installation boundary, not an
adversarial filesystem model. The API provides `rustc`, `host`, `environment`,
`require_option` and `revalidate`. Environment selection rejects loader/version
overrides and conflicting rustc/rustdoc selection.

## Qualification sequence to prepare next

1. The original thirteen synthetic controls in `tests/test_runtime_compiler.py` passed at
   source `bd2ca683`, through the existing canonical supervisor with exact source
   snapshots. They exercise
   final-root probing, fresh copies, ordinary sources/link omissions, mismatches,
   collisions, native completeness, support-tool rpaths, forged probe proof,
   changed installed bytes, capacity interruption and retained failed attempts.
   The successor adds a fourteenth control that corrupts the copied driver before
   the first output stamp capture and requires rejection before any probe/ready
   record. The destination-readback change passed all fourteen controls at source
   `2c92ae36`; the fresh evidence is `results/runtime-compiler-controls-02`.
2. Freeze a real admitted runtime specification from completed runtime receipts,
   complete current native/source inventories and raw loader declarations. Include
   required support-tool bytes and their actual closure explicitly. Bind the
   ordinary source provider to the exact source commit and prior source proof.
3. In a fresh supervised record, install once with the unchanged capacity floor.
   Retain all actual source/copy/probe identities and failures. Probe final-root
   rustc/rustdoc/support versions and actual dyld images; verify full non-system
   closure and every copied byte. Run native metadata/link/execution, uncalled
   type/borrow/const errors, proc-macro/build-script and native-source diagnostic
   controls with exact ordinary compiler behavior and restored source.
4. Only a later separate tool checkpoint binds/rebuilds exporter and wrapper for
   this final installed runtime (retaining the existing build compiler/private
   sysroot identities). Probe the published tool path and actual loaded driver.
   New std-MIR and ordinary-launcher source/diagnostic/history qualification remain
   necessary. Their success is an external qualified record, not a rewrite of
   this immutable installation or a relabeling of prior original-path evidence.

The original thirteen synthetic controls passed without skips in 0.273s; supervisor
46637/helper46640/test46642 held canonical admission from 1789344515.779358 to
1789344516.1693618. Exact raw outputs, eight source snapshots, frozen manifest and
supervisor/launch records are retained in `results/runtime-compiler-controls-01`.
The historical source/evidence remain unchanged. The readback repair at
`2c92ae36` subsequently passed fourteen controls without skips in 0.325s, under
supervisor41323/helper41328/test41330 with canonical admission
1789345082.696852–1789345083.0905862. Its separate raw/source/launch evidence is
`results/runtime-compiler-controls-02`. Source AST parsing and whitespace checks
also passed. No real runtime copy,
compiler probe, native qualification, exporter rebuild, publication, benchmark
or holdout workload has run. Synthetic passing controls do not qualify a real
compiler installation or application workflow.
