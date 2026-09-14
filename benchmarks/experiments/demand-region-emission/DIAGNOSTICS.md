# Interleaved demand code diagnostics

Demand operation maps use schema 3 and demand_regions=true. Each ordinary
fragment records region_pc; a function may occur in multiple disjoint chunks.
Eager fallback functions and scalar bodies retain whole-function chunks without
region_pc. Demand range maps use schema 2 and demand_regions=true. Eager formats
remain operation schemas 1/2 and range schema 1, without the new optional fields.

Reconstruct each fragment from its immutable retained analysis and original
assertion base. Resolve only emitter-declared same-function links using final
published targets; unready targets keep their original VM tails. Check every
published word, fragment extent, entry, resume address, internal target and
assertion. Require a bijection between publication receipts and nonzero table
slots, including a zero sentinel. Sorted chunks cover the complete arena.
Diagnostic work runs after guest execution and cannot establish timing gains.

Run all 373 bytecode controls in debug/release and both exact eager capture
reconstructions. Four additional controls cover interleaved preparation order,
empty/limited arenas, mixed eager fallback and six malformed publication
receipts, plus actual guest executions with dumps, scalar composition and full
profile comparison. CLI exposure, workspace/strict qualification and original
project profiles/changed-source measurements remain pending.
