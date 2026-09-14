# Native scalar Call candidate

Experimental `--jit-scalar-calls` requires resumable JIT execution and full
artifact validation. V5 format and the strict compiler/exporter are unchanged.
The qualified proof/IR/body implementation is copied into bytecode source;
the original standalone diagnostic sources remain frozen as reference history.

Each newly reached caller lazily prepares its direct scalar callees once,
using bounded proof work and the existing total native arena capacity. All
preparation is charged to JIT compilation time. The first bridge caps arguments
at 64 (1,184 bytes of private Call scratch) independently of bounded leaf spill
storage. Ordinary callee bodies and interpreter fallback remain available.

Guards check the original instruction, frame, memory and working limits, plus
preexisting input/result ranges. Scalar code preserves logical addresses and
writes only its private output. Success commits result, retained zero padding,
peak memory, Call/Return counts and original instruction budget. Failure restores
caller ABI/SP and continues with the existing Call without an early error.
The generated hot path contains no Rust callback or foreign backend.

Optional profiles add `jit_scalar_hits`, exact per-original-PC counts committed
only on successful leaves. These counts contribute to `jit_instructions`;
normal native block ends remain unchanged. Operation-map schema 2 classifies
scalar bodies separately and independently reconstructs their exact bytes.
Whole-body spans do not claim a mapping from scalar machine instructions to
individual original PCs. Code dumps retain contiguous shared-arena coverage.

The first focused qualification runs seven complete-program controls in both
profiles, including ordinary-interpreter comparisons, full-width aliases,
budget/depth/memory tails, fallible private leaves, heap boundary guards, large
caller register arrays, prepared option identity, shared code admission and
independent code-map reconstruction. Full regressions, strict/Cargo controls,
original project profiles/assertions and changed-source timing gates remain
required. This candidate is not adopted and has no performance conclusion.
