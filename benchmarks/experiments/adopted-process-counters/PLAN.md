# Current adopted runtime hardware costs

Refresh the historical whole-process instruction comparison using the adopted
df4006 tool (VM 6ac4dd9e), not the old 49746a22 runtime. This is a diagnostic,
not a performance adoption screen or a changed-source build-time result.

First `adopted-process-counter-controls-01` revalidates the preserved process
counter launcher's source/build identity, then runs its bounded 200k/2M spin
controls and intentional exit-seven control. The launcher only waits for its
own naturally exited child and reads final counters twice before reaping it.
The old launcher has retained source and build receipts but no modern closure;
this fresh qualification does not claim to retroactively close that campaign.

After independent successful closure, `adopted-process-counters-01` executes
three alternating native/JIT pairs for each original fre block-boundary and
exhaustive assertion. Use native row 38 and adopted row 39 from the closed
heap-layout primary: both are the exact restored source state. Keep ordinary
OS entropy, one native test thread, original instruction/allocation budgets,
and the adopted scalar-call/resumable-call/persistent-register settings.
No profiling, sampling, injected libraries, source edits, compiler, or candidate.

The counts cover each target process's entire lifetime, including libtest or
VM decode/analysis/codegen. They are not phase counters, pure guest counts,
exact entropy pairs, or Cargo command timings. Preserve every pair and report
the spread; no result-dependent retries or selection. Three pairs give only
directional evidence. A later candidate still needs the changed-source primary
and all existing guards. No defaults change here.

Shared lock admission 45 seconds; 12 GiB initial and 8 GiB before each child
and closure. No shared target or other session changes. Freeze controllers,
inputs, and source through terminal success and independent recomputation.
