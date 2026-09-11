# Custom Rust execution engine

The guest backend is this repository's MIR lowerer, bytecode interpreter and
direct AArch64 emitter. Rustc supplies Rust semantics; no external interpreter,
LLVM guest backend or JIT library executes unsupported guest code.

## Compilation and publication

Cargo builds procedural macros and build scripts as ordinary native programs.
The pinned rustc driver checks the selected library/test target, resolves concrete
instances and layouts, and exports a selected reachable graph. The default path
retains ordinary type and borrow checking. Experimental partial-checking modes
are explicitly labeled and are not the qualified development policy.

Bytecode is associated with Cargo's exact metadata artifact through a sidecar.
Selection and lowering options are tracked compiler inputs, so changing the
selection currently invalidates the selected target. The launcher checks tool
and artifact identities and creates fresh guest state for execution. The optional
std-MIR sysroot supplies reusable standard-library metadata, not precompiled guest
machine code. Native host tools retain their host sysroot.

Lowering preserves compiler-provided layouts and emits explicit calls, memory
operations, assertions and control flow. Scalar frame coloring, promotion,
inlining and control-flow passes have separate legality checks. Function display
names are diagnostic strings; compiler-generated shims can share a name. Future
function caches need stable identities and relocations, not name-only keys.

## Interpreter and JIT

The interpreter uses initialized 128-bit virtual registers, a guest frame stack,
readonly data, mutable statics and a guest heap. A JIT object stages a function
when it is first entered. It compiles supported bytecode regions and links
successors within that function. The default path returns Calls, Returns and
unsupported native operations to the custom interpreter. Optional experimental
paths also execute Calls and Returns natively. The JIT is not an eager
whole-program compiler and is not retained across separate guest executions.

Generated code receives current storage pointers at entry; it cannot keep those
pointers across VM allocations or frame changes. Code is appended to a bounded
MAP_JIT arena on its owning thread. Published entries never move. Capacity or
known encoding limits decline a function before publication; internal relocation
errors remain errors. The JIT's unsafe entry contract documents arena lengths,
register storage, profiling counters and exclusive lifetimes.

Native regions consume the same logical instruction budget as interpretation.
When a region will not fit, the interpreter executes the remaining instructions
individually to preserve fault ordering. Local constant/value forwarding and a
small register cache are reset at conservative boundaries. The optional
`--jit-persistent-registers` analysis carries full-width values across native
block edges, with spills where VM continuation or aliasing requires them.

`--jit-resumable-calls` executes native Calls/Returns over initialized guest
frames. It uses one host ABI frame and immutable per-function/per-PC entry
tables, avoiding recursive host-stack growth. Storage preparation and code
publication happen outside generated execution. Calls preflight storage, depth,
logical budgets and target readiness before committing progress; argument-copy
order and required initialization remain explicit. Large ranges clear in exact
64-byte batches followed by the existing tail.

An unsupported operation or unready target returns the exact active guest frame
and PC to the VM, which validates the continuation and consumes the returned
operation once. Root and TLS completion remain in the VM. This mode excludes
the earlier complete-tree/stub options and stays disabled by default. Its
debug/release, native differential and TLS qualification does not remove the
application compatibility limits below. [ABI and experiment](docs/NATIVE-CALL-EXPERIMENT.md),
[resumable design](benchmarks/experiments/resumable-native-calls/PLAN.md).

## Semantics and compatibility limits

The native emitter supports little-endian AArch64 on macOS. The interpreter is
the reference engine; the frontend/artifact paths are qualified on the pinned
64-bit host. This is not a hostile-code sandbox or a Rust undefined-behavior
detector. The tagged stack/data and heap arenas do not model pointer provenance.
Memory operands use target-width addresses; opaque function identities have
stricter validation. Minimum arena storage is not a full null guard page.

Guest byte and live-allocation budgets bound specific VM resources, not total
host RSS, map metadata, compiler memory or executable mappings. Memory and
readonly checks remain explicit in both execution paths.

Selected zero-argument test bodies can return unit or standard `Result<(), E>`.
Batch execution is not libtest: `should_panic`, discovery and complete ignore/
harness semantics are not implemented. Explicit unavailable-call trapping can
allow export to continue, but reaching the unavailable call stops execution.
The normal-return try-callback option does not implement panic unwinding.

General Rust application startup, threads, OS integration and arbitrary FFI are
not supported. TLS initialization/cleanup has a supported subset. These limits
must be resolved before claiming large-codebase development support.

[Usage](README.md) · [Measured status](STATUS.md) · [Next work](RUNTIME-NEXT.md)
