# Next isolated ABI experiment: keep the instruction budget in x22

The [field census](../../../results/aggregate-relocation-cursor-census-02/assessment.md)
reconciles all 1,304 cursor samples, with no ambiguous groups. Remaining-budget
access is 761/7,562 token thread samples (10.06%) and 154/2,042 folded samples
(7.54%). Token's budget samples split into 484 ordinary regions, 171 Calls and
106 Returns. These shares identify a target; they do not predict savings.

Use the fully qualified aggregate-relocation tool `9637b0ac` as the comparison
control. Its compiler passes both primary gates, broad correctness and all seven
held-outs, but is still isolated from production source. Keep its exact exporter
and wrapper bytes, guest flags and artifacts. Build a separately identified
experimental VM; do not change defaults or an existing installed tool.

## ABI and implementation boundary

Reserve x22 for the remaining u64 instruction budget throughout a linked
resumable native chain. The current host prologue already saves/restores x22.
The persistent guest-register pairs start at x23, so this should not reduce
their count. Audit every emitter path for x22 clobbers before relying on that.
Ordinary non-resumable and native-tree/stub modes keep their existing ABI.

Load x22 from `State.remaining` once in the external prologue, **before** the
internal `resume` label. Native Call/Return targets enter at that label and must
inherit the live budget rather than reload the stale memory copy. Ordinary
region guards compare/subtract the same block size as before. Transition guards
and charges keep their current order and exact one-instruction consumption.
Store x22 to `State.remaining` on every path returning to Rust, before restoring
the host's original x22. Keep `Boundary` publication/validation unchanged.

Calls/Returns currently use x22 as temporary storage. The proposed replacement
is bounded, not a general register allocator:

- During Call preflight, use x17 for the proposed register end. That value dies
  before argument address checks and copies, which can clobber x17.
- After all argument copies, use x17 for the new register-array pointer. Verify
  that zeroing, destination materialization and frame publication preserve it;
  move it to x0 before profile switching and the final callee lookup.
- For Return, load the saved register base into x17 **after** the checked result
  copy, immediately before publishing register length. This is a read of private
  host Frame metadata, not guest memory. Verify the Frame remains unchanged and
  that moving this read across a possible guest fault changes no visible state.

If a clobber or observability assumption fails, revise the documented ABI before
building. Do not silently steal a persistent register or add unchecked memory
access. Do not move budget checks to backedges or remove required frame clearing.

## Correctness and evidence

Keep all frozen comparison/profile sources and failed histories unchanged.
Use a tracked build recipe with source and component hashes. Check emitted code
and focused differential cases for internal links, callee-entry labels, nested
Calls/Returns, VM fallback, first-time compilation, growth/capacity declines,
zero/one/exact/short budgets, straight-line tails, loops, memory/arithmetic/assert
faults, root Return, TLS callbacks and profile-hit accounting. Exercise profiling
on/off and persistent registers on/off. Verify every host exit publishes budget
before restoring the saved register, and preserves the C ABI.

Run the existing broad workspace, native differential, TLS/destructor and fre
body qualifications on the candidate. Every original assertion, fault order,
instruction limit and observable count remains mandatory. Artifacts must be
byte-identical between the two VMs; a differing artifact is a control failure.
No LLVM/external guest backend, fake threads/unwinding or native fallback.

## Fixed complete-command gates

Use the same two primary real-edit workflows and all seven held-outs, with three
cycles, rotated modes, independent Cargo checks, original/wrong edits and source
restoration. Native remains 18 jobs/O0/incremental/default test concurrency;
custom builds remain four jobs. Keep the original enlarged MIR policy where
already selected. Include compilation/export and execution in each edited command.

Before interpreting a fine-grained result, run matched identical-tool A/A controls
for the primary workflows using the current qualified tool and same schedule.
Require **at least 10% paired token complete-command wall improvement and lower
child CPU**; folded must stay within 5% paired wall and CPU regression. The token
gain must exceed the token A/A envelope: the larger of the absolute paired-median
ratio's deviation from 1 and the nearest-rank 90th percentile of the fifteen
absolute paired ratio deviations. Keep all A/A samples; do not retry an otherwise
valid control to obtain a narrower envelope. If this ambitious
gate fails, preserve the result and park the change rather than loosen the gate
or tune a series of small variants. Every held-out must independently stay within
5% paired wall and CPU regression before adoption. Do not pool cases or count
unchanged builds as the primary outcome.

Source integration of the qualified compiler/runtime combination remains a
separate reviewable step with a reproducible build and component-identity check.
The diagnostic profiles themselves are not an adoption result.
