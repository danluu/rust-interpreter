# Effective limits are visible and checked

Suite reports now include the per-test instruction, allocation, memory and frame
limits, plus the separately scoped JIT code budget. Fields appear on passing and
failing test runs. The launcher checks them against its CLI settings and the
workflow verifier checks the independent benchmark configuration. Older immutable
VM reports remain readable; qualification of new VMs requires the fields.

All 323 Rust tests per profile (one ignored), 41 Python tests, twelve controlled
saved-suite commands across pgrust/fre/Ruff, and 32 pgrust source-edit/check/
restoration commands pass. Sixteen actual pgrust suite reports were checked for
mandatory effective limits, including the wrong edit and restored source.
Fresh/prepared old/new execution has identical logical steps and peak guest
memory under replayed entropy. Guest limits and execution semantics do not change.

[Receipts](summary.json) · [Protocol](../../benchmarks/experiments/prepared-jit/LIMITS.md)
