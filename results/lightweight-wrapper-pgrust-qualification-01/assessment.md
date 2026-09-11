# Pgrust qualification of lightweight compiler routing

The real generic `hash_bytes` API edit passed all four original tests with the
new wrapper. Nine primary commands and three independent checks completed;
all six paired artifacts match, original source was restored and ten frozen
script/case inputs verified. The wrong multiplier still failed in every mode.

This compares fixed `78e60cdd` with `c341296c`, using the same VM binary and
ordinary JIT options in both (resumable/persistent calls off). Leaf inlining,
selected tests, source, checking, budgets and native controls match the case.
This isolates the pipeline from the previous runtime experiment.

The single edited command took 0.750 s native, 0.551 s baseline and 0.538 s
candidate. The independent check took 0.424 s. Initial target-cache-cold commands
took 0.841, 0.570 and 0.552 s respectively. These single observations qualify
the workflow, not performance or retention. Repetitions and Nushell's std-MIR
host/target case are required before drawing that conclusion.

[Commands and controls](summary.json) · [Verification](verification.json)
