# Oxc clean native development history

The complete upstream `oxc_linter` library-test crate passed the fixed plugin
normalization history without compiler, loader or debug-stripping warnings.
All three unchanged tests passed for the original source, three cumulative
production refactors and the restored source. The intentional wrong-prefix
edit produced all three genuine assertion failures. All 64 supervised children
completed as expected, and the source was restored byte-for-byte.

Oxc remains pinned at `4d5c812d6b16c23fa71d106cf87f7f20ddee69b1`, using its
actual upstream Rust 1.98.1 toolchain, unchanged Cargo profiles/default features,
two Cargo jobs and default libtest scheduling. The fresh native target uses
the separately qualified complete toolchain copy with its checksum-pinned
official LLVM-tools component. Rustc and Cargo retain their original hashes
and version output; the original installation and earlier warning-bearing
run are preserved. [Toolchain qualification](../oxc-native-toolchain-01/README.md)

This is a useful warm application rebuild case: for every changed and restored
state, Cargo reported only the `oxc_linter` library-test target as newly compiled
(`fresh=false`); its dependency artifacts were fresh. It therefore avoids the
Nushell edit path's native host `nu-protocol` dependency rebuild. These observations
qualify the native side of this development case. Interpreter/JIT compatibility
and a repeated performance comparison remain unqualified.

## Diagnostic observations

The table records whole-child elapsed times from one complete history. Each
production edit is a distinct state, not a repeated sample of one workload.

| Source state | Seconds | Result |
| --- | ---: | --- |
| Cold complete-crate discovery build | 62.183 | Clean build |
| Original, already built during discovery | 0.192 | 3 pass; `fresh=true` |
| Wrong prefix | 8.078 | 3 assertion failures |
| Scoped production refactor | 11.918 | 3 pass |
| Cumulative unscoped refactor | 11.757 | 3 pass |
| Cumulative borrowed branch refactor | 8.326 | 3 pass |
| Restored original source | 11.802 | 3 pass |

The 0.192-second observation contains no source edit and does not satisfy the
0.5-second edited-build target. The production edits take 8.326–11.918 seconds
with native Rust in this history. The complete native test executable is
107,592,208 bytes. No source extraction, easier test subset or reduced build
setting was substituted.

Full source, registry, original toolchain and composed toolchain inventories
matched before and after. SDK selection and all rustc/Cargo/rust-objcopy loader
closures also matched. The stage used the canonical lock with a 600-second
wait and 24/9/8 GiB entry/stop/floor. System dyld libraries are tied to the
recorded uname build; SDK/provider selection does not claim a complete SDK
byte inventory.

## Evidence

`evidence.tar.gz` contains 506 ordinary members, 44,397,565 logical bytes and
8,350,249 compressed bytes. It preserves the final source/plan/launch, all child
and outer receipts, raw streams, complete Cargo artifact events, test assertions,
source-state hashes, compiler/SDK/loader identities and independent reconciliation.
Every member and gzip CRC/EOF was read back. Native build and acquired payloads
remain in the owned workspace, bound by complete inventories and hashes.

- Archive: `f910f71b7c19333eda5c418588c4ba33033c0c94f63805d747168ef5fb160702`.
- Manifest: `bccf0118757833c46235f7629f27ed1a110d04346e847c438050230ed1bedf59`.
- Native receipt: `8c4e6b26f69e3834f5c256ff9bddf6c8aae8b5d3474fb5218e38cef372cf53c9`.
- Independent verification: `53809e3dd06226b73ab194922621d9124587ed578d244e6d3859e38d36183925`.

No frozen holdout was inspected. The original Nushell acceptance gate remains
unchanged.
