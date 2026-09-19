# Direct run-make continuation, source proposal only

Status: unexecuted, without a launch or output freeze. This is the next
qualification step for the independent options-hash candidate. It does not
apply the packed-storage or single-Walk patches, establish application
compatibility, or measure edited-build performance.

X is `/Users/danluu/dev/rust-interp-runtime-exporter-20260918`.
N is X/.work/hir-options-hash-compiler-01; S is N/source; B is S/build.
The acquired source commit is
`4de35bdacef0e3cd18a66bc30b5459c19e09b118`.
H is `aarch64-apple-darwin`; D2 is B/H/stage0; E2 is B/H/stage1.
These are source-derived roles, not assertions that their future build
outputs exist or are qualified. `source-bindings.json` records the inspected
source bytes; it is not an admission receipt.

The prerequisite is the actual successful eight-stage compiler build and its
independent verification, including all lowering and interface tests, E2
identity/policy probes, and the final run-make-support build. Keep the original
build evidence immutable. The continuation must use its actual D2, E2, support
outputs, exact bootstrap configuration, private Cargo home, SDK/provider and
source identities. A missing prerequisite cannot be substituted with C, the
installed R compiler, an old support rlib, or a prospective filename.

## Why two direct children

`src/tools/compiletest/src/runtest/run_make.rs::run_rmake_test` always compiles
and executes a recipe. It has no compile-only branch. Do not run compiletest,
`x test tests/run-make/...`, or an exploratory recipe first.

The continuation has exactly two top-level workload children: one recipe
compilation using D2 and one execution of that new recipe using E2 for its
nested compiler calls. The recipe and fixture remain byte-for-byte unchanged.
The second child includes all nested compilations, native test executions,
expected failures, corruption and version-override checks in `rmake.rs`.
Top-level child count is not a claim that only two processes execute.

## Discover actual outputs after the build

1. Bind the passed build terminal, all eight command receipts and full raw
   streams, acquisition and metadata receipts, source commit/full inventory,
   configuration and providers. Reconcile actual support compiler argv with
   D2, its crate source, target, profile, extra filename and output directories.
   Preserve their exact argument order and environment.
2. Bootstrap `ToolBuildResult.artifacts` is populated from Cargo
   `compiler-artifact` messages. The compiletest builder chooses the first
   artifact with basename starting `librun_make_support` and extension `rlib`,
   plus optional `rmeta`. Prefer actual retained messages when available.
   `stream_cargo` forwards these messages only with `json_output`; `-vv` alone
   does not guarantee they are present. If they were consumed, derive the
   uniquely identified support outputs from the actual rustc command,
   dep-info, top-level library and exact completed output membership. Prove
   aliases/uplifts have the same bytes. Reject ambiguity or stale unrelated
   variants; never choose the newest matching glob or rebuild for discovery.
3. Keep separate the support rlib and optional rmeta: embed-metadata=no can
   place them in different directories. The optional flag is allowed only
   when the actual build produced the identified rmeta.
4. Let T = B/H/bootstrap-tools. Enumerate `T/H/release/build` and
   `T/release/build` exactly as `discover_out_dirs`: root entries, their child
   entries, their child entries, then paths ending in `out`. This is not an
   unrestricted recursive search. Record the observed iteration order and
   exact membership; do not silently sort library search order. Fail on
   unreadable entries or indirect/unowned output routes. Retain each selected
   directory's relevant library contents and full hashes/stamps.
5. Separately apply bootstrap's `discover_out_dirs_with_dylibs` to
   `T/H/release/build`: the same depth, selecting `out` directories containing
   an immediate `.dylib` entry. This supplies the base loader search path,
   not all of the `-Ldependency` paths. Bind the exact files and loader closure
   of D2, E2, required support dylibs and the generated recipe, using actual
   current metadata/provider evidence. A new loader uncertainty requires a
   separately reviewed metadata proposal, not extra hidden workload children.
6. Bind the exact source directory membership (currently `rmake.rs` and
   `fixture.rs`) and both hashes. After admission, require a fresh owned base
   directory under N, with the recipe executable outside its fresh
   `rmake_out` subdirectory. Copy all inputs other than rmake.rs as compiletest
   does. Never call compiletest's remove-existing-base operation on an old
   directory. Do not mutate either source file.

