# Bulk initialization qualification

Source `001065a` / tool `78e60cdd` passes all **257 workspace tests in debug and
release**, one ignored. The new emitted-code test compares exact dirty ranges
against independent Rust slice clearing, covering lengths through 256, boundaries
around 512/1024/4096, every alignment modulo 64, conservative minimums and empty
one-past-end. Full prefix/suffix equality detects writes outside the range.
Existing ABI, recursion, continuation, profile, budget, copy and TLS tests pass.

The custom resumable emitter now batches known large ranges in 64-byte stores,
then uses the old exact tail. Small ranges and tree/stub references are unchanged.
Required frame/register initialization and guest memory/budget semantics are
preserved. No bytecode/exporter source changes or guest compiler dependencies.

The immutable installed VM is `60b00d7d`; exporter `64d7102e` is byte-identical to
tool `035ef708`. Full hashes and source archive/compiler identity are recorded in
[the release receipt](summary.json) and [build index](../../benchmarks/tool-builds.json).
The debug receipt used pre-commit HEAD with an exact source snapshot; release
installation uses the committed source. These are correctness checks, not
performance or broad execution qualification. Original-artifact checks and the
unchanged E2E gates remain required.
