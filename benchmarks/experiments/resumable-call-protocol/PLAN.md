# Resumable call protocol candidate

This prospective runtime candidate starts at composed source e1b023d and
compares against the corrected, qualified composition 8b16be8e. Its token
comparison saved 4.9% command wall but missed the 8% target and CPU A/A noise
limit. That completed result will not be retried as an unchanged candidate.
The historical frame-padding proof was invalidated and corrected before this
work; the held original fixed-clear VM must not be executed.

## Changes and invariants

1. Clear the actual dynamic padding separately from a fixed payload for frames
   up to 256 bytes. Keep the proven already-aligned path and the existing large
   clear. All lengths are checked before stores; preserve fault and charge order.
2. Retain x16's ready callee target for callers with at most 2048 virtual
   registers. Both halves fit scaled immediate accesses. Larger callers keep
   the reload after argument accesses and live spills. The remaining successful
   call helpers preserve x16; no reserved platform register is used.
3. Combine frame backing and logical depth limits when constructing the host
   cursor. Keep memory, register and total working-memory checks separate.
   No unproved combined slack or descriptor elision is introduced.

Tests cover exact clear extents including dynamic padding, unaligned host
starts and scratch/budget canaries; small/large virtual registers, argument and
return copies, live caller spills and exact instruction limits. Existing tests
cover profiling, TLS, ABI preservation, fault ordering and recursive bounds.
The historical alignment issue is tested by arithmetic invariants, never an
unsafe memory-corruption reproduction. Vector counters, broader inlining and
register-allocation changes are excluded from this candidate.

## Qualification

Host qualification floor: 4 GiB. Reuse the existing qualified host dependency
cache .work/fixed-frame-clear-combined-build-01/target, with two Cargo workers,
locked offline dependencies and the shared benchmark lock with 45-second
admission. Run all 395 Rust tests in debug and release, one ignored each.
Freeze Rust inputs and this plan before building. Install immutable VM bytes,
retaining exporter/wrapper from 8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e.
Run original saved selections, serial replay and ordinary two-worker suites,
and strict native/cache fixtures before performance measurements. Keep exact
bytecode, logical counts and outcomes checks on equivalent inputs. No process-
global entropy injection into concurrent suites or Cargo.

## Planned edited-command comparison

Freeze a concrete driver after qualification. Compare the new VM, the corrected
composition, its identical-tool A/A duplicate, and the fixed selected-suite
anchor fe9dcae0. Include ordinary default-thread Cargo/libtest, explicit native
line-tables and cargo check. Two Cargo workers and two prepared custom workers
remain fixed. The new VM and corrected composition retain the same exporter;
require matching exported bytecode for each source state.

Use three cycles of five real production edits, original source, wrong edit
and final compiled restoration: 154 commands, fifteen pairs per comparison,
and fifteen A/A pairs. Preserve original tests and all outcomes. Balance the
four custom modes with a frozen four-order Williams schedule. Admit 12 GiB for
fre and 6 GiB for pgrust; require 3 GiB before every child. No partial-pair
splicing, automatic retry, or repetition to seek a pass.

The token combined candidate needs 8% command-wall improvement versus the
fixed selected-suite anchor, CPU within 1+max(1%, observed A/A CPU envelope),
and an improvement beyond the observed A/A wall envelope versus the corrected
composition. The A/A envelope is the largest absolute per-edit median departure
across three cycles; require wall <=4%, CPU <=3%. It is descriptive, not a
confidence interval. Folded and pgrust guard both wall and CPU within 5% versus
both custom controls. Keep the original three-test anchor result distinct.

Main has independently gained compiler work reuse. The fixed comparison above
isolates this runtime change with immutable compiler bytes; before adoption,
integrate and qualify against that newer main compiler as well. Do not multiply
separate optimization ratios or treat saved-runtime timings as command gains.
Defaults stay unchanged pending complete qualification and adoption evidence.
