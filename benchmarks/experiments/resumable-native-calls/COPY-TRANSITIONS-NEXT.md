# Keep checked memory transfers inside resumable native execution

The current tool78 token sample has 15.59% native-boundary self PCs and 2.13%
memory-copy host PCs. A fresh whole-run instruction profile attributes
19,769,609 of 22,417,721 interpreted instructions (88.19%) to CopyDynamic and
fixed Copy. Frequent dynamic transfers occur in stable sorting; fixed transfers
include 136/336/352-byte aggregates. Counts reconcile exactly with VM instruction
statistics. They are instrumented observations, not latency or a speed prediction.

Folded has only 4,772 such interpreted transfers among 85,769 interpreted
instructions; its dominant sampled cost remains frame clearing. Do not reopen
the low-scope argument-zeroing/private-array proposals or tune clearing batches.

Implement native dynamic-length and larger fixed-length memmove in the existing
opt-in resumable mode. This removes repeated preparation/publication around
ordinary guest memory transfers, without a host helper call or new backend.
Keep the ordinary JIT as an independent reference. No bytecode/exporter format
or source assertion changes. No project/function-name specialization.

Read all operands before effects; preserve the VM's current usize conversion.
Empty copies accept dangling addresses and touch no bytes. Nonempty copies
validate both entire ranges, source first, including destination readonly
protection, before the first read/write. Compare resolved host addresses to choose
forward/backward copying; each unaligned pair/byte access stays within its proven
range and overlap works at every displacement. Use bounded emitted loops, not
size-proportional code. Clobber only documented scratch registers, invalidate
local memory facts conservatively, and preserve persistent values, guest/frame
state, exact budgets, profiling and decline behavior. A copy consumes one guest
instruction regardless of byte count, matching the interpreter.

Qualification: execute emitted transfers on independent dirty memory snapshots
against Rust memmove, with all alignments modulo16, overlap in both directions,
equal pointers, separate arenas, boundary lengths, dangling empty ranges,
invalid source/destination ranges and readonly destinations. Check full backing
bytes after success and failure. Check register/cache/ABI preservation, budgets,
profiles and code-limit decline in full VM executions. Run the complete debug
and release workspace suites, then original folded/token artifact smokes using
an immutable tool. Preserve failures and sources before fixes.

Before measuring, keep these gates fixed: three repeats of the five original
edit states (15 pairs/workflow), alternating order and original wrong-edit,
artifact and source-restoration checks. Compare candidate and tool78 with
resumable/persistent options matched. Require at least 10% token paired median
wall improvement, lower child CPU, and no >5% folded wall/CPU regression. This
gate tests a new gain, not the old near-miss against b2. If it fails, park this
experiment without more batch/opcode tuning to cross the threshold.

If it passes, separately retain the original b2 comparison gates (20% token,
10% folded, CPU improvement), seven held-out workflows with no unresolved >5%
regression, and broader native/TLS/fre correctness qualification. No default
change until all applicable gates pass. Native compilation remains an explicit
control; no LLVM/external guest fallback.

[Current token sample](../../../results/resumable-bulk-token-sample-01/assessment.md)
· [Token counts](../../../results/resumable-bulk-token-transitions-01/summary.json)
· [Folded counts](../../../results/resumable-bulk-folded-transitions-01/summary.json)
