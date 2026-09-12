# Investigate narrower persistent JIT register assignments

The current custom AArch64 JIT retains at most three virtual registers in six
native registers, always allocating two native registers to each u128 value.
The checked bytecode often defines addresses, loaded bytes/words, comparisons
and narrow arithmetic whose upper 64 bits are zero. A conservative whole-function
proof might allow up to six such values in the existing native register bank.
This changes only native register assignment and materialization, not the guest
ABI, bytecode format, frontend checking or published arithmetic semantics.

First measure feasibility on the actual saved token/folded programs and their
existing profiles. Enumerate every definition of a virtual register; classify it
as narrow only if every possible definition provably clears the upper half.
Unknown operations and any potentially wide definition decline. Account for
read-before-write initialization, repeated definitions, destination/overflow
aliasing, loops, dead/unreachable code and interpreter exits. Derive definitions
from the authoritative register visitor, then classify semantics conservatively.
Do not assume that Rust types or sampled values make a register narrow.

Compare the current fixed three-pair assignment with bounded packing into the
same six native registers. Report assigned values, static and profile-weighted
uses at boundaries, extra narrow assignments and unproved cases. Bind program,
profile and source hashes. This is a feasibility census, not a speedup estimate.
Proceed only if the additional assignments cover meaningful dynamic traffic;
otherwise choose a different structural direction without a timing experiment.

Any implementation must preserve full-width values at VM exits, native Calls and
Returns, budget exits, assertions, memory errors and unsupported-op fallbacks.
The six-register host ABI bank and stack save area remain bounded. Existing
persistent-register behavior stays available as a control. Qualify both profiles,
wide-value/alias/loop/fallback/fault-order regressions and seeded valid-program
comparisons before timing. Keep all other parked optimizations disabled.

If feasible and correct, preregister the exact candidate and baseline identities
before a saved-runtime screen. Use six balanced token pairs with recorded/replayed
entropy and a fixed minimum 10% wall improvement, no CPU regression. Failed
screens stop this candidate; no repeated attempts to cross the gate. A passing
screen proceeds to actual source-edit/build/test commands and held-out projects,
including comparisons with their best retained anchors. All reported gains must
state the workload, engine flags and whether compilation is included.

Keep one active workload, two Cargo workers, bounded 45-second global-lock waits
and an 8 GiB free-space floor before children. Use completed regenerable public
compiler caches only when storage reclamation is necessary; preserve sources,
artifacts, installed tools, raw evidence, private caches and unrelated work.
