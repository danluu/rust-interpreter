# Shared emission templates: staging prototype

The completed preparation audit finds duplicated per-worker native preparation,
while the cross-edit feasibility census shows substantial identity churn for
token. Prototype sharing immutable function templates within one prepared suite
first. Both owners borrow the same fully checked immutable Program. There is
no persistent file cache, cross-program lookup, skipped checking, or shared
executable arena. Each owner keeps fresh guest state and its own MAP_JIT arena.

Stage1 is compiled only under cfg(test). It adds precise emission-site records
for assertion fault immediates and scalar target immediates, captures relative
entries/resume tables plus original assertion PCs, and reconstructs a staging
object for another owner without publishing or executing code. Relocations
must contain the exact canonical existing MOVZ/MOVK sequence; scalar sites must
lead to BLR x16. Re-encoding a value must retain its instruction count or miss.
No branch widening or heuristic scan of arbitrary native words is permitted.

Scope is exact Program address/lifetime, numeric function ID, emitter options
and each direct callee's actual scalar admission/shape. Current scalar target
addresses and per-owner assertion indices are rebound explicitly. Ordinary
callee layouts/zeroing and function bodies are identical by immutable Program
identity. Scalar preparation must still run independently before a future
lookup, preserving proof-work, scalar-work and code-budget accounting. Disabled
tree/stub/profile modes remain disabled. Finite code and resume-table capacity
are checked before restoring; no admission failure changes owner state.

Six focused controls compare every native word, relative entry, resume offset,
assertion message/owner and statistics against fresh emission. Cover multiple
assertions and repeated scalar targets, zero/nonzero assertion offsets,
changed scalar admission, immediate encoding width, distinct Program objects,
different IDs/options, code and resume-table bounds, malformed relocations,
overlap, missing sites and native-word corruption. A template is a trusted
in-memory product of this emitter, not a deserializer for untrusted native code.

No runtime path or CLI option is wired in Stage1. Test-only observations omitted
by restoration are not used to qualify guest execution. Before production
wiring, add bounded storage, thread sharing, accounting, exact owner lifetime,
cache-miss fallback and original-assertion/error/budget execution tests. Then
qualify workspace/strict checks and real changed-source benchmarks, with all
lookup/locking/copying/population costs inside command timing. Parser-focused
gating may be appropriate only after actual sharing coverage is established;
the parser is pgrust gram_core, not Nushell (older internal labels are wrong).

Serial root lock with45second wait; two Cargo/test workers; existing root target
only; build floor max(14GiB,8GiB+2*allocated target),8GiB child floor. Freeze source
before executing focused debug/release tests. Preserve failed attempts and all
successful commands; close original terminal evidence without rerunning them.
