# Retained VM CPU diagnostic

`report.py` analyzes three owned token-phrase executions against the exact
`57a54edd` binary. It verifies the source, binary, artifact, sample PID, live JIT
mapping and disassembled host call sites before partitioning stack counts.
The original RNG and assertions remain enabled. No sampled wall time is used
as benchmark evidence.

The raw files stay in `.work/retained-token-cpu-sample-04`; the checked-in result
is [the CPU report](../../../results/retained-token-cpu-sample-04/summary.md).
To repeat the sampling with the retained local tool and artifact, use a fresh
run ID (the reporter currently selects the recorded `-04` run):

```sh
python3 scripts/sample_owned_vm.py \
  --tool-key 57a54edd6b64db0e7a1a854dfb42ec0d519cde40366be977fe26d51bb1e16497 \
  --artifact .work/runs/paired-scalar-packed-cache-token-phrase-01/artifacts/candidate/0-0.rbc \
  --artifact-sha256 c263d8924ec053275d9e807c4b5dce5d1a4c7082c9019e75b5c0532242008334 \
  --run-id retained-token-cpu-new
```

Tools and artifact are local build products, not Git contents. Their identities
are recorded in the report. The sampler uses the benchmark lock, creates its
own VM processes and inspects those exact PIDs; it sends no process signals.
