# Oxc native input acquisition

The exact Oxc source and upstream Rust 1.98.1 default-profile toolchain have
been acquired in private task-owned homes. This result qualifies the saved
inputs. It contains no Oxc target build, application compatibility result,
warm-edit benchmark, or 0.5-second claim.

Oxc is pinned to `4d5c812d6b16c23fa71d106cf87f7f20ddee69b1`. The installed
compiler identifies itself as `rustc 1.98.1 (48a229cea 2026-09-01)`, host
`aarch64-apple-darwin`, LLVM 22.1.8. Its actual executable SHA-256 is
`766eda9d8f53afd6fc7f27b3cd2e444dd22afacb5afa710a5625fc8e45b8c941`.
Cargo identifies itself as 1.98.1 at commit `797e8a9bc`, executable SHA-256
`6e17e865f3a20dd55a1d212f849f58b77124179f0de7c52973096d84ba34118d`.
Both probes and actual Cargo commands used the private installed binaries;
every child retains its full environment, command, identities, times and raw output.

The original acquisition attempt completed all twelve children successfully:
exact shallow checkout, upstream default-profile toolchain installation,
compiler/Cargo identification, locked fetch and offline metadata. Its validator
then failed because it expected `.cargo-checksum.json` inside Cargo's ordinary
registry cache. That file belongs to the vendored-directory source convention.
The failed controller, receipt, traceback and all prior outputs remain intact.

A separate reviewed continuation performed no download, extraction, repair or
source edit. All twelve synthetic integrity controls passed without warnings.
All seven continuation children succeeded. The verifier checked all 323
downloaded `.crate` archives against the exact `Cargo.lock`, and compared all
12,804 ordinary archive members with their extracted bytes (145,325,952 bytes).
It rejected traversal, duplicate paths, links, special entries and unexpected
tree members. The sole allowed generated member is the root `.cargo-ok`, with
exact bytes `{"v":1}`; the pinned Cargo implementation creates that marker
after successful extraction. It does not create a registry `.cargo-checksum.json`.

Resolved metadata contains 381 packages: 315 registry and 66 local packages.
The fetch also retained eight locked registry packages absent from the filtered
metadata; they received the same validation. These counts are not a Cargo build
unit graph. The full source inventory was unchanged before and after the
continuation, Git HEAD/status and all 43 initially reviewed files matched, and
the actual compiler/Cargo binaries and routes were revalidated afterward.
The complete installed toolchain inventory records 65,977 entries and
1,205,089,261 regular-file bytes.

Both stages used the canonical workload lock with a 600-second wait, 16 GiB
entry, 9 GiB capacity stop and 8 GiB running floor. The continuation retained
1,834,225,664 allocated bytes across its own evidence and acquired inputs;
58,013,978,624 bytes remained free. These guards are sampled limits, not a
filesystem reservation. No unrelated workload was controlled.

## Retained evidence

`evidence.tar.gz` contains 145 ordinary members (34,860,710 uncompressed bytes),
including both controllers' frozen source copies, manifests, launch records,
outer/child receipts, complete raw streams, source/registry/toolchain inventories
and the independent reconciliation. All members and gzip CRC/EOF were read back.
The compressed archive is 5,936,362 bytes, SHA-256
`51c8c354e1e98fb3de5e320d6c61f736266048f4abb93eebf3eb8402d23c6e53`.
`manifest.json` is SHA-256
`3034564b47ad17d75013868d4bf91463862d4e9e922112bb91e311fbdde1cc34`.
Downloaded payloads and external executor bytes remain in the owned setup;
their full inventories or frozen hashes are retained rather than duplicating
the installations in Git.

The successful continuation receipt is SHA-256
`8ee603c94547bd358efae566c23987dbd980444296ea57f0d17fc705c093845f`;
registry proof `0c23175c6ea063a65a1cf6e161a0e818908cdd282d231357ab07486d50149370`;
toolchain inventory `db3e2c5a41d995822c0625c04f6c40719b6ffd7c66bd08eb2b4198fa27b8a379`.
The original failed receipt remains SHA-256
`52cce75add06f6a31506ac4dbb1d0082759cd62d9dcd722b00b235dabaeddf13`.

The subsequent native compatibility controller preserves the complete library
test crate, upstream profiles/features and libtest scheduling. It must pass
all three unchanged tests in the original, three cumulative production edits
and restored states; the wrong-prefix state must produce all three genuine
assertion failures. SDK/provider and loader checks precede that compilation.
Native compatibility, interpreter/JIT compatibility and warm-edit measurement
remain separate gates. The original Nushell acceptance target and frozen
holdouts are unchanged.
