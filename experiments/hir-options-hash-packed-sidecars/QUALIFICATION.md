# Combined candidate qualification plan — no execution

Source generation is the next review boundary, not compiler-build approval.
Review exact `bindings.json`, generator, verifier and their immutable source
associations first. After separately authorized generation, reconcile all 30
source files and 29 acyclic identity inputs, retain the new identity and exact
patch, and verify that current `context.rs` and the cached-hash wire encoding are
unchanged. The source verifier must pass before proposing a build. Preserve
failed prefixes and all original proposals; do not repair them in place.

Derive the future build recipe from the actual combined source and current
qualified toolchain/SDK/provider metadata. Keep the existing canonical workload
lock and admission/capacity policies. Do not reuse old compiled outputs or
qualifications as evidence for the combined compiler. Its native/private
metadata, support library, driver and exporter must share the new source
identity. The historical compiler passed 27 lowering, 18 interface and 15 support
tests; those historical counts are references, not results of this candidate.

Run the existing lowering and interface suites, preserving both adapted storage
tests: malformed/truncated/wrong-key/checksum/hardlink cases and valid-checksum
invalid-current-tree rejection. Preserve the support tests and documentation
policy when rebuilding support. Retain the options-hash driver's independent
contexts, all option/hash relationships, serial and concurrent behavior.

The **actual compiler-session test target** must additionally run all nine new
`hir_body_cache::tests` functions, whose exact names are in `bindings.json`:

- Framing, magic, count, sorted unique IDs, lengths and trailing-byte rejection.
- Private queued bytes and immutable inherited hardlinked inode.
- Drop without publication, policy separation and unchanged-hit no rewrite.
- Corrupt inherited pack and bounded queue as ordinary cache misses.
- Distinct session ownership and concurrent owner updates.
- Total size and entry-count limits refusing only new bytes.
- Symlink handling.
- Create and injected partial-write failure preserving inherited bytes.
- Rename failure preserving the destination and removing only owned temporary data.

Lowering tests alone do not execute those session tests. Keep the record's full
format/key/checksum and every current entry/tree/journal/preparation/materializer/
recapture/poststate check. The storage map holds opaque bytes, never a reusable
semantic qualification or old HIR/session pointer.

Run the actual run-make recipe with its narrow `.json` to `.pack` discovery
change. Preserve all original cold/hit, real corruption, edit/restore, trait,
wrong-identity, diagnostics, type/borrow/const/panic/lint/error assertions and
unabridged output. File-discovery changes must not silently skip corruption.

Compile the existing unrun `hir-packed-sidecars/controls/stop_driver.rs` with
the matching new metadata/runtime pair. Require a real eligible anchor capture
before the callback in fresh Stop and Continue histories. Stop before
finalization must not publish; Continue must produce the pack in the finalized
directory. Also compile an anchor followed by a real type/borrow/const error,
and fail a changed source after a successful prior pack: no failed-session
publication, prior pack bytes intact, restored successful reuse observed.

Explicit exporter finalization is a distinct path: `mir-export` finishes its
demand-cache session before returning `Compilation::Stop`. Qualify that route
as well. `Drop` never publishes. The new publication log is emitted before the
incremental-directory rename, so it alone does not prove availability in the
next session. Require filesystem evidence. Diagnostic readers must explicitly
recognize the exact producer line without dropping raw stderr or relaxing
unrelated diagnostics.

Preserve the 4 MiB record, 256 MiB policy-pack and 65,536-entry bounds. Two policy
maps can retain 512 MiB serialized payload; the exact-length read buffer can
temporarily add 256 MiB, before Arc/BTreeMap, allocator, decoder and current
record overhead. These are payload bounds, not an RSS guarantee. Observe peak
memory and first-pack-read/final-publication costs in a separately admitted run.
Failed allocation, framing, open or publication loses an optimization; it must
not change ordinary lowering or mutate an inherited hardlink through append.

Old loose sidecars remain copied by `copy_files`; this proposal has no migration
deletion/filter. Use fresh independent cache histories for attribution. Retain
the unchanged strict Ruff tests and intentional failures, actual source edits
and restores, direct compiler stderr and bytecode checks. Compare the qualified
options-hash candidate with the combined candidate without single-Walk mixed
in. Keep instrumented diagnostic and normal latency results separate. No
compiler or application execution is authorized by this source draft.
