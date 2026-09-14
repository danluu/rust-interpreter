# Bounded branch-aware liveness census

The linear region model still has only 7/13 candidate samples. Test the remaining
conservatism explicitly: build each native region's machine CFG from numeric
direct B/B.cond/CBZ/TBZ instructions, keeping external transfers fully live.
Unknown encodings, SIMD, calls and indirect transfers retain all registers;
all loads/stores and control effects remain. Use a bounded monotone worklist,
declining a region if its fixed-point work allowance is exhausted.

Compare two return seeds on the same saved code: every physical register/SP/NZCV,
and the JIT's declared `extern "C" fn(...) -> u64` contract. The latter consumes
x0, x18 through x30, SP and conservative vector state. It does not demand values
in caller-clobbered integer scratch registers or NZCV after RET x30. Bind the
exact adopted `platform::Code::call` and `return_to_vm` sources. This is a model
of observable returns, not permission to execute or alter ABI code.

Require the linear region candidates to be included in the all-register CFG
result, and the all-register result to be included in the C-return result.
Run all 16 prior controls plus five CFG controls, including diamonds, cycles,
external exits, unknown calls, flags and observable return registers. Reconcile
the same saved sample totals for both policies. No guest or compiler execution,
runtime patch, machine-code publication, new timing or relaxed adoption gate.
