# Census of repeated address validation

The paired-transfer primary completes 154 expected outcomes but gains only
0.71% wall, below 1.77% A/A. Complete its mandatory guards without retiming.
The next step is a typed, offline census of repeated validation within existing
native regions. Do not change the emitter or remove a check in this first step.

Use the three saved current artifacts and exact wide-operation profiles. Their
regions match the paired profiles. Decode and validate bytecode, verify every
profile function, operation, register count and interval against it, and hash
both inputs. Reuse the existing bounded profile reader. This diagnostic creates
no JIT and executes no guest instruction. Run it only after the active benchmark
controller finishes and under the shared lock with two Cargo workers for its
build and conservative disk admission.

For each observed native interval, start with empty symbolic facts and an empty
cache of checked ranges. Count positive-size Load/Store operations only. Model
the emitter's existing Local/Imm/binary constant folding so accesses already
known to be within the current frame are excluded. Local forwarding can remove
those accesses entirely; the census is not a count of hardware memory traffic.
For other accesses, track the largest checked read and write range for that
exact virtual register. A later read fits either a read or write range; a later
write requires a prior write range. An earlier read cannot establish write
permission. Record permission upgrades separately from full reusable checks.

Invalidate ranges on every definition of their address register, after the
operation's reads. This includes a Load whose output aliases its address.
Reset at every native interval and at opaque effects that might change memory.
Zero-byte operations establish no positive-size proof. Limit the proposed
cache to 16 entries, clearing conservatively when a new entry would exceed
that bound. Include unreachable definitions in symbolic invalidation when
they are in the supplied interval; never infer a value from a Rust type or
sampled Debug text. Keep all analysis bounded and report declined functions
without treating their unknown opportunities as zero-cost work.

Weight observations by the recorded interval entry count, handling overlapping
intervals independently. Report native bytecode accesses, already-known local
accesses, baseline checks, candidate reusable checks, permission upgrades,
invalidations and capacity clears. Include function/PC attribution. These are
logical opportunity counts, not elapsed time, retired instructions or a proof
that the optimization will be profitable.

Tests should distinguish size containment and growth, read/write permission,
zero sizes, aliased output invalidation, intervening definitions, interval and
opaque-effect resets, local constant folding, cache capacity and analysis
limits. The CLI must reject malformed/mismatched or oversized input and avoid
overwriting an existing report. No unchecked guest execution is needed.

If the census shows material repeated work, separately design an emitter
change that reuses only a successful same-region validation. Host translation
must still use the current backing bases. Preserve null, bounds, readonly,
overflow, budget and first-fault behavior. VM budget tails and interior PCs
must not inherit a proof established only by an earlier native entry. This is
different from rearranging the original checks or changing the memory model.
Qualify any later implementation and freeze its own complete-command comparison.
