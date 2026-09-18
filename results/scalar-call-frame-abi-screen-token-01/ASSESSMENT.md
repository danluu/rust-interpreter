# Private Call ABI: parked after the complete primary

All 40 changed-source protocol commands completed with matching original test
outcomes, intentional wrong-result detection, source restoration and identical
candidate/control bytecode. The candidate passed 21 focused and 597 workspace
controls per profile, 121 strict Cargo/cache commands and six exact original
profiles before timing. Its installed VM is source- and SHA-bound by build-01.

Median paired wall ratio is **0.994813** (0.52% lower), CPU **0.968224** (3.18%
lower). The unchanged A/A wall envelope is **0.016892**; wall plus that envelope
is **1.011705**, so the primary fails. CPU plus its envelope is 0.981220.
Candidate/native wall is 1.667517. Do not run larger comparisons or adopt this
revision. Do not repeat an unchanged screen or alter its gate.

Descriptive nested stages show Cargo +103.4 ms, build-to-ready +103.7 ms and
execution -68.4 ms. Those measurements are neither additive nor causal; a
runtime-only change does not explain the Cargo variation. Separate earlier
candidate screens do not establish their relative causal performance.

The private ABI removes six pointer save/restore accesses and four argument
setup instructions per successful scalar Call. Scalar-body sizes and all
original logical counts are unchanged; profiled arena sizes shrink by 22,204,
27,664 and 1,092 bytes across the three original cases. This static result does
not establish a wall-time improvement.

Next inspect successful scalar leaves for invariant success-path instruction
counts and zero-byte results. The Call bridge still transfers a dynamic step
counter and result storage even where those may be provably unnecessary. First
reconstruct saved qualified bodies and count actual successful Calls; preserve
full guards, original resource/error ordering and all guest-visible behavior.
Only a materially changed, fully qualified candidate may receive a new screen.
