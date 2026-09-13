# Qualify the resumable-to-tree bridge in stages

Follow [the bridge contract](../bounded-tree-bridge-census/BRIDGE-CONTRACT.md).
The broad eligibility census justifies a prototype, not adoption. The first
stage contains only admission and fault-frame materialization primitives; no
runtime option or guest execution path invokes them yet.

Run the independent wide-integer admission model and native ABI/descriptor probe
in debug and release. The probe writes only owned initialized host descriptors,
checks untouched neighbors and guest backing, and verifies x19-x28, LR/SP and
the first-fault capture across simulated unwind depths. Keep the adopted paths
unmodified until these primitives are qualified. A later wiring change needs
complete nested/fault/limit fixtures and all broader workspace and real-edit
qualification described in the contract.

Use the existing shared target with two Cargo workers, 45-second shared-lock
admission, 16 GiB initial free disk and 8 GiB per child. Freeze exact sources and
retain all command results and setup times. No benchmark, subagent or AWS action
is part of this focused primitive qualification.

The next stage enables the extended tree ABI only in focused native fixtures.
A shared region partition excludes any function with a guarded ordinary body,
then propagates exclusion to all ancestors. No VM runtime option enables it.
Run four controls per profile, including the previous primitives, nested
success/fault materialization and transitive guarded-body exclusion. Nested
fixtures cover both profiling modes and persistent-register modes, failed
arguments, faults after completed children, arithmetic, assertion, trap and
memory failures, with independently specified active descriptors and ABI checks.

The wiring stage exposes only an explicit disabled `Limits.jit_tree_bridge`
option requiring resumable execution. The normal Call remains after stronger
bridge guards; prepared owners bind the option. Tree and ordinary counters have
separate arrays and exact ends; tree Calls exclude the outer bridge Call.
Run 17 controls per profile: four bridge primitives/nested cases, six full-VM
wiring controls and seven unchanged standalone-tree controls. The emitted
preflight is compared with the independent wide arithmetic contract. Full-VM
controls cover profiles, fresh prepared reuse, every short budget, code/depth/
working-memory limits, original alias/copy cases, nested faults and unavailable
cyclic/unsupported trees. No CLI/benchmark invocation is enabled by this stage.

Full qualification now includes the CLI and launcher flag, explicit forwarding
and option validation, a global quarter-arena tree quota, a full-adapter ABI/
prepared-bound probe and existing large-register cases with bridge both on/off.
Follow QUALIFICATION.md; the first full build expects 556 workspace controls
per profile. Earlier focused controllers retain their original stage counts
and must not be reused against later source as if unchanged.
