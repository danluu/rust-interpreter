# Costs in the completed session-runtime histories

The [saved-history analysis](../results/session-runtime-closed-costs-01/summary.json)
uses240 original suite reports from fifteen valid edits per arm in four completed
histories. It reproduces every original performance verdict without a compiler,
guest invocation or new timing sample. Published aggregates omit private names.

These are separate descriptive medians in seconds. Guest compile counters measure
work across tests, not an elapsed-time partition; stages overlap and medians must
not be added to infer gains or a critical path.

| Workload, candidate | Command wall | Build to ready | Execution | Longest test | JIT compile work |
| --- | ---: | ---: | ---: | ---: | ---: |
| fre token |3.6632|1.4286|2.2007|2.1334|0.1981|
| fre folded |1.5858|0.9054|0.6335|0.6140|0.0250|
| pgrust hashfn |0.5456|0.4821|0.0179|0.0139|0.0010|
| private rg-aot |0.2811|0.2300|0.0055|0.0009|0.0008|

On token, median execution is2.4233s for the adopted runtime,2.2714s for the
candidate with history disabled, and2.2007s with history enabled. Corresponding
JIT compile work is0.2592s,0.2645s and0.1981s. These distinct paired comparisons
do not establish additive component benefits. The candidate's longest test
still consumes most of its measured execution interval, supporting further
investigation of that test's emitted code after the current guards finish.

Pgrust and rg-aot have little guest execution left relative to their command
durations; improving native guest code alone has little room to move those rows.
Their completed regression passes remain neutral versus the adopted runtime.
Compiler/Cargo changes remain with the separately owned workstream. Parser
incremental/default profiles and Nushell are still required before adoption.
