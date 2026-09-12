# Reuse the scalar frame plan during export

Recorded before source edits or measurements on 2026-09-12.

- Base: `30404bf363c36be8e70be405ff335a4b23f3cb1c`.
- Task-owned branch: `perf/reuse-scalar-plan-20260912`.
- Task-owned worktree: `/Users/danluu/dev/rust-interp-build-plan-20260912`.
- Build-time candidate only; no runtime or persistent cache change.

`scalar_frame::pack` already constructs scalar MIR events and runs the bounded
planner, including its independent coloring certificate. Later,
`byte_writes::capture` reconstructs those events and reruns the same planner to
check the chosen local slots. Retain the first chosen layout and shapes in
`Lower`, then consume that certificate during capture. Keep the exact extent,
slot count, offsets and sizes checks. Preserve the uncolored fallback when the
planner declines or does not shrink the frame.

The retained certificate describes only original MIR locals, before hidden
caller-location storage and lowering temporaries. Aggregate `ByteUses`, emitted
byte coverage, normal/cleanup result edges, aggregate planning and the final
independent relocation certificate remain unchanged. Preserve the existing
origin/input-bound early declines. Synthetic `Lower::empty` adapters keep no
certificate and continue to bypass ordinary local capture.

Keep `Lower::new`'s initial layout work and strict Rust frontend checks unchanged.
Store no MIR event graph in the certificate. Focused tests cover chosen and
uncolored layouts, bounded/non-improving planner fallback and rejected stale
slot/extent certificates. Root schedules all compilation, tests and timing.

The retained token profile reports 691 ms graph lowering, including 95.8 ms
aggregate capture. The duplicate work is only part of capture; these are
attribution figures, not a speedup prediction. The prospective screen requires
at least 5% paired build-time wall improvement and improving build CPU on the
public token workload, with no greater than 5% guard regression on pgrust.
No candidate timings have been collected.

## Adaptation to current main before measurement

Merged `c1c3b3a952edab2554a1f6f1b861d4be58b18951` into the task-owned branch
before candidate builds or timing. This incorporates the intervening exporter
dependency observation and optional function-payload replay implementation.

`ChosenLayout` remains private, transient `Lower` state. It is not part of
`Observation` or `reuse::Template` and changes neither serialization schema.
Actual green cache hits decode/rebind an existing observation and bypass
`Lower::new`, packing and capture. Red/missing entries take the normal lowering
path. Verification's declined-tape fallback constructs another independent
`Lower`, which obtains and consumes its own certificate. Synthetic Result test
adapters still bypass ordinary local capture.

Independent review identified that constructing dedicated fallback slots during
packing would move a checked-overflow panic ahead of capture's existing
origin/input declines for an already invalid frame. Keep that reconstruction at
certificate consumption, after the unchanged declines, including when packing
selected a smaller layout. A focused regression test covers this ordering.
The unchanged aggregate event data and slot shapes preserve observation semantic
bytes; `capture_nanos` remains the existing intentionally ignored timing field.
Cache namespaces already include the exporter executable hash, and baseline and
candidate measurements must retain separate Cargo/cache directories.
