# Isolated Miri component acquisition

The official component archive was downloaded from the URL and verified against
the hash in the already-installed 2026-09-08 nightly channel manifest. Only its
miri and cargo-miri executables were extracted into a task-owned workspace.
No installed toolchain or user cache was changed. The retained records identify
the archive, binaries and channel manifest; the binaries themselves remain in
the named workspace and are not duplicated in this publication.

The Miri test records separately identify compiler, sysroot, commands and results.
