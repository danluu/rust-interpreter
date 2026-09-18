# Native auxiliary-tool remedy

Native attempt 01 passed the unchanged six-state Oxc test history but produced
`rust-objcopy` loader warnings. Its original Rust 1.98.1 default-profile
installation, complete inventories and warning-bearing native target remain
untouched. No clean performance result is claimed.

The saved Rust distribution manifest, SHA-256
`e44f4ea0a633aa3e497e4dd161424419fbd7bdc203606ef840634fdd22dab9bf`,
advertises the exact official matching component at
`https://static.rust-lang.org/dist/2026-09-03/llvm-tools-1.98.1-aarch64-apple-darwin.tar.xz`,
SHA-256 `9b68ac31be7c6d25a08ce34dbd2c1d026b8006905e74415b6d9576678379ecbc`.
The distribution manifest identifies the archive; its internal payload and
installation manifest must be inspected before composing a new toolchain.

`acquire_llvm_tools.py` and `llvm-tools-acquisition-plan-01.json` admit only
curl identity and this one download. They use the canonical lock with a
600-second wait, 16 GiB entry, 9 GiB stop and 8 GiB floor, a 256 MiB archive
limit, 512 MiB retained allocation limit, and a 1 GiB streamed unpacked limit.
Curl accepts HTTPS only, has a 300-second overall limit and no retry. Inspection
checks the archive SHA, complete ordinary-file/directory membership, collision
and traversal rejection, and exact component installation-manifest membership.
The official component must actually declare the missing host-library
`libLLVM.dylib`. This stage neither extracts nor installs the component.

After that proof, the planned composition is a fresh private complete copy of
the original toolchain plus the official component payload. All original
compiler/Cargo and standard-library bytes, modes and versions must be preserved;
overlapping component members must be byte-identical or composition fails.
A new separately recorded composition identity will describe the complete
component, its provenance and any installer bookkeeping. No replacement of the
original installation, application changes, profile/strip override, custom
loader environment or silent compiler substitution is permitted.

The concrete composition controller and child allowlist are frozen only after
the component membership is known. Proposed bounds are 16 GiB entry, 9/8 GiB
stop/floor, 3 GiB for the fresh copied installation and 128 MiB evidence, again
under the canonical 600-second lock. Identity probes and loader inspection must
include the actual auxiliary stripping executable and its resolved LLVM
provider in addition to rustc/Cargo. A genuine debug object must contain debug
sections before the selected `rust-objcopy --strip-debug` invocation and lack
them afterward. An ordinary compiler-driven strip must also complete without
a loader diagnostic. The checks must retain full commands, routes, bytes,
source/object/output hashes and raw receipts.

A subsequent fresh native target then repeats the same Oxc revision, complete
library-test compilation, original tests, wrong-prefix assertion failures,
three production edits and restored-source tests. Compiler identity and the
complete copied/component closure are checked before and after; all Cargo
streams must be free of the unresolved strip warnings. Cold setup, correctness
controls and future repeated warm-edit observations remain separate. No easier
project/test subset, old edited artifact, disabled strip operation or lowered
build setting can satisfy the target.

The official component acquisition passed. It declares 15 new payload files,
including the missing host LLVM provider. That provider is byte-identical to
the original root LLVM library; its archive-supplied mode is preserved.

Composition attempt 01 preserved every original file and added all 15 official
files in a fresh private prefix. The actual `rust-objcopy` successfully stripped
a real debug object with no diagnostics. The attempt then failed an incorrect
fixture expectation that `-C strip=debuginfo` removes debug information from an
intermediate rlib. All 25 children returned zero, and the failed attempt is
retained unchanged.

The exact Rust 1.98.1 compiler source at commit
`48a229ceaefd4985c50990b14116b6d856af0985` routes rlibs through `link_rlib`,
bypassing `link_natively`. Its Darwin native-output branch explicitly invokes
`rust-objcopy` for `-C strip=debuginfo`. The correct compiler-driven control is
therefore the already-planned final executable. Source bytes and their
provenance are retained; the relevant implementation is
[link.rs](https://github.com/rust-lang/rust/blob/48a229ceaefd4985c50990b14116b6d856af0985/compiler/rustc_codegen_ssa/src/back/link.rs#L1168).

`continue_native_toolchain.py` admits a separate 24-child continuation over the
saved bytes: eight compiler/Cargo identity probes, the final binary compilation
and execution returning 42, and fourteen final loader probes. It validates
the complete original and composed inventories before and after, binds every
prior receipt and raw stream, and retains the successful direct-object check.
It does not copy, install, download or modify the toolchains.

The continuation passed all 24 children without diagnostics. The subsequent
fresh native Oxc history also passed all 64 children and all six source states
without warnings. See [toolchain evidence](../../results/oxc-native-toolchain-01/README.md)
and [clean native history](../../results/oxc-native-compatibility-02/README.md).
Interpreter/JIT compatibility remains a separate next step.
