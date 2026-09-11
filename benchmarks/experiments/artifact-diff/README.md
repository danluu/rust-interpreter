# Typed artifact comparison

Compare two retained `.rbc` files with the current wire-format decoder:

```sh
cargo +nightly-2026-09-08 run --locked --offline \
  --manifest-path benchmarks/experiments/artifact-diff/Cargo.toml -- A.rbc B.rbc
```

Run under the project benchmark lock when other task measurements may be active.
The tool validates both programs, compares functions by index, reports header
and opcode changes, and summarizes data changes. It does not join by function
name: compiler-generated shims can share names.

This is a structural diagnostic, **not an equivalence proof**. In particular,
changed immediate values may contain pointers, integers, or packed values; the
report never assumes they can be normalized. Bytecode and compiler cache history
remain part of the benchmark evidence.
