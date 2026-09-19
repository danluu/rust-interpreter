# Cache the immutable incremental option hash

This candidate was derived from compiler commit
`7efc0d9484da82cd327deb3b48616f8ec81eaf8d`. Its private compiler build and direct
crate tests passed; see [the build evidence](../../results/hir-options-hash-build-02/README.md).
Application performance remains unmeasured, and the candidate has not replaced
the installed application runtime.

`artifacts-01/candidate.patch` adds a private `OnceLock<Hash64>` to
`GlobalCaches`, a `TyCtxt::incremental_options_hash()` accessor, and replaces
the per-body calculation with that accessor. The existing
`.as_u64().encode(&mut encoder)` stays byte-for-byte unchanged. Encoding a
`Hash64` directly would change the wire representation and is not part of this
candidate. The option hash remains the complete `dep_tracking_hash(false)`.

`GlobalCtxt` borrows `Session` immutably for its entire lifetime; its default
caches are recreated for each context. Public `Options` can be cloned and
mutated before compilation, so the cache is neither inside `Options` nor
process-global or keyed by a potentially reused pointer. `OnceLock<Hash64>`
supports concurrent access and already has a compiler precedent in the
single-key query cache. The initializer only hashes immutable values and
does not enter queries. Initialization remains behind the existing body
eligibility checks, so unused caches never calculate the hash.

The pinned implementation builds three option maps, with 24, 34, and 164
entries, on each call. For N accepted body preparations this candidate replaces
N complete hash calculations with one calculation and N cache accesses. That
static observation is not a timing result or evidence that the 0.5-second
target has been reached. The repeated body walks, serialization, JSON
checksum checks, Current/tree/journal validation, materialization, and hit
recapture/poststate audits are all unchanged.

`prepare.py` reads exact Git blobs and retains their SHA-256 hashes and Git
object IDs. It generates two candidate source files and the patch. `verify.py`
checks those bytes and applies the patch only to a fresh two-file scratch copy
under this experiment owner's `.work`. Neither command builds or executes
compiler code. `source-verification.json` records that limited check.

The patch intentionally retains the historical source identity as an input
reference. **Before any compiler build**, a separately reviewed source
qualification must regenerate `SOURCE_IDENTITY` from the complete inherited
source closure plus the changed context file. Do not apply this two-file
semantic patch directly to an installed compiler or present its old source
identity as qualification of the candidate. See [QUALIFICATION.md](QUALIFICATION.md)
for the qualification design. Completed stages are recorded separately in
`results/`; a successful compiler build alone does not qualify an application
installation or establish a performance gain.
