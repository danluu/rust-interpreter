# Guarded related pointer ranges in resumable native regions

The conditional census is complete: 265.03M potential redundant checks in the
block test, including 229.94M in generic 36-/108-access SipHash regions. Implement
and qualify this new mechanism on main 7e86b3d. The previous checked-address,
scalar-Copy and budget candidates remain absent. Counts alone do not establish
performance; qualification and a prospective screen precede a full comparison.

## Entry and failure behavior

Scope the candidate to existing resumable native regions. Select at most one
complete root group per region, with at least eight fixed accesses and at most
4 KiB extent. This threshold amortizes the multi-check preflight; freeze it
before real execution instead of tuning it to timing results. Retain a 4M
per-function analysis-work bound and the existing 1024-PC region limit. Ordinary
Jit::run deliberately rejects zero progress; do not silently loosen that
contract. run_resumable already uses Boundary::finish, which verifies an exact
unchanged entry state for zero-progress Continue. The VM then dispatches one
bytecode operation before its next JIT lookup. A guard decline must return the
original region PC through that existing path, without any budget debit,
profile hit, guest memory write, call or register value change. For linked
successors, earlier native progress remains counted while the current region
starts in the interpreter. No repeated-entry loop is required.

Set internal and resume entries before the guard so no native edge bypasses it.
Put all preflight instructions before the original budget debit and region
profile count. A short budget and a failed guard must both use the original
interpreter tail. Existing persistent register assignments must be respected
when reading a root; a raw stale register-array load is not sufficient. A
FrameSlot root reads only a statically proved eight-byte active-frame slot.

Guard branches must not join guest-memory failure tails: a whole-range failure
can precede successful writes that the original program performs before its
later fault. Collect speculative declines separately and target an entry-state
return. All nonselected accesses keep their original checks and ordering.

## Proof and address reuse

Use a typed bounded region plan, independent of project/function names and
runtime sampled values. Include every selected fixed access and every write
whose frame-disjointness is assumed. Preserve exact site identity (PC, operand,
width and read/write role), including both Copy operands. No truncated JSON
report may be consumed as an execution plan. Unknown writes invalidate future
slot-derived identities; already captured register values remain unchanged.
The runtime plan needs its own complete typed sites and a bounded work budget.

Validate the full logical extent without overflow, and prove that all selected
accesses remain in the same original linear/heap address classification.
The heap tag is 1<<62 and classification is an unsigned comparison, not a single
bit. Validate the whole range using existing null, bounds and readonly rules.
If any selected write exists, a whole-range write check is conservative and
may decline otherwise valid mixed readonly/readwrite accesses. That is okay
only because the original path runs on decline. The original guest arithmetic
and overflow results remain executed; proof only replaces address translation.

For conditional frame provenance, prove the complete translated host range is
disjoint from the active frame. Both complete host ranges must already be valid,
nonwrapping allocations before interval comparisons. A same-frame pointer or
partially overlapping extent declines. Other-frame pointers may be accepted.
No host pointers enter bytecode registers or guest-addressable memory.

Cache the validated host base only until the region ends. Use v16/d16 as a
caller-saved location: AAPCS64 section6.1.2 lists v16..v31 as caller-saved, and the
current supported region emitters use v0..v7 for fixed Copy and v0 for popcount.
This needs an exhaustive supported-op/source audit plus actual encoding and
preservation tests before use. New direct-word encodings must be verified with
platform assembly/disassembly; no external guest backend is introduced.
Source: https://github.com/ARM-software/abi-aa/blob/main/aapcs64/aapcs64.rst

Use the cached base and a per-site displacement for selected addresses; keep
all other local forwarding, guest register values and cache invalidation rules
unchanged. Replacing get() must preserve its live-in bookkeeping even when no
register-array load is emitted; otherwise a linked backedge could lose a value. Future regions/calls/VM returns cannot inherit this cache. Record
speculative guard code separately in the exact operation map.

## Required qualification before real timing

Test generated preflights against an independent arithmetic/range oracle,
including low/high offsets, null, exact end, one-past end, readonly overlap,
TAG crossings, high invalid addresses and arithmetic wrap. Exercise linear and
heap storage, same-frame and other-frame roots, unaligned slots and ranges,
byte/word/wide Copy/overlap, both root forms and all aliases. Test all budgets
around entry/exit and linked backedges. A rejected whole range must preserve
earlier successful stores and the original eventual fault. A successful guard
must preserve all guest bytes and exact per-PC/native interval counts.

Existing ABI, continuation, cache, memory, source-error, selection, suite and
entropy controls remain mandatory. Preserve complete generated-map coverage,
including a dedicated guard span, and inspect whether the dominant test really
uses the new path. Freeze one changed-source token screen only after a candidate
passes qualification. Cancel unstarted full cases if that screen fails; retain
all five full gates for adoption. The expected benefit is unmeasured.

## Build and acceptance sequence

Use two Cargo workers and the shared lock with 45-second admission and 8 GiB
per-command floor. Freeze sources, tests and runners before qualification.
Retain every failed admission/build/check. Keep the baseline compiler/exporter
and wrapper exactly pinned; only the custom VM is the runtime treatment.

Before timing, require workspace debug/release tests, relevant Python harness
checks, seven real selections, nine suites, 203 strict cache/Cargo controls and
three current profiles. Exact per-PC work, native transitions, memory/entropy
and generated-map reconstruction must pass. Account for new guard spans
separately from original operations. If real inputs take declines, report the
changed native/interpreter partition and investigate before relaxing any
previous exact-profile criterion. No silent comparison adjustment.

The first workspace build expects478 Rust tests per profile (eight new tests)
and one ignored. Verify the new direct instruction words through the separate
encoding driver before executing candidate tests. Retain exporter/wrapper key
e729a493261568d841d3ef212bcdfeef8fa4bf715cd26538f3cb9d1fa447e846.

Freeze the existing 40-command token screen with baseline/duplicate/candidate/
anchor/native, all twelve original assertions and five cumulative valid source
edits. Its one-cycle A/A envelope and paired wall/CPU gate retain their previous
definitions. Failure cancels the unstarted full comparison; no retiming. A pass
requires the separately frozen five-case full protocol before adoption.
