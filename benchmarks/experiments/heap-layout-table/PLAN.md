# Exact heap ownership table experiment

Status: UNBUILT. No default/runtime installation or timing has changed.

Latest closed adopted samples attribute73/155 self samples to heap-context work,
including exact layout validation and live-allocation map insertion/removal.
These partial windows are not timing predictions. No previous allocation-table
candidate was found in the mechanism/history search. Native allocator bridges
and address-selection changes are different, unselected proposals.

Change only the private live-allocation layout table from BTreeMap to the standard
HashMap behind the explicit heap-layout-hash build feature. It supports only
get/insert/remove/len/is_empty and is never iterated to choose guest addresses.
The free-range BTreeMap and lowest-address first-fit algorithm remain exact.
Allocation/reallocation/deallocation bodies, errors, zeroing, static prefix,
limits, release coalescing, guest addresses and all JIT code remain unchanged.
Use the standard seeded hasher; no weak custom hash or unchecked lookup.

Preserve an exact fca687eb heap.rs copy as a test-only reference. Four new controls
compare all returned addresses, errors, full guest bytes and known live layouts,
including16 distinct host hash seeds, first-fit alignment, free coalescing,
reallocation failure/moves/shrink/growth, zeroing and the static prefix. A seeded
128000-operation history comparison uses the unchanged tree implementation as
reference, with final release of all live blocks. These tests are UNRUN.

Before any benchmark: source-bound debug/release qualification of the feature,
existing heap/C allocator regressions, full workspace controls, strict/cache
frontend checks, three original guest profiles with exact PC/memory/entropy,
then an explicit content-addressed candidate installation. Any metadata growth
or constructor cost belongs inside the original whole edited-source commands.
Only a fresh predeclared40-command fre primary may admit held-outs; preserve
all existing failure/variation gates, ordinary native comparisons and resource
bounds. No source/binary from a parked performance candidate is composed here.

Build only after fresh max(14GiB,8GiB+2*allocated shared target) admission, with
2 Cargo/test workers and shared lock45s. The shared target is never cleaned.
Original source and selected benchmark artifacts stay frozen through closure.
The paused goal, private evidence and all peer sessions remain untouched.