Concrete paths, bytes, hashes, loader routes, output allocation reservation,
and the continuation's exact launch will be frozen only after discovery.

## Recipe compilation

One direct argv, using the actual resolved paths above, with cwd S:

```text
D2/bin/rustc
  -o FRESH_BASE/rmake
  [one -Ldependency=PATH per support-host out directory, in observed order]
  [one -Ldependency=PATH per support-host-dependency out directory, in order]
  --extern run_make_support=ACTUAL_SUPPORT_RLIB
  --edition=2024
  S/tests/run-make/hir-body-cache-capture/rmake.rs
  -Cprefer-dynamic
  [--extern run_make_support=ACTUAL_SUPPORT_RMETA]
  -Dunused_must_use
```

The recipe is compiled by D2, which built run-make-support. It must have
`RUSTC_BOOTSTRAP=-1`, exactly as compiletest requires for stable recipe APIs.
No HIR cache flags, instrumentation, extra optimizations, source edits or
alternate compiler wrapper are inserted into this command. The source-bound
normal compiletest `RUSTC_FORCE_RUSTC_VERSION=compiletest` remains present.

## Environment derivation

Start from the explicit actual build environment; remove unintended ambient
compiler flags, wrappers and guest/interpreter overrides. Preserve the
qualified private homes, offline/download rejection, executor PATH,
DEVELOPER_DIR, locale and provider choices. TMPDIR must be a fresh owned
continuation path. Every addition/removal is recorded in the concrete plan.

Bootstrap Python's `build_bootstrap_cmd` mutates a private environment for
building bootstrap. The later bootstrap binary is launched with a fresh
`os.environ.copy()` at bootstrap.py:1412. In particular, do not assume its
private D2/lib loader addition becomes the runtime environment.

Bootstrap `tool_cmd` forms base DYLD_LIBRARY_PATH from the discovered
bootstrap-tool out directories containing dylibs, followed by the original
bootstrap environment's loader paths. The approved build environment omits
DYLD_LIBRARY_PATH; verify this against the actual receipt. It still sets the
variable to the joined sequence for compiletest. The direct recipe compile
inherits this base string. The direct recipe execution splits that string
with Rust path-list semantics and appends D2/lib/rustlib/H/lib. Preserve empty
path-list components: if the joined base is empty, split_paths yields an empty
component. Do not normalize or deduplicate the sequence. All working
directories are owned and frozen/fresh as specified.

The recipe environment follows these source-derived rules:

| Variable | Value or derivation |
| --- | --- |
| RUSTC_BOOTSTRAP | `1` for recipe execution; `-1` only for recipe compile |
| RUSTC_FORCE_RUSTC_VERSION | `compiletest` |
| LD_LIB_PATH_ENVVAR | `DYLD_LIBRARY_PATH` |
| DYLD_LIBRARY_PATH | Exact base sequence plus D2/lib/rustlib/H/lib |
| HOST_RUSTC_DYLIB_PATH | E2/lib, from builder.rustc_libdir(stage1) |
| TARGET_EXE_DYLIB_PATH | E2/lib/rustlib/H/lib |
| TARGET | H |
| PYTHON | Actual qualified bootstrap Python |
| SOURCE_ROOT | S |
| BUILD_ROOT | B/H |
| RUSTC | Actual E2/bin/rustc |
| LLVM_COMPONENTS | Actual qualified llvm-config --components text, trimmed as bootstrap does |
| LLVM_BIN_DIR, LLVM_FILECHECK | Actual selected LLVM provider routes from metadata/build evidence |
| __BOOTSTRAP_JOBS | `2` |
| __RMAKE_VERBOSE_SUBPROCESS_OUTPUT | `1`, explicitly request complete successful subprocess output |
| __STD_REMAP_DEBUGINFO_ENABLED | `1`, matching remap-debuginfo=true |
| __RUSTC_DEBUG_ASSERTIONS_ENABLED, __STD_DEBUG_ASSERTIONS_ENABLED | Absent, matching both false |
| RUSTFLAGS | Absent |
| CARGO | Absent, since this is run-make rather than run-make-cargo |

Also derive the ordinary bootstrap test environment (including
RUST_TEST_TMPDIR, test threads, DOC_RUST_LANG_ORG_CHANNEL and configured
sanitizer flags) from the actual configuration. No bless, remote runner,
MSVC/musl or forced-clang mode is selected. RUSTDOC is supplied by normal
RunMake setup even though this fixture does not call it; its actual route
must be recorded if retained in the mirrored environment. Do not invent a
new rustdoc build to run a fixture that does not use rustdoc.

