# Qualified Oxc native auxiliary tools

The private Rust 1.98.1 toolchain now has a separately recorded complete copy
with every file from its matching official LLVM-tools component. Its original
65,977 files retain their exact bytes and modes; the component adds 15 files.
Rustc and Cargo retain their original executable hashes and version output.
The original installation is unchanged. No application profile, feature, test,
strip flag or loader environment was changed to repair the missing provider.

The official archive SHA-256 is
`9b68ac31be7c6d25a08ce34dbd2c1d026b8006905e74415b6d9576678379ecbc`.
Its host `libLLVM.dylib` is byte-identical to the original top-level provider,
SHA-256 `6f65eb3fd2cef5fa962c20b0520ee91a393b15bbe8b19b46d363d791b6bab028`.
The acquisition validated all archive members and the complete installation
manifest before any composition. The custom rustup link points at the new
private prefix; an external composition ledger records the added payload.
Original installer bookkeeping is preserved, rather than claiming rustup
installed this component into the original toolchain.

The first composition attempt is retained as a failure. All 25 children
returned zero without stderr, and direct `rust-objcopy --strip-debug` removed
the debug sections from a real compiler-generated object. The controller then
incorrectly expected an intermediate rlib to have been stripped. The exact
compiler source routes rlibs around native linking; its Darwin final-executable
branch explicitly invokes `rust-objcopy`. [Rust source](https://github.com/rust-lang/rust/blob/48a229ceaefd4985c50990b14116b6d856af0985/compiler/rustc_codegen_ssa/src/back/link.rs#L1168)

A separately frozen continuation used the saved installation without copying,
downloading or modifying it. All 24 children passed without stderr: eight
compiler/Cargo identity probes, a compiler-driven stripped executable returning
42, and fourteen final loader probes. The rustc, Cargo and actual rust-objcopy
closures matched the earlier probes. Complete original and composed inventories
matched before and after. The failed fixture and successful continuation have
separate terminal receipts and raw evidence.

These are toolchain qualification controls, not application performance
measurements. A fresh native Oxc target must still repeat the complete selected
test crate and six-state edit history without warnings. System dyld libraries
are tied to the recorded uname build; recorded SDK/provider selection does not
claim a full SDK byte inventory.

The stages use the canonical lock with a 600-second wait and 16/9/8 GiB
entry/stop/floor. The archive retains 360 ordinary members, 59,713,133 logical
bytes and 12,978,800 compressed bytes. Every member, gzip CRC and EOF was read
back. Large acquired payloads and external executor copies remain in their
owned paths, bound by the retained complete inventories and hashes.

- Archive: `f3bf160d9f704787628d49bf80b022939a99c07cb5b3edc0e8da7a6ed7e3067e`.
- Manifest: `0b2c977676aff73a15fab8002540a23940a7aabfea2827604f2766423fab9eee`.
- Retained failed composition: `809e89116cdd95e6839153f954775d66280c8b75457233ce940928a6cd431510`.
- Qualified continuation: `0bd57aa5e0bcf665a9a6b585011f57c90b80708323384c402f38f5653e926fce`.
- Independent verification: `1ab6249fcde504ff375996c531f5119a1d2550078edf38947a449aea23df1a10`.

No frozen holdout was inspected. The Nushell acceptance gate and interpreter/JIT
compatibility remain separate.
