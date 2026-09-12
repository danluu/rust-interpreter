# Immediate interpreter implementation notes

Artifact build `scalar-abi-artifact-build-01` passes 297 debug/release workspace
tests, one ignored, including eight format tests. Both exact original version-5
artifacts roundtrip unchanged through the new decoder. No scalar guest has run,
and no tool was published. Use its exact copied source/provenance or reapply the
committed artifact injection to integrated `5b2330c`.

Implement runtime changes in a new isolated recipe so the artifact milestone's
source and receipts stay reproducible. Reuse the existing VM loop, with a const
scalar-ABI specialization and a borrowed validated ABI table. The old execution
API must continue rejecting version 6; Artifact methods validate metadata and
select the new path. Interpreter-only support is the next correctness milestone;
report JIT unsupported explicitly until native resumable support exists.

Relevant existing mechanics:

- `execute_impl` in bytecode/lib.rs starts at line 648; retain its legacy wrapper
  and route it to a shared loop with `SCALAR=false` and an empty table. Scalar
  Artifact APIs validate once and use the same loop with `SCALAR=true`. Preserve
  all existing Limits option checks; profiled execution remains separate.
- Root argument width rejection precedes execution. For scalar arguments, skip
  their memory stores and populate the fresh register vector after validation.
  Root registers already start at zero. Result/argument aliasing must retain the
  supplied argument value.
- Calls reserve memory, charge/check working registers, copy arguments in order,
  check depth, initialize registers, then push. Scalar arguments need initialized
  register backing before their ordered reads; copy other arguments normally.
  Clear the callee's registers before assigning inputs, never afterward. The
  caller register slice cannot survive a Vec resize; after its last use for the
  destination/indirect handle, read sources by the saved caller register base.
  Keep observable memory/depth/partial-failure order. Native publication later
  must match the same boundary even on decline or fault.
- Initialize the scalar result register to zero before assigning arguments,
  so a result aliased to an input receives the input. This preserves initial-zero
  semantics on reused backing without forcing whole-array clearing solely for
  implicit Return reads. Extend the existing register initialization proof to
  accept explicit initialized inputs (arguments plus that result register).
  The unchanged legacy proof must retain its behavior.
- Return reads a scalar register (masked to slot width) or the original memory
  slot. Root/TLS completion uses the selected value; ordinary returns store a
  scalar to the caller's memory destination in the existing pop/truncate order.
  No Frame layout change is needed until caller register destinations arrive.
- Indirect calls already validate argument/result widths against the target;
  they can use the same callee ABI table after resolving the existing handle.
- `tls::advance` initializes callback registers then stores one pointer argument.
  Support its scalar argument location, preserving callback order, limits,
  reentrancy and root reset semantics. Callback results must remain zero-sized.

Tests need direct and indirect mixed calls, recursion/repeated backing, scalar
root arguments/results and input/result aliases, all widths/upper bits, initial
zero results, TLS callbacks, exact budgets/profiles and error ordering. Compare
manual scalar fixtures with equivalent legacy-memory programs. Frame/memory
peaks may differ only when a subsequent explicit compiler transformation changes
their layouts; this milestone keeps layouts. Do not execute the admission probe
bodies, whose inserted zero argument initializers are intentionally unsuitable.

After this milestone, complete native resumable support, caller value operands
and compiler admission before claiming the value-passing objective. The contract
and fresh complete-command gates in CONTRACT.md remain in force.
