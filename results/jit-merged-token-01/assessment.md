# Merged JIT diagnosis: no material token change

The qualified current-source VM and historical control are effectively tied:
six controlled pairs give a 0.18% median wall improvement and 0.17% CPU.
All 14 executions preserve the two qualified streams, stdout, instructions and
peak memory. This measures saved-program execution including startup, not
edited commands. The merged VM is build ae0a49e / 9ae79198 (7e4ae256 binary),
whose bytecode Rust source matches the current checkout.

Three fresh, separately sampled executions locate 88.64% of 6,828 self samples
in generated code. Native call/return entries account for 40.76% of all samples;
boundary plus dispatcher self samples total 2.86%. Exact code attribution finds
9.37% in budget-counter loads/stores, 9.67% in zero loops, 8.82% in direct register
array stores, and 4.06% in ABI byte-copy loops. These partial perturbed windows
are not independent costs or speedup predictions. Code publication also occurs
inside sampled execution; its samples remain in the denominator.

[Raw-bound attribution](../jit-merged-token-sample-01/generated-attribution.json)
and [cursor detail](../jit-merged-token-sample-01/cursor-attribution.json) retain
all samples. The old budget-register and guarded-argument candidates saved only
about 1% end to end despite apparently large sampled costs. Do not retry them,
the fixed-clear candidate, or the failed persistent-cache screen.

Next implement bounded whole-function constant/address rematerialization for
resumable persistent-register execution. The current fact cache ends at each
native region. Uniform definitions and existing full-CFG liveness can prove
which values may be reconstructed across regions, free native pairs for dynamic
values, and expose checked local addresses at calls and memory operations.
Preserve explicit materialization before interpreter continuations and all
initial-register semantics. This is a new candidate requiring its own tests
and complete edited-command screen; no gain is established yet.
