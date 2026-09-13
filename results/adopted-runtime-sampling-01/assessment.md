Two fresh owned executions of the adopted VM pass their original assertions,
selection checks and same-process native-code reconstruction. Six sampling/
summarization/attribution stages finish. There are1,651 /1,439 attributed
generated self-PC samples in the block/exhaustive windows, with zero unassigned
generated samples. Native Call/Return spans account for26.23% /34.68% of those
samples; register flushing adds8.18% /12.51%. Native memory operations remain
substantial, while guard setup has little sampled weight.

The retained exact logical profiles report66.40M /70.37M resumable native calls
versus1.93M /2.42M VM entries. These counters describe different boundaries:
native Call/Return spans are not interpreter exits. The new host heap buckets
contain58 /117 samples out of1,933 /1,836 captured thread samples, so allocator
bridging is not the first hypothesis from these windows. Host counts can include
post-execution diagnostics;150 /182 samples are explicitly classified that way.

Next add a test-only partition of the current native call/return emitter into
admission, charging/spills, frame clearing, argument address/copy, frame
publication and return/dispatch work. Reconstruct these exact saved unprofiled
words and maps before applying the finer labels to the already captured PCs.
No new guest execution is needed for that partition. Use actual subpart samples
to choose a compatible protocol optimization; do not drop runtime guards or
infer a speedup from static instruction counts.

These are two partial perturbed windows with ordinary entropy, not timings or
whole-program percentages. The prior 726-command result and its source/compiler
identities remain unchanged. All process identities/terminal records and source,
artifact, catalog and code-map hashes are retained. No peer process is controlled.
