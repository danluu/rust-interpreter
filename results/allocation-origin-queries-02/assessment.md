# Allocation-origin queries with exact serialized bounds

The corrected inspector passes the original static/TLS/padding/missing-content
queries and ten rejection checks. One static retains all three request origins.
Six equal-content allocations remain distinct, including mutable LEFT and RIGHT
TLS values. Full function context and the recursive relocation ancestry verify.

Output sizing now streams the same indented/escaped representation and trailing
newline that write_json publishes, and checks again after adding the source map.
The exact byte boundary passes and one byte less rejects. Match, request and
ancestry bounds, wrong artifact binding and duplicate function identity also
reject. All seven original input/source hashes remain unchanged.

Supervisor 70529/controller 70540 finished successfully. The separate actual
[CLI02 inspection](../allocation-origin-static-cli-02/summary.json) also succeeds.
The prior qualification and its source snapshot remain visible; the size check
was corrected before using this inspector on a large project. This diagnostic
changes no guest behavior or bytecode and infers no allocation equivalence.

See [results](summary.json) and
[trace plan](../../benchmarks/experiments/artifact-diff/CONSTANT-IDENTITY-NEXT.md).
