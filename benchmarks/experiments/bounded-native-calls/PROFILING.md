# Profiling the current native-call boundary

After the primary E2E corpus finishes, sample three fresh executions of each
saved original artifact using the exact qualified candidate binary and both
native flags. Folded uses one-second windows because its complete execution is
short; token uses three-second windows. Capture the same-process live JIT arena
before sampling. Preserve original RNG, assertions, instruction/allocation limits,
process identities, stdout/stderr and all diagnostic commands. Do not run these
samples concurrently with builds or measured commands.

```sh
python3 scripts/sample_owned_vm.py \
  --tool-key 2f31c6a09b1b4c0915e7c50a4e9369c3e29a3ec8c38889504a0ba9c408628aef \
  --artifact .work/runs/paired-scalar-packed-cache-token-phrase-01/artifacts/candidate/0-0.rbc \
  --artifact-sha256 c263d8924ec053275d9e807c4b5dce5d1a4c7082c9019e75b5c0532242008334 \
  --run-id native-region-token-sample-01 --repetitions 3 --duration 3 \
  --jit-native-calls --jit-native-call-stubs
python3 scripts/summarize_owned_sample.py --run-id native-region-token-sample-01
```

Use a new run ID for each execution. The public report partitions captured
thread samples into self counts by subtracting immediate child counts. Generated
PCs are checked against that process's recorded live mapping. Grouped host PCs
remain grouped, and unknown addresses remain unresolved. This reporter does not
reuse host-call offsets from the older VM binary. The original 57a54edd report
used inclusive dispatcher-call-site categories; these new categories are not a
before/after subtraction against those old percentages.

These are perturbed windows, not complete-command timing evidence or a forecast
of savings. The next implementation should follow the observed remaining cost:
large VM-boundary cost motivates a broader continuation/call ABI; large generated
cost motivates inspecting generated setup/copies and values spilled at every
block edge. Register assignment across blocks requires external-entry reloads,
VM-exit spills, preserved callee-saved machine registers, complete u128 values,
and explicit joins/call behavior. Reducing correct initialization or omitting
bounds is not an acceptable shortcut. Any candidate still faces the original
folded/token gates and held-out/broader qualification.
