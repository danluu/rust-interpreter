# Private aggregate frame relocation

The unchanged-code observer passes its predeclared scope gate: additional
weighted local-byte scope is 55.97% folded and 31.90% token. Both original
artifacts and assertions match; all direct-frame bytes have accepted inventories.
Historical counts are explicitly labeled. These percentages predict no timing.

Build a separate exporter from the immutable current source `aa2f6ea`, retaining
the exact 0e VM and wrapper. Reuse the qualified byte-write/liveness analysis.
Keep initialization and all VM checks. Do not adopt a production default yet.

1. Record named MIR local identity at address construction, keyed by the fresh
   Local destination register. Old scalar coloring already aliases physical
   offsets; offsets alone cannot identify the correct new local. Surviving
   Local register IDs persist through existing scalar promotion.
2. Resolve actual Call byte ABIs after all bodies are lowered. Reuse the bounded
   planner and certificate, preserving partial-write input liveness, normal
   result edges, dead-write interference, entry zeros and address exclusions.
3. Build a complete relocation before mutating a function. Check every surviving
   Local origin against the original slot; unknown addresses below the local
   extent decline the whole function. Anonymous trailing scratch/caller slots
   move by a common delta rounded down to a multiple of frame alignment. This
   preserves their alignment and disjointness from the new local extent.
4. Relocate return/argument ABI slots and tuple-spread subslots using their
   dedicated original ABI origins. Preserve sizes and order; decline ambiguous
   containment, malformed bounds or overflow. Apply only a strict frame saving.
   If any validation fails, retain the entire original function.
5. Test split old scalar aliases, surviving/deleted Local origins, scratch
   alignment, spread arguments, caller-location arguments, zero-size slots,
   overflow, unknown origins and atomic failure. Retain independent byte-state
   tests, loop/join/cleanup cases and all existing compiler tests.

Before timing, run original folded/token assertions with fresh candidate exports,
validate bytecode, and compare interpreted/JIT behavior on focused relocation
fixtures including padding and normal Call results. Report actual before/after
frames and conservative declines. Do not require identical artifacts across the
compiler change; require identical source edits, assertions, runtime, frontend
flags and all other comparison controls. Qualify the changed-exporter comparison
verifier explicitly before using it.

Predeclared full-command gate: three cycles of the original five production
edits per primary, rotated native/control/candidate order, original and wrong-edit
controls, exact source restoration and child CPU. Require folded paired wall
improvement at least 10% with lower CPU; token wall/CPU regression at most 5%.
The baseline is tool 0e with the existing enlarged MIR budgets. Include analysis
and relocation costs in every timed candidate build. If either primary fails,
park this transformation without a threshold sweep. If both pass, require all
seven held-out cases within 5% wall/CPU and fresh broad native/TLS/fre correctness
before retention. Keep failures and incomplete runs as evidence.
