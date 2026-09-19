# Isolated compiler construction proposal

This packet prepares a new compiler from exact commit
`7efc0d9484da82cd327deb3b48616f8ec81eaf8d`. No compiler checkout,
provider acquisition, compiler build or qualification has executed.
The original compiler, its build tree, installed R, B2 and published tools stay
immutable. The candidate is not adopted and has no measured speedup.

`freeze_source.py` derives the acyclic identity from every inherited full source
file plus the modified full `rustc_middle/src/ty/context.rs`. Its output
`source-01/candidate.patch` changes exactly context.rs, body_cache/mod.rs and
body_cache/source_identity.rs. The manifest binds 25 hashed closure files and
the generated identity file, retaining the previous identity independently.

`derive_providers.py` reads the three exact compiler lockfiles and only their
named sparse-index/cache paths. It verifies every available archive against its
lockfile checksum and each locked version against its sparse-index checksum.
The proposal includes 495 package-name index files and 405 archives. All 280
packages referenced by 694 existing C/build dep-info files are included.
The other 203 locked archives remain explicitly absent. Historical consumption
does not prove all future platform/feature selections; any new absent demand
must fail offline, with no automatic retry, fetch or scope reduction.

The source/provider acquisition stage will use a fresh owned namespace,
`X/.work/hir-options-hash-compiler-01`, with source, Cargo home, temporary files
and later B3 all beneath it. It will clone only the exact local compiler and
backtrace repositories, with no hardlinks or alternates; check out the pinned
commits; apply the reviewed three-file patch; and make a new source commit.
All other Git submodules stay unmaterialized. New Git configuration disables
external/global hooks, signing, credential prompts and nonlocal protocols.
The source tree must match its full Git blob inventory before and after the
patch, with full SHA-256 content inventories retained. Existing compiler
source and providers require complete pre/post validation. Parent Cargo
configuration files and source-local configurations are part of admission.

The exact bootstrap file remains SHA-256
`71b495da8fc35ca1321322f56065eb149ecd82fa3c8ff7ef4d4c10ec53f0df9b`.
Six pinned archives are copied to the new build/cache namespace; their sum is
197,096,268 bytes. These provide stage0 and downloaded CI LLVM. No LLVM source
build, fresh download, rustup fallback or replacement compiler is permitted.
The private Cargo home receives only the proposed index records/config and
available lockfile-checksummed archives; it may unpack these during a later
offline build. Shared Cargo state is read only.

Admission uses the canonical 600-second lock, 24 GiB entry, 9 GiB stop and
8 GiB floor. The aggregate new compiler/source/provider/B3/control namespace
has a proposed 14 GiB allocated-byte cap; acquisition uses at most 2 GiB of
that cap. Exact current host/tool/SDK admission and a finite monitored build
controller remain required before compilation. Historical device stamps are
not reused.

A read-only nonfollowing inspection of original C/build at Unix time
1789774931–1789774932 counted 19,313 regular files: 10,346,779,866 logical bytes,
10,397,208,576 allocated bytes counting each path, and 8,696,233,984 allocated
bytes by unique inode. It did not follow five symlinks, including build/host.
The root stamp was unchanged, but this is a current-tree estimate subject to
concurrent drift, not an immutable snapshot, a peak bound or APFS reuse credit.
The main Git tree has 62,696 blobs totaling 225,874,511 bytes, with about 52.9 MB
of Git objects; backtrace and private provider bytes are additional.

The later compiler stage preserves the existing recipe and configuration:

```
./x check --stage 1 compiler/rustc_ast_lowering --jobs 2 -vv
./x test --stage 1 compiler/rustc_ast_lowering --jobs 2 -vv
./x build --stage 1 compiler/rustc library --jobs 2 -vv
NEW_STAGE1/bin/rustc -vV
NEW_STAGE1/bin/rustc --print sysroot
NEW_STAGE1/bin/rustc -Zhelp
./x test --stage 1 compiler/rustc_interface --jobs 2 -vv
```

The lowering crate must retain all 27 existing controls, and the full interface
test target retains the option-hash distinctions. The run-make recipe must
execute exactly once directly, using its newly built support artifacts and an
explicitly derived current build environment. The recipe source and assertions
remain unchanged; stdout/stderr go directly to unabridged files. Do not first
run it through compiletest's known 524,288-byte capture limit and then rerun it.
The exact compiletest-only recipe construction command/environment is a later
review input, not an authorized command in this proposal.

The concrete hash-control driver in `../controls/driver.rs` belongs to a later
stage after fresh B3 qualification. Stage1's native compiler and beta-built
private metadata have different roles: compile this rustc_private driver with
the pinned beta D compiler, a new B3 containing this candidate's metadata and
the candidate runtime driver; never combine the new native driver with old B2.
Then run one serial and one parallel process, eight contexts each, with exact
loader provenance. No installed runtime or tool publication is implied.
