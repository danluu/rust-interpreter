Typed scalar compiler candidate, based on qualified caller-value runtime e651b25c.

Capture scalar layouts and private full-place MIR uses after strict frontend
checking. Carry their identities through the existing validated relocation map.
After the existing optimizers, prove each candidate's final address uses,
dominance, unique definitions and exact direct-call widths. Reject overlapping,
interior, indirect and unrecognized address uses. Bound all analysis. Promote
formal inputs/results and caller locals to canonical full-u128 registers with
width-preserving operations and explicit CallValue operands. Preserve frame
extent and mixed address bridges. Runtime initialization supplies ABI registers;
only new private registers receive entry zeroes.

Publish version 6 Artifact only with the explicit experimental --scalar-values
option. Track the option in rustc dep-info and audit identity; hash the encoded
artifact in the existing sidecar/trace publication path. Version 5 controls keep
the existing encoding. No demand/lazy-checking combination. The experiment
launcher is separate from the frozen production launcher.

First qualify debug/release workspace tests, including transform differentials
against the original memory program, exact candidate budgets/profiles, width
and storage matrices, recursion, aliases, zero initialization and rejected
address proofs. Build actual exporter/VM/wrapper binaries. Then use real Rust
fixtures to qualify typed capture, relocation, strict cold errors, flag changes,
publication, audit packs, traces and execution with original assertions.

Only after that freeze the complete candidate and run fresh primary histories:
three cycles of five actual edits, interleaved A/A and candidate, matched Cargo
check floor, complete-command wall and child CPU. Token needs at least 10% wall
improvement beyond the A/A envelope; folded has separate 5% wall/CPU guards.
Seven held-outs follow a primary pass. Instruction counts and bridge-only
timings do not replace those gates. Full libtest, general threads, unwinding
and broad FFI are still unsupported.
