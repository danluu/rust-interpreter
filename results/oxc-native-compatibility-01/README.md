# Oxc native test history, with unresolved stripping warnings

The complete upstream Oxc library-test crate compiled using its installed
Rust 1.98.1 toolchain, unchanged profiles/default features, two Cargo jobs and
default libtest scheduling. All three unchanged plugin tests passed in the
original, three cumulative production edits and restored source states. The
wrong-prefix edit produced all three genuine assertion failures. The final
source was restored byte-for-byte. All 56 supervised children completed with
their expected statuses; every changed and restored Cargo artifact was newly
compiled (`fresh=false`).

**Clean native performance remains unqualified.** Seven Cargo stderr streams
contain `rust-objcopy` debug-stripping failures. The actual freshly installed
tool cannot resolve `@rpath/libLLVM.dylib` at its auxiliary host-library path.
There are eight unique reported dyld process IDs; Cargo replays the two cached
proc-macro warnings in later commands. No strip/profile flags, application
source, loader environment or toolchain files were changed to suppress this.
The tests pass despite the warning, so the controller's passing semantic result
does not establish a complete clean native toolchain.

The ordinary rustc component contains both the 242,128-byte `rust-objcopy`
(`a7a547d50b4f643710e30238f451b355514cdcf819bd1d3b3e0d6264fca9a121`)
and a top-level 139,564,208-byte `libLLVM.dylib`
(`6f65eb3fd2cef5fa962c20b0520ee91a393b15bbe8b19b46d363d791b6bab028`).
Its host-library location lacks that dylib. The saved matching distribution
manifest advertises the official LLVM-tools component; a separate bounded
acquisition/inspection stage is being prepared. The original installation and
this result remain unchanged. A clean follow-up must validate ordinary debug
stripping on a real object and repeat the complete case with preserved compiler
bytes/version and application settings.

## Diagnostic observations

These are one history's whole-child elapsed times, with stripping failures.
They are retained setup observations, not a clean benchmark or a speedup claim.

| Source state | Seconds | Result |
| --- | ---: | --- |
| Cold complete-crate discovery build | 61.534 | Build completed with warnings |
| Original, already built during discovery | 0.292 | 3 pass; `fresh=true` |
| Wrong prefix | 7.991 | 3 assertion failures |
| Scoped production refactor | 11.616 | 3 pass |
| Cumulative unscoped refactor | 11.325 | 3 pass |
| Cumulative borrowed branch refactor | 7.875 | 3 pass |
| Restored original source | 11.571 | 3 pass |

The already-built original observation contains no source edit and does not
satisfy the 0.5-second edited-build target. The complete native test executable
is 108,191,592 bytes. This development case is unchanged; no easier test subset
or source extraction was substituted.

The stage used the canonical lock (600-second admission), 24 GiB entry,
9 GiB capacity stop and 8 GiB running floor. Native target allocation ended at
2,508,173,312 bytes, evidence at 40,337,408 bytes and shared free space at
53,657,907,200 bytes. Full source/registry/toolchain inventories, compiler
identities, SDK selection and rustc/Cargo loader closures matched before and
after the history. The loader closure covered rustc/Cargo, not the auxiliary
stripping executable; that limitation is now explicit. System dyld-cache
libraries are tied to the recorded uname build, and SDK settings/provider
selection is recorded without claiming a complete SDK byte inventory.

## Evidence

`evidence.tar.gz` contains 286 ordinary members, 29,295,709 uncompressed bytes
and 5,111,043 compressed bytes. It preserves the frozen source/plan/launch,
source-state hashes, all child and outer receipts, complete Cargo artifacts and
raw streams (including every warning), SDK/loader comparisons, independent
reconciliation and the saved distribution/provider diagnosis. Native target and
acquired payload bytes remain in the owned workspace. Every archive member and
gzip CRC/EOF was read back.

- Archive SHA-256: `ab75c7937f3f40f2bab3dcdf325a855c584c2ffd2055bfca202c14256fa6410e`.
- Manifest SHA-256: `2fe3d9b4d6a30f98a5de7855714f559773026860fe6c127c5fdcc973e44da3d4`.
- Native receipt SHA-256: `2528b14df331738b6064c11f1de603ac8f0648ecdd722ac6b6294ca34d036c4c`.
- Independent verification SHA-256: `03fcbd7365771320fd4cb6c59cd1f09153d6caf8fd047847cb3ad7fb6e6b7fd9`.

Interpreter/JIT compatibility and the original Nushell acceptance gate remain
separate. No frozen holdout was inspected.
