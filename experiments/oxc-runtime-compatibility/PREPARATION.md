# Oxc runtime compatibility preparation

This extends the qualified Oxc native history at revision
`4d5c812d6b16c23fa71d106cf87f7f20ddee69b1`. The original three plugin tests,
wrong-prefix negative control, three cumulative production refactors and
byte-exact restoration remain unchanged. Native qualification is recorded in
`results/oxc-native-compatibility-02`; no performance improvement is claimed.

The runtime owner is
`/Users/danluu/dev/rust-interp-runtime-installation-r-20260918` (RROOT).
Preparation must not modify its scripts or an already frozen Ruff admission.
The controller and evidence remain in the separate Oxc worktree. Ruff is the
first application integration; Oxc follows it after the exact published tool
key and frozen plan are reviewed.

## Source and dependency ownership

The original qualified Oxc source and private registry cache remain unchanged.
A fresh full source copy, including its independent Git object database, is
proposed at `RROOT/.work/sources/oxc`. Copying must preserve every ordinary file
and contained source symlink, use new inodes, reject existing destinations and
bind the new ownership marker to RROOT. Git identity/status checks are read-only
(`GIT_OPTIONAL_LOCKS=0`) and must confirm the original revision and source bytes.
No checkout filters, downloads, application edits or profile changes are needed.

The prepared shared standard-library identity includes the absolute Cargo-home
configuration paths. Selecting another Cargo home would invalidate that
publication. The shared `/Users/danluu/.cargo` cache currently has 228 of the
323 packages already qualified in the Oxc private cache. The other 95 archive
and source-tree pairs are absent. In the prepared snapshot, 271 required index
version records match the private cache byte-for-byte and the remaining 52
records are in 52 entirely absent index files. No existing index file needs
replacement.

A proposed bounded acquisition can therefore copy only the absent archive/tree
pairs and index files with exclusive creation, retaining a ledger of every new
path. Every package archive must match Cargo.lock and its extracted ordinary
members must match the archive, including the exact Cargo marker. Existing
registry files remain unchanged and are revalidated. A destination that appears
before creation causes a retained failure, never an overwrite or deletion.
These counts are read-only preparation findings, not an executed acquisition.

The concrete acquisition controller is `acquire_runtime_source.py`, prepared by
`prepare_acquisition.py`. It first runs 17 synthetic copy/lock controls, then
eight read-only Git identity/version children. The full source tree, including
its independent Git database, is copied with new inodes. Only the ownership
marker changes. The private source and all qualified registry bytes are checked
before and after; every preexisting shared package and index file is bound to
its complete content and modes. Required index version records must match the
private records and locked archive checksums.

The controller takes the canonical lock first, then Cargo's existing
`.package-cache` download lock only while validating and adding registry
objects. Both waits are bounded at 600 seconds. The download lock's inode is
bound before opening and while held; it is released on every exit and before
any subsequent child. This matches the pinned Cargo `3c0b5347` implementation
and macOS Rust `File::try_lock`/`flock` route. No shared/mutate cache lock is
acquired inside the download lock. An append-only intent ledger retains every
exclusive destination even if a copy fails. `.cargo-ok` is copied after all
ordinary members, and existing bytes are never replaced or removed.

Acquisition requires 16 GiB free at admission, stops at 9 GiB, and preserves an
8 GiB floor. Its finite allocation bound is 640 MiB including at most 128 MiB
of evidence; this covers about 145 MiB of source/package payload plus index
files and filesystem allocation. Capacity is checked during copies and archive
validation. Failure preserves all evidence and partial owned outputs without
retry. This stage has no network request, compiler invocation, application edit,
profile change, runtime execution, or timing claim.

The first executed launcher stopped before admission because the original
frozen-input predicate rejected Apple's `/usr/bin/git` hardlinks. Its original
recorded stamp already had 78 links and its hash was unchanged. The failure and
all 136 frozen input bytes are retained. The successor admits hardlinks only
for explicitly recorded executors whose exact route, stamp and hash still
match; source, cache and copied outputs keep their single-link requirement.

## Ordinary launcher history

The proposed correctness controller invokes `RROOT/scripts/interpreter.py`
directly, with explicit published runtime/compiler/std keys and separate fresh
interpreter and JIT cache namespaces. It retains actual compiler argv, launch
receipts and selected bytecode identity. Application settings and complete
library-test compilation remain unchanged. Runtime compatibility is reported
with its exact support policy; it does not imply general Rust runtime support.

Each successful source state runs all three entries in one ordinary batch.
Ordinary batches stop on the first failure, so the wrong-prefix state invokes
each entry separately in the same engine's owned cache. This establishes all
three assertion failures for both engines. The history has 16 ordinary launcher
children: five successful states times two engines plus three negative entries
times two engines. This is a correctness history, not a timed comparison.

The outer controller owns the canonical benchmark lock with a 600-second wait;
the ordinary launcher only takes its own per-workspace invocation lock. There
is no nested canonical acquisition. Source restoration and complete source,
registry, runtime, tool, prepared-std and configuration revalidation are required
on the recorded paths. No run is admitted until the actual tool publication,
bounded resource plan, source freeze and exact launch have been reviewed.
