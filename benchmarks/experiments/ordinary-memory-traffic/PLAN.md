# Ordinary virtual-register memory traffic

Use the adopted VM's two already-closed original token captures. Count actual
unsigned 64-bit LDR/STR instructions with base x0, and only exact emitter
MOVZ/MOVK x16 + ADD x16,x0,x16 recipes followed immediately by an x16 memory
instruction. Record the register slot, low/high half, direction, span and payload
register. Do not classify arbitrary x16 accesses or infer aliases. Keep scalar
bodies separate. Reconcile every generated self-PC sample with the original
mapping and captured words, including non-memory and unsupported categories.
Samples and static instruction counts are diagnostic, not retired loads or time.

Freeze source and raw captures, use a host assembler only as an independent
encoding oracle, and exercise malformed/unsupported sequence controls before
the census. No guest execution or production change is needed. Compare observed
traffic with earlier failed width-packing and enlarged-cache experiments before
implementing anything. Compiler/Cargo work stays with the other session.

Build admission currently fails at about 11.2 GiB free. First retire only eligible
nonexecutable compiler intermediates in the five exact caches of the closed
failed continuation/snapshot 40-command screen. Verify all original evidence,
source restoration, process/open-file status and protected hashes under shared
and invocation locks. Preserve shared target, every executable and artifact,
private/peer files and all other caches. Record both deletion inventory and
closure. This is maintenance, not benchmark timing.
