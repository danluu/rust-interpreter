# Clear exact short tails with bounded stores

The newly closed current ES8 samples identify substantial self PCs in the
byte loop of zero_range, especially padding committed after scalar calls. This
is distinct from the parked wide-clear bundle, which retained scalar tails.

First bind the four closed ES8/token captures and recognize the entire exact
ten-word current zero_range helper. Count chunks and byte-tail samples
separately, reject unaligned/mutated patterns and retain ambiguous sample PCs.
No runtime build or guest execution belongs to this scope. Independently assemble
the proposed tail and compare its exact words; test its native instruction model
against a byte-slice oracle for every remainder, alignment and dirty canary.

Proposed implementation keeps the16-byte chunk loop. On its exit x9 is the exact
remaining length0..15. A CBZ skips empty tails. Four TBZ instructions select
8/4/2/1-byte zero stores with exact postincrement, so no byte beyond the prechecked
end is accessed. x11 still reaches x12; live registers, original initialization,
memory/fault/budget/profiling semantics and strict Rust checking remain. Audit
every helper caller for scratch and flags before implementation. No zero elision,
new ISA feature, vector state, arbitrary overstore or workload-specific policy.

Only meaningful closed scope authorizes implementation. Existing native dirty
range/canary, bulk clear, padding and live-register tests must pass both profiles,
with focused instruction-encoding and exhaustive tail coverage. Then run full
workspace/strict frontend and original-guest qualification with immutable tools.
No timing-only acceptance or unchanged timing retry.

The prospective real-edit primary is current ES8, selected before candidate
execution because of this new independently retained evidence. Require paired
candidate/baseline wall gain at least1% and larger than the full maximum absolute
A/A envelope, plus CPU no worse beyond its A/A envelope. Use all five original
valid edits, wrong edit and compiled restoration, matchedtwo workers, independent
native and identical baseline controls. Failure parks it. A primary pass still
requires token/folded/pgrust/private rg-aot/Nushell and parser original-test and
changed-source guards before adoption; the old parked experiments stay parked.

Scope admission12GiB, childfloor8GiB, sharedlock45s. No tool target cleanup or
process control. The existing shared compiler target remains protected and its
current26.63GB build admission is unchanged. Before native qualification choose
an explicitly owned bounded runtime-only build target if full shared-target
admission remains unavailable; record cold setup costs and a separate conservative
growth reservation. Do not start a build until that concrete resource plan is
frozen. Current scope only emits a small nonexecutable assembler object.
