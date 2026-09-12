# Aggregate relocation: folded execution profile

Three original-test executions verify with immutable VM 21d1e163 and tool 9637b0ac. All 1,967 generated-code self samples bind to their own emitted instructions; 2,042 thread samples were captured. Generated clearing accounts for 20.42% of captured self samples.

The artifact is the exact original-source candidate from the completed primary comparison. Original assertions, RNG, instruction/allocation limits and runtime options remain unchanged. Every VM and diagnostic child finished naturally. Captures are partial and perturbed; sample shares are not latency measurements or predictions of savings. Unclassified generated instructions remain grouped, and source integration remains a separate task.
