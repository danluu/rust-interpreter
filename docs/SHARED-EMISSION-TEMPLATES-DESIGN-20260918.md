# Sharing emission work across prepared-suite workers

The current prepared suite retains code separately in each worker. Sharing an
immutable template can remove duplicate emission without requiring cross-edit
identity matching, a persistent native-code format or disk I/O. Each worker
still prepares scalar callees independently and owns its executable arena,
assertion table, resume tables, resource counters and fresh guest state.

The first prototype is test-only. It records exact assertion/scalar immediate
sites during emission, then restores relative native code for another owner of
the same immutable Program. Six controls per build profile compare restored
words and metadata against fresh emission; they also check missing scalar
entries, instruction-count changes, different programs/options, resource
capacity and corrupt relocation records. No template enters guest execution.

Next implement a scoped, bounded store. It borrows exactly one Program and
contains immutable, thread-safe template objects. Use one retained template
per numeric function ID; a scalar-admission mismatch takes the existing emitter
path. Never wait for another worker to finish compiling a function. Snapshot an
Arc under a short mutex hold, then perform copying and relocation outside the
lock. A racing publisher retains at most one object. A poisoned lock, full
store or incompatible object produces a cache miss. Test that no JIT arena or
thread-bound Jit owner crosses a worker boundary.

Account template words, entry/resume vectors, relocation records, assertion PCs,
scalar signatures, the slot index and object overhead against a finite budget.
Check arithmetic and reject before retaining oversized objects. Temporary
capture/restore allocations remain bounded by the existing per-owner native
limit; they also belong in peak-memory reporting. Do not grow or evict a live
template while another worker reads it. First test concurrent duplicate
publication, capacity exhaustion, independent restoration and lifetime behavior
without executing code.

Production integration follows only after these controls. Keep an explicit
option disabled by default. Construct the store once per prepared suite; a
one-worker or fresh-owner configuration should decline the option explicitly
or use a documented no-sharing path. Each JIT must prepare its scalar callees
before lookup, retaining the original proof/scalar-work and code-budget order.
Restore must check current code capacity and resume-table admission before
ordinary publication. On a miss, emit normally and optionally retain an
immutable template. Always build assertion references from the current Program.

Measure lookup, capture, relocation, locking and copying as part of the complete
changed-source command. Keep per-owner hits, misses and saved emission work
separate from cumulative code counters. Full original assertions, strict
type/borrow rejection, resource-limit/error order, isolated guest state and
unprofiled native identity are required before timing. Two-worker parser
preparation may benefit most, but choose its primary only after a real coverage
qualification. The parser workload is pgrust gram_core. The existing token,
small-project and Nushell regression guards remain relevant.

Persistent reuse between edited programs remains a separate possible extension.
The input census is not sufficient to authorize it: it would additionally need
stable dependency identities, backend/options/version binding, admission and
relocation proofs, robust bounded publication and measured I/O/keying costs.
