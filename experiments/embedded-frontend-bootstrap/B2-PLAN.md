# Fresh sysroot with the beta auxiliary-tool dependency

This is a source proposal. No new metadata inspector, assembly, auxiliary probe,
compiler build, or compositor test has run. The original B334, its manifest,
completed stock smoke and Cargo-produced binaries remain unchanged.

The saved Cargo005 exited zero, but its stderr contains 13 strip warnings and
13 dyld missing-library errors. The beta `rust-objcopy` searches
`lib/rustlib/aarch64-apple-darwin/bin/../lib/libLLVM.dylib`; the original complete
beta archive library payload supplied LLVM only at `lib/libLLVM.dylib`.
Cargo's exit status therefore does not establish a successful strip build.

The retained beta archive contains the exact provider, SHA-256
`0d514b73a257a599a433ea7076945639c326cb8483cb06d0dae91d7ceebd842a`.
Pinned `dist.rs:2534–2544` selects unversioned LLVM on Darwin, and
`dist.rs:2743–2747` explicitly places it in the target library directory for
auxiliary tools' `../lib` rpath. E's different LLVM is not a substitute for this
beta dependency. `B2-PROPOSAL.json` binds the prior plan/manifest/Cargo receipt,
original archive/member identities, these source files, and the fresh paths.
Those are retained proof reads; this proposal has not re-opened either archive
or inventoried any live compiler artifact.

The source extension adds optional `archive_copies` to `inspect_inputs`:

```python
archive_copies=[{
    'source_destination': 'lib/libLLVM.dylib',
    'destination': 'lib/rustlib/aarch64-apple-darwin/lib/libLLVM.dylib',
}]
```

Each source must be an original selected ordinary archive member. Every
destination still passes the independent file/directory collision check, even
for identical bytes. Chained copies and duplicate destinations fail. The
complete plan records these explicit mappings; assembly rejects an unrecorded
repeated member before creating output. Assembly groups a member's destinations
and separately copies and hashes every output to a fresh inode. The existing
per-MiB capacity checks, exhaustive output manifest and final input rechecks
remain in effect. Calls without copies preserve the original plan schema and
behavior. Two new synthetic controls exercise real tiny archive assembly with
two destinations and independent inodes, plus collisions/chains and unrecorded
duplicates. All eight original controls remain; all ten are unrun here.

The metadata-only successor must first retain the exact failed Cargo history
and original B/source/runtime proofs. It must revalidate the existing complete
stamp/producer association, both beta archives and all private inputs using
the prior stock runner's guards, then call this successor `inspect_inputs`
with the single mapping above. Freeze the entire resulting plan and the actual
source/SDK/loader/configuration closure before assembly admission. It may
inspect the original auxiliary binary's Mach-O dependency/rpath declarations
with retained tool commands, but it must not execute the known failing helper
as a substitute for a new B2 proof. This document and proposal JSON are not a
materialized assembly plan or a passing metadata receipt.

Future assembly uses only fresh independent directories named in the proposal.
The expected payload is 335 files / 1,055,383,020 logical bytes, including the
additional 143,503,040-byte beta LLVM copy; the historical metadata proof set
adds 121,803,811 bytes. These are payload observations, not a peak allocation
bound. Entry16GiB, active9GiB stop and8GiB floor remain unchanged. Do not use
hardlinks, symlinks, in-place repair of B334 or cleanup of historical inputs.

After separately approved assembly, static Mach-O closure inspection and an
actual `B2/.../bin/rust-objcopy --version` with retained dyld output must prove
that the helper loads the new beta LLVM copy and no unexpected non-system
library. A real strip operation on a fresh owned debug-bearing file is also
required; neither a successful version probe nor an empty/no-op output proves
stripping. Preserve before/after file and debug-section evidence. Source-level
`link.rs:1530–1534` identifies Darwin's `--strip-debug` route; the actual D
invocation remains the final authority for the downloaded beta compiler.

Any later exporter rebuild needs a new compiler-role binding naming B2's new
manifest, a fresh target, full raw Cargo output including all verbose rows,
and explicit absence of strip failures. Keep `-Lnative=E/lib` and the runtime
rpath unchanged. Pinned `link.rs:144–201` places explicit native search paths
before the target-lib LLVM fallback, but actual linking and loaded-library
proof must establish that the exporter still uses E's driver/LLVM while the
auxiliary tool uses beta LLVM. Repeat the unchanged frontend compatibility
controls on the newly built binaries. Existing binaries keep their original
B334 association, including the failed strip tooling. No publication or
performance qualification follows from this source change.
