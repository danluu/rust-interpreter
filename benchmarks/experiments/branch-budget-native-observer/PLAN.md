# Separate observer for reservation code maps

Copy the qualified scratch-memory-values native_observation.py into this new
experiment directory; leave the historical source and its frozen users unchanged.
Preserve the schema-2 ownership and original-PC logical-count checks. Admit the
new budget_edge span only as an eight-byte non-flag-setting ADD x22,x22,#delta
followed by a function-local unconditional branch.

Decode the exact four-word source/destination budget guards. Verify positive
refund arithmetic, ordinary checked/fast entry offsets, strict forward and
unguarded fast destinations, and checked Call/Return budget entry encodings.
These additional checks certify positive-refund thunks only; they do not claim
to independently certify every zero-refund direct link or the complete CFG.

Retain three inherited observer controls and add six corrupt-map/arithmetic/edge
controls. Run and independently close all nine before consuming candidate native
maps, then reconstruct those maps against their exact post-execution machine
bytes and original logical counts. This source is initially unqualified.
