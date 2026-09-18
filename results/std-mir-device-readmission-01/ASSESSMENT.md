# Retain immutable standard metadata across a volume device change

The September18 strict-runtime preflight stopped before any guest ran because
all26 retained std-MIR artifact stamps had device16777231 instead of16777229.
Every inode, byte length and nanosecond modification time still matched, and
complete SHA256 verification confirmed every artifact's original bytes.

The launcher now permits only a uniform device-number change to enter readmission.
It verifies every artifact through an open file, checks stamps before and after
hashing, checks the complete inventory again, and records exact current stamps
in a separate receipt. Other stamp changes, changed bytes or an altered receipt
fail. Warm validation retains the existing exact-stamp contract. The original
ready manifest and metadata files are unchanged; no rebuild or Rust checking is
skipped. This repair adds no native runtime optimization.

Seven focused controls pass under both Homebrew Python3.14 and system Python3.9.6,
including byte mutation with preserved stamps, replacement, mixed devices,
mutation while hashing and invalid receipts. Full Python discovery passes421
with22 declared skips. The complete122-command strict/cache suite passed after
readmission using the qualified composed VM; that result does not establish a
performance improvement or adoption of the runtime experiment. The later hashing
implementation keeps compatibility with system Python; its complete fresh Python
qualification is retained in runtime-composition-launcher-02.

The three selected source files in the main publication worktree match their
qualified hashes exactly. Peer compiler-selection and workflow additions remain.
The std certificate and system-Python output are retained here; full source/log
bindings are in the two launcher closures and the immutable experimental commits.
