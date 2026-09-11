# Reproduce the token-phrase edit workflow

The tracked workflow runs the original exhaustive byte-semantics test and the
directed restart and route-boundary tests. It applies five production edits,
keeps the original assertions, and requires a deliberately wrong edit to fail.
The custom engines use a 150,000 live-allocation limit; native Cargo uses its
normal allocator. The engine's byte-memory budget remains 64 MiB.

Prepare the pinned fre checkout with `python3 scripts/prepare.py fre` and install
the pinned Rust toolchain/dependencies as described in the main project docs.
Commands run offline. The harness builds the current tools and reusable std-MIR
metadata if needed, before the measured commands. Those setup costs are separate
from the report's cold Cargo commands. Use a fresh run ID for each run.

For a comparison against an already installed immutable baseline:

```sh
python3 scripts/bench_e2e_workflow.py \
  --run-id token-phrase-new --cycles 3 \
  --project fre --workflow token-phrase-allocation \
  --batch --std-mir --inline-leaves --baseline-inline-leaves \
  --trap-unsupported-calls --run-try-callbacks \
  --build-tool-opt-level 0 \
  --instruction-limit 100000000000 --allocation-limit 150000 \
  --guest-mir-opt-level 3 --guest-mir-inline-scale 8 \
  --baseline-tool-key 6bf10fda528666a64f4b59b0869da9a0d01ade862e822cf45dc1768dc57f9757 \
  --comparison-engine jit --expect-identical-bytecode
```

The baseline must have been built locally from its retained source; binaries and
caches are excluded from Git. Omit `--expect-identical-bytecode` for an exporter
change that intentionally changes bytecode, and separately verify that change.
The current candidate is built from the checked-out sources unless an installed
`--candidate-tool-key` is specified.

The case, harness, launcher and report generator are all tracked. The selected
case and script hashes are recorded with each run. Results go to
`results/RUN_ID`; raw commands and artifacts go to `.work/runs/RUN_ID` and the
isolated interpreter workspaces. Existing output directories are never reused.

The current native control uses the repository's test profile, four Cargo jobs
and one test thread. It is a specified control, not the best possible native
configuration. Three cycles produce fifteen edited pairs, with each edit in
every mode position. Each cycle rebuilds original source and repeats the wrong
edit control. Only the initial original commands are cold. Per-edit timing and
CPU spreads remain descriptive; their win count is not a statistical or general
performance guarantee. Keep
compute and frontend-dominated workflows separate when interpreting results.
