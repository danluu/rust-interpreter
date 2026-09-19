# Analyze retained native indirect-call regions without repeating guests

Both current-composition captures completed once, including successful original
assertions, same-process maps/code dumps and zero JIT declines. Initial analysis
stopped on the legacy validator's closed list of region kinds. The block summary
was already generated; its attribution file was not written. Preserve that failed
analysis and every original capture. No guest or profiler is rerun.

Use a separate validator and attribution adapter, leaving all originally frozen
sources unchanged. Accept resumable_indirect_call only when both map flags are
Boolean true and resumable mode is enabled. Require exactly one original
CallIndirect PC and a matching transition span. The older control profile may
have zero native end at that interpreted site, or the same one-PC end; reject any
other extent. Preserve all ordinary boundary, code hash, PID, complete word/span,
name, ordinal, assertion and per-PC coverage checks. Add positive current-indirect
and corrupt flags/opcode/extent/span controls, retaining all legacy controls.

Qualify these controls and both complete retained captures under the shared lock
with12GiB initial/8GiB child floors. Bind the initial failure and previously closed
sampler proof. Then generate only missing summaries and attributions, independently
close, and use operation categories as perturbed diagnostics, never speed claims.
