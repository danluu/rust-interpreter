# Complete folded-trie execution profile

The retained artifact runs all 18 original tests from the production-edit workflow.
Its instrumented profile accounts for all 4,920,614,764 virtual instructions:
4,771,793,621 in generated code and 148,821,143 interpreted. Generated code is entered
87,967,634 times. The runtime executes 43,586,672 direct calls and 18,876,336 copies
in the host loop; 17,804,889 copies are exactly 80 bytes and 1,065,289 are 48 bytes.
The current emitter handles copies up to 32 bytes.

A separate uninstrumented execution was sampled for one second. Of 774 samples,
324 are inside the verified generated-code mapping and 450 are in
host code. Frame reservation/zeroing, dispatch and copying are prominent. These
counts do not establish a speedup or attribute all dispatch cost to copies.

A bounded native-copy experiment is worth measuring: read all bytes before writing,
validate both full ranges, preserve arena checks and overlap behavior, and compare
the same artifact plus full edited commands. Retain the complete exhaustive tests.
Strict checking and custom code generation remain in place.

[Complete workflow and timing limitations](../e2e-workflow-fre-folded-literal-trie-cpu-feature-01/summary.md).
Raw per-PC counts, CPU stacks, mapping, process ownership, hashes and commands are
linked in [the provenance record](summary.json). Instrumented times are diagnostic.
