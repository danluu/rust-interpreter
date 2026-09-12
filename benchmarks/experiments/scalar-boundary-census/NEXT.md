# Next: scalar values across guest calls

The typed census passes both exact original profile reconciliations. The observer
passes 45 exporter checks and produces byte-identical folded/token exports with
the unchanged integrated VM/wrapper. Six observer tests and five typed-join tests
cover bounds, overlapping storage, relocation, identity and profile accounting.
The first export's ABI-offset assumption failed closed and remains preserved.

Token's MIR-eligible primitive/other-scalar arguments account for 46.00M/42.55M
direct argument copies, and 74.44M/52.87M full callee loads or copy reads. Eligible
results account for 23.21M/24.46M returns and almost exactly one result write per
return. An entry-load/return-store adaptation preserves those boundary copies;
its potential is principally repeated reads and address construction. These
counts favor investigating values across the boundary instead of another
memory-ABI-only change. They do not predict a 10% improvement.

Choose a custom scalar value-passing ABI prototype, keeping aggregate/reference
storage semantics and all strict Rust checks. Do not integrate whole-call,
guarded-slot or budget-register candidates. Root remains `5b2330c` / `9637b0ac`.

First perform bounded static admission using the real scalar transform's full
address-use proof. MIR-eligible rows are candidates, not a proof that final
bytecode can be promoted. Require exact-width Load/Store/Copy uses, unambiguous
address-register definitions, dominance, no escaping address or partial access,
and explicit handling of argument initialization and result publication. Preserve
cold branches and assertion failures. Rank the admitted subset against the same
two exact profiles before deciding which ABI fields to implement.

Then freeze the wire/runtime contract before changed guest execution:

- Explicit versioned function/call metadata for scalar register arguments and
  results; the existing memory ABI remains valid for unconverted boundaries.
  Bytecode validation checks shape, widths, register indices and initialization.
- The custom interpreter is the reference implementation. Native resumable Calls
  already transfer across guest frames; extend that machinery without host
  recursion or an external backend. A value ABI still has register transfers;
  it is not literally zero-copy.
- Direct and indirect function identities, Rust shims, mixed argument kinds,
  tracked-caller arguments and TLS roots retain their contracts. Start with a
  conservative admitted subset, with explicit wrappers or declines where needed.
- Entry values must be initialized before any read, and result values published
  only on a successful return. Preserve width/upper-bit semantics, runtime budget
  charging, partial faults, continuation state and exact profile accounting.
- LLVM is only an explicitly labeled native control/host build dependency; no
  LLVM or external interpreter/JIT guest fallback. No fake threads or unwinding.

Qualification before timing: typed primitive/thin-pointer/scalar-layout fixtures,
negative address/call/aggregate/partial-access cases, malformed bytecode, repeated
and recursive calls, indirect calls, all integer widths, panic/cold paths,
initialization, exact short budgets, TLS and native/interpreter differentials.
Original real test assertions and strict uncalled type/borrow errors remain.

Freeze implementation bounds and artifacts, then run fresh complete A/A and
candidate histories: three repeats of each of five real edits, interleaved tools,
matched checking floor, wall and child CPU. Target at least 10% token complete-
command wall reduction beyond same-workflow A/A variation, with a separate 5%
folded wall/CPU regression guard. Full seven-workflow held-outs follow only if
the primary gate passes. Keep all pairs and failed attempts. These are new
candidate gates, not a revision of any parked experiment's decision.

Full libtest behavior, real unwinding/threads, broader OS/FFI and fastest-native
qualification remain open. The selected body workloads cannot establish general
large-codebase usability by themselves.
