# Native indirect calls with immutable ABI metadata

Base:70b09b03, the adopted runtime plus the closed indirect-call observer.
Publication main separately preserves the newer descriptor-I/O integration;
this isolated prototype starts from the exact profiled runtime source. Integration
with subsequent main changes requires its own correctness qualification.

The two exact original token profiles show1,025,947/843,776 indirect calls,
all caller continuations ready, and only20/23 unprepared callee entries. Start
with a general native transition, not profile-selected targets. Each function's
validated argument-size vector and result size receive an exact signature ID.
Native code validates all128 handle bits, the tag and bounded index, then compares
the immutable signature ID before reading callee layout or native entry metadata.
Only host-owned entry tables provide branch addresses. Cold, missing, capacity-
limited or unsupported metadata paths fall back to the VM before charging work.

Reuse the direct-call protocol: budget/profile charging, frame alignment and
clearing, initialized register storage, ordered argument copies, result address,
frame publication and Return dispatch. Preserve exact errors and limits. Metadata
is bounded, allocated before native execution, never exposed as guest memory,
and remains at stable addresses for its JIT lifetime. The experimental --jit-indirect-calls flag is disabled by default and requires
--jit-resumable-calls. Prepared owners reject changes to this option.
No code rewriting, target
cache, unbounded specialization, artifact-format change, or checking deferral.

First qualify pure metadata and native transition fixtures (invalid handles,
signature mismatches, cold targets, multiple targets, alignment, zero-sized and
wide arguments, overlapping callee slots, large registers, limits, fault order,
profiling and recursion). Then full workspace debug/release checks, strict error
and cache controls, and original saved-case profiles with exact logical counts,
memory and entropy. Native/interpreted placement may change only at indirect
calls; code maps must represent each compiled transition honestly.

Measure only after qualification: the primary-first40-command token screen,
with the existing paired A/A wall and CPU gates, original/wrong/valid/restored
edits and ordinary native control. No new repetition rule or relaxed gate.
Only a passing primary permits full original project histories and regression
guards. Keep setup/build costs separate, and record all failures. Default JIT
capacity remains16 MiB; unchanged-build timing is not optimization evidence.

Use benchmark.lock,45-second admission, two Cargo workers,16 GiB build admission,
12 GiB diagnostic admission and8 GiB per-child floor. Preserve shared targets,
other worktrees/processes, private data and the paused goal. No subagents.
