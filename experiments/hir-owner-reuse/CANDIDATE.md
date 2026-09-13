# Opt-in source candidate

`reuse-hir-owners.patch` is generated against exact source commit
`58e1e1f5311f4424ea81def4763081f6da62d9b3`. `patch.json` binds every original and
replacement file and every candidate input. The compiler checkout was read only.
No compiler was built, no test was run, and the patch has not been applied there.

The patch adds `-Zreuse-hir-owners=yes` (default false, tracked), the closed gate
from the feasibility spike, complete capture/materialization for that subset,
fallible record loading, storage, five unit controls and a run-make history.
Unsupported input takes the original lowerer. Cache damage, invalid IDs, unknown
fields, version/key/checksum mismatch, unavailable storage or unsupported output
cannot become a hit. The entire record is checked before constructing the fresh
lowering context. Materialization has no fallible lookup or query feed; its unwraps
are confined to values already checked by the private `CheckedTree` constructor.

`with_lctx` always creates the normal context, including the ordinary disambiguator
steal, then uses a checked tree or invokes the original closure once. Both paths
run the original `into_owner_info`, hashes, HIR indexing and subsequent compiler
checks. A miss is publishable only with no generated definitions, generated AST
IDs, attributes, delayed lints, child owners, trait-map output, opaque data or
transient impl-trait state. Failed output capture keeps the existing stock result.

Sidecars are flat files in `tcx.incr_comp_session.session_directory`. The pinned
incremental implementation copies/hard-links these files into its private locked
working session (`persist/fs.rs:364`), removes incompatible session contents
(`persist/load.rs:217`) and publishes only a successful compilation
(`persist/fs.rs:296`). Writes use create-new temporaries and rename, preserving
old hard-linked inodes. No global cache or separate persistence daemon is added.

The full encoded key includes normal `cfg_version`, the tracked-options hash,
the codec's own source digest, and the complete current expanded/resolved input.
Version overrides are conservatively unsupported. This follows rustc's ordinary
compiler/session compatibility contract; immutable installation proof remains a
separate experiment prerequisite. It adds no whole-compiler binary rehash loop.
The payload is a closed serde record using existing pinned compiler dependencies,
with serde_json's normal recursion cap, a 2 MiB byte limit, owner/node/depth/string
limits, exact key comparison and an integrity fingerprint. It neither catches
compiler panics nor substitutes diagnostic text. Parsing, key checks, codec work,
cache reads/writes, source lookup, allocation and hash/index regeneration all stay
inside the compiler command.

The prepared unit tests cover malformed JSON, unknown fields, wrong keys/checksum,
invalid and duplicate IDs, UTF-8 span boundaries, oversized records, unavailable
storage, and preserving an old hard-linked cache inode. The run-make history
requires actual hits on an unchanged arithmetic function across fresh body edits
and Unicode source shifts; compares native off/on execution; changes a primitive
name's resolution to an application type; exercises attributed/generic/lifetime/
closure/macro fallback; compares complete raw JSON diagnostics for uncalled type,
move, const and constant-panic errors; compiles restorations; corrupts sidecars;
and changes a tracked compiler option. They are prepared, not passing evidence.

The first qualification is a reviewed fresh compiler source commit, then a
canonical-lock build and the owner module's unit tests, the unstable-option hash
test and `tests/run-make/reuse-hir-owners`. Actual build/API errors remain possible
until that compile. The patch must also pass the existing workspace/exporter and
strict diagnostic/source-map controls before application screening. A new compiler
source commit requires its own truthful `/rustc/<commit>` identity and installation;
the existing Cmono compiler, tools and measurements cannot be relabeled.

`-Zincremental-info` adds per-owner `hit`, `miss`, or `rejected-input` records with
item kind and function name for qualification/coverage inspection. Aggregate these
by item kind and separately inspect rejection families before another performance
claim. The initial gate has real ordinary parser inputs (attribute-free parsing
uses `ForceCollect::No`), but scalar-local-only coverage is expected to be limited.
Nonlocal types/calls are deliberately excluded. Expanding them requires current
`DefPathHash` rebasing, exact resolver data, and explicit exclusion or replay of
legacy const-generic/delegation/query-sensitive lowering paths. This patch does
not save parsing, macro expansion, resolution, or the mandatory HIR indexing pass.
Whether its extra key/codec work saves time is unmeasured.
