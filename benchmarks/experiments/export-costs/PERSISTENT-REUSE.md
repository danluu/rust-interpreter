# Persistent function templates in the compiler's incremental session

Current-MIR recipes reconstruct the complex fixtures, semantic-edit fixture
and complete token history. Token payloads cover 5,203 functions and occupy
about 61 MB in the initial fixed-width encoding; 172 direct dynamic-vtable
functions remain in the full-lowering path. This payload size is a cost to
measure, not evidence of a speedup.

Use one bounded cache file in `tcx.incr_comp_session`, obtained through
`rustc_incremental::in_incr_comp_dir_sess`. The pinned compiler copies/links
all files from its prior finalized session into a new working directory and
renames that directory only after successful metadata/link finalization.
Write a new temporary inode and rename it over our cache filename; never write
through the inherited hard link. A failed compiler session must not publish
our staged payload as a successful predecessor. Preserve normal compiler
finalization. Do not manage or delete the compiler's other files.

The cache namespace includes the exact exporter binary, payload schema, target
and lowering policies. It also qualifies the mono-item dependency-node key:
a payload/header mismatch must not reuse dependency edges collected by another
exporter or policy. Keep rustc's mono-item identity as the other component of
the key. Only this metadata-only exporter produces these non-query nodes; the
application path continues to reject native code generation. Add explicit
policy, tool/schema and corrupt-payload controls.

First run persistent verification. Every original function is fully lowered.
For a green node with a valid previous payload, reconstruct the second graph
from that prior payload and the current MIR. Red/missing/declined entries use
the current payload or full lowering. Compare exact functions, frame
observations, guest addresses, bytes, alias classes, graph scheduling, TLS and
unavailable-call diagnostics. Record actual prior-payload uses separately from
same-session reconstructions and count every fallback.

Then introduce an explicit reuse mode that skips original lowering only for a
qualified green payload and retains the same current-session binding path.
Strict type/borrow checking still precedes export. Never execute stale output
after a compiler error. Qualify the original fixture assertions, semantic edits,
layout/ABI/constant changes, source restoration, invalid unselected bodies,
policy changes, corrupt/missing payloads and metadata-finalization failures.

Measure file input/output, integrity checks, decoding, green checks and binding
separately before scheduling a performance screen. Remove diagnostic graph
comparisons from timing runs. Only actual edited build/test commands can
establish a gain. If the first boundary's storage/binding costs consume its
benefit, change the boundary or representation based on that evidence before
running full performance primaries.

Pinned implementation evidence: rustc revision
`cea272fa356e94bd2ee2cadf376630aa0683867a`,
`rustc_incremental/src/persist/fs.rs` (`copy_files`, session preparation and
finalization), `rustc_interface/src/queries.rs` (error check before finalization),
`rustc_middle/src/ty/context.rs` (session access), and
`rustc_middle/src/dep_graph/dep_node.rs` (non-query fingerprint semantics).
