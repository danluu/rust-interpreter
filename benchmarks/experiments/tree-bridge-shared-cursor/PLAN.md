# Shared cursor for bounded native trees

The first bridge failed its 40-command primary (wall 0.995499, CPU 1.021747;
A/A wall 9.9249%). No unchanged retry or full/held-out study follows. The closed
profile census reports 180,361,120 / 381,018,567 tree regions, each with two
budget memory accesses and four budget instructions. Outer bridges number
25,967,646 / 26,487,455. These are instruction counts, not cycle savings.

Change the experimental internal ABI: retain the resumable cursor in x19 and
remaining instruction budget in x22 across every bounded tree. Whole-tree
admission already proves every path affordable, so debit the static region
length with one immediate subtraction. Use x17 for the child register pointer
after ordered argument copies. Keep standalone tree ABI and charging unchanged.

Share the state prefix (budget/profile/live memory/peak/calls) directly. Bridge
fault metadata and separate tree profile tables remain in the private cursor
extension. Root adapters save the original profile pointer, budget and calls
for accounting, without duplicating the state prefix or switching x19. Restore
external host x22 in wrappers; preserve the decremented guest value on every
internal normal/fault edge. Use the adopted frame/register clear helpers for
bridge children so the new ABI retains current ordinary clear behavior.

Preserve planner, guarded-body exclusions, quarter-arena duplicate-code quota,
16 MiB default, ordered aliases, exact fault stack reconstruction and all
strict rustc checks. No frontend/exporter, workload, worker or limit changes.
Old compiled candidates remain immutable and independently reproducible.

Qualify native primitive/nested/full-adapter ABI probes, independent wide bounds,
all short budgets/faults/prepared runs, original standalone tree tests and full
workspace debug/release. Then 119 strict/cache controls and original three
profiles with exact logical counts/memory/entropy; retain changed backend
accounting and code quota. Reuse launcher/protocol evidence only when source
hashes match exactly. New complete-command measurements compare with the adopted
VM, five A/A pairs and the unchanged 40-command primary gate. Only success
permits the full primary and existing large/small project guards. Two workers,
shared benchmark lock, 16 GiB setup / 14 GiB screen admission / 8 GiB child floor.
Record setup by exact tool key; preserve every failure. No goal activation,
subagents, peer process control or AWS service changes.
