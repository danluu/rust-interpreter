# Guarded native Call argument slots

The completed [typed census](../../../results/call-slot-census-02/assessment.md)
finds 324,531,401 of 326,206,317 token native argument checks and 80,948,861 of
82,536,622 folded checks refer to known caller-frame slots. No function declined
analysis. This is enough coverage to test a change, not a predicted speedup.
The x22 budget ABI remains parked; do not combine it with this candidate.

## Implementation boundary

Build an isolated VM from integrated source `5b2330c` / tool `9637b0ac`. Copy the
exact qualified exporter and wrapper into its separately identified tool. Preserve
all historical tools and keep the root Rust sources unchanged during comparison.

For resumable functions only, collect bounded semantic-basic-block address hints
once during lazy function compilation. Use the typed census rules and complete
register-write visitor. Unknown/over-bound functions keep the old emitter. Store
only Call argument offsets; do not add per-PC dense register tables or change the
bytecode, Frame layout, working-memory accounting or return-address representation.

At each nonempty known argument, after the same transition guards, instruction
charge, clearing and peak update, load the actual low-64-bit guest address and
compare it with `current_frame_base + known_offset`. On equality, form its host
address directly from the unchanged memory base. On inequality, execute the
existing checked-address sequence at the original point. Then use the unchanged
ABI copy. The guard must neither exit to the VM nor charge a second instruction.
Zero-size and unknown arguments retain their existing paths. Results/Returns
retain their existing checks and timing of failures.

The fast case requires the static offset plus exact argument size to fit the
current allocated caller frame. Recheck this extent in the emitter even if the
analysis supplied it. The runtime equality guard makes the hint advisory:
incorrect/absent facts cannot permit an invalid address. Do not substitute static
facts into general register state or assume high u128 bits are zero.

## Entry and fault contract

`run_resumable` verifies an emitter-owned entry and a valid initialized VM stack.
`Boundary` checks frame/storage extents. Neither verifies that every register
matches a previously executed Local instruction. Direct entry and continuation
tests also construct initialized register storage. Treat register values as
arbitrary under that storage contract; do not silently strengthen it.

The guard must work with persistent pairs enabled/disabled and external/internal
entries, including descendant fallback and host reallocation between entries.
Only guest offsets survive across calls. Audit x9–x17 scratch clobbers, large
register loads, x21 callee base, x22 temporaries and all three persistent pairs.
Keep original bad-argument order, readonly/heap/null faults, budgets, partial-copy
effects, frame/register initialization, profile counts, TLS and host randomness.

## Qualification and fixed decision

Before performance: debug/release workspace checks; focused address-guard and
analysis tests; exact-budget/profile differential cases; direct external entries
with deliberately mismatched hints/addresses; local, heap, null, end-of-frame,
overflow and zero-size ranges; multiple arguments with later faults; large
register offsets; recursion, fallback and ABI canaries. Verify successful
original folded/token artifacts and their instruction/profile accounting, using
per-execution accounting for random token paths. Preserve every failure.

Use the existing repeated complete-command harness, original/wrong edits, fixed
15 pairs per case, isolated Cargo histories, native/check controls and unchanged
400/800/240 MIR settings. First run two fresh identical-control comparisons, then
the candidate folded and token comparisons. Require token paired wall at most
0.90 of control, lower child CPU, and a gain exceeding its A/A envelope. Require
folded wall and CPU at most 1.05. Define the A/A envelope exactly as the preceding
budget comparison: maximum of absolute median ratio deviation and rank 14 of 15
absolute paired deviations. Retain all valid samples; do not retry to narrow it.

If the primary fails, park the candidate without threshold tuning. If it passes,
require fresh 47,004-command native differential validation, TLS/destructor
qualification, all 382 fre bodies with fresh native controls, and seven separate
held-out 5% wall/CPU guards before root integration. Private reports contain only
aggregates. Follow any disk-stop amendment explicitly; never pool partial retries.

The scoped goal is a measured improvement to the existing custom guest engine.
This does not qualify full libtest, unwinding, threads or general OS/FFI support.
