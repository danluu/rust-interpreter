# Compare structural scalar expansion opportunities before implementation

The read-only scalar primary failed. Its duplicate-read opportunities are small
and concentrated. Use closed typed Call metadata and the exact adopted-VM
Call/Return and native-PC samples to compare three prospective bounds:

* Wider local frames/registers and results: at most 512 bytecode operations,
  8192 frame bytes, 4096 registers, 16-byte arguments and 256-byte result;
  no direct or indirect Calls. At least one current shape bound must expand.
* One additional Call layer: retain the existing 512 operation/frame/register
  limits and 16-byte boundaries; require every direct callee to have a complete
  read-only/strict scalar native plan. Reject indirect Calls.
* The already identified 16 small scalar cycles, without claiming a bound on
  their iteration count or a viable native transaction.

All three are optimistic structural filters, not effect/alias or native proofs.
Count both transition and body samples without double counting native spans.
Body samples can expose work missed by counting Call sites alone. Reconstruct
the exact existing transition partition and verify the closed sources/artifacts.
Record all candidates and sampled targets, including zero-coverage cases.

This is Python analysis of saved public evidence: no guest run, JIT publication,
compiler rebuild or timing claim. Keep the shared lock, 12 GiB admission and
8 GiB floor. Preserve prior tree, wider-memory, cycle and read-only results.
