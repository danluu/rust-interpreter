# Source audit of the cached calculation

The candidate memoizes the value of `Options::dep_tracking_hash(false)` for
one immutable `GlobalCtxt`. For compiler commit
`7efc0d9484da82cd327deb3b48616f8ec81eaf8d`, the audited hash path reads stored
option values only. It does not read files, environment variables, the current
directory, a symbol interner, or mutable thread-local state while hashing.
This is a static source finding; the Rust qualification controls remain unrun.

The exact source references and hashes are retained in
`purity-01/source-references.json`. The existing patch/manifest and original
source verification were preserved unchanged. The additional hasher source
copies come from the already cached crate archive; its complete SHA-256 matches
the compiler's pinned Cargo.lock checksum.

## Complete option-hash dispatch

`compiler/rustc_session/src/options.rs:265` creates a fresh sorted map of
references to tracked top-level fields, hashes it, then hashes the codegen and
unstable substructures. Their analogous generated implementation is at line 588.
The macro definitions at lines 42 and 52 select fields based only on their
compile-time marker and the supplied `for_crate_hash` boolean. The false case
includes all `TRACKED_NO_CRATE_HASH` values. No parser/default constructor is
invoked during hashing.

The entire `dep_tracking` module is in
`compiler/rustc_session/src/config.rs:3327`. Its `stable_hash` at line 3555
iterates the supplied map and hashes each fixed field label and referenced
value. Its nontrivial implementations are exhaustive:

| Implementation | Inputs consumed |
| --- | --- |
| `Option<T>` | Stored discriminant and contained value |
| Pairs and triples | Fixed positional tags and each stored member |
| `Vec<T>` | Stored length, index and each stored element |
| `FxIndexMap<T,V>` | Stored length and entries in existing order |
| `OutputTypes` | Stored map length, output kinds and, for the false variant, stored output paths |
| `impl_dep_tracking_hash_via_hash!` | Delegates to the listed type's ordinary `Hash`, not rustc's context-dependent `StableHash` |

`error_format` is passed through but none of these implementations consults
external state through it. The two substructures use this same dispatch.
The current tracked option families contain primitives, owned strings/paths,
plain enums/bitsets/structs, and the containers above. The audited declarations
have 24 top-level, 34 codegen and 164 unstable tracked entries. Notable multiline
entries include `Vec<(PointerAuthOption, bool)>` and `split_dwarf_out_dir`.

## Custom and compound ordinary Hash implementations

- `rustc_target/src/spec/tuple.rs:37`: `TargetTuple` hashes its discriminant,
  tuple string and stored target JSON contents. `from_path` reads the file at
  construction time; `Hash` never calls it or reads the file again. The ignored
  rustdoc-only pathname remains ignored.
- `rustc_span/src/lib.rs:327`: `RealFileName` hashes its stored local/remapped
  filename components and scope bits. `was_fully_remapped` only examines the
  scope bitset. `InnerRealFileName` derives `Hash` over three `PathBuf` fields.
  No current-directory lookup or source-map/TLS access occurs in this path.
- `library/std/src/path.rs:2285` and 3797: `PathBuf` delegates to `Path`, which
  hashes the path's own bytes/components. `OsString`/`OsStr` hashing in
  `library/std/src/ffi/os_str.rs:802` and 1661 similarly uses stored bytes.
  This performs lexical path handling, not canonicalization or filesystem I/O.
- `rustc_session/src/utils.rs:23`: `NativeLib` derives ordinary `Hash` over
  strings, `NativeLibKind` and optional booleans. `NativeLibKind` derives Hash
  over its enum and optional scalar modifiers. The adjacent
  `CanonicalizedPath::new` does filesystem work, but is not called by this hash
  path; `externs` and search paths are untracked here.
- `OutFileName`, `SwitchWithOptPath` and `LinkerPluginLto` derive Hash over enum
  discriminants and stored `PathBuf`/optional values. In particular hashing
  `OutFileName::Stdout` does not call `is_tty`.
- The remaining compound configuration values (`AutoDiff`, `Offload`,
  `CodegenRetagOptions`, `InstrumentMcount`/options, `InstrumentXRay`,
  `BranchProtection`/`PacRet`/`PAuthKey`, `NextSolverConfig`,
  `PatchableFunctionEntry`, `PointerAuthOption`) derive ordinary Hash over
  stored enums, numbers, booleans, strings and nested plain values. Defaults
  and compiler feature queries are not invoked by their derived hashes.
- `Align` hashes its stored exponent; `SanitizerSet` hashes its stored bits;
  `RustcVersion` hashes three stored integers. Its separate
  `current_overridable()` environment-reading function is not used by Hash.
  `UnstableFeatures`, lint `Level`, crate/output kinds and the remaining
  target/codegen enum types likewise derive Hash over their stored values.
  `LanguageIdentifier` has a generic dispatch implementation but is not a
  field type reachable from these pinned tracked option declarations.

## Hasher state

`rustc_data_structures/src/stable_hash.rs:18` aliases `StableHasher` to
`rustc_stable_hash::StableSipHasher128`. The pinned `rustc-stable-hash 0.1.2`
implementation constructs an owned `SipHasher128` with fixed keys `(0,0)`
(`src/stable_hasher.rs:124`, `src/sip128.rs:421`). It uses its own initialized
state/buffer and integer operations. There is no random seed, environment
read, TLS lookup or callback into a compiler context. Hash64 conversion keeps
the existing result bits.

Consequently, repeated calculations over the same immutable option values
have the same inputs and result. `OnceLock<Hash64>` changes their frequency,
without caching a mutable query or suppressing a required external read.
This conclusion is specific to the source-bound implementation; a future
change to hash dispatch or a tracked type requires revalidation. The proposed
serial/parallel, changed-option and full replay/diagnostic controls remain
required before this uncompiled source candidate can be qualified.
