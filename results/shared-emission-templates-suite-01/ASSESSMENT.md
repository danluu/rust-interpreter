# Original suite compatibility and actual sharing

All13 commands pass with VM
`d071c9123c40cd9ee9ad4dd1bb13faed046373a7d743ebc85919b08c029e8ebd`:
seven original-workload suite commands and six rejection controls. The preceding
closed workspace gate passes635 Rust tests per profile and434 Python tests;
the closed121-command native/reference/cache/Cargo qualification preserves
unreachable type/borrow rejection and source restoration.

Both original and deliberately wrong pgrust gram_core artifacts preserve all114
original test outcomes with ordinary two-worker preparation, requested sharing
with one worker, and requested sharing with two workers. The latter actually
restores797 templates/3,799,956 native bytes on the original source and53
templates/151,512 bytes on the wrong source. Counts include preparation by tests
that fail their original assertions. The original store charges37,929,344 bytes
for2,635 retained templates, within its64MiB bound; this accounting is not RSS.

Requested sharing with one worker creates no shared store. The original private
rg-aot one-entry suite similarly reports one effective worker and no store even
when two workers are requested. Fresh mode, interpreter mode, missing resumable
calls, duplicate flags, missing batch mode and an actual partially checked
artifact reject before guest execution.

These are compatibility and mechanism observations with ordinary OS entropy,
not an end-to-end performance comparison. The saved artifacts and native
outcomes are hash-bound to previously closed histories. No source is edited,
native reference is rerun, assertion is weakened, or instruction/byte counter
interpreted as time saved. Actual reuse clears the prospective mechanism gate;
only the separately frozen changed-source primary can establish a speed gain.
