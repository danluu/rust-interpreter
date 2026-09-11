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

The preserved Nushell interface comparison can also be inspected without running
a compiler, decoder binary or guest program:

```sh
python3 benchmarks/experiments/artifact-diff/inspect_literal_history.py \
  --run-id UNIQUE_LITERAL_INSPECTION_ID
```

This reads the earlier typed reports, verifies the six artifact hashes, counts
literal bytes in serialized files and inspects the recorded immediate prefixes.
It reads the pinned public source through Git and writes a new immutable report.
File offsets, packed numeric halves and guest pointers remain distinct concepts.