For non-MSVC, compiletest supplies CC, CXX, AR, CC_DEFAULT_FLAGS and
CXX_DEFAULT_FLAGS. Bootstrap derives flags from the current cc::Tool args,
filters all -O and /O prefixes, then adds its unhandled flags (including
`-stdlib=libc++` for Darwin C++). Values must come from the actual bound
bootstrap/provider configuration and recorded output, not guessed defaults.
The recipe's executed helper subgraph uses only Rustc, native run, filesystem,
and assertions; it does not call C/C++/ar/rustdoc/LLVM helpers. If exact unused
values are unavailable, explicitly omit and document those unused variables
after source review instead of claiming complete compiletest environment
identity. This does not permit omission of the compiler/loader/version fields
used by the recipe.

run_make_support::rustc prepends cwd and HOST_RUSTC_DYLIB_PATH to the recipe's
DYLD list, adds `-L cwd`, and supplies TARGET. Native run prepends cwd and
TARGET_EXE_DYLIB_PATH, then the recipe's DYLD list, and sets LC_ALL=C. The
fixture itself removes RUSTC_FORCE_RUSTC_VERSION for normal histories and
reintroduces empty/nonempty values for its override-rejection controls.
Preserve that distinction; globally removing the override would change the
test contract.

## Execution, evidence and bounds

The second argv is only `FRESH_BASE/rmake`, cwd FRESH_BASE/rmake_out, with
the frozen environment above. Execute it once after the recipe compile and
generated-binary/loader checks pass. Do not rerun earlier compiler tests or
trim the recipe to selected assertions.

Retain stdout/stderr directly to ordinary files. The support library's verbose
path prints each nested command, status and complete output even for expected
compiler failures. Do not route through compiletest's read2_abbreviated, use
terminal snippets as evidence, or assert absence of all compiler errors: the
unchanged recipe deliberately requires type, borrow, const and lint errors.
Its final successful return is required together with source-bound audit of
all phases and preserved verbose output. The actual nested histories and
timestamps are diagnostic qualification evidence, not benchmark samples.

The unchanged recipe tests stock/capture parity, cold and repeated captures,
changed source/spans/traits, reuse/tree/journal/poststate checks, intentional
sidecar truncation, uncalled error and feature/entry context checks, normal
restoration, and empty/nonempty version overrides producing no HIR sidecars.
The continuation audits the observed output against these actual source
assertions. It does not infer global eligible-body coverage from event counts.

Use canonical benchmark.lock with a 600-second admission bound and inherited
lock ownership, existing supervisor and exact fresh child process records.
Preserve X's 24 GiB entry / 9 GiB stop / 8 GiB floor, 14 GiB aggregate N
allocation, and 256 MiB aggregate evidence budget unless an explicit successor
is reviewed. The current bounded_command helper fixes cwd to S and evidence
to the initial build. The continuation needs a narrow reviewed adaptation
that permits exactly S and its fresh recipe output directory, counts both
evidence namespaces, and samples throughout each child. Do not change a
frozen build helper in place. Exact retention/allocation reservations are
chosen from actual completed build size before admission.

Copy/rehash relevant outputs before and after use; distinguish expected
hardlinks within owned build roots from outside aliases. The recipe may alter
only its fresh output namespace. Recheck full source, SDK/provider and compiler
identities around the stage. Capture controller/child PID, parent, command,
cwd, environment, start/end and complete raw hashes. Capacity stopping is
limited to a newly created, revalidated owned process group. Failures retain
all partial files and receipts, with no automatic rerun or fallback.

## Remaining inputs before a runnable packet

- Actual passed eight-stage build, actual D2/E2 outputs and support artifacts.
- Actual ordered out-directory membership and loader closure; no guessed rlib
  hash, driver suffix or dylib filename.
- Actual LLVM component/provider records and exact used environment values;
  explicit reviewed handling of any unused, unavailable compiletest values.
- Actual available space, N allocation and concrete two-child supervision and
  evidence reservation.
- Source/preparer/controller review followed by an exact launch authorization.

No compiler, compiletest, recipe, native fixture or LLVM probe was executed in
preparing this proposal.
