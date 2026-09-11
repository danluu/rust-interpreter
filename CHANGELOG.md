# Checked-in changes

## 2026-09-10 review follow-up

- `a2a0e04`: known JIT branch/assertion limits decline before code publication;
  internal relocation errors remain errors. Explicit unsafe entry/thread contract.
  Five new tests; workspace check: 188 bytecode, 11 exporter and 3 cache tests pass.
- `93abea7`: repeated real-edit cycles, balanced mode positions, child CPU time,
  source transitions and per-edit spread. All 63 token commands completed.
  Paired artifacts match; stronger cross-history identity failed and is retained
  as an unresolved diagnostic. The retained engine remains slower than native.
- Current documentation now separates mechanisms, measured status, upcoming work
  and historical narratives. The results index is generated without deleting or
  relocating existing evidence. Every external suggestion has a recorded decision.

## Earlier retained work

- `9358c2b`: tracked token workflow, allocation-limit flag and reproducible launcher.
- `a01ad19`, `641867b`, `58657e0`, `d3983e2`: typed MIR/frame inventories and
  owned-process CPU sampling; argument-only zero elision was parked.
- `6b2c61f`: retained local-memory forwarding in the custom JIT; source `57a54edd`
  reproduces measured `af9aa691` production binaries exactly.
- `32f5e2f`: initialized local Git with the prior engine, benchmarks and evidence.

Historical experimental details remain in [results](results/INDEX.md) and
[the pre-review documentation](docs/history/README-20260910-before-review.md).
