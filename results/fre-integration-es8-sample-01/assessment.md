# Generated execution dominates the es8i target

Three fresh owned VM executions passed the original assertions. Each capture
binds sampled PCs to code and mapping dumped by that same process. All process,
binary, artifact and source identities verify; all children are terminal.

Of 7,662 captured thread samples, 98.33% are in generated code. Host native
boundary handling is 0.80%, dispatch 0.10%, and JIT preparation 0.03%. Within
generated code, exact zeroing sequences account for 14.81% of all samples,
cursor loads/stores 14.66%, direct register-array stores 7.37% and loads 2.02%.
Call-transition ranges account for 2,603 samples and return ranges for 705.
The remainder includes ordinary instructions not resolved by this classifier.

Hot functions include the test oracle, range iteration and iterator adapter
closures, plus production pair/quad scanning. The uninstrumented target runs
about 19.4 billion guest instructions and 152 million resumable native calls.
Repeated JIT construction and host reentry are poor first targets for this case.

Investigate a conservative write-before-read proof for frame clearing. The old
argument-only census was already parked and should not be repeated. First
measure how many sampled clearing sites a stronger proof covers, requiring
known caller-local argument sources and preserving arbitrary pointer aliases,
alignment padding, result initialization, resource limits and terminal faults.
Do not adopt elision or predict a speedup from sample percentages alone.

[Summary](summary.json) · [Exact generated attribution](generated-attribution.json).
